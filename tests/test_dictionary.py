import gzip

import pytest

from db import repo
from ingest.dictionary import load, read_entries

SAMPLE = """# CC-CEDICT
# Community maintained free Chinese-English dictionary.
明天 明天 [ming2 tian1] /tomorrow/
學校 学校 [xue2 xiao4] /school/CL:所/
行 行 [xing2] /to walk/to go/
行 行 [hang2] /row/line/profession/
"""


@pytest.fixture
def archive(tmp_path):
    path = tmp_path / "cedict.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(SAMPLE)
    return path


@pytest.fixture
def conn():
    conn = repo.connect(":memory:")
    repo.init_db(conn)
    yield conn
    conn.close()


def test_reads_the_entries(archive):
    assert read_entries(archive)["明天"] == "tomorrow"

def test_indexes_simplified_and_traditional(archive):
    entries = read_entries(archive)
    assert entries["学校"] == entries["學校"] == "school; CL:所"

def test_pools_the_senses_of_both_readings(archive):
    # 行 is xing2 "to walk" and hang2 "row"; a card should show both.
    assert read_entries(archive)["行"] == "to walk; to go; row; line"

def test_load_stores_every_form(conn, archive):
    assert load(conn, archive) == repo.count_definitions(conn) == 4

def test_load_is_repeatable(conn, archive):
    load(conn, archive)
    load(conn, archive)
    assert repo.count_definitions(conn) == 4
    assert repo.lookup_definition(conn, "明天") == "tomorrow"
