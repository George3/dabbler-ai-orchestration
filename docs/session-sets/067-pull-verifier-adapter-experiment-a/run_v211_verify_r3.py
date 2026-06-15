"""R3 verification of the 0.21.1 R2 fix (bounded vs unbounded brace in ReDoS guard)."""
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
    "Round 3 verification of the dabbler-ai-router 0.21.1 ReDoS guard. Round 2 "
    "found one Moderate false-positive: the nested-quantifier scanner treated "
    "ANY brace after a quantifier-bearing group as a dangerous outer quantifier, "
    "so safe BOUNDED reps like (a+){2} or (ab(c+)d){3} were wrongly rejected. "
    "FIX: _brace_quant_at() now classifies a brace as 'unbounded' ({n,}) vs "
    "'bounded' ({n} / {n,m}) vs literal; the scanner flags only when an "
    "UNBOUNDED outer quantifier (* + or {n,}) is applied to a body that itself "
    "contains an UNBOUNDED quantifier (* + or {n,}), and body detection now also "
    "marks an unbounded {n,} (so (a{2,})+ is still caught). Confirm:\n"
    "- still catches: (a+)+, (.*)*, ((a+))+, (ab(c+)d)+, (a+){2,}, (a{2,})+;\n"
    "- no longer false-positives: (a+){2}, (ab(c+)d){3}, (a{2,3})+, (\\d{3})+, "
    "(foo|bar)+, (a+)?, character classes like [*+]+, escaped parens;\n"
    "- the scanner itself is linear (no backtracking) and _BRACE_RE is anchored "
    "(re.match) so it cannot scan the whole pattern per '{'.\n"
    "Do NOT re-flag the agreed baseline (suite green; producer opt-in; 068 "
    "deferrals; caps post-hoc; this is a HEURISTIC, full isolation is 068).\n\n"
    "Reply one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, "
    "Findings (Severity/Category/Location/Description+fix).\n\n"
    "=== DIFF: ai_router/pull_verifier.py ===\n"
    + diff("ai_router/pull_verifier.py")
    + "\n=== DIFF: ai_router/tests/test_pull_verifier.py ===\n"
    + diff("ai_router/tests/test_pull_verifier.py")
)

r = route(TASK, task_type="session-verification", max_tier=3)
out = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a/v0.21.1-verification-round-3.md"
out.write_text(r.content, encoding="utf-8")
print("Wrote", out, len(r.content), "chars")
