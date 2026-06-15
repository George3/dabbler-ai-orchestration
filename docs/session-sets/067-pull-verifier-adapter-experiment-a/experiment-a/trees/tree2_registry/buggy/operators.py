"""The operator catalogue. Each operator has a unique `name` and `symbol`."""


class Operator:
    def __init__(self, name, symbol, arity, func):
        self.name = name
        self.symbol = symbol
        self.arity = arity
        self.func = func


# NOTE: "neg" and "minus" are DISTINCT operators but were both given the name
# "minus" below - a duplicate name. (Seeded defect D5: a name collision.)
OPERATORS = [
    Operator("add", "+", 2, lambda a, b: a + b),
    Operator("minus", "-", 2, lambda a, b: a - b),
    Operator("times", "*", 2, lambda a, b: a * b),
    Operator("divide", "/", 2, lambda a, b: a / b),
    Operator("minus", "_", 1, lambda a: -a),
]
