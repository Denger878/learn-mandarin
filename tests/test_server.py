import json
import threading
import urllib.error
import urllib.request

import pytest

from web.server import create_server

TEXT = "今天天气很好。明天我要去学校。"


@pytest.fixture
def base_url(tmp_path):
    """Run the real server on a spare port, in its own thread."""
    ready = threading.Event()
    box = {}

    def run():
        server = create_server(str(tmp_path / "test.db"), "127.0.0.1", 0)
        box["server"] = server
        box["port"] = server.server_address[1]
        ready.set()
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert ready.wait(5), "server did not start"
    yield f"http://127.0.0.1:{box['port']}"
    box["server"].shutdown()
    box["server"].server_close()
    thread.join(5)


def get(url, path):
    with urllib.request.urlopen(url + path) as response:
        return response.status, response.read(), response.headers.get("Content-Type")

def get_json(url, path):
    return json.loads(get(url, path)[1])

def post_json(url, path, payload):
    request = urllib.request.Request(
        url + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def test_index_is_served(base_url):
    status, body, content_type = get(base_url, "/")
    assert status == 200
    assert b"learn mandarin" in body
    assert content_type.startswith("text/html")

def test_stylesheet_and_script_are_served(base_url):
    assert get(base_url, "/static/style.css")[2].startswith("text/css")
    assert get(base_url, "/static/app.js")[2].startswith("text/javascript")

def test_unknown_path_is_404(base_url):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(base_url, "/nope")
    assert caught.value.code == 404

def test_static_cannot_escape_its_directory(base_url):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(base_url, "/static/../server.py")
    assert caught.value.code == 404

def test_stats_start_empty(base_url):
    assert get_json(base_url, "/api/stats") == {
        "new": 0, "learning": 0, "known": 0, "mastered": 0}

def test_a_full_round_trip(base_url):
    imported = post_json(base_url, "/api/import", {"text": TEXT, "source": "dm"})
    assert imported["ok"] is True

    first = get_json(base_url, "/api/next?mode=learn")
    assert first["card"]["hanzi"]
    assert first["remaining"] > 0

    graded = post_json(base_url, "/api/answer", {
        "mode": "learn", "term_id": first["card"]["id"], "guess": "zzz"})
    assert graded["correct"] is False
    assert graded["pinyin"]

    saved = post_json(base_url, "/api/meaning", {
        "term_id": first["card"]["id"], "meaning": "today's weather"})
    assert saved["ok"] is True

    second = get_json(base_url, "/api/next?mode=learn")
    assert second["card"]["id"] != first["card"]["id"]

    assert get_json(base_url, "/api/stats")["learning"] == 1

def test_the_pile_is_remembered_between_requests(base_url):
    post_json(base_url, "/api/import", {"text": TEXT, "source": "dm"})
    first = get_json(base_url, "/api/next?mode=learn")["card"]
    post_json(base_url, "/api/answer",
              {"mode": "learn", "term_id": first["id"], "guess": "zzz"})
    for _ in range(3):
        card = get_json(base_url, "/api/next?mode=learn")["card"]
        assert card is None or card["id"] != first["id"]

def test_review_mode_starts_empty(base_url):
    post_json(base_url, "/api/import", {"text": TEXT, "source": "dm"})
    assert get_json(base_url, "/api/next?mode=review")["card"] is None

def test_a_bad_mode_is_rejected(base_url):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(base_url, "/api/next?mode=cram")
    assert caught.value.code == 400

def test_malformed_json_is_rejected(base_url):
    request = urllib.request.Request(
        base_url + "/api/import", data=b"{not json", method="POST",
        headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 400

def test_duplicate_import_is_refused(base_url):
    post_json(base_url, "/api/import", {"text": TEXT, "source": "dm"})
    again = post_json(base_url, "/api/import", {"text": TEXT, "source": "gc"})
    assert again["ok"] is False
