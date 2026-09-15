PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS terms (
    id INTEGER PRIMARY KEY,
    hanzi TEXT NOT NULL UNIQUE,
    pinyin TEXT NOT NULL,
    meaning TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    streak INTEGER NOT NULL DEFAULT 0,
    due_at TEXT
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    source TEXT,
    content_hash TEXT NOT NULL UNIQUE,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sightings (
    id INTEGER PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES terms(id),
    import_id INTEGER NOT NULL REFERENCES imports(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES terms(id),
    reviewed_at TEXT NOT NULL,
    answer_given TEXT NOT NULL,
    correct INTEGER NOT NULL
);

CREATE INDEX idx_sightings_term ON sightings(term_id);
CREATE INDEX idx_reviews_term ON reviews(term_id);