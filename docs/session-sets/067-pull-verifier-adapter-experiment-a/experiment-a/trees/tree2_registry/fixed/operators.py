"""The operator catalogue. Each operator has a unique `name` and `symbol`."""


class Operator:
    def __init__(self, name, symbol, arity, func):
        self.name = name
        self.symbol = symbol
        self.arity = arity
        self.func = func


OPERATORS = [
    Operator("add", "+", 2, lambda a, b: a + b),
    Operator("minus", "-", 2, lambda a, b: a - b),
    Operator("times", "*", 2, lambda a, b: a * b),
    Operator("divide", "/", 2, lambda a, b: a / b),
    Operator("neg", "_", 1, lambda a: -a),
]
