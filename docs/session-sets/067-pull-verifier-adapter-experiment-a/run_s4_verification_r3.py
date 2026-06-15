"""Set 067 S4 - R3 verification of the budget-aware forced-verdict adapter fix."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import route  # noqa: E402
SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"
def diff(p):
    return subprocess.run(["git","--no-pager","diff","--",p], cwd=REPO,
                          capture_output=True, text=True).stdout
TASK = f"""Round 3 targeted verification, Set 067 Session 4. The S4 dogfood
surfaced an adapter defect: frontier reasoning models (GPT-5.4 at 28 probes,
Sonnet at 18) over-probe and exhaust the token/cost budget WITHOUT ever calling
submit_verdict, because the loop's only forced-verdict trigger was the final
turn (turn == max_turns-1), and the hard budget/cost ceiling breaks the loop at
the top BEFORE that final turn is reached -> an empty run (stop=token-budget /
cost-ceiling, no verdict). FIX (ai_router/pull_verifier.py): a budget-aware
forced verdict - once cumulative spend crosses _FORCE_VERDICT_BUDGET_FRACTION
(0.85) of EITHER the token budget OR the cost ceiling, force submit_verdict on
that call so the model commits a verdict from what it has read instead of being
cut off empty.

Verify: (1) the guard correctly fires before the hard ceiling and yields a
verdict (stop=verdict), not after; (2) it does NOT break the existing hard-stop
caps (a run that crosses the ceiling with no prior near-budget turn still stops
STOP_TOKEN_BUDGET/STOP_COST_CEILING); (3) 0.85 leaves headroom for one more
forced (short) call under the hard ceiling; (4) no regression to the
deterministic-servant / sandbox / trace invariants. Do NOT re-flag the agreed
baseline (suite green; producer opt-in; 068 deferrals; ASCII-only). This is a
small, isolated diff.

Reply with a one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, a
Findings list (Severity/Category/Location/Description+fix).

=== DIFF: ai_router/pull_verifier.py ===
{diff('ai_router/pull_verifier.py')}

=== DIFF: ai_router/tests/test_pull_verifier.py ===
{diff('ai_router/tests/test_pull_verifier.py')}
"""
result = route(TASK, task_type="session-verification", max_tier=3)
out = SET_DIR / "s4-verification-round-3.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars)")
