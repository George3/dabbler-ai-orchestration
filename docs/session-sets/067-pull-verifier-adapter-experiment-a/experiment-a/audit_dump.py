"""Set 067 S3 Experiment A - audit dump for manual adjudication.

Dumps every (routed-arm x cross-file-defect) cell that the automated grade
matched, plus path-aware catches/misses on the same defects for context, with
the relevant text excerpts, so the orchestrator can adjudicate per the
pre-registered audit rule: a routed catch of a CROSS-FILE defect counts only if
the text identifies the ACTUAL defect mechanism (real duplicate / key mismatch /
incompleteness), not a generic conditional hypothetical. Read-only; no API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade  # noqa: E402

RAW = HERE / "raw"
K = grade.K
CROSS = [d["id"] for d in grade.DEFECTS if d["label_context"] == "cross-file"]


def _run_text(tree, arm, k):
    p = RAW / tree / f"{arm}_k{k}.json"
    if not p.exists():
        return None, None
    rec = json.loads(p.read_text(encoding="utf-8"))
    return rec, grade._matched(rec, tree)


def main():
    for did in CROSS:
        d = grade.DEFECT[did]
        tree = d["tree"]
        print("=" * 78)
        print(f"{did} [{d['severity']}, cross-file] {tree} :: {d['class']}")
        print(f"  TRUTH: {d['description']}")
        for arm in ["A1", "A2", "B1", "B2"]:
            caught_ks = []
            for k in range(1, K + 1):
                rec, caught = _run_text(tree, arm, k)
                if rec is None:
                    continue
                if did in caught:
                    caught_ks.append(k)
            tag = "routed" if arm in grade.ROUTED else "path-aware"
            print(f"  -- {arm} ({tag}): automated-caught in K={caught_ks}")
            # For routed cross-file matches, dump the deciding text excerpt.
            if arm in grade.ROUTED and caught_ks:
                rec, _ = _run_text(tree, arm, caught_ks[0])
                text = (rec.get("content") or "")
                # crude: print lines mentioning a predicate anchor token
                anchors = [a for grp in d["predicate"]["all"] for a in grp]
                lines = [ln for ln in text.splitlines()
                         if any(a.lower() in ln.lower() for a in anchors)]
                for ln in lines[:6]:
                    print(f"       | {ln.strip()[:160]}")


if __name__ == "__main__":
    main()
