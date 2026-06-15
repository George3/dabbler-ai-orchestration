"""Set 068 S2 - symmetric re-grade evidence dump.

For each path-aware arm (B1, B2) and each CROSS-FILE defect, find which
finding(s) in each replicate (k=1..3) cause the pre-registered predicate to
match, and dump their full text. This is the evidence the symmetric audit
adjudicates: does the path-aware arm NAME THE ACTUAL MECHANISM (the same
strict standard the original audit applied only to routed x cross-file), or
did the predicate match on a token/substring artifact in an unrelated finding?

Reads the committed Set 067 raw outputs; writes a UTF-8 markdown dump.
Deterministic, NO API.
"""
from __future__ import annotations

import json
from pathlib import Path

S067 = Path(__file__).resolve().parents[2] / "067-pull-verifier-adapter-experiment-a" / "experiment-a"
RAW = S067 / "raw"
CAT = json.loads((S067 / "catalogue.json").read_text(encoding="utf-8"))
OUT = Path(__file__).resolve().parent / "pathaware-crossfile-evidence.md"

DEFECTS = {d["id"]: d for d in CAT["defects"]}
CROSS_FILE = [d["id"] for d in CAT["defects"] if d["label_context"] == "cross-file"]
PATH_AWARE_ARMS = ["B1", "B2"]
K = 3


def _predicate_match_text(pred: dict, text: str) -> bool:
    t = text.lower()
    for group in pred["all"]:
        if not any(alt.lower() in t for alt in group):
            return False
    return True


def _which_groups_hit(pred: dict, text: str):
    """Return, per predicate group, the alternative substrings present."""
    t = text.lower()
    hits = []
    for group in pred["all"]:
        present = [alt for alt in group if alt.lower() in t]
        hits.append(present)
    return hits


def main() -> int:
    lines = ["# Path-aware cross-file catch evidence (Set 068 S2 symmetric re-grade)\n"]
    lines.append(
        "For each B-arm x cross-file defect the arm is credited with (automated "
        "union), the finding(s) whose text triggers the predicate, with the "
        "matched tokens per group. Adjudication question (symmetric with the "
        "Set 067 routed audit): does the finding NAME THE ACTUAL MECHANISM?\n"
    )
    for did in CROSS_FILE:
        d = DEFECTS[did]
        tree = d["tree"]
        lines.append(f"\n---\n\n## {did} ({d['severity']}, {d['class']}) - tree {tree}\n")
        lines.append(f"**Seeded mechanism:** {d['description']}\n")
        lines.append(f"**Predicate:** `{json.dumps(d['predicate']['all'])}`\n")
        for arm in PATH_AWARE_ARMS:
            arm_caught_any = False
            arm_lines = []
            for k in range(1, K + 1):
                p = RAW / tree / f"{arm}_k{k}.json"
                if not p.exists():
                    continue
                rec = json.loads(p.read_text(encoding="utf-8"))
                crit = rec.get("critique") or {}
                findings = crit.get("findings") or []
                # combined-text match (same as grade.py) determines credit
                combined = "\n".join(
                    [crit.get("verdict", ""), crit.get("summary", "")]
                    + [
                        f"{f.get('description','')} {f.get('severity','')} {f.get('category','')}"
                        for f in findings
                    ]
                )
                if not _predicate_match_text(d["predicate"], combined):
                    continue
                arm_caught_any = True
                # find finding(s) that individually carry the match, else show summary
                matching = []
                for f in findings:
                    ftext = f"{f.get('description','')} {f.get('severity','')} {f.get('category','')}"
                    # a finding 'contributes' if it supplies any group token
                    groups = _which_groups_hit(d["predicate"], ftext)
                    if any(groups):
                        matching.append((f, groups))
                arm_lines.append(f"\n  ### {arm} k{k}")
                # show which finding fully matches alone, vs spread across findings
                full_alone = [
                    (f, g) for (f, g) in matching
                    if _predicate_match_text(d["predicate"], f"{f.get('description','')}")
                ]
                if full_alone:
                    arm_lines.append("  - SINGLE-FINDING match (mechanism in one finding):")
                    for f, g in full_alone:
                        arm_lines.append(
                            f"    - [{f.get('severity','')}] {f.get('description','').strip()}"
                        )
                else:
                    arm_lines.append(
                        "  - NO single finding matches alone; predicate satisfied only "
                        "by COMBINING text across findings/summary. Contributing pieces:"
                    )
                    sm = crit.get("summary", "")
                    if sm and any(_which_groups_hit(d["predicate"], sm)):
                        arm_lines.append(f"    - [summary] {sm.strip()[:500]}")
                    for f, g in matching:
                        arm_lines.append(
                            f"    - [{f.get('severity','')}] toks={g} :: {f.get('description','').strip()[:500]}"
                        )
            if arm_caught_any:
                lines.append(f"\n**{arm}: CREDITED** (cross-file)\n")
                lines.extend(arm_lines)
            else:
                lines.append(f"\n**{arm}: not credited**\n")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
