# learn-mandarin

Local Mandarin reading trainer. Segments text I paste in, ranks words by
weighted frequency, drills them by typing toneless pinyin.

## Architecture rules
- All SQL lives in db/repo.py. Nothing else imports sqlite3 or contains SQL.
- core/ modules are pure logic: no database, no I/O. Testable with fabricated data.
- Frequency is always derived from the sightings table, never stored as a counter.
- English meanings are joined in from the definitions table at query time, never
  copied onto terms. terms.meaning holds only what the user typed; the queries
  COALESCE over the dictionary so a dictionary reload can't overwrite it.
- Transactions: repo functions don't commit; the caller does, once per logical operation.
- web/api.py is the only place core/ and db/ meet. It pulls the ranked pile,
  grades the answer, writes it back, and commits once per card.

## Stack
Python 3.13, SQLite, jieba, pypinyin, pytest. React + Vite for the interface,
served as a static build by the Python server.

## Scheduler design

Terms have four statuses: new, learning, known, mastered.

Learn mode pulls terms with status new/learning, ranked by weighted frequency
computed from the sightings table joined to imports:
  dm = 2.0, gc = 0.5, discovery = 1.0, null = 1.0

Review mode pulls status = known, ranked the same way. There is no spaced
repetition and no due dates: the two modes are just two piles the user picks
between, one of words being learned and one of words already known.

Frequency is never stored. It is recomputed at query time so that known words
keep accumulating learning rank in the background, and so a bad import can be
deleted and the ranking self-corrects.

Every ranking query sums over the whole sightings table, so a new import
re-ranks words from every past import too. A word first seen months ago rises
the moment it turns up again.

The ordering lives only in the result set of learn_queue/review_queue. The terms
table is never reordered or rewritten to express rank: an import only inserts
rows for words not seen before. Row order in terms is insertion order and means
nothing. The queue is a transient list, rebuilt by ORDER BY weight DESC on every
request and thrown away after it. That is why nothing needs re-sorting on import
and why deleting an import costs zero writes.

Two counters on terms: streak (consecutive correct) and wrong_streak
(consecutive wrong). A correct answer zeroes wrong_streak and vice versa.

Promotion: streak reaches 5 in learn mode -> known.
Demotion: wrong_streak reaches 3 in review mode -> back to learning,
keeping its frequency-derived rank.
Mastered: user can manually mark a known word as mastered; it is never shown again.

Instead of repositioning terms in a queue, the scheduler holds an in-memory
cooldown: term_id -> cards remaining. Wrong = 50 cards, correct = 100 cards.
next_term returns the highest-ranked term not on cooldown.

The cooldown is a plain dict on the Scheduler object, held by App.cooldowns and
built in web/server.py at startup. There is one per mode, so the two piles cool
independently. It never touches SQLite. record_answer puts a term on cooldown
after each answer, and the same call ages every other entry down by one, dropping
any that reach zero: a cooldown is spent by other cards being answered, not by
elapsed time. Stopping the server clears the lot, which is intended -- it is a
session-level "don't repeat yourself", not a schedule.

core/scheduler.py must not import sqlite3 or db.repo. It takes a list of terms
and returns one, so it can be tested with fabricated data.

A term moves new -> learning on its first attempt, so "new" means untouched.
Promotion and demotion reset both counters: a streak only counts runs within
the status the term is currently in.
