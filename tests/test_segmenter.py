from core.segmenter import to_pinyin, is_chinese, all_chinese, segment

def test_to_pinyin_multi_character():
    assert to_pinyin("明天") == "mingtian"
def test_to_pinyin_single_character():
    assert to_pinyin("好") == "hao"

def test_is_chinese_true():
    assert is_chinese("好") is True
def test_is_chinese_false_for_latin():
    assert is_chinese("a") is False

def test_all_chinese_rejects_mixed():
    assert all_chinese("天气ok") is False

def test_segment_finds_words():
    assert segment("今天天气很好") == ["今天天气", "很", "好"]
def test_segment_drops_latin_and_digits():
    assert segment("今天3pm很好") == ["今天", "很", "好"]
def test_segment_drops_punctuation():
    assert segment("你好，世界！") == ["你好", "世界"]
def test_segment_empty_string():
    assert segment("") == []
def test_segment_no_chinese():
    assert segment("max is awesome") == []