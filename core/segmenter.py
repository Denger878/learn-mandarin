import jieba
from pypinyin import lazy_pinyin, Style

def to_pinyin(hanzi):
    """Convert hanzi to toneless pinyin with no spaces."""
    syllables = lazy_pinyin(hanzi, style=Style.NORMAL)
    pinyin = ""
    for syllable in syllables:
        pinyin += syllable
    return pinyin

def is_chinese(ch):
    return "\u4e00" <= ch <= "\u9fff"

def all_chinese(word):
    for ch in word:
        if not is_chinese(ch):
            return False
    return True

def segment(text):
    """Split text into Chinese words, dropping anything that isn't Chinese."""
    words = []
    for word in jieba.cut(text):
        if all_chinese(word):
            words.append(word)
    return words


