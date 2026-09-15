"""Drives one drill session: pulls ranked terms, grades typed pinyin, writes back.

This is the layer that joins the pure scheduler to the database. It owns the
transaction: one commit per answered card.
"""

from datetime import datetime, timezone

from core import scheduler
from core.normalize import is_correct
from db import repo


class Session:
    def __init__(self, conn, mode, limit=None):
        if mode not in (scheduler.LEARN, scheduler.REVIEW):
            raise ValueError(f"unknown mode: {mode}")
        self.conn = conn
        self.mode = mode
        self.limit = limit
        self.scheduler = scheduler.Scheduler()

    def queue(self):
        """The current ranked queue for this mode, straight from the database."""
        if self.mode == scheduler.LEARN:
            return repo.learn_queue(self.conn, self.limit)
        return repo.review_queue(self.conn, self.limit)

    def next_card(self):
        """The next term to show, or None if everything is on cooldown."""
        return self.scheduler.next_term(self.queue())

    def answer(self, term, answer_given):
        """Grade one answer, persist it, and put the term on cooldown.

        Returns (correct, changes) where changes is the term's new status and
        counters.
        """
        correct = is_correct(term["pinyin"], answer_given)
        changes = scheduler.apply_answer(term, correct, self.mode)
        now = datetime.now(timezone.utc).isoformat()

        repo.insert_review(self.conn, term["id"], now, answer_given, correct)
        repo.update_term_progress(
            self.conn,
            term["id"],
            changes["status"],
            changes["streak"],
            changes["wrong_streak"],
        )
        self.conn.commit()

        self.scheduler.record_answer(term["id"], correct)
        return correct, changes

    def mark_mastered(self, term_id):
        """Retire a known term for good."""
        repo.mark_mastered(self.conn, term_id)
        self.conn.commit()
