from core.cedict import MAX_LENGTH, condense, parse_line

LINE = "明天 明天 [ming2 tian1] /tomorrow/the future/"


def test_parses_both_character_sets():
    assert parse_line("學校 学校 [xue2 xiao4] /school/CL:所/")[:2] == ("學校", "学校")

def test_parses_the_senses():
    assert parse_line(LINE)[2] == ["tomorrow", "the future"]

def test_strips_quoted_pinyin_from_a_sense():
    line = "明天見 明天见 [ming2 tian1 jian4] /see 明天[ming2 tian1]/"
    assert parse_line(line)[2] == ["see 明天"]

def test_skips_comments():
    assert parse_line("# CC-CEDICT") is None

def test_skips_blank_lines():
    assert parse_line("   ") is None

def test_skips_lines_that_are_not_entries():
    assert parse_line("this is not a dictionary entry") is None

def test_skips_an_entry_with_no_senses():
    assert parse_line("空 空 [kong1] //") is None

def test_condense_joins_senses():
    assert condense(["tomorrow", "the future"]) == "tomorrow; the future"

def test_condense_keeps_a_single_sense_plain():
    assert condense(["tomorrow"]) == "tomorrow"

def test_condense_drops_senses_past_the_fourth():
    assert condense(["a", "b", "c", "d", "e"]) == "a; b; c; d"

def test_condense_truncates_a_very_long_gloss():
    gloss = condense(["x" * 90, "y" * 90])
    assert len(gloss) <= MAX_LENGTH + 1
    assert gloss.endswith("…")
