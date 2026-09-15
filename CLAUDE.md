# learn-mandarin

Local Mandarin reading trainer. Segments text I paste in, ranks words by
weighted frequency, drills them by typing toneless pinyin.

## Architecture rules
- All SQL lives in db/repo.py. Nothing else imports sqlite3 or contains SQL.
- core/ modules are pure logic: no database, no I/O. Testable with fabricated data.
- Frequency is always derived from the sightings table, never stored as a counter.
- Transactions: repo functions don't commit; the caller does, once per logical operation.
- drill/session.py is the only place core/ and db/ meet. It pulls the ranked
  queue, grades the answer, writes it back, and commits once per card.

## Stack
Python 3.13, SQLite, jieba, pypinyin, pytest.

## Scheduler design

Terms have four statuses: new, learning, known, mastered.

Learn mode pulls terms with status new/learning, ranked by weighted frequency
computed from the sightings table joined to imports:
  dm = 2.0, gc = 1.0, discovery = 0.5, null = 1.0

Review mode pulls status = known, ranked the same way. There is no spaced
repetition and no due dates: the two modes are just two piles the user picks
between, one of words being learned and one of words already known.

Frequency is never stored. It is recomputed at query time so that known words
keep accumulating learning rank in the background, and so a bad import can be
deleted and the ranking self-corrects.

Two counters on terms: streak (consecutive correct) and wrong_streak
(consecutive wrong). A correct answer zeroes wrong_streak and vice versa.

Promotion: streak reaches 5 in learn mode -> known.
Demotion: wrong_streak reaches 3 in review mode -> back to learning,
keeping its frequency-derived rank.
Mastered: user can manually mark a known word as mastered; it is never shown again.

Instead of repositioning terms in a queue, the scheduler holds an in-memory
cooldown: term_id -> cards remaining. Wrong = 20 cards, correct = 60 cards.
next_term returns the highest-ranked term not on cooldown.

core/scheduler.py must not import sqlite3 or db.repo. It takes a list of terms
and returns one, so it can be tested with fabricated data.

A term moves new -> learning on its first attempt, so "new" means untouched.
Promotion and demotion reset both counters: a streak only counts runs within
the status the term is currently in.
