# registry

Builds a lookup table over the operator catalogue (`operators.py`).

## Contract

- The registry indexes EVERY operator in `OPERATORS`; `len(registry) ==
  len(OPERATORS)`. Operator names are unique, so none is dropped.
- `precedence(symbol)` returns the binding precedence for an operator SYMBOL.
- `lookup(name)` returns the `Operator` with that name, or raises `KeyError`
  for an unknown name - it never substitutes a different operator.
- `is_binary(op)` is True only for two-operand (arity 2) operators.
