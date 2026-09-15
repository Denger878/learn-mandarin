# learn-mandarin

A local Mandarin reading trainer. Ingests text I actually encounter through Wechat,
ranks words by how often I see them, and tests me on them through typing pinyin.

## Running it

    pip install -r requirements.txt
    python -m web.server

Then open http://127.0.0.1:8000. Everything runs on this machine and writes to
`mandarin.db` in the working directory. Nothing is deployed and nothing leaves
the laptop.

## The three tabs

- **input text** — paste Chinese text and say where it came from (dm, gc,
  discovery, other). Every word in it is segmented and recorded as a sighting.
  The same text can't be imported twice.
- **learn new words** — drills words you haven't learned yet, most frequent
  first. Type the pinyin without tones. Five correct in a row moves a word to
  your known pile.
- **review known words** — drills the words you already know. Three wrong in a
  row sends one back to learning. A word can be marked mastered to retire it.

## Layout

    core/     pure logic: segmenting, pinyin comparison, the scheduler
    db/       every line of SQL in the project
    ingest/   turning pasted text into sightings
    drill/    joins the scheduler to the database, owns the transaction
    web/      local HTTP server and the browser interface
    tests/    pytest
