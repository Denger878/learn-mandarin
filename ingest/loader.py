from db import repo
from core.segmenter import segment, to_pinyin
from pathlib import Path
import hashlib
from datetime import datetime, timezone

def content_hash(text):
    """SHA-256 of the text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ingest_text(conn, text, filename, source=None):
    """Import raw text. Returns sightings recorded, or 0 if already imported."""
    h = content_hash(text)
    timestamp = datetime.now(timezone.utc).isoformat()
    count = 0

    if repo.import_exists(conn, h):
        return 0
    import_id = repo.insert_import(conn, filename, source, h, timestamp)
    words = segment(text)
    for word in words:
        pinyin = to_pinyin(word)
        term_id = repo.get_or_create_term(conn, word, pinyin)
        repo.insert_sighting(conn, term_id, import_id)
        count += 1
    conn.commit()
    return count

