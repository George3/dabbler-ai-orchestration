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
