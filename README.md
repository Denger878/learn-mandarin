# learn-mandarin

A local Mandarin reading trainer. Ingests text I actually encounter through Wechat,
ranks words by how often I see them, and tests me on them through typing pinyin.

## Running it

First time only:

    pip install -r requirements.txt
    cd frontend && npm install && npm run build && cd ..
    python -m ingest.dictionary

Then, any time:

    python -m web.server

Open http://127.0.0.1:8000. Everything runs on this machine and writes to
`mandarin.db` in the working directory. Nothing is deployed and nothing leaves
the laptop.

### Changing the interface

The frontend is React, built by Vite into `web/dist`, which the Python server
serves. After editing anything in `frontend/src`, run `npm run build` again.

For hot reload while working on it, run the API and the Vite dev server side by
side and use the Vite URL:

    python -m web.server          # terminal 1, the API on :8000
    cd frontend && npm run dev    # terminal 2, the interface on :5173

## The three tabs

- **input text** — paste Chinese text and say where it came from (dm, gc,
  discovery, other). Every word in it is segmented and recorded as a sighting.
  The same text can't be imported twice.
- **learn new words** — drills words you haven't learned yet, most frequent
  first. Type the pinyin without tones. Five correct in a row moves a word to
  your known pile. The English comes from the dictionary; type your own over it
  and yours is what shows from then on.
- **review known words** — drills the words you already know. Three wrong in a
  row sends one back to learning. A word can be marked mastered to retire it.

## Layout

    core/      pure logic: segmenting, pinyin comparison, the scheduler, CEDICT parsing
    db/        every line of SQL in the project
    ingest/    turning pasted text into sightings
    web/       the JSON API (api.py) and the local HTTP server (server.py)
    frontend/  React interface (Vite); builds into web/dist
    tests/     pytest

## The English definitions

`python -m ingest.dictionary` downloads CC-CEDICT once into `data/` and loads it
into the `definitions` table. That is the only time anything is fetched: the
meaning on a card comes from a local join, not a lookup service. Run it again
whenever you want a newer dictionary; it replaces what's there and leaves your
words, counters and typed-in meanings alone.

Definitions are never copied onto your words. `terms.meaning` holds only what
you typed yourself, and the queries fall back to the dictionary, so your own
wording always wins and a dictionary update never overwrites it.

CC-CEDICT is community maintained, published by [MDBG](https://www.mdbg.net/chinese/dictionary?page=cc-cedict)
under the [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
licence.
