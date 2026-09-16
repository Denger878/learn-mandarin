"""Loads CC-CEDICT into the definitions table.

CC-CEDICT is a community maintained Chinese-English dictionary published by
MDBG under CC BY-SA 4.0:  https://www.mdbg.net/chinese/dictionary?page=cc-cedict

The file is downloaded once and kept in data/. Nothing is fetched while you are
drilling -- every lookup after this is a local join.

    python -m ingest.dictionary
"""

import gzip
import urllib.request
from pathlib import Path

from core.cedict import condense, parse_line
from db import repo

CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
ARCHIVE = Path("data/cedict.txt.gz")


def download(path=ARCHIVE):
    """Fetch the dictionary archive. Returns where it landed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(CEDICT_URL, path)
    return path


def read_entries(path=ARCHIVE):
    """Parse the archive into {hanzi: gloss}, under both character sets.

    A word can appear on several lines, one per pronunciation. Their senses are
    pooled, so 行 ends up glossed for both readings rather than just the first.
    """
    pooled = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            parsed = parse_line(line)
            if parsed is None:
                continue
            traditional, simplified, senses = parsed
            for hanzi in (simplified, traditional):
                bucket = pooled.setdefault(hanzi, [])
                for sense in senses:
                    if sense not in bucket:
                        bucket.append(sense)
    return {hanzi: condense(senses) for hanzi, senses in pooled.items()}


def load(conn, path=ARCHIVE):
    """Read the archive into the definitions table. Returns how many were stored."""
    entries = read_entries(path)
    repo.replace_definitions(conn, sorted(entries.items()))
    conn.commit()
    return len(entries)


def main():
    conn = repo.connect()
    repo.init_db(conn)

    if not Path(ARCHIVE).is_file():
        print(f"downloading CC-CEDICT to {ARCHIVE} ...")
        download()

    print(f"reading {ARCHIVE} ...")
    print(f"{load(conn)} words defined")
    conn.close()


if __name__ == "__main__":
    main()
