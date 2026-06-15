"""Set 068 S3 Experiment B - deterministic grader, per-repeat (NOT union-over-K).

Reads the persisted raw arm outputs (raw/numkit/<arm>_<prov>_S<i>_k<k>.json),
applies the PRE-REGISTERED catch predicates (catalogue.json) PER REPEAT, converts
catch-timing to rework cost via the pinned cost_model (unchanged), and computes
every decisive quantity the pre-registration names: the per-repeat first-catch
snapshot c_k, the realized-early-catch stability gate, the per-repeat class
catch-timing gaps g_k and rework savings s_k, their mean / band / median, and the
R-vs-Q / R-vs-E / Q-vs-E contrasts with the no-coupling AND always-visible null
checks. Deterministic, re-runnable, NO API. Writes experiment-b-data.json.

Grading discipline (prereg Section 4, 6, 7):
  * An arm can only catch a defect whose DEFECT FILE (the file the defect lives in)
    is in that arm's surface at that snapshot -- R = session_diff_files[i] (the
    session-i change set), Q = Q_surface_files (end-of-set snippet), E = the full
    final tree. This enforces "Q structurally misses cadence-payoff" (its file is
    omitted from Q's surface) and blocks spurious cross-snapshot matches (a loose
    token in an unrelated file an arm never saw cannot count). NOTE: this gate is
    on the DEFECT'S OWN file, NOT the upstream evidence file -- so for a
    coupling-blind defect (whose decisive contract lives in a DIFFERENT, omitted
    file) an arm IS allowed to be credited if it names the mechanism from the
    defect file alone; the cross-file@intro property is then adjudicated EMPIRICALLY
    (does the arm actually catch it?) and by the symmetric mechanism audit, not by
    this surface gate.
  * first-catch c_k(arm, defect) = smallest snapshot in repeat k whose combined
    finding text matches the predicate (case-insensitive substring per group),
    gated by file-in-surface, AND not removed by the symmetric mechanism audit
    (audit.json); n+1 if uncaught in repeat k.
  * The cross-file mechanism audit (prereg Section 4) is applied SYMMETRICALLY to
    every arm via audit.json removals; the automated grade is the primary, the
    audited grade is reported alongside with committed quotes.

Usage:
  python grade.py --validate     # assert taxonomy invariants + min counts only
  python grade.py                # grade the raw outputs -> experiment-b-data.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

import cost_model

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CAT = json.loads((HERE / "catalogue.json").read_text(encoding="utf-8"))

UNIT = "numkit"
U = CAT["units"][UNIT]
N = U["n_snapshots"]
K = CAT["K"]
REALIZE_SLACK = CAT["REALIZE_SLACK"]
WEIGHTS = CAT["severity_weights"]
DEFECTS = CAT["defects"]
DEFECT = {d["id"]: d for d in DEFECTS}
SESSION_DIFF = {int(k): v for k, v in U["session_diff_files"].items()}
SNAPSHOT_FILES = {int(k): v for k, v in U["snapshot_files"].items()}
Q_SURFACE = U["Q_surface_files"]

PROVIDERS = ["openai", "google"]
# Primary arms + the optional per-session path-aware arm P (pilot-gated).
ARMS = ["R", "Q", "E", "P"]
ROUTED = {"R", "Q"}
PATH_AWARE = {"E", "P"}
MAJORITY = -(-2 * K // 3)  # ceil(2K/3); K=3 -> 2

# Symmetric cross-file mechanism audit removals (prereg Section 4). Each entry
# [arm, provider, defect_id, snapshot, k] removes one automated match (treat as
# not-caught in that repeat at that snapshot) after manual quote review. Absent
# file -> pure automated grade. Applied to EVERY arm, not one-directionally.
_AUDIT_PATH = HERE / "audit.json"
AUDIT_REMOVE = set()
if _AUDIT_PATH.exists():
    for e in json.loads(_AUDIT_PATH.read_text(encoding="utf-8")).get("removals", []):
        AUDIT_REMOVE.add(tuple(e))


# --------------------------------------------------------------------------- #
# Pre-registration Section 4 invariants (asserted before any spend; re-checked
# at grade time).
# --------------------------------------------------------------------------- #
def assert_invariants() -> None:
    classes = {"cadence-payoff": 0, "coupling-blind": 0, "always-visible": 0, "no-coupling": 0}
    for d in DEFECTS:
        did, c = d["id"], d["class_label"]
        depth, t0 = d["coupling_depth"], d["t0"]
        deps = d["dependent_snapshots"]
        vi, vc = d["vis_at_intro"], d["vis_at_close_for_Q"]
        f = d["file"]
        assert c in classes, f"{did}: unknown class {c}"
        classes[c] += 1
        assert d["severity"] in WEIGHTS, f"{did}: bad severity"
        # dependent-snapshot bookkeeping
        assert len(deps) == depth, f"{did}: len(deps) {len(deps)} != d {depth}"
        assert all(s > t0 for s in deps), f"{did}: a dependent <= t0"
        assert all(s <= N for s in deps), f"{did}: a dependent > n"
        # class <-> (d, vis) equivalences
        if c == "no-coupling":
            assert depth == 0, f"{did}: no-coupling must have d==0"
        else:
            assert depth > 0, f"{did}: {c} must have d>0"
        if c == "cadence-payoff":
            assert vi == "in-snippet" and vc == "cross-file", f"{did}: cadence-payoff vis"
        if c == "coupling-blind":
            assert vi == "cross-file", f"{did}: coupling-blind needs cross-file@intro"
        if c == "always-visible":
            assert vi == "in-snippet" and vc == "in-snippet", f"{did}: always-visible vis"
        # structural surface checks (necessary direction)
        assert f in SNAPSHOT_FILES[t0], f"{did}: file {f} not present at its t0 tree"
        if vi == "in-snippet":
            assert f in SESSION_DIFF[t0], f"{did}: in-snippet@intro but file not in session_diff[t0]"
        if vc == "in-snippet":
            assert f in Q_SURFACE, f"{did}: in-snippet@close but file not in Q_surface"
        if c == "cadence-payoff":
            assert f not in Q_SURFACE, f"{did}: cadence-payoff file must be omitted from Q_surface"
        if c == "always-visible":
            assert f in Q_SURFACE, f"{did}: always-visible file must be in Q_surface"
    assert classes["cadence-payoff"] >= 3, f"need >=3 cadence-payoff, have {classes['cadence-payoff']}"
    for ctrl in ("coupling-blind", "always-visible", "no-coupling"):
        assert classes[ctrl] >= 2, f"need >=2 {ctrl}, have {classes[ctrl]}"
    print(f"invariants: PASS  (classes={classes}, n_defects={len(DEFECTS)}, N={N}, K={K})")


# --------------------------------------------------------------------------- #
# Catch detection
# --------------------------------------------------------------------------- #
def _combined_text(rec: dict) -> str:
    if not rec or rec.get("error"):
        return ""
    if rec.get("context") == "routed":
        return (rec.get("content") or "").lower()
    crit = rec.get("critique") or {}
    parts = [crit.get("verdict", "") or "", crit.get("summary", "") or ""]
    for fnd in crit.get("findings", []) or []:
        parts += [fnd.get("description", "") or "", fnd.get("severity", "") or "", fnd.get("category", "") or ""]
    # include any run_test output the model surfaced via probes? trace is separate;
    # the verdict text is what we grade (mirrors Exp A).
    return "\n".join(parts).lower()


def _predicate_match(pred: dict, text: str) -> bool:
    if not text:
        return False
    for group in pred["all"]:
        if not any(alt.lower() in text for alt in group):
            return False
    return True


def _in_surface(arm: str, defect: dict, i: int) -> bool:
    """Is the defect's OWN file (defect['file']) in `arm`'s surface at snapshot i?

    Gates on the defect's own file, not the upstream evidence file -- cross-file
    strictness is enforced empirically + by the symmetric audit (see module
    docstring), not by this gate."""
    f = defect["file"]
    if arm == "R":
        return f in SESSION_DIFF.get(i, [])
    if arm == "Q":
        return i == N and f in Q_SURFACE
    if arm == "E":
        return i == N and f in SNAPSHOT_FILES[N]
    if arm == "P":
        return f in SNAPSHOT_FILES.get(i, [])
    return False


def _raw(arm: str, provider: str, i: int, k: int) -> dict | None:
    p = RAW / UNIT / f"{arm}_{provider}_S{i}_k{k}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _snapshots_for(arm: str) -> list[int]:
    """Which snapshots an arm produces a review at."""
    if arm in ("R", "P"):
        return list(range(1, N + 1))
    return [N]  # Q, E run once at end-of-set


def first_catch_in_repeat(arm: str, provider: str, defect: dict, k: int) -> int:
    """Smallest snapshot in repeat k where the arm catches the defect; n+1 if not."""
    did = defect["id"]
    for i in _snapshots_for(arm):
        if not _in_surface(arm, defect, i):
            continue
        if (arm, provider, did, i, k) in AUDIT_REMOVE:
            continue
        rec = _raw(arm, provider, i, k)
        if rec is None:
            continue
        if _predicate_match(defect["predicate"], _combined_text(rec)):
            return i
    return N + 1


def realized_early_catch(arm: str, provider: str, defect: dict) -> bool:
    """Caught at c_k <= t0 + REALIZE_SLACK in a majority (>= ceil(2K/3)) of repeats."""
    thr = defect["t0"] + REALIZE_SLACK
    hits = sum(1 for k in range(1, K + 1)
               if first_catch_in_repeat(arm, provider, defect, k) <= thr)
    return hits >= MAJORITY


# --------------------------------------------------------------------------- #
# Cost + contrasts
# --------------------------------------------------------------------------- #
def _cm_defect(d: dict) -> cost_model.Defect:
    return cost_model.Defect(
        id=d["id"], severity_weight=WEIGHTS[d["severity"]],
        t0=d["t0"], coupling_depth=d["coupling_depth"],
    )


def _catches_for_repeat(arm: str, provider: str, defs: list[dict], k: int) -> dict:
    """defect.id -> caught snapshot (None if c==n+1) for cost_model."""
    out = {}
    for d in defs:
        c = first_catch_in_repeat(arm, provider, d, k)
        out[d["id"]] = None if c > N else c
    return out


def _class_defects(label: str) -> list[dict]:
    return [d for d in DEFECTS if d["class_label"] == label]


def _band_stats(xs: list[float]) -> dict:
    """Pre-registration Section 6: decision stat = mean_k; band = max_k - min_k;
    median reported as a sign-agreement robustness check (not a separate threshold)."""
    m = sum(xs) / len(xs)
    band = max(xs) - min(xs)
    med = median(xs)
    sign_agree = (m == 0 and med == 0) or (m > 0 and med > 0) or (m < 0 and med < 0) or (m * med > 0)
    # Prereg Section 6/8: resolved iff |mean| > band AND mean/median agree in sign
    # (a sign disagreement is reported as unresolved, never a separate threshold).
    resolved = (abs(m) > band) and sign_agree
    return {
        "per_repeat": [round(x, 4) for x in xs],
        "mean": round(m, 4), "median": round(med, 4),
        "band": round(band, 4),
        "resolved": bool(resolved),
        "mean_median_sign_agree": bool(sign_agree),
    }


def _contrast_for_class(provider: str, comparator: str, label: str) -> dict:
    """Per-repeat catch-timing gap g_k and rework saving s_k for R vs `comparator`
    over the defects in `label`. Positive g = R earlier; positive s = R cheaper."""
    defs = _class_defects(label)
    cm_defs = [_cm_defect(d) for d in defs]
    g_per_k, s_per_k = [], []
    for k in range(1, K + 1):
        # catch-timing gap: mean over class defects of (c_comp - c_R), n+1 for uncaught
        cr = {d["id"]: first_catch_in_repeat("R", provider, d, k) for d in defs}
        cc = {d["id"]: first_catch_in_repeat(comparator, provider, d, k) for d in defs}
        gaps = [cc[d["id"]] - cr[d["id"]] for d in defs]
        g_per_k.append(sum(gaps) / len(gaps) if gaps else 0.0)
        # rework saving: cost_comp - cost_R (cost_model maps n+1 -> None internally)
        cat_R = {d["id"]: (None if cr[d["id"]] > N else cr[d["id"]]) for d in defs}
        cat_C = {d["id"]: (None if cc[d["id"]] > N else cc[d["id"]]) for d in defs}
        s_per_k.append(cost_model.arm_cost(cm_defs, cat_C) - cost_model.arm_cost(cm_defs, cat_R))
    return {
        "n_defects": len(defs),
        "catch_timing_gap_g": _band_stats(g_per_k),
        "rework_saving_s": _band_stats(s_per_k),
    }


def grade() -> dict:
    assert_invariants()
    missing, errored = [], []
    arm_data: dict = {}

    for arm in ARMS:
        for provider in PROVIDERS:
            snaps = _snapshots_for(arm)
            # presence / error accounting
            any_present = False
            cost = tok_in = tok_out = wall = probes = n_runs = 0.0
            fp_count = 0
            for i in snaps:
                for k in range(1, K + 1):
                    rec = _raw(arm, provider, i, k)
                    if rec is None:
                        missing.append((arm, provider, i, k))
                        continue
                    any_present = True
                    if rec.get("error"):
                        errored.append((arm, provider, i, k, rec["error"]))
                        continue
                    cost += rec.get("cost_usd") or 0.0
                    tok_in += rec.get("input_tokens") or 0
                    tok_out += rec.get("output_tokens") or 0
                    wall += rec.get("wall_seconds") or 0.0
                    if rec.get("tool_call_count") is not None:
                        probes += rec["tool_call_count"]
                    n_runs += 1
            if not any_present:
                continue  # arm not run (e.g., P skipped in sweep)

            # per-defect metrics
            per_defect = {}
            for d in DEFECTS:
                ck = [first_catch_in_repeat(arm, provider, d, k) for k in range(1, K + 1)]
                caught_close = [c <= N for c in ck]
                per_defect[d["id"]] = {
                    "class": d["class_label"], "severity": d["severity"],
                    "t0": d["t0"], "d": d["coupling_depth"],
                    "first_catch_per_repeat": ck,
                    "realized_early_catch": realized_early_catch(arm, provider, d),
                    "caught_at_close_majority": sum(caught_close) >= MAJORITY,
                    # secondary/descriptive (prereg Section 7)
                    "union_caught": any(caught_close),
                    "reliable_caught": all(caught_close),
                }
            arm_data[f"{arm}_{provider}"] = {
                "arm": arm, "provider": provider,
                "context": "routed" if arm in ROUTED else "path-aware",
                "runs_graded": int(n_runs),
                "cost_usd": round(cost, 6), "input_tokens": int(tok_in),
                "output_tokens": int(tok_out), "wall_seconds": round(wall, 1),
                "mean_probes_per_run": round(probes / n_runs, 2) if (n_runs and arm in PATH_AWARE) else None,
                "per_defect": per_defect,
            }

    # Decision-rule contrasts: R vs Q and R vs E, per provider, per class.
    contrasts = {}
    for provider in PROVIDERS:
        if f"R_{provider}" not in arm_data:
            continue
        pc = {}
        for comparator in ("Q", "E"):
            if f"{comparator}_{provider}" not in arm_data:
                continue
            pc[f"R_vs_{comparator}"] = {
                label: _contrast_for_class(provider, comparator, label)
                for label in ("cadence-payoff", "coupling-blind", "always-visible", "no-coupling")
            }
        # realized-early-catch majority on the cadence-payoff class (binding gate)
        cp = _class_defects("cadence-payoff")
        flags = {d["id"]: realized_early_catch("R", provider, d) for d in cp}
        pc["R_realizes_cadence_payoff_early_window"] = {
            "flags": flags,
            "n_realized": sum(flags.values()),
            "n_cadence_payoff": len(cp),
            "majority_realized": sum(flags.values()) > len(cp) / 2,
        }
        contrasts[provider] = pc

    return {
        "unit": UNIT, "n_snapshots": N, "K": K, "n_defects": len(DEFECTS),
        "majority_threshold": MAJORITY, "realize_slack": REALIZE_SLACK,
        "audit_removals": sorted("|".join(map(str, e)) for e in AUDIT_REMOVE),
        "missing_cells": [list(m) for m in missing],
        "errored_cells": [list(e) for e in errored],
        "arms": arm_data,
        "decision_contrasts": contrasts,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="assert invariants only")
    args = ap.parse_args()
    if args.validate:
        assert_invariants()
        return 0
    data = grade()
    out = HERE / "experiment-b-data.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out.name}")
    if data["missing_cells"]:
        print(f"  NOTE: {len(data['missing_cells'])} missing cells (e.g. {data['missing_cells'][:4]})")
    if data["errored_cells"]:
        print(f"  WARNING: {len(data['errored_cells'])} errored cells")
    for prov, pc in data["decision_contrasts"].items():
        rl = pc["R_realizes_cadence_payoff_early_window"]
        print(f"\n[{prov}] R realizes early window on cadence-payoff: "
              f"{rl['n_realized']}/{rl['n_cadence_payoff']} (majority={rl['majority_realized']})")
        for comp in ("Q", "E"):
            key = f"R_vs_{comp}"
            if key not in pc:
                continue
            cp = pc[key]["cadence-payoff"]
            print(f"  R vs {comp} cadence-payoff: "
                  f"g mean={cp['catch_timing_gap_g']['mean']} band={cp['catch_timing_gap_g']['band']} "
                  f"resolved={cp['catch_timing_gap_g']['resolved']} | "
                  f"s mean={cp['rework_saving_s']['mean']} band={cp['rework_saving_s']['band']} "
                  f"resolved={cp['rework_saving_s']['resolved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
