from core.scheduler import (
    CORRECT_COOLDOWN,
    KNOWN,
    LEARN,
    LEARNING,
    NEW,
    REVIEW,
    WRONG_COOLDOWN,
    Scheduler,
    apply_answer,
)


def term(id, status=NEW, streak=0, wrong_streak=0):
    return {"id": id, "hanzi": "好", "pinyin": "hao",
            "status": status, "streak": streak, "wrong_streak": wrong_streak}


# --- selection -------------------------------------------------------------

def test_next_term_takes_the_highest_ranked():
    assert Scheduler().next_term([term(1), term(2)])["id"] == 1

def test_next_term_skips_a_term_on_cooldown():
    s = Scheduler()
    s.record_answer(1, correct=True)
    assert s.next_term([term(1), term(2)])["id"] == 2

def test_next_term_returns_none_when_everything_is_on_cooldown():
    s = Scheduler()
    s.record_answer(1, correct=True)
    assert s.next_term([term(1)]) is None

def test_next_term_on_empty_queue():
    assert Scheduler().next_term([]) is None

def test_wrong_answer_costs_fewer_cards_than_a_correct_one():
    s = Scheduler()
    s.record_answer(1, correct=False)
    s.record_answer(2, correct=True)
    assert s.cooldown_remaining(1) == WRONG_COOLDOWN - 1
    assert s.cooldown_remaining(2) == CORRECT_COOLDOWN

def test_cooldown_expires_after_enough_cards():
    s = Scheduler(wrong_cooldown=2, correct_cooldown=2)
    s.record_answer(1, correct=False)
    s.record_answer(2, correct=False)
    assert s.next_term([term(1), term(2), term(3)])["id"] == 3
    s.record_answer(3, correct=False)
    assert s.next_term([term(1), term(2), term(3)])["id"] == 1

def test_term_comes_back_round_and_can_be_answered_again():
    s = Scheduler(wrong_cooldown=1, correct_cooldown=1)
    s.record_answer(1, correct=False)
    s.record_answer(2, correct=False)
    s.record_answer(1, correct=True)
    assert s.cooldown_remaining(1) == 1
    assert s.cooldown_remaining(2) == 0

def test_clear_forgets_cooldowns():
    s = Scheduler()
    s.record_answer(1, correct=True)
    s.clear()
    assert s.next_term([term(1)])["id"] == 1


# --- transitions -----------------------------------------------------------

def test_correct_answer_zeroes_wrong_streak():
    assert apply_answer(term(1, LEARNING, streak=0, wrong_streak=2), True, LEARN) == {
        "status": LEARNING, "streak": 1, "wrong_streak": 0}

def test_wrong_answer_zeroes_streak():
    assert apply_answer(term(1, LEARNING, streak=3), False, LEARN) == {
        "status": LEARNING, "streak": 0, "wrong_streak": 1}

def test_first_attempt_moves_new_to_learning():
    assert apply_answer(term(1, NEW), True, LEARN)["status"] == LEARNING

def test_streak_of_five_promotes_to_known():
    after = apply_answer(term(1, LEARNING, streak=4), True, LEARN)
    assert after["status"] == KNOWN
    assert after["streak"] == 0
    assert after["wrong_streak"] == 0

def test_four_in_a_row_is_not_yet_known():
    assert apply_answer(term(1, LEARNING, streak=3), True, LEARN)["status"] == LEARNING

def test_three_wrong_in_review_demotes_to_learning():
    after = apply_answer(term(1, KNOWN, wrong_streak=2), False, REVIEW)
    assert after["status"] == LEARNING
    assert after["wrong_streak"] == 0

def test_two_wrong_in_review_stays_known():
    assert apply_answer(term(1, KNOWN, wrong_streak=1), False, REVIEW)["status"] == KNOWN

def test_a_correct_review_answer_breaks_the_wrong_streak():
    after = apply_answer(term(1, KNOWN, wrong_streak=2), True, REVIEW)
    assert after == {"status": KNOWN, "streak": 1, "wrong_streak": 0}

def test_apply_answer_does_not_mutate_the_term():
    t = term(1, LEARNING, streak=4)
    apply_answer(t, True, LEARN)
    assert t == term(1, LEARNING, streak=4)
