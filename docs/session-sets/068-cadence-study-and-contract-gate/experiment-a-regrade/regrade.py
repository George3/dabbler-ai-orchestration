"""Set 068 S2 - Experiment A SYMMETRIC re-grade.

Re-analyses the committed Set 067 Experiment A raw outputs under THREE grading
regimes, to settle the 0.21.1 erratum's two points:

  1. AUTOMATED PRIMARY (pre-registered): per-replicate weighted catch rate,
     mean over K, with the across-K noise band. NO audit. This is the metric
     the pre-registration named primary. (Union is a secondary, audit-dependent
     view.)
  2. ASYMMETRIC UNION (what Set 067 reported): union-over-K with ONLY the
     routed x cross-file audit applied (067 audit.json).
  3. SYMMETRIC UNION (this re-grade): union-over-K with the routed audit AND
     the path-aware x cross-file audit (audit-symmetric.json) applied -- the
     SAME strict 'names the mechanism' rule on both arms.

Also reports, for cross-file cells, how many catches SURVIVE strict grading on
each side (the honest symmetry check), and the audit-independent existence
proofs (D5/D9). Deterministic, NO API. Writes experiment-a-regrade-data.json.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S067 = HERE.parents[1] / "067-pull-verifier-adapter-experiment-a" / "experiment-a"
RAW = S067 / "raw"
CAT = json.loads((S067 / "catalogue.json").read_text(encoding="utf-8"))
ROUTED_AUDIT = json.loads((S067 / "audit.json").read_text(encoding="utf-8")).get("overrides", {})
SYM_AUDIT = json.loads((HERE / "audit-symmetric.json").read_text(encoding="utf-8")).get("overrides", {})

ARMS = ["A1", "A2", "B1", "B2"]
ROUTED = {"A1", "A2"}
PATH_AWARE = {"B1", "B2"}
WEIGHTS = CAT["severity_weights"]
DEFECTS = CAT["defects"]
DEFECT = {d["id"]: d for d in DEFECTS}
BY_TREE: dict[str, list] = {}
for d in DEFECTS:
    BY_TREE.setdefault(d["tree"], []).append(d)
TOTAL_WEIGHT = sum(WEIGHTS[d["severity"]] for d in DEFECTS)
CROSS_FILE = [d["id"] for d in DEFECTS if d["label_context"] == "cross-file"]
K = 3


def _combined_text(rec: dict) -> str:
    if rec.get("error"):
        return ""
    if rec.get("context") == "routed":
        return (rec.get("content") or "").lower()
    crit = rec.get("critique") or {}
    parts = [crit.get("verdict", ""), crit.get("summary", "")]
    for f in crit.get("findings", []) or []:
        parts += [f.get("description", ""), f.get("severity", ""), f.get("category", "")]
    return "\n".join(parts).lower()


def _pred_match(pred: dict, text: str) -> bool:
    for group in pred["all"]:
        if not any(alt.lower() in text for alt in group):
            return False
    return True


def _matched(rec: dict, tree: str) -> set:
    text = _combined_text(rec)
    if not text:
        return set()
    return {d["id"] for d in BY_TREE[tree] if _pred_match(d["predicate"], text)}


def _load(tree, arm, k):
    p = RAW / tree / f"{arm}_k{k}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _w(ids) -> int:
    return sum(WEIGHTS[DEFECT[i]["severity"]] for i in ids)


def _rate(ids) -> float:
    return round(_w(ids) / TOTAL_WEIGHT, 4)


def _apply_audit(arm: str, union: set, audit: dict) -> set:
    out = set(union)
    for key, val in audit.items():
        a, did = key.split(":")
        if a != arm:
            continue
        if val and did not in out:
            out.add(did)
        elif (not val) and did in out:
            out.discard(did)
    return out


def grade():
    per_arm = {}
    for arm in ARMS:
        replicate = []  # set of caught ids per k (automated)
        for k in range(1, K + 1):
            caught = set()
            for tree in BY_TREE:
                rec = _load(tree, arm, k)
                if rec is None or rec.get("error"):
                    continue
                caught |= _matched(rec, tree)
            replicate.append(caught)
        union_auto = set().union(*replicate) if replicate else set()
        # regime 2: routed audit only
        union_asym = _apply_audit(arm, union_auto, ROUTED_AUDIT)
        # regime 3: routed audit + symmetric path-aware audit
        union_sym = _apply_audit(arm, union_asym, SYM_AUDIT)
        rep_rates = [_rate(c) for c in replicate]
        # AUDITED replicate-level: apply the mechanism audits PER REPLICATE
        # (both audits are removals only -> subtract rejected cells from each k).
        replicate_sym = [_apply_audit(arm, _apply_audit(arm, c, ROUTED_AUDIT), SYM_AUDIT) for c in replicate]
        rep_rates_sym = [_rate(c) for c in replicate_sym]
        per_arm[arm] = {
            "context": "routed" if arm in ROUTED else "path-aware",
            "provider": "openai" if arm in ("A1", "B1") else "google",
            "replicate_rates": rep_rates,
            "replicate_mean": round(sum(rep_rates) / len(rep_rates), 4),
            "noise_band": round(max(rep_rates) - min(rep_rates), 4),
            "replicate_rates_sym_audited": rep_rates_sym,
            "replicate_mean_sym_audited": round(sum(rep_rates_sym) / len(rep_rates_sym), 4),
            "noise_band_sym_audited": round(max(rep_rates_sym) - min(rep_rates_sym), 4),
            "union_auto": sorted(union_auto, key=lambda i: int(i[1:])),
            "union_asym": sorted(union_asym, key=lambda i: int(i[1:])),
            "union_sym": sorted(union_sym, key=lambda i: int(i[1:])),
            "rate_union_auto": _rate(union_auto),
            "rate_union_asym": _rate(union_asym),
            "rate_union_sym": _rate(union_sym),
        }

    _MEAN_KEYS = {"replicate_mean", "replicate_mean_sym_audited"}
    _BAND_KEYS = {"replicate_mean": "noise_band", "replicate_mean_sym_audited": "noise_band_sym_audited"}

    def contrast(b, a, key):
        is_mean = key in _MEAN_KEYS
        band_key = _BAND_KEYS.get(key, "noise_band")
        return {
            "metric": key,
            "b": per_arm[b][key] if is_mean else _rate(per_arm[b][key]),
            "a": per_arm[a][key] if is_mean else _rate(per_arm[a][key]),
            "gap": round(
                (per_arm[b][key] - per_arm[a][key]) if is_mean
                else (_rate(per_arm[b][key]) - _rate(per_arm[a][key])), 4
            ),
            "noise_band_max": round(max(per_arm[b][band_key], per_arm[a][band_key]), 4),
        }

    contrasts = {}
    for b, a, label in [("B1", "A1", "GPT"), ("B2", "A2", "Gemini")]:
        contrasts[f"{b}_minus_{a}_{label}"] = {
            "automated_primary_replicate_mean": contrast(b, a, "replicate_mean"),
            "sym_audited_replicate_mean": contrast(b, a, "replicate_mean_sym_audited"),
            "asym_union_067": contrast(b, a, "union_asym"),
            "sym_union_068": contrast(b, a, "union_sym"),
        }

    # Strict-survival on cross-file cells (the honest symmetry check).
    def survival(arms, audit_chain):
        total = 0
        survive = 0
        cells = []
        for arm in arms:
            auto = set(per_arm[arm]["union_auto"])
            after = auto
            for aud in audit_chain:
                after = _apply_audit(arm, after, aud)
            for did in CROSS_FILE:
                if did in auto:
                    total += 1
                    kept = did in after
                    survive += int(kept)
                    cells.append({"cell": f"{arm}:{did}", "kept": kept})
        return {"survive": survive, "total": total, "cells": cells}

    routed_surv = survival(["A1", "A2"], [ROUTED_AUDIT])
    pa_surv = survival(["B1", "B2"], [ROUTED_AUDIT, SYM_AUDIT])

    # Audit-independent, replicate-independent existence proofs.
    def caught_all_k(arm, did):
        for k in range(1, K + 1):
            rec = _load(DEFECT[did]["tree"], arm, k)
            if rec is None or rec.get("error") or did not in _matched(rec, DEFECT[did]["tree"]):
                return False
        return True

    def caught_any_k(arm, did):
        for k in range(1, K + 1):
            rec = _load(DEFECT[did]["tree"], arm, k)
            if rec and not rec.get("error") and did in _matched(rec, DEFECT[did]["tree"]):
                return True
        return False

    existence = {}
    for did in ["D5", "D9"]:
        existence[did] = {
            "severity": DEFECT[did]["severity"],
            "pathaware_B1_all_k": caught_all_k("B1", did),
            "pathaware_B2_all_k": caught_all_k("B2", did),
            "routed_A1_any_k": caught_any_k("A1", did),
            "routed_A2_any_k": caught_any_k("A2", did),
        }

    # Pair-level for H2 (provider multiplicity within routed).
    def pair(arms, key):
        ids = set()
        for arm in arms:
            ids |= set(per_arm[arm][key])
        return sorted(ids, key=lambda i: int(i[1:]))

    h2 = {
        "automated": {
            "A1_auto": per_arm["A1"]["union_auto"],
            "A2_auto": per_arm["A2"]["union_auto"],
            "routed_pair_auto_rate": _rate(pair(["A1", "A2"], "union_auto")),
            "best_single_routed_auto_rate": max(per_arm["A1"]["rate_union_auto"], per_arm["A2"]["rate_union_auto"]),
            "second_routed_provider_adds": _rate(pair(["A1", "A2"], "union_auto")) - max(per_arm["A1"]["rate_union_auto"], per_arm["A2"]["rate_union_auto"]),
        },
        "sym_union": {
            "routed_pair_sym_rate": _rate(pair(["A1", "A2"], "union_sym")),
            "pathaware_pair_sym_rate": _rate(pair(["B1", "B2"], "union_sym")),
            "pathaware_pair_minus_routed_pair_sym": round(_rate(pair(["B1", "B2"], "union_sym")) - _rate(pair(["A1", "A2"], "union_sym")), 4),
        },
    }

    return {
        "total_weight": TOTAL_WEIGHT, "K": K, "n_defects": len(DEFECTS),
        "cross_file_defects": CROSS_FILE,
        "per_arm": per_arm,
        "contrasts": contrasts,
        "cross_file_strict_survival": {"routed": routed_surv, "path_aware": pa_surv},
        "existence_proofs": existence,
        "H2": h2,
        "symmetric_audit_overrides": SYM_AUDIT,
        "routed_audit_overrides": ROUTED_AUDIT,
    }


def main() -> int:
    data = grade()
    out = HERE / "experiment-a-regrade-data.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out.name}\n")
    pa = data["per_arm"]
    print("Per-arm (replicate-mean auto / sym-audited +/- band ; union rates auto/asym/sym):")
    for a in ARMS:
        d = pa[a]
        print(f"  {a} {d['context']:10s}/{d['provider']:6s} mean_auto={d['replicate_mean']:.4f} "
              f"mean_symaud={d['replicate_mean_sym_audited']:.4f} band_symaud={d['noise_band_sym_audited']:.4f} "
              f"| union auto={d['rate_union_auto']:.4f} asym={d['rate_union_asym']:.4f} sym={d['rate_union_sym']:.4f}")
    print("\nContrasts (gap vs noise band):")
    for name, c in data["contrasts"].items():
        print(f"  {name}:")
        for regime, v in c.items():
            verdict = "EXCEEDS band" if abs(v["gap"]) > v["noise_band_max"] else "INSIDE band"
            print(f"    {regime:34s} gap={v['gap']:+.4f} band={v['noise_band_max']:.4f}  -> {verdict}")
    s = data["cross_file_strict_survival"]
    print(f"\nCross-file strict survival: routed {s['routed']['survive']}/{s['routed']['total']} | "
          f"path-aware {s['path_aware']['survive']}/{s['path_aware']['total']}")
    print("\nExistence proofs (audit- & replicate-independent):")
    for did, e in data["existence_proofs"].items():
        print(f"  {did} ({e['severity']}): B1_all_k={e['pathaware_B1_all_k']} B2_all_k={e['pathaware_B2_all_k']} "
              f"| A1_any_k={e['routed_A1_any_k']} A2_any_k={e['routed_A2_any_k']}")
    h2 = data["H2"]
    print(f"\nH2 second-routed-provider adds (automated): {h2['automated']['second_routed_provider_adds']:+.4f}")
    print(f"H2 path-aware-pair - routed-pair (sym union): {h2['sym_union']['pathaware_pair_minus_routed_pair_sym']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
