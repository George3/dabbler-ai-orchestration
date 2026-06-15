"""Core length quantities and the unit factor table.

A unit's factor is the number of BASE units (metres) in ONE of that unit, so a
length in some unit is converted to metres by MULTIPLYING the value by the unit's
factor. Contract for this module:

  * the base unit is "m" with factor 1.0;
  * "cm" (centimetre) = 0.01 m;  "mm" (millimetre) = 0.001 m;  "km" = 1000.0 m;
  * `Quantity.describe()` renders "<value> <unit>" (value first), e.g. "3.0 m",
    for human display (nothing else in the toolkit depends on it).
"""
from dataclasses import dataclass

# factor = metres per 1 unit (see module contract above).
UNITS = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.01,
    "km": 100.0,
}


@dataclass
class Quantity:
    value: float
    unit: str

    def describe(self):
        """Human label, value first then unit, e.g. '3.0 m'."""
        return "%s %s" % (self.unit, self.value)
