# engine

Evaluates a parsed `(op, a, b)` triple.

## Contract

- `safe_div(a, b)` must signal divide-by-zero (raise), never return a wrong
  numeric answer that downstream code treats as a real result.
- `compute(op, a, b, mode="lenient")` in STRICT mode must REJECT an unknown
  operator (raise); lenient mode may pass it through.
- `evaluate(...)` caches results; the cache must not return a value computed
  under a different `precision` setting.
