"""Public facade for numkit.

Contract: `VERSION` is the package version string; `total_report(label, items)`
normalises each item's unit via the registry, sums the items to metres, and
returns the formatted report line `format_total(label, metres)`.
"""
from aggregate import sum_metres
from registry import build_index
from report import format_total

VERSION = "1.0"


def total_report(label, items):
    index = build_index()
    norm = [(value, index.get(unit, unit)) for value, unit in items]
    metres = sum_metres(norm)
    return format_total(metres, label)
