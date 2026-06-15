import engine

_CACHE = {}
_PRECISION = 2


def set_precision(p):
    global _PRECISION
    _PRECISION = p


def evaluate(op, a, b):
    """Evaluate via the engine in strict mode, with result caching."""
    key = (op, a, b)
    if key in _CACHE:
        return _CACHE[key]
    raw = engine.compute(op, a, b, mode="strict")
    result = round(raw, _PRECISION) if raw is not None else None
    _CACHE[key] = result
    return result
