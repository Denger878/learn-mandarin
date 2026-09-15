from core.normalize import normalize_pinyin, is_correct

def test_strips_tone_marks():
    assert normalize_pinyin("míngtiān") == "mingtian"
def test_lowercases():
    assert normalize_pinyin("MingTian") == "mingtian"
def test_removes_spaces():
    assert normalize_pinyin("ni hao") == "nihao"
def test_combined_mess():
    assert normalize_pinyin("  Nǐ  Hǎo  ") == "nihao"
def test_already_clean_is_unchanged():
    assert normalize_pinyin("mingtian") == "mingtian"

def test_correct_answer_with_spaces():
    assert is_correct("nihao", "ni hao") is True
def test_correct_answer_against_toned_storage():
    assert is_correct("nǐhǎo", "nihao") is True
def test_wrong_answer():
    assert is_correct("mingtian", "jintian") is False