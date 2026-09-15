import unicodedata

def normalize_pinyin(text):
    """Reduce pinyin to a canonical comparable form."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = ""
    for ch in decomposed:
        if unicodedata.combining(ch) == 0:
            stripped += ch
    return stripped.lower().replace(" ", "").replace("\t", "")


def is_correct(stored_pinyin, user_answer):
    """Compare a user's typed answer against the stored pinyin."""
    return normalize_pinyin(user_answer) == normalize_pinyin(stored_pinyin)
