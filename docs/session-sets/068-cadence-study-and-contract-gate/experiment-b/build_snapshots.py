"""Set 068 S3 Experiment B - staged-snapshot builder for the cadence study.

Builds ONE multi-session unit ("numkit", a tiny numeric-length toolkit) as an
ORDERED, MONOTONE sequence of frozen snapshots S1 -> ... -> S5. Each source file
is introduced in exactly ONE session and never modified afterwards, so:

    S(i)             = every file whose intro session <= i      (the full tree)
    S(i) \\ S(i-1)    = the files introduced in session i        (R's surface)

Later files genuinely import earlier ones (registry imports quantity, convert
imports registry+quantity, aggregate imports convert, report/api import
aggregate), so a defect in an early file is depended on by later snapshots --
that downstream dependency is what creates coupling (pre-registration Section 2).

Twelve defects are seeded inline (NO `# BUG` markers in the emitted source -- the
ground truth lives in catalogue.json). Each cadence-payoff / always-visible defect
violates a contract stated IN THE SAME FILE'S docstring (so it is genuinely
in-snippet@intro); each coupling-blind defect is only recognizable with a file the
introducing session's diff omits (genuinely cross-file@intro). The trees are
otherwise correct by construction; a per-snapshot smoke test exercises only the
bug-immune base-unit path so `run_test` (arm E) sees a GREEN suite -- the seeded
bugs live in paths the existing tests do not cover (that is *why* they escape).

Deterministic, NO API. Run:  python build_snapshots.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNIT = "numkit"
SNAP_ROOT = HERE / "snapshots" / UNIT

# --------------------------------------------------------------------------- #
# Each file: (intro_session, source). Introduced once, frozen thereafter.
# The seeded defect(s) per file are noted in the module-level provenance comment
# block BELOW (in THIS builder, not the emitted file) and pinned in catalogue.json.
# --------------------------------------------------------------------------- #

QUANTITY_PY = '''\
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
'''

REGISTRY_PY = '''\
"""Human-alias registry for unit names.

Contract: `build_index()` returns a dict mapping EVERY canonical unit name AND
every human alias to the CANONICAL unit name (so callers can normalise free-text
unit names before conversion). Every registered alias is a valid conversion input
the rest of the toolkit must accept.
"""

# alias -> canonical unit name.
ALIASES = {
    "metre": "m",
    "meter": "m",
    "centimetre": "cm",
    "centimeter": "cm",
    "millimetre": "mm",
    "millimeter": "mm",
    "kilometre": "km",
    "klick": "km",
}

CANONICAL = ("m", "cm", "mm", "km")


def build_index():
    """Map canonical names and all aliases to the canonical unit name."""
    index = {}
    for name in CANONICAL:
        index[name] = name
    for alias, canonical in ALIASES.items():
        index[alias] = alias
    return index
'''

CONVERT_PY = '''\
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
'''

AGGREGATE_PY = '''\
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
'''

REPORT_PY = '''\
"""Human-readable rendering of aggregate results.

Contract: `format_total(label, metres)` renders 'LABEL: <metres> m' with the
numeric value shown to 3 decimal places.
"""


def format_total(label, metres):
    return "%s: %.1f m" % (label, metres)
'''

API_PY = '''\
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
'''

SMOKE_TEST_PY = '''\
"""Bug-immune smoke test (the project's EXISTING coverage).

Asserts only the base-unit invariants that hold regardless of the seeded defects,
so `run_test` reports GREEN -- the seeded bugs live in paths this suite never
exercises (which is precisely why they escape a per-snapshot test run).
"""
import quantity


def test_base_unit_is_identity():
    assert quantity.UNITS["m"] == 1.0


def test_units_table_has_core_names():
    for name in ("m", "cm", "mm", "km"):
        assert name in quantity.UNITS
'''

# filename -> (intro_session, source). Order = construction order.
FILES = {
    "quantity.py": (1, QUANTITY_PY),
    "registry.py": (2, REGISTRY_PY),
    "convert.py": (3, CONVERT_PY),
    "aggregate.py": (4, AGGREGATE_PY),
    "report.py": (5, REPORT_PY),
    "api.py": (5, API_PY),
}

N_SNAPSHOTS = 5


def snapshot_files(i: int) -> list[str]:
    """Full tree at S(i): every file introduced in session <= i (sorted)."""
    return sorted(f for f, (intro, _) in FILES.items() if intro <= i)


def session_diff_files(i: int) -> list[str]:
    """R's surface at session i: files introduced in exactly session i (sorted)."""
    return sorted(f for f, (intro, _) in FILES.items() if intro == i)


def build() -> None:
    if SNAP_ROOT.exists():
        shutil.rmtree(SNAP_ROOT)
    for i in range(1, N_SNAPSHOTS + 1):
        snap = SNAP_ROOT / f"S{i}"
        snap.mkdir(parents=True, exist_ok=True)
        for fname in snapshot_files(i):
            (snap / fname).write_text(FILES[fname][1], encoding="utf-8")
        # Each snapshot ships the (passing) smoke suite at the tree root so
        # `python -m pytest` discovers it and `import quantity` resolves under
        # pytest's default prepend import mode -- run_test (arm E) sees GREEN.
        (snap / "test_smoke.py").write_text(SMOKE_TEST_PY, encoding="utf-8")
    # Emit the per-session manifest the catalogue/grader cross-check against.
    manifest = {
        "unit": UNIT,
        "n_snapshots": N_SNAPSHOTS,
        "snapshot_files": {str(i): snapshot_files(i) for i in range(1, N_SNAPSHOTS + 1)},
        "session_diff_files": {str(i): session_diff_files(i) for i in range(1, N_SNAPSHOTS + 1)},
    }
    (HERE / "snapshot-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Built {N_SNAPSHOTS} snapshots under {SNAP_ROOT}")
    for i in range(1, N_SNAPSHOTS + 1):
        print(f"  S{i}: tree={snapshot_files(i)}  diff={session_diff_files(i)}")
    print(f"Wrote {HERE / 'snapshot-manifest.json'}")


if __name__ == "__main__":
    build()
