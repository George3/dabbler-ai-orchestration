"""Set 069 S6 -- routed verification of the DOGFOOD PATCH (Step 6).

The S6 dogfood (the new execution-capable producer over this set's own diff)
caught two defects the S5 per-session routed verification missed:
  (1) Major: check_floor_ratchet_coverage matched coverage on a finding's free-text
      DESCRIPTION as well as the stable ref -> one description-keyed candidate could
      cover several distinct reproduced defects. FIX: removed the description
      fallback; coverage matches only the stable "<provider>:<index>" ref.
  (2) Minor: the scoreboard schema described falseReproduced as "without a valid
      replay" (implying it derives from `replayed`), but score_benchmark records it
      as an INDEPENDENT integrity flag (a replay can run yet validate the wrong
      entrypoint). FIX: clarified the schema prose; the code is unchanged.
Verify the patch is correct, complete, and introduces no regression. gpt-5-4
(top tier; no escalation risk, L-064-7).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

FILES = [
    "ai_router/floor_ratchet.py",
    "ai_router/tests/test_floor_ratchet.py",
    "docs/replacement-scoreboard.schema.json",
    "ai_router/CHANGELOG.md",
]
DIFF = subprocess.run(
    ["git", "diff", "HEAD", "--", *FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout
COVERAGE_SRC = subprocess.run(
    [sys.executable, "-c",
     "import inspect,ai_router.floor_ratchet as fr;"
     "print(inspect.getsource(fr.check_floor_ratchet_coverage))"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider verifier for the Set 069 S6 DOGFOOD PATCH. Return the
structured verdict. This is a narrow patch review, not a whole-session re-review.

CONTEXT: the new execution-capable pull_critique producer (the very feature Set 069
shipped), run over this set's own diff, caught two defects in the S5 code that the
S5 per-session routed verification had missed. Both are now fixed. Confirm each fix
is correct + complete and introduces no regression. The full ai_router suite is
GREEN at this commit (incl. the new regression test). Do not invent new issues.

FIX 1 (Major -> resolved?). `check_floor_ratchet_coverage` previously accepted a
candidate as covering a reproduced finding when the candidate's `defect.findingRef`
equaled EITHER the stable "<provider>:<index>" ref OR the finding's free-text
`description`. Because descriptions are not unique, one description-keyed candidate
could satisfy coverage for several distinct reproduced defects -- under-enforcing
the mandatory rule (every reproduced probeable defect needs its OWN candidate). The
fix removes the description fallback so coverage matches ONLY the stable ref.
Confirm: (a) the description fallback is gone; (b) the stable-ref match still works
(a candidate built by build_candidate_from_finding, which records the stable
finding_ref, still covers its finding); (c) the new regression test actually
exercises the hole (a description-keyed candidate no longer covers a distinct
finding); (d) no legitimate coverage path is broken (admitted/pending/waived still
count; rejected still does not). Here is the patched function in full:

{COVERAGE_SRC}

FIX 2 (Minor -> resolved?). The replacement-scoreboard schema described
`falseReproduced` as "wrongly tagged REPRODUCED without a valid replay", implying
it is derived from `replayed == false`. But `score_benchmark` records it as an
INDEPENDENT flag (a replay can run yet validate the wrong entrypoint -- a
meta-oracle failure -- so a detection can be replayed=true AND falseReproduced=true).
The fix clarifies the schema description to state it is an independent integrity
flag, NOT derived from `replayed`; the code is intentionally unchanged. Confirm the
new prose is accurate and consistent with `score_benchmark`'s arithmetic
(false_reproduced counts any detected outcome with falseReproduced=true, regardless
of replayed), and that the CHANGELOG entry describes this correctly.

Return: verdict (VERIFIED or ISSUES_FOUND), one-line summary, and any residual
issue (file + quoted text + correction). VERIFIED if both fixes are correct and
complete.

=== STAGED/HEAD DIFF (the patch) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=45,
        max_tier=3,
        session_set=str(HERE),
        session_number=6,
    )
    out = HERE / "s6-patch-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
