"""A local-only HTTP server for the trainer. Nothing is deployed anywhere.

Single threaded on purpose: one person drilling in one browser, one SQLite
connection, no locking to think about.
"""

import json
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from db import repo
from web.api import App

DIST = Path(__file__).parent / "dist"

CONTENT_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".map": "application/json",
}

NOT_BUILT_PAGE = b"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>learn mandarin</title></head>
<body style="font:16px system-ui;max-width:32rem;margin:15vh auto;padding:0 1rem">
<h1 style="font-size:1.1rem">The interface hasn't been built yet.</h1>
<p>Run this once, then reload:</p>
<pre style="background:#f4f4f4;padding:1rem;border-radius:8px">cd frontend
npm install
npm run build</pre>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, app=None, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            return self._route(self._get_api, path)
        self._send_static(path.lstrip("/") or "index.html")

    def do_POST(self):
        body = self._read_json()
        if body is None:
            return self._send_error(400, "Bad JSON")
        self._route(self._post_api, self.path.split("?")[0], body)

    def _get_api(self, path):
        if path == "/api/stats":
            return self.app.stats()
        if path == "/api/next":
            return self.app.next_card(self._query("mode", "learn"))
        return None

    def _post_api(self, path, body):
        if path == "/api/import":
            return self.app.import_text(body.get("text"), body.get("source"))
        if path == "/api/answer":
            return self.app.answer(body.get("mode"), body.get("term_id"), body.get("guess"))
        if path == "/api/meaning":
            return self.app.set_meaning(body.get("term_id"), body.get("meaning"))
        if path == "/api/master":
            return self.app.master(body.get("term_id"))
        return None

    def _route(self, handler, *args):
        """Run one API handler. A bad argument is the caller's fault, not a crash."""
        try:
            payload = handler(*args)
        except ValueError as exc:
            return self._send_error(400, str(exc))
        if payload is None:
            return self._send_error(404, "Not found")
        self._send_json(payload)

    def log_message(self, fmt, *args):
        pass  # the terminal stays quiet; the browser is the interface

    # --- plumbing -----------------------------------------------------------

    def _query(self, key, default=None):
        if "?" not in self.path:
            return default
        for pair in self.path.split("?", 1)[1].split("&"):
            name, _, value = pair.partition("=")
            if name == key:
                return value
        return default

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _send_static(self, name):
        """Serve a file out of the Vite build."""
        root = DIST.resolve()
        if not (root / "index.html").is_file():
            return self._respond(503, "text/html; charset=utf-8", NOT_BUILT_PAGE)

        target = (root / name).resolve()
        if not target.is_file() or root not in target.parents:
            return self._send_error(404, "Not found")

        content_type = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        self._respond(200, f"{content_type}; charset=utf-8", target.read_bytes())

    def _send_json(self, payload, status=200):
        self._respond(status, "application/json; charset=utf-8",
                      json.dumps(payload).encode("utf-8"))

    def _send_error(self, status, message):
        self._send_json({"ok": False, "message": message}, status)

    def _respond(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(db_path="mandarin.db", host="127.0.0.1", port=8000):
    """Wire up a database, the app and an HTTP server.

    The connection is opened here so that it belongs to whichever thread ends
    up serving requests; SQLite connections can't be shared across threads.
    """
    conn = repo.connect(db_path)
    repo.init_db(conn)
    return HTTPServer((host, port), partial(Handler, app=App(conn)))


def serve(db_path="mandarin.db", host="127.0.0.1", port=8000):
    server = create_server(db_path, host, port)
    host, port = server.server_address[:2]
    print(f"learn-mandarin running at http://{host}:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
