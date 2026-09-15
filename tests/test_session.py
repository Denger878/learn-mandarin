import pytest

from core import scheduler
from db import repo
from drill.session import Session


@pytest.fixture
def conn():
    conn = repo.connect(":memory:")
    repo.init_db(conn)
    import_id = repo.insert_import(conn, "s.txt", "dm", "hash", "2026-01-01T00:00:00")
    for hanzi, pinyin, times in (("明天", "míngtiān", 3), ("今天", "jīntiān", 1)):
        term_id = repo.get_or_create_term(conn, hanzi, pinyin)
        for _ in range(times):
            repo.insert_sighting(conn, term_id, import_id)
    conn.commit()
    yield conn
    conn.close()


def test_learn_serves_the_most_frequent_word_first(conn):
    assert Session(conn, scheduler.LEARN).next_card()["hanzi"] == "明天"

def test_answer_grades_toneless_typing(conn):
    session = Session(conn, scheduler.LEARN)
    correct, _ = session.answer(session.next_card(), "ming tian")
    assert correct is True

def test_answer_moves_on_to_the_next_card(conn):
    session = Session(conn, scheduler.LEARN)
    session.answer(session.next_card(), "mingtian")
    assert session.next_card()["hanzi"] == "今天"

def test_a_wrong_answer_is_persisted(conn):
    session = Session(conn, scheduler.LEARN)
    card = session.next_card()
    correct, changes = session.answer(card, "nihao")
    assert correct is False
    row = repo.get_term(conn, card["id"])
    assert (row["status"], row["streak"], row["wrong_streak"]) == ("learning", 0, 1)
    assert changes["status"] == "learning"

def test_five_correct_moves_the_word_into_the_known_bank(conn):
    session = Session(conn, scheduler.LEARN)
    card = session.next_card()
    for _ in range(5):
        session.answer(card, "mingtian")
        card = repo.get_term(conn, card["id"])
    assert card["status"] == "known"
    assert [r["hanzi"] for r in repo.review_queue(conn)] == ["明天"]
    assert [r["hanzi"] for r in repo.learn_queue(conn)] == ["今天"]

def test_three_wrong_in_review_sends_it_back_to_learning(conn):
    term_id = repo.get_term_by_hanzi(conn, "明天")
    repo.update_term_progress(conn, term_id, "known", 0, 0)
    conn.commit()

    session = Session(conn, scheduler.REVIEW)
    for _ in range(3):
        session.answer(repo.get_term(conn, term_id), "wrong")

    assert repo.get_term(conn, term_id)["status"] == "learning"
    assert repo.review_queue(conn) == []
    # Rank is derived from sightings, so the demoted word keeps its place.
    assert [r["hanzi"] for r in repo.learn_queue(conn)] == ["明天", "今天"]

def test_every_answer_is_logged(conn):
    session = Session(conn, scheduler.LEARN)
    card = session.next_card()
    session.answer(card, "mingtian")
    session.answer(card, "oops")
    rows = conn.execute("SELECT answer_given, correct FROM reviews ORDER BY id").fetchall()
    assert [(r["answer_given"], r["correct"]) for r in rows] == [("mingtian", 1), ("oops", 0)]

def test_mark_mastered_takes_a_word_out_of_circulation(conn):
    term_id = repo.get_term_by_hanzi(conn, "明天")
    repo.update_term_progress(conn, term_id, "known", 5, 0)
    conn.commit()

    Session(conn, scheduler.REVIEW).mark_mastered(term_id)
    assert repo.review_queue(conn) == []
    assert [r["hanzi"] for r in repo.learn_queue(conn)] == ["今天"]

def test_next_card_is_none_once_the_queue_is_on_cooldown(conn):
    session = Session(conn, scheduler.LEARN)
    session.answer(session.next_card(), "mingtian")
    session.answer(session.next_card(), "jintian")
    assert session.next_card() is None

def test_unknown_mode_is_rejected(conn):
    with pytest.raises(ValueError):
        Session(conn, "cram")
