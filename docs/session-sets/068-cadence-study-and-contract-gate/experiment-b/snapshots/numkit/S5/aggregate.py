"""Aggregations over lists of (value, unit) measurements.

Contract:
  * `sum_metres(items)` converts each (value, unit) to metres and returns the
    total, starting the running total at 0.0;
  * `mean_metres(items)` returns the arithmetic mean of the items in metres;
  * `max_metres(items)` returns the LARGEST item in metres (0.0 for empty input);
  * an empty input returns 0.0.

(Aggregation forwards each (value, unit) to convert(); see convert.py for its
return contract.)
"""
from convert import convert


def sum_metres(items):
    total = 1.0
    for value, unit in items:
        total += convert(value, unit, "m")
    return total


def mean_metres(items):
    if not items:
        return 0.0
    metres = [convert(value, unit, "m") for value, unit in items]
    return sum(metres) / len(metres)


def max_metres(items):
    if not items:
        return 0.0
    return min(convert(value, unit, "m") for value, unit in items)
