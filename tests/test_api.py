import pytest

from db import repo
from web.api import App


@pytest.fixture
def app():
    conn = repo.connect(":memory:")
    repo.init_db(conn)
    yield App(conn)
    conn.close()


TEXT = "今天天气很好。明天我要去学校。"


def test_import_records_sightings(app):
    result = app.import_text(TEXT, "dm")
    assert result["ok"] is True
    assert result["sightings"] > 0
    assert app.stats()["new"] > 0

def test_import_rejects_a_duplicate(app):
    app.import_text(TEXT, "dm")
    assert app.import_text(TEXT, "gc")["ok"] is False

def test_import_rejects_empty_text(app):
    assert app.import_text("   ", "dm")["ok"] is False

def test_import_rejects_text_with_no_chinese(app):
    assert app.import_text("hello there", "dm")["ok"] is False

def test_import_rejects_an_unknown_source(app):
    assert app.import_text(TEXT, "twitter")["ok"] is False

def test_other_source_is_stored_as_null(app):
    app.import_text(TEXT, "other")
    term_id = repo.get_term_by_hanzi(app.conn, "明天")
    assert repo.weighted_frequency(app.conn, term_id) == 1.0

def test_dm_source_is_weighted_double(app):
    app.import_text(TEXT, "dm")
    term_id = repo.get_term_by_hanzi(app.conn, "明天")
    assert repo.weighted_frequency(app.conn, term_id) == 2.0

def test_next_card_withholds_the_pinyin(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    assert "pinyin" not in card
    assert card["hanzi"]

def test_next_card_is_none_on_an_empty_pile(app):
    assert app.next_card("learn") == {"card": None, "remaining": 0}

def test_unknown_mode_is_rejected(app):
    with pytest.raises(ValueError):
        app.next_card("cram")

def test_a_correct_answer_reveals_the_pinyin(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    term = repo.get_term(app.conn, card["id"])
    result = app.answer("learn", card["id"], term["pinyin"])
    assert result["correct"] is True
    assert result["pinyin"] == term["pinyin"]

def test_a_wrong_answer_still_reveals_the_pinyin(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    result = app.answer("learn", card["id"], "zzz")
    assert result["correct"] is False
    assert result["pinyin"]

def test_answering_moves_to_a_different_card(app):
    app.import_text(TEXT, "dm")
    first = app.next_card("learn")["card"]
    app.answer("learn", first["id"], "zzz")
    assert app.next_card("learn")["card"]["id"] != first["id"]

def test_answer_rejects_an_unknown_term(app):
    assert app.answer("learn", 999, "hao")["ok"] is False

def test_five_correct_answers_promote_the_word(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    pinyin = repo.get_term(app.conn, card["id"])["pinyin"]
    for _ in range(4):
        assert app.answer("learn", card["id"], pinyin)["promoted"] is False
    result = app.answer("learn", card["id"], pinyin)
    assert result["promoted"] is True
    assert result["status"] == "known"
    assert app.next_card("review")["card"]["id"] == card["id"]

def test_three_wrong_reviews_demote_the_word(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    repo.update_term_progress(app.conn, card["id"], "known", 0, 0)
    app.conn.commit()
    for _ in range(2):
        assert app.answer("review", card["id"], "zzz")["demoted"] is False
    assert app.answer("review", card["id"], "zzz")["demoted"] is True
    assert app.stats()["known"] == 0

def test_meaning_can_be_filled_in_while_drilling(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    assert card["meaning"] is None
    app.set_meaning(card["id"], "  tomorrow  ")
    assert repo.get_term(app.conn, card["id"])["meaning"] == "tomorrow"

def test_blank_meaning_is_stored_as_nothing(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    app.set_meaning(card["id"], "   ")
    assert repo.get_term(app.conn, card["id"])["meaning"] is None

def test_only_known_words_can_be_mastered(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    assert app.master(card["id"])["ok"] is False

def test_mastering_takes_a_word_out_of_both_piles(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    repo.update_term_progress(app.conn, card["id"], "known", 0, 0)
    app.conn.commit()
    assert app.master(card["id"])["ok"] is True
    assert app.stats()["mastered"] == 1
    assert app.next_card("review")["card"] is None
    assert all(c["id"] != card["id"] for c in [app.next_card("learn")["card"]])

def test_stats_reports_every_status(app):
    assert app.stats() == {"new": 0, "learning": 0, "known": 0, "mastered": 0}

def test_cooldown_survives_between_requests(app):
    app.import_text(TEXT, "dm")
    card = app.next_card("learn")["card"]
    app.answer("learn", card["id"], "zzz")
    seen = []
    for _ in range(3):
        nxt = app.next_card("learn")["card"]
        if nxt is None:
            break
        seen.append(nxt["id"])
    assert card["id"] not in seen
