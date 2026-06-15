"""Set 067 S3 Experiment A - deterministic grader + metrics.

Reads the persisted raw arm outputs (raw/<tree>/<arm>_k<k>.json), applies the
PRE-REGISTERED catch predicates (catalogue.json), and computes every metric the
pre-registration names: severity-weighted catch rate (union + per-replicate
distribution), the probeable/novel and in-snippet/cross-file splits, the H1/H2/H3
contrasts, the noise band, falsifier coverage, and cost/latency/tool-calls.
Deterministic and re-runnable (NO API). Writes experiment-a-data.json.

A defect is "caught" by a run iff its predicate.all matches the run's combined
text: for every inner list, at least one alternative is a case-insensitive
substring. This is the primary automated grade; the orchestrator's manual audit
delta (per pre-registration Section 5) is recorded in experiment-a-results.md.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CAT = json.loads((HERE / "catalogue.json").read_text(encoding="utf-8"))

# Manual-audit overrides on the UNION catch (pre-registration Section 5). Keyed
# "<arm>:<defect>" -> bool. The audit rule (pre-committed): for a CROSS-FILE
# defect, a routed catch counts only if the text identifies the ACTUAL defect
# mechanism (the real duplicate / key mismatch / incompleteness), NOT a generic
# conditional hypothetical ("if there were a duplicate name..."). False removes
# an automated match; true adds a missed one. Absent file -> pure automated grade.
_AUDIT_PATH = HERE / "audit.json"
AUDIT = (
    json.loads(_AUDIT_PATH.read_text(encoding="utf-8")).get("overrides", {})
    if _AUDIT_PATH.exists() else {}
)

ARMS = ["A1", "A2", "B1", "B2"]
ROUTED = {"A1", "A2"}
PATH_AWARE = {"B1", "B2"}
WEIGHTS = CAT["severity_weights"]
DEFECTS = CAT["defects"]
BY_TREE: dict[str, list] = {}
for d in DEFECTS:
    BY_TREE.setdefault(d["tree"], []).append(d)
DEFECT = {d["id"]: d for d in DEFECTS}
TOTAL_WEIGHT = sum(WEIGHTS[d["severity"]] for d in DEFECTS)
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


def _predicate_match(pred: dict, text: str) -> bool:
    for group in pred["all"]:
        if not any(alt.lower() in text for alt in group):
            return False
    return True


def _matched(rec: dict, tree: str) -> set:
    text = _combined_text(rec)
    if not text:
        return set()
    return {d["id"] for d in BY_TREE[tree] if _predicate_match(d["predicate"], text)}


def _load(tree: str, arm: str, k: int) -> dict | None:
    p = RAW / tree / f"{arm}_k{k}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _weight(ids) -> int:
    return sum(WEIGHTS[DEFECT[i]["severity"]] for i in ids)


def _subset(ids, key, val) -> set:
    return {i for i in ids if DEFECT[i][key] == val}


def grade() -> dict:
    missing, errored = [], []
    # Per arm: per-replicate caught sets (k=1..K, across all trees), union, reliable.
    arm_data: dict[str, dict] = {}
    fp_records = []  # path-aware unmatched findings (candidate false positives)

    for arm in ARMS:
        replicate_caught = []  # list over k of set of caught defect ids
        reliable_by_tree = {}
        union = set()
        cost = tok_in = tok_out = wall = probes = n = 0.0
        per_run_catch_counts = []
        for k in range(1, K + 1):
            caught_k = set()
            for tree in BY_TREE:
                rec = _load(tree, arm, k)
                if rec is None:
                    missing.append((tree, arm, k))
                    continue
                if rec.get("error"):
                    errored.append((tree, arm, k, rec["error"]))
                    continue
                c = _matched(rec, tree)
                caught_k |= c
                # accumulate cost/usage
                cost += rec.get("cost_usd") or 0.0
                tok_in += rec.get("input_tokens") or 0
                tok_out += rec.get("output_tokens") or 0
                wall += rec.get("wall_seconds") or 0.0
                if rec.get("tool_call_count") is not None:
                    probes += rec["tool_call_count"]
                n += 1
                per_run_catch_counts.append(len(c))
                # reliable tracking
                reliable_by_tree.setdefault(tree, []).append(c)
                # candidate false positives (path-aware only: structured findings)
                if arm in PATH_AWARE:
                    crit = rec.get("critique") or {}
                    for f in crit.get("findings", []) or []:
                        text = (f.get("description", "")).lower()
                        hit = any(
                            _predicate_match(d["predicate"], text)
                            for d in BY_TREE[tree]
                        )
                        if not hit:
                            fp_records.append({
                                "tree": tree, "arm": arm, "k": k,
                                "severity": f.get("severity", ""),
                                "description": f.get("description", "")[:300],
                            })
            replicate_caught.append(caught_k)
            union |= caught_k

        # Apply manual-audit overrides to the UNION (authoritative for cross-file).
        union_auto = set(union)
        applied = []
        for key, val in AUDIT.items():
            a, did = key.split(":")
            if a != arm:
                continue
            if val and did not in union:
                union.add(did)
                applied.append(key + "=+")
            elif (not val) and did in union:
                union.discard(did)
                applied.append(key + "=-")

        reliable = set()
        for tree, sets in reliable_by_tree.items():
            if len(sets) == K:
                inter = set.intersection(*sets) if sets else set()
                reliable |= inter

        rep_weighted = [round(_weight(c) / TOTAL_WEIGHT, 4) for c in replicate_caught]
        rep_counts = [len(c) for c in replicate_caught]
        arm_data[arm] = {
            "context": "routed" if arm in ROUTED else "path-aware",
            "provider": ("openai" if arm in ("A1", "B1") else "google"),
            "union_caught": sorted(union, key=lambda i: int(i[1:])),
            "union_caught_automated": sorted(union_auto, key=lambda i: int(i[1:])),
            "audit_overrides_applied": applied,
            "reliable_caught": sorted(reliable, key=lambda i: int(i[1:])),
            "union_count": len(union),
            "union_weighted_rate": round(_weight(union) / TOTAL_WEIGHT, 4),
            "replicate_caught_counts": rep_counts,
            "replicate_weighted_rates": rep_weighted,
            "replicate_rate_mean": round(sum(rep_weighted) / len(rep_weighted), 4),
            "replicate_rate_min": min(rep_weighted),
            "replicate_rate_max": max(rep_weighted),
            "noise_band": round(max(rep_weighted) - min(rep_weighted), 4),
            "union_probeable": sorted(_subset(union, "label_probeable", "probeable"), key=lambda i: int(i[1:])),
            "union_novel": sorted(_subset(union, "label_probeable", "novel"), key=lambda i: int(i[1:])),
            "union_in_snippet": sorted(_subset(union, "label_context", "in-snippet"), key=lambda i: int(i[1:])),
            "union_cross_file": sorted(_subset(union, "label_context", "cross-file"), key=lambda i: int(i[1:])),
            "cost_usd": round(cost, 6),
            "input_tokens": int(tok_in),
            "output_tokens": int(tok_out),
            "wall_seconds": round(wall, 1),
            "runs_graded": int(n),
            "mean_probes_per_run": round(probes / n, 2) if (n and arm in PATH_AWARE) else None,
        }

    # Derived pair cells (union over both providers AND over K).
    routed_pair = set(arm_data["A1"]["union_caught"]) | set(arm_data["A2"]["union_caught"])
    pa_pair = set(arm_data["B1"]["union_caught"]) | set(arm_data["B2"]["union_caught"])

    def pack(ids):
        ids = sorted(ids, key=lambda i: int(i[1:]))
        return {
            "ids": ids, "count": len(ids),
            "weighted_rate": round(_weight(ids) / TOTAL_WEIGHT, 4),
            "cross_file": sorted(_subset(ids, "label_context", "cross-file"), key=lambda i: int(i[1:])),
            "in_snippet": sorted(_subset(ids, "label_context", "in-snippet"), key=lambda i: int(i[1:])),
            "probeable": sorted(_subset(ids, "label_probeable", "probeable"), key=lambda i: int(i[1:])),
            "novel": sorted(_subset(ids, "label_probeable", "novel"), key=lambda i: int(i[1:])),
        }

    # H1 context contrasts (same provider): B - A.
    def contrast(b, a):
        bset, aset = set(arm_data[b]["union_caught"]), set(arm_data[a]["union_caught"])
        gained = bset - aset
        lost = aset - bset
        return {
            "weighted_gap": round(
                arm_data[b]["union_weighted_rate"] - arm_data[a]["union_weighted_rate"], 4
            ),
            "gained_by_pathaware": sorted(gained, key=lambda i: int(i[1:])),
            "gained_cross_file": sorted(_subset(gained, "label_context", "cross-file"), key=lambda i: int(i[1:])),
            "gained_in_snippet": sorted(_subset(gained, "label_context", "in-snippet"), key=lambda i: int(i[1:])),
            "lost_vs_routed": sorted(lost, key=lambda i: int(i[1:])),
            "noise_band_max": round(max(arm_data[b]["noise_band"], arm_data[a]["noise_band"]), 4),
        }

    # Falsifier coverage (from catalogue discriminates flags).
    discriminating = [d["id"] for d in DEFECTS if d.get("discriminates")]
    non_discriminating = [d["id"] for d in DEFECTS if not d.get("discriminates")]

    # Per-defect who-caught matrix (union over K).
    matrix = {}
    for d in DEFECTS:
        matrix[d["id"]] = {
            "severity": d["severity"], "label_probeable": d["label_probeable"],
            "label_context": d["label_context"], "class": d["class"],
            "caught_by": [a for a in ARMS if d["id"] in arm_data[a]["union_caught"]],
            "falsifier": d["id"] in discriminating,
        }

    return {
        "n_trees": len(BY_TREE), "K": K, "n_defects": len(DEFECTS),
        "total_weight": TOTAL_WEIGHT,
        "missing_cells": missing, "errored_cells": errored,
        "arms": arm_data,
        "derived": {
            "routed_pair": pack(routed_pair),
            "path_aware_pair": pack(pa_pair),
            "H3_routed_unique_vs_pathaware_pair": pack(routed_pair - pa_pair),
            "pathaware_unique_vs_routed_pair": pack(pa_pair - routed_pair),
        },
        "H1_context_contrasts": {
            "B1_minus_A1_GPT": contrast("B1", "A1"),
            "B2_minus_A2_Gemini": contrast("B2", "A2"),
        },
        "H2_provider_multiplicity": {
            "routed_pair_weighted_rate": pack(routed_pair)["weighted_rate"],
            "best_single_routed_weighted_rate": max(
                arm_data["A1"]["union_weighted_rate"], arm_data["A2"]["union_weighted_rate"]
            ),
            "pathaware_pair_weighted_rate": pack(pa_pair)["weighted_rate"],
            "pathaware_pair_minus_routed_pair": round(
                pack(pa_pair)["weighted_rate"] - pack(routed_pair)["weighted_rate"], 4
            ),
        },
        "H4_falsifier": {
            "discriminating": discriminating,
            "non_discriminating": non_discriminating,
            "coverage_count": len(discriminating),
            "coverage_rate": round(len(discriminating) / len(DEFECTS), 4),
        },
        "false_positives_pathaware": {
            "count": len(fp_records), "records": fp_records,
        },
        "defect_matrix": matrix,
    }


def main() -> int:
    data = grade()
    out = HERE / "experiment-a-data.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out.name}")
    if data["missing_cells"]:
        print(f"  WARNING: {len(data['missing_cells'])} missing cells: {data['missing_cells'][:8]}")
    if data["errored_cells"]:
        print(f"  WARNING: {len(data['errored_cells'])} errored cells")
    print("\nPer-arm union-caught (weighted rate, noise band):")
    for a in ARMS:
        ad = data["arms"][a]
        print(
            f"  {a} ({ad['context']}/{ad['provider']}): "
            f"caught={ad['union_count']}/{data['n_defects']} "
            f"wrate={ad['union_weighted_rate']} band={ad['noise_band']} "
            f"cross_file={len(ad['union_cross_file'])} novel={len(ad['union_novel'])} "
            f"cost=${ad['cost_usd']:.3f}"
        )
    d = data["derived"]
    print(f"\nrouted-pair caught {d['routed_pair']['count']} (wrate {d['routed_pair']['weighted_rate']})")
    print(f"path-aware-pair caught {d['path_aware_pair']['count']} (wrate {d['path_aware_pair']['weighted_rate']})")
    print(f"H3 routed-unique (routed_pair - pa_pair): {d['H3_routed_unique_vs_pathaware_pair']['ids']}")
    print(f"pa-unique (pa_pair - routed_pair): {d['pathaware_unique_vs_routed_pair']['ids']}")
    h1 = data["H1_context_contrasts"]
    print(f"\nH1 B1-A1 (GPT) weighted_gap={h1['B1_minus_A1_GPT']['weighted_gap']} gained_cross_file={h1['B1_minus_A1_GPT']['gained_cross_file']}")
    print(f"H1 B2-A2 (Gemini) weighted_gap={h1['B2_minus_A2_Gemini']['weighted_gap']} gained_cross_file={h1['B2_minus_A2_Gemini']['gained_cross_file']}")
    print(f"\nH4 falsifier coverage: {data['H4_falsifier']['coverage_count']}/{data['n_defects']} ({data['H4_falsifier']['coverage_rate']})")
    print(f"path-aware candidate false positives: {data['false_positives_pathaware']['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
