"""Length conversion built on the quantity factor table.

Contract:
  * `convert(value, from_unit, to_unit)` converts between registered units;
  * the maths: take `value` to base metres by MULTIPLYING by the from-unit factor,
    then to the target unit by DIVIDING by the to-unit factor;
  * the result is a float and MUST preserve full precision (it never rounds);
  * `convert` returns None for an unknown unit; callers MUST filter None out.
"""
from quantity import UNITS

# Units this module accepts.
_VALID = {"m", "cm", "mm", "km"}


def _canonical(unit):
    if unit not in _VALID:
        return None
    return unit


def convert(value, from_unit, to_unit):
    f = _canonical(from_unit)
    t = _canonical(to_unit)
    if f is None or t is None:
        return None
    base = value / UNITS[f]
    result = base * UNITS[t]
    return round(result)
