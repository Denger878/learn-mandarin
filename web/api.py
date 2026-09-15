"""Everything the interface can do, as plain methods over plain dicts.

No HTTP here: web/server.py wraps this. This is also the only place core/ and
db/ meet -- it pulls the ranked pile, grades the answer, writes it back, and
commits once per card. Each mode keeps its own cooldown, which lives in memory
for as long as the app is running.
"""

from datetime import datetime, timezone

from core import scheduler
from core.normalize import is_correct
from db import repo
from ingest.loader import content_hash, ingest_text

SOURCES = ("dm", "gc", "discovery", "other")


class App:
    def __init__(self, conn):
        self.conn = conn
        self.cooldowns = {
            scheduler.LEARN: scheduler.Scheduler(),
            scheduler.REVIEW: scheduler.Scheduler(),
        }

    # --- tab 1: input text --------------------------------------------------

    def import_text(self, text, source, filename=None):
        """Segment pasted text and record a sighting for every word in it."""
        text = (text or "").strip()
        if not text:
            return {"ok": False, "message": "Nothing pasted."}
        if source not in SOURCES:
            return {"ok": False, "message": f"Unknown source: {source}"}
        if repo.import_exists(self.conn, content_hash(text)):
            return {"ok": False, "message": "Already imported this text."}

        # "other" is stored as no source at all, and counts as weight 1.0.
        stored_source = None if source == "other" else source
        filename = filename or "pasted"
        sightings = ingest_text(self.conn, text, filename, stored_source)
        if sightings == 0:
            return {"ok": False, "message": "No Chinese words found."}
        return {"ok": True, "message": f"Recorded {sightings} sightings.", "sightings": sightings}

    # --- tabs 2 and 3: drilling ---------------------------------------------

    def queue(self, mode):
        """The ranked pile for one mode, straight from the database."""
        if self._checked(mode) == scheduler.LEARN:
            return repo.learn_queue(self.conn)
        return repo.review_queue(self.conn)

    def next_card(self, mode):
        """The next word to show. Pinyin is withheld until the answer is graded."""
        queue = self.queue(mode)
        card = self.cooldowns[mode].next_term(queue)
        if card is None:
            return {"card": None, "remaining": len(queue)}
        return {
            "card": {
                "id": card["id"],
                "hanzi": card["hanzi"],
                "meaning": card["meaning"],
                "status": card["status"],
                "streak": card["streak"],
            },
            "remaining": len(queue),
        }

    def answer(self, mode, term_id, guess):
        """Grade a typed guess, save it, and report what it did to the word."""
        self._checked(mode)
        term = repo.get_term(self.conn, term_id)
        if term is None:
            return {"ok": False, "message": "No such word."}

        guess = guess or ""
        was = term["status"]
        correct = is_correct(term["pinyin"], guess)
        changes = scheduler.apply_answer(term, correct, mode)

        repo.insert_review(self.conn, term["id"],
                           datetime.now(timezone.utc).isoformat(), guess, correct)
        repo.update_term_progress(self.conn, term["id"], changes["status"],
                                  changes["streak"], changes["wrong_streak"])
        self.conn.commit()
        self.cooldowns[mode].record_answer(term["id"], correct)

        now = changes["status"]
        return {
            "ok": True,
            "correct": correct,
            "pinyin": term["pinyin"],
            "meaning": term["meaning"],
            "hanzi": term["hanzi"],
            "status": now,
            "streak": changes["streak"],
            "promoted": now == scheduler.KNOWN and was != scheduler.KNOWN,
            "demoted": was == scheduler.KNOWN and now != scheduler.KNOWN,
        }

    def set_meaning(self, term_id, meaning):
        """Fill in the English for a word while drilling it."""
        repo.set_meaning(self.conn, term_id, (meaning or "").strip() or None)
        self.conn.commit()
        return {"ok": True}

    def master(self, term_id):
        """Retire a known word so it never comes up again."""
        term = repo.get_term(self.conn, term_id)
        if term is None or term["status"] != scheduler.KNOWN:
            return {"ok": False, "message": "Only known words can be mastered."}
        repo.mark_mastered(self.conn, term_id)
        self.conn.commit()
        return {"ok": True, "message": f"{term['hanzi']} mastered."}

    def stats(self):
        """How many words sit in each status."""
        counts = repo.count_by_status(self.conn)
        return {status: counts.get(status, 0)
                for status in (scheduler.NEW, scheduler.LEARNING,
                               scheduler.KNOWN, scheduler.MASTERED)}

    def _checked(self, mode):
        if mode not in self.cooldowns:
            raise ValueError(f"unknown mode: {mode}")
        return mode
