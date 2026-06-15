from operators import OPERATORS

# name -> Operator. (Built from OPERATORS; names are unique.)
REGISTRY = {op.name: op for op in OPERATORS}

# Binding precedence, keyed by operator SYMBOL.
PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "_": 3}

IDENTITY = OPERATORS[0]


def lookup(name):
    """Return the Operator registered under `name`."""
    return REGISTRY[name]


def precedence(symbol):
    """Return the binding precedence for an operator symbol."""
    return PRECEDENCE.get(symbol, 0)


def is_binary(op):
    """True iff `op` takes two operands."""
    return op.arity == 2
