import sqlite3
from pathlib import Path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn):
    """Run schema.sql to create tables if needed."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def get_term_by_hanzi(conn, hanzi):
    """Return the term's id, or None if not found."""
    row = conn.execute("SELECT id FROM terms WHERE hanzi = ?", (hanzi,)).fetchone()
    return row[0] if row else None

def insert_term(conn, hanzi, pinyin):
    """Insert a new term, return its new id."""
    cur = conn.execute("INSERT INTO terms (hanzi, pinyin) VALUES (?, ?)", (hanzi, pinyin))
    id = cur.lastrowid
    return id

def get_or_create_term(conn, hanzi, pinyin):
    """Return existing id if the word is known, otherwise insert and return the new id."""
    existing = get_term_by_hanzi(conn, hanzi)
    if existing is not None:
        return existing
    else:
        return insert_term(conn, hanzi, pinyin)
    
def import_exists(conn, content_hash):
    """Return True if an import with this hash has already been recorded."""
    row = conn.execute("SELECT 1 FROM imports WHERE content_hash = ?", (content_hash,)).fetchone()
    return row is not None

def insert_import(conn, filename, source, content_hash, imported_at):
    """Insert an import record, return its new id."""
    cur = conn.execute("INSERT INTO imports (filename, source, content_hash, imported_at) VALUES (?, ?, ?, ?)", (filename, source, content_hash, imported_at))
    return cur.lastrowid

def insert_sighting(conn, term_id, import_id):
    """Insert a sighting row."""
    conn.execute("INSERT INTO sightings (term_id, import_id) VALUES (?, ?)", (term_id, import_id))
