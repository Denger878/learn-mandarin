import pytest

from db import repo


@pytest.fixture
def conn():
    conn = repo.connect(":memory:")
    repo.init_db(conn)
    yield conn
    conn.close()


def add(conn, hanzi, pinyin, source, times=1, status="new"):
    """Record a term seen `times` over in one import from `source`."""
    import_id = repo.insert_import(conn, f"{hanzi}-{source}.txt", source,
                                   f"hash-{hanzi}-{source}", "2026-01-01T00:00:00")
    term_id = repo.get_or_create_term(conn, hanzi, pinyin)
    for _ in range(times):
        repo.insert_sighting(conn, term_id, import_id)
    conn.execute("UPDATE terms SET status = ? WHERE id = ?", (status, term_id))
    conn.commit()
    return term_id


def test_dm_sightings_outrank_gc(conn):
    gc = add(conn, "明天", "mingtian", "gc", times=6)
    dm = add(conn, "今天", "jintian", "dm", times=2)
    assert [r["id"] for r in repo.learn_queue(conn)] == [dm, gc]

def test_gc_counts_half(conn):
    gc = add(conn, "明天", "mingtian", "gc", times=3)
    disc = add(conn, "今天", "jintian", "discovery", times=2)
    assert repo.weighted_frequency(conn, gc) == 1.5
    # fewer discovery sightings still outrank more gc ones
    assert [r["id"] for r in repo.learn_queue(conn)] == [disc, gc]

def test_discovery_counts_the_same_as_no_source(conn):
    disc = add(conn, "明天", "mingtian", "discovery", times=2)
    plain = add(conn, "今天", "jintian", None, times=2)
    assert repo.weighted_frequency(conn, disc) == repo.weighted_frequency(conn, plain) == 2.0

def test_equal_weight_falls_back_to_insertion_order(conn):
    first = add(conn, "明天", "mingtian", "discovery", times=1)   # 1 x 1.0
    second = add(conn, "今天", "jintian", "gc", times=2)          # 2 x 0.5
    assert repo.weighted_frequency(conn, first) == repo.weighted_frequency(conn, second)
    assert [r["id"] for r in repo.learn_queue(conn)] == [first, second]

def test_null_source_counts_as_one(conn):
    assert repo.weighted_frequency(conn, add(conn, "好", "hao", None, times=3)) == 3.0

def test_unknown_source_counts_as_one(conn):
    assert repo.weighted_frequency(conn, add(conn, "好", "hao", "wechat", times=2)) == 2.0

def test_learn_queue_excludes_known_and_mastered(conn):
    learning = add(conn, "明天", "mingtian", "dm", status="learning")
    add(conn, "今天", "jintian", "dm", status="known")
    add(conn, "好", "hao", "dm", status="mastered")
    assert [r["id"] for r in repo.learn_queue(conn)] == [learning]

def test_learn_queue_respects_limit(conn):
    add(conn, "明天", "mingtian", "dm", times=5)
    add(conn, "今天", "jintian", "dm", times=1)
    assert len(repo.learn_queue(conn, limit=1)) == 1

def test_deleting_an_import_self_corrects_the_ranking(conn):
    top = add(conn, "明天", "mingtian", "dm", times=5)
    other = add(conn, "今天", "jintian", "gc", times=2)
    assert repo.learn_queue(conn)[0]["id"] == top

    conn.execute("DELETE FROM sightings WHERE term_id = ?", (top,))
    conn.execute("DELETE FROM imports WHERE source = 'dm'")
    conn.commit()
    assert [r["id"] for r in repo.learn_queue(conn)] == [other]

def test_review_queue_holds_the_known_bank(conn):
    rare = add(conn, "明天", "mingtian", "gc", times=1, status="known")
    common = add(conn, "今天", "jintian", "gc", times=4, status="known")
    assert [r["id"] for r in repo.review_queue(conn)] == [common, rare]

def test_a_known_word_survives_losing_its_sightings(conn):
    term_id = add(conn, "明天", "mingtian", "dm", status="known")
    conn.execute("DELETE FROM sightings")
    conn.commit()
    assert [r["id"] for r in repo.review_queue(conn)] == [term_id]

def test_set_meaning(conn):
    term_id = add(conn, "明天", "mingtian", "dm")
    repo.set_meaning(conn, term_id, "tomorrow")
    conn.commit()
    assert repo.get_term(conn, term_id)["meaning"] == "tomorrow"

def test_review_queue_excludes_everything_but_known(conn):
    add(conn, "明天", "mingtian", "dm", status="learning")
    add(conn, "好", "hao", "dm", status="mastered")
    assert repo.review_queue(conn) == []

def test_a_term_with_no_sightings_is_not_in_the_learn_queue(conn):
    repo.insert_term(conn, "好", "hao")
    conn.commit()
    assert repo.learn_queue(conn) == []

def test_weighted_frequency_of_an_unseen_term_is_zero(conn):
    term_id = repo.insert_term(conn, "好", "hao")
    conn.commit()
    assert repo.weighted_frequency(conn, term_id) == 0.0

def test_mark_mastered_retires_the_term(conn):
    term_id = add(conn, "好", "hao", "dm", status="known")
    repo.mark_mastered(conn, term_id)
    conn.commit()
    assert repo.get_term(conn, term_id)["status"] == "mastered"
    assert repo.review_queue(conn) == []

def test_insert_review_logs_the_answer(conn):
    term_id = add(conn, "好", "hao", "dm")
    repo.insert_review(conn, term_id, "2026-01-01T00:00:00", "hau", False)
    conn.commit()
    row = conn.execute("SELECT answer_given, correct FROM reviews").fetchone()
    assert (row["answer_given"], row["correct"]) == ("hau", 0)

def test_count_by_status(conn):
    add(conn, "明天", "mingtian", "dm", status="learning")
    add(conn, "今天", "jintian", "dm", status="known")
    add(conn, "好", "hao", "dm", status="known")
    assert repo.count_by_status(conn) == {"learning": 1, "known": 2}

def test_get_or_create_term_keeps_the_meaning(conn):
    term_id = repo.get_or_create_term(conn, "好", "hao", "good")
    conn.commit()
    assert repo.get_term(conn, term_id)["meaning"] == "good"

def test_migrate_adds_wrong_streak_to_an_older_db(conn):
    conn.execute("DROP TABLE terms")
    conn.execute("""CREATE TABLE terms (
        id INTEGER PRIMARY KEY, hanzi TEXT NOT NULL UNIQUE, pinyin TEXT NOT NULL,
        meaning TEXT, status TEXT NOT NULL DEFAULT 'new',
        streak INTEGER NOT NULL DEFAULT 0, due_at TEXT)""")
    conn.execute("INSERT INTO terms (hanzi, pinyin) VALUES ('好', 'hao')")
    repo.migrate(conn)
    conn.commit()
    assert repo.get_term(conn, 1)["wrong_streak"] == 0


# --- dictionary ------------------------------------------------------------

def define(conn, *pairs):
    repo.replace_definitions(conn, pairs)
    conn.commit()

def test_a_term_picks_up_its_dictionary_meaning(conn):
    term_id = add(conn, "明天", "mingtian", "dm")
    define(conn, ("明天", "tomorrow"))
    assert repo.get_term(conn, term_id)["meaning"] == "tomorrow"
    assert repo.learn_queue(conn)[0]["meaning"] == "tomorrow"

def test_your_own_meaning_beats_the_dictionary(conn):
    term_id = add(conn, "明天", "mingtian", "dm")
    define(conn, ("明天", "tomorrow"))
    repo.set_meaning(conn, term_id, "the day after today")
    conn.commit()
    assert repo.get_term(conn, term_id)["meaning"] == "the day after today"

def test_an_undefined_term_has_no_meaning(conn):
    term_id = add(conn, "明天", "mingtian", "dm")
    define(conn, ("今天", "today"))
    assert repo.get_term(conn, term_id)["meaning"] is None

def test_the_dictionary_reaches_the_review_pile(conn):
    add(conn, "明天", "mingtian", "dm", status="known")
    define(conn, ("明天", "tomorrow"))
    assert repo.review_queue(conn)[0]["meaning"] == "tomorrow"

def test_replacing_the_dictionary_drops_the_old_one(conn):
    define(conn, ("明天", "tomorrow"))
    define(conn, ("今天", "today"))
    assert repo.count_definitions(conn) == 1
    assert repo.lookup_definition(conn, "明天") is None
    assert repo.lookup_definition(conn, "今天") == "today"

def test_definitions_do_not_duplicate_queue_rows(conn):
    add(conn, "明天", "mingtian", "dm", times=3)
    define(conn, ("明天", "tomorrow"))
    assert len(repo.learn_queue(conn)) == 1
