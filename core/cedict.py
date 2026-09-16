import re

ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+\[[^\]]*\]\s+/(.+)/\s*$")
QUOTED_PINYIN = re.compile(r"\s*\[[^\]]*\]")
MAX_SENSES = 4
MAX_LENGTH = 160

def parse_line(line):
    """Return (traditional, simplified, senses), or None for comments and junk."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    match = ENTRY.match(line)
    if match is None:
        return None

    traditional, simplified, body = match.groups()
    senses = [QUOTED_PINYIN.sub("", part).strip() for part in body.split("/")]
    senses = [sense for sense in senses if sense]
    if not senses:
        return None
    return traditional, simplified, senses

def condense(senses):
    """Join senses into one short gloss: 'tomorrow; the future'."""
    gloss = "; ".join(senses[:MAX_SENSES])
    if len(gloss) > MAX_LENGTH:
        gloss = gloss[:MAX_LENGTH].rstrip(" ;,") + "…"
    return gloss
