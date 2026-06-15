"""Set 068 Experiment B - PRE-REGISTERED rework cost model.

Pinned in Session 2, BEFORE any arm runs (see experiment-b-preregistration.md
Section 5). The verdict in experiment-b-results.md (S3) must use THIS function
unchanged; it cannot be tuned after seeing data. The ONLY empirical input is the
catch snapshot `c` per defect per arm -- everything else is a fixed property of
the committed snapshot dependency graph.

Run `python cost_model.py` to execute the invariant self-tests.
Deterministic, NO API.
"""
from __future__ import annotations

from dataclasses import dataclass

# Pre-registered constants (FIXED 2026-06-15, Session 2). Do not change in S3.
BASE_FIX = 1            # cost to fix the defect itself
COUPLING_PENALTY = 1    # extra rework-units per downstream snapshot built on the bug


def escape_penalty(d: int) -> int:
    """A never-caught coupling defect costs strictly more than catching it at set
    end. Pre-registered as 1 + d so escape > caught-after-d-dependents (= d)."""
    return 1 + d


@dataclass(frozen=True)
class Defect:
    """A seeded Experiment B defect. All fields fixed before any arm runs."""
    id: str
    severity_weight: int      # Critical=3, Major=2, Minor=1
    t0: int                   # introduction snapshot index (1-based)
    coupling_depth: int       # d = number of later snapshots that build on it


def rework_units(defect: Defect, caught_at: int | None) -> int:
    """Rework-units for a defect first caught at snapshot `caught_at` (1-based),
    or None if never caught by the arm.

    elapsed          = max(0, caught_at - t0)         snapshots between intro & catch
    dependents_built = min(d, elapsed)                downstream work done before catch
    units            = BASE_FIX + COUPLING_PENALTY*dependents_built
                       (+ escape_penalty(d) if never caught)
    """
    if caught_at is None:
        return BASE_FIX + COUPLING_PENALTY * defect.coupling_depth + escape_penalty(defect.coupling_depth)
    if caught_at < defect.t0:
        raise ValueError(f"{defect.id}: caught_at {caught_at} precedes introduction t0 {defect.t0}")
    elapsed = max(0, caught_at - defect.t0)
    dependents_built = min(defect.coupling_depth, elapsed)
    return BASE_FIX + COUPLING_PENALTY * dependents_built


def defect_cost(defect: Defect, caught_at: int | None) -> int:
    """Severity-weighted rework cost for one defect under one arm."""
    return defect.severity_weight * rework_units(defect, caught_at)


def arm_cost(defects: list[Defect], catches: dict[str, int | None]) -> int:
    """Total severity-weighted rework cost for an arm.

    `catches` maps defect.id -> earliest-catch snapshot (or None if never caught).
    A defect id absent from `catches` is treated as never caught.
    """
    return sum(defect_cost(d, catches.get(d.id)) for d in defects)


def arm_cost_by_class(defects: list[Defect], catches: dict[str, int | None]) -> dict[str, int]:
    """Cost split into coupling (d>0) vs no-coupling (d==0) classes -- the saving
    must be concentrated in the coupling class (decision rule Section 8)."""
    out = {"coupling": 0, "no_coupling": 0}
    for d in defects:
        c = defect_cost(d, catches.get(d.id))
        out["coupling" if d.coupling_depth > 0 else "no_coupling"] += c
    return out


def _self_test() -> None:
    # No-coupling control: cost is INVARIANT to catch timing (the built-in null).
    nd = Defect("N1", severity_weight=2, t0=1, coupling_depth=0)
    costs = {c: defect_cost(nd, c) for c in (1, 2, 3, 4)}
    assert len(set(costs.values())) == 1, f"d=0 cost must not vary with timing: {costs}"
    assert defect_cost(nd, 1) == 2 * BASE_FIX

    # Coupling defect: cost is MONOTONE NON-DECREASING in catch snapshot, and
    # strictly increases until the catch lags the coupling depth.
    cd = Defect("C1", severity_weight=3, t0=1, coupling_depth=3)
    series = [rework_units(cd, c) for c in (1, 2, 3, 4, 5)]
    assert series == [1, 2, 3, 4, 4], f"coupling rework curve wrong: {series}"  # caps at t0+d
    assert all(series[i] <= series[i + 1] for i in range(len(series) - 1)), "must be monotone"

    # Catch-at-introduction == just the base fix.
    assert rework_units(cd, cd.t0) == BASE_FIX

    # Never caught costs strictly more than catching at set end (after d dependents).
    caught_at_end = rework_units(cd, cd.t0 + cd.coupling_depth)   # = 1 + d = 4
    never = rework_units(cd, None)                                # = 1 + d + (1+d) = 8
    assert never > caught_at_end, (never, caught_at_end)

    # caught_at before introduction is an error (snapshots are monotone).
    try:
        rework_units(cd, 0)
        raise AssertionError("expected ValueError for caught_at < t0")
    except ValueError:
        pass

    # Earlier-catch arm is never more expensive than a later-catch arm (per defect).
    defects = [cd, nd, Defect("C2", 2, t0=2, coupling_depth=2)]
    early = {"C1": 1, "N1": 3, "C2": 2}
    late = {"C1": 4, "N1": 1, "C2": None}
    assert arm_cost(defects, early) < arm_cost(defects, late)

    bc = arm_cost_by_class(defects, early)
    assert bc["no_coupling"] == 2 * BASE_FIX  # N1 only
    print("cost_model self-test: PASS")


if __name__ == "__main__":
    _self_test()
