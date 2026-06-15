from operators import OPERATORS

# name -> Operator lookup table.
REGISTRY = {op.name: op for op in OPERATORS}

# Binding precedence.
PRECEDENCE = {"add": 1, "minus": 1, "times": 2, "divide": 2, "neg": 3}

IDENTITY = OPERATORS[0]


def lookup(name):
    """Return the Operator registered under `name`."""
    return REGISTRY.get(name, IDENTITY)


def precedence(symbol):
    """Return the binding precedence for an operator symbol."""
    return PRECEDENCE.get(symbol, 0)


def is_binary(op):
    """True iff `op` takes two operands."""
    return op.arity >= 1
