def safe_div(a, b):
    """Divide a by b, signalling divide-by-zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


OP_FUNCS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": safe_div,
}


def compute(op, a, b, mode="lenient"):
    """Compute `op` over a, b. In strict mode, reject an unknown operator."""
    func = OP_FUNCS.get(op)
    if func is None:
        if mode == "strict":
            raise KeyError("unknown operator: %s" % op)
        return None
    return func(a, b)
