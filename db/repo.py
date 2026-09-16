import sqlite3
from pathlib import Path
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Weighted frequency: how much one sighting counts for, by the source of the
# import it came from. An unrecognised or missing source counts as 1.0.
SOURCE_WEIGHT_SQL = """
    CASE i.source
        WHEN 'dm' THEN 2.0
        WHEN 'gc' THEN 1.0
        WHEN 'discovery' THEN 0.5
        ELSE 1.0
    END
"""

# A term's meaning is whatever you typed in, falling back to the dictionary.
TERM_COLUMNS = ("t.id, t.hanzi, t.pinyin, COALESCE(t.meaning, d.meaning) AS meaning, "
                "t.status, t.streak, t.wrong_streak")

DEFINITION_JOIN = "LEFT JOIN definitions d ON d.hanzi = t.hanzi"


def connect(db_path="mandarin.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn):
    """Run schema.sql to create tables if needed, then bring older dbs forward."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    migrate(conn)
    conn.commit()
    return

def migrate(conn):
    """Add columns that schema.sql can't add to an already-created table."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(terms)")}
    if "wrong_streak" not in columns:
        conn.execute("ALTER TABLE terms ADD COLUMN wrong_streak INTEGER NOT NULL DEFAULT 0")

def get_term_by_hanzi(conn, hanzi):
    """Return the term's id, or None if not found."""
    row = conn.execute("SELECT id FROM terms WHERE hanzi = ?", (hanzi,)).fetchone()
    return row[0] if row else None

def insert_term(conn, hanzi, pinyin, meaning=None):
    """Insert a new term, return its new id."""
    cur = conn.execute("INSERT INTO terms (hanzi, pinyin, meaning) VALUES (?, ?, ?)", (hanzi, pinyin, meaning))
    id = cur.lastrowid
    return id

def get_or_create_term(conn, hanzi, pinyin, meaning=None):
    """Return existing id if the word is known, otherwise insert and return the new id."""
    existing = get_term_by_hanzi(conn, hanzi)
    if existing is not None:
        return existing
    else:
        return insert_term(conn, hanzi, pinyin, meaning)
    
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


def learn_queue(conn, limit=None):
    """Terms with status new/learning, highest weighted frequency first.

    Frequency is recomputed here from sightings every time, never read off a
    stored counter, so deleting a bad import self-corrects the ranking. A term
    with no sightings left has not been seen and drops out of the backlog.
    """
    rows = conn.execute(f"""
        SELECT {TERM_COLUMNS}, SUM({SOURCE_WEIGHT_SQL}) AS weight
        FROM terms t
        JOIN sightings s ON s.term_id = t.id
        JOIN imports i ON i.id = s.import_id
        {DEFINITION_JOIN}
        WHERE t.status IN ('new', 'learning')
        GROUP BY t.id
        ORDER BY weight DESC, t.id ASC
        {"LIMIT ?" if limit is not None else ""}
    """, (limit,) if limit is not None else ()).fetchall()
    return rows

def review_queue(conn, limit=None):
    """Terms with status known, highest weighted frequency first.

    Left joined, unlike the learn queue: a word you already know stays in the
    bank even if the import that introduced it is deleted.
    """
    rows = conn.execute(f"""
        SELECT {TERM_COLUMNS}, COALESCE(SUM({SOURCE_WEIGHT_SQL}), 0) AS weight
        FROM terms t
        LEFT JOIN sightings s ON s.term_id = t.id
        LEFT JOIN imports i ON i.id = s.import_id
        {DEFINITION_JOIN}
        WHERE t.status = 'known'
        GROUP BY t.id
        ORDER BY weight DESC, t.id ASC
        {"LIMIT ?" if limit is not None else ""}
    """, (limit,) if limit is not None else ()).fetchall()
    return rows

def get_term(conn, term_id):
    """Return the full term row, or None if there is no such term."""
    return conn.execute(
        f"SELECT {TERM_COLUMNS} FROM terms t {DEFINITION_JOIN} WHERE t.id = ?", (term_id,)
    ).fetchone()

def weighted_frequency(conn, term_id):
    """The weighted sighting count behind a term's rank."""
    row = conn.execute(f"""
        SELECT SUM({SOURCE_WEIGHT_SQL}) AS weight
        FROM sightings s
        JOIN imports i ON i.id = s.import_id
        WHERE s.term_id = ?
    """, (term_id,)).fetchone()
    return row[0] or 0.0

def update_term_progress(conn, term_id, status, streak, wrong_streak):
    """Write back the counters and status the scheduler worked out."""
    conn.execute(
        "UPDATE terms SET status = ?, streak = ?, wrong_streak = ? WHERE id = ?",
        (status, streak, wrong_streak, term_id),
    )

def mark_mastered(conn, term_id):
    """Retire a known term. Mastered terms are never shown again."""
    conn.execute("UPDATE terms SET status = 'mastered' WHERE id = ?", (term_id,))

def set_meaning(conn, term_id, meaning):
    """Save the English meaning typed in while drilling."""
    conn.execute("UPDATE terms SET meaning = ? WHERE id = ?", (meaning, term_id))

def insert_review(conn, term_id, reviewed_at, answer_given, correct):
    """Log one answered card, return its new id."""
    cur = conn.execute(
        "INSERT INTO reviews (term_id, reviewed_at, answer_given, correct) VALUES (?, ?, ?, ?)",
        (term_id, reviewed_at, answer_given, 1 if correct else 0),
    )
    return cur.lastrowid

def count_by_status(conn):
    """How many terms sit in each status, as a dict."""
    rows = conn.execute("SELECT status, COUNT(*) FROM terms GROUP BY status").fetchall()
    return {row[0]: row[1] for row in rows}

def replace_definitions(conn, entries):
    """Swap in a freshly parsed dictionary. `entries` is (hanzi, meaning) pairs."""
    conn.execute("DELETE FROM definitions")
    conn.executemany("INSERT INTO definitions (hanzi, meaning) VALUES (?, ?)", entries)

def count_definitions(conn):
    """How many words the dictionary knows."""
    return conn.execute("SELECT COUNT(*) FROM definitions").fetchone()[0]

def lookup_definition(conn, hanzi):
    """The dictionary gloss for one word, or None if it isn't in there."""
    row = conn.execute("SELECT meaning FROM definitions WHERE hanzi = ?", (hanzi,)).fetchone()
    return row[0] if row else None
