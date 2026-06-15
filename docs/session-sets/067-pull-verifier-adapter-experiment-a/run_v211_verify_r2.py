"""R2 verification of the two 0.21.1 R1 fixes (no f-string brace pitfalls)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import route  # noqa: E402


def diff(p):
    return subprocess.run(
        ["git", "--no-pager", "diff", "--", p], cwd=REPO,
        capture_output=True, text=True,
    ).stdout


TASK = (
    "Round 2 verification of the dabbler-ai-router 0.21.1 patch. Round 1 found "
    "TWO Major issues; both were fixed. Confirm each is resolved with no "
    "regression. Do NOT re-flag the agreed baseline (suite green; producer "
    "opt-in; 068 deferrals; ASCII-only; caps post-hoc).\n\n"
    "R1 FINDING A (Protocol): a turn with multiple/sibling submit_verdict calls "
    "left extra verdict calls unanswered -> potential provider 400. FIX: "
    "pull_route iterates ALL verdict_calls (finalizing on the first VALID one "
    "and breaking; the break path needs no answers since the loop ends), and on "
    "the continue path emits a tool_result for EVERY non_verdict_call AND EVERY "
    "verdict_call (each invalid one gets its error text). Verify every tool_use "
    "on a non-terminating turn is answered and the valid-verdict break path is "
    "correct.\n\n"
    "R1 FINDING B (Security/ReDoS): the single-regex heuristic missed nested "
    "groups like ((a+))+ and (ab(c+)d)+. FIX: replaced with "
    "_has_nested_quantifier(), a linear single-pass scanner with a group stack "
    "that propagates an inner unbounded quantifier (* or +) outward through "
    "group boundaries and flags when an unbounded-quantifier-bearing group is "
    "itself quantified. Char classes and escapes are skipped. Verify it catches "
    "the nested variants, does NOT false-positive on normal patterns "
    "(alternation groups, bounded {n} reps, quantifier chars inside a character "
    "class, escaped parens), and is itself linear (not ReDoS-prone).\n\n"
    "Reply one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, "
    "Findings (Severity/Category/Location/Description+fix).\n\n"
    "=== DIFF: ai_router/pull_verifier.py ===\n"
    + diff("ai_router/pull_verifier.py")
    + "\n=== DIFF: ai_router/tests/test_pull_verifier.py ===\n"
    + diff("ai_router/tests/test_pull_verifier.py")
)

r = route(TASK, task_type="session-verification", max_tier=3)
out = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a/v0.21.1-verification-round-2.md"
out.write_text(r.content, encoding="utf-8")
print("Wrote", out, len(r.content), "chars")
