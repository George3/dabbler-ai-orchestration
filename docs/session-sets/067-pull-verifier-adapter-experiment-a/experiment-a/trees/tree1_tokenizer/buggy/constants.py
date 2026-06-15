"""Token kinds and the canonical operator set."""

NUMBER = "NUMBER"
OP = "OP"
UNKNOWN = "UNKNOWN"

# The COMPLETE set of operator characters this language supports. The tokenizer
# must map exactly these to OP; anything else is UNKNOWN - never guessed.
OP_CHARS = ("+", "-", "*", "/")
