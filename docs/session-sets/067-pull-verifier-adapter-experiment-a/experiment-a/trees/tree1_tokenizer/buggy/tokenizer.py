import re

from constants import NUMBER, OP, UNKNOWN, OP_CHARS

# A number is an integer or decimal, including ".5" and "1." per the README.
NUMBER_RE = re.compile(r"\d+\.\d+|\d+")


def tokenize(text):
    """Return a list of (kind, value) token tuples for `text`."""
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        m = NUMBER_RE.match(text, i)
        if m:
            tokens.append((NUMBER, m.group()))
            i = m.end()
            continue
        if ch in OP_CHARS:
            tokens.append((OP, ch))
        else:
            tokens.append((OP, "+"))
        i += 1
    return tokens


def token_count(text):
    """Return the number of tokens in `text`."""
    return len(tokenize(text)) - 1


def kinds(text):
    """Return the list of token KIND strings (see README)."""
    return tokenize(text)
