NEW = "new"
LEARNING = "learning"
KNOWN = "known"
MASTERED = "mastered"

LEARN = "learn"
REVIEW = "review"

PROMOTION_STREAK = 5
DEMOTION_WRONG_STREAK = 3

WRONG_COOLDOWN = 50
CORRECT_COOLDOWN = 100


class Scheduler:
    """Serves terms from a ranked list, skipping anything still on cooldown.

    Terms are never repositioned in a queue. The caller re-reads the ranked
    list as often as it likes; this object only remembers how many more cards
    must go by before each recently answered term may come round again.
    """

    def __init__(self, wrong_cooldown=WRONG_COOLDOWN, correct_cooldown=CORRECT_COOLDOWN):
        self.wrong_cooldown = wrong_cooldown
        self.correct_cooldown = correct_cooldown
        self.cooldowns = {}

    def next_term(self, terms):
        """Return the highest-ranked term not on cooldown, or None.

        `terms` is expected to already be in the order the mode wants them.
        """
        for term in terms:
            if self.cooldowns.get(term["id"], 0) <= 0:
                return term
        return None

    def record_answer(self, term_id, correct):
        """Consume one card: age every cooldown, then park the answered term."""
        for other_id in list(self.cooldowns):
            self.cooldowns[other_id] -= 1
            if self.cooldowns[other_id] <= 0:
                del self.cooldowns[other_id]
        self.cooldowns[term_id] = self.correct_cooldown if correct else self.wrong_cooldown

    def cooldown_remaining(self, term_id):
        """Cards left before this term may be served again. 0 means available."""
        return self.cooldowns.get(term_id, 0)

    def clear(self):
        """Forget all cooldowns. Called when a session ends."""
        self.cooldowns.clear()


def apply_answer(term, correct, mode):
    """Return the term's counters and status after one answer.

    Result is a dict of the fields that changed on the term: status, streak,
    wrong_streak. Promotion and demotion reset both counters, since they only
    count runs within the status the term is currently in.
    """
    status = term["status"]
    streak = term["streak"]
    wrong_streak = term["wrong_streak"]

    if correct:
        streak += 1
        wrong_streak = 0
    else:
        wrong_streak += 1
        streak = 0

    if mode == LEARN:
        # Any attempt moves an untouched word out of the backlog.
        if status == NEW:
            status = LEARNING
        if status == LEARNING and streak >= PROMOTION_STREAK:
            status = KNOWN
            streak = 0
            wrong_streak = 0
    elif mode == REVIEW:
        if status == KNOWN and wrong_streak >= DEMOTION_WRONG_STREAK:
            # Back to learning. Rank is derived from sightings, so it is kept
            # automatically and nothing needs to be carried over here.
            status = LEARNING
            streak = 0
            wrong_streak = 0

    return {"status": status, "streak": streak, "wrong_streak": wrong_streak}
