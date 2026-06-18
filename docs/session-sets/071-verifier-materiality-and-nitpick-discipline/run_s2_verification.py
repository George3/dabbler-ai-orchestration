"""Set 071 S2 — cross-provider session verification (routed gate REQUIRED).

routed_gate => REQUIRED (blast-radius/multi-module/breadth) + the shared
verification surface is high-blast. Verifier is GPT-5.4 (openai), a different
provider than the Claude/anthropic orchestrator. Strong adversarial framing
(verification.md). Raw output saved to sN-verification[-round-M].md (never
edited). Pass the round on the CLI: `run_s2_verification.py [round]`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import ai_router
from ai_router import build_verification_prompt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROUND = int(sys.argv[1]) if len(sys.argv) > 1 else 1

CONVENTIONS = """\
## Up-front conventions (read before reviewing — Set 071 Session 2)

**Suite baseline:** full pytest suite is **2150 passed / 5 skipped** on this
diff (was 2126/5 after S1; +24 new tests). The 5 skips are pre-existing
real-Podman-on-Windows skips (by design). All Set 070 framing-pin tests in
test_verification_framing.py still pass (additivity proof). Do NOT flag the
baseline as a defect.

**Release contract:** NO release this session. ai_router is NOT version-bumped
and NOT published in S2 — the PyPI minor release is Session 3's deliverable.
Do not flag the absent version bump / changelog as a defect.

**Operator decision (settled):** the verdict grammar stays **BINARY**
(VERIFIED / ISSUES_FOUND). This was an explicit operator decision point in the
spec, routed to a cross-provider consult (GPT-5.4 + Gemini-Pro + a fresh Claude
synthesis), which converged UNANIMOUSLY on binary. Do NOT recommend adding a
third verdict token (VERIFIED_WITH_NITS); that was considered and rejected this
session by design. Blocking-ness is intentionally a derived predicate
(is_blocking_verdict), NOT the bare verdict token.

**Scope of S2 (what to check):**
1. `ai_router/verification.py` — the severity-anchored blocking classifier
   (`is_blocking_verdict`, `classify_blocking`/`BlockingClassification`) and the
   cross-round issue ledger (`reconcile_issue_ledger`/`LedgerReconciliation`),
   PLUS a load-bearing fix to `parse_verification_response` (the
   "ISSUES FOUND" header self-match + the "**Severity:** Minor" regex that could
   not read a markdown-bold severity). The `(verdict, issues)` contract is
   preserved.
2. `docs/ai-led-session-workflow.md` — the new Step-6 subsection "Materiality
   and the re-verify loop discipline (Set 071)" + the Step-7 and Mode-B wiring.
3. `ai_router/tests/test_blocking_classifier.py` — the classifier matrix, the
   verbatim `pytest`-vs-`python -m pytest -v` churn regression (must classify
   non-blocking), and the ledger tests.

**By-design judgment to weigh, not flag as a gap:** the "no resurrection under
new wording" rule is enforced in code only on the **stable id** (a RESOLVED id
cannot reopen). Recognising that two *differently-worded* findings are the same
point is the orchestrator's judgment, documented as such in the loop-discipline
subsection. That split is intentional, not an oversight.

**Hard constraint (L-069-2):** the strong devil's-advocate framing must NOT be
weakened. This change is strictly additive over it. Apply your own materiality
bar: report Critical/Major defects with the three-part "so what?" (violation /
impact / evidence); put immaterial observations under NITS — do not manufacture
a Minor to avoid a clean verdict.
"""

ORIGINAL_TASK = CONVENTIONS + "\n\n" + (HERE / "spec.md").read_text(encoding="utf-8")


def staged_diff() -> str:
    return subprocess.run(
        ["git", "diff", "--cached", "--", "ai_router", "docs/ai-led-session-workflow.md"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout


def main() -> None:
    diff = staged_diff()
    verif_py = (REPO / "ai_router" / "verification.py").read_text(encoding="utf-8")
    test_py = (REPO / "ai_router" / "tests" / "test_blocking_classifier.py").read_text(encoding="utf-8")

    response = (
        "# Set 071 S2 — changes under review\n\n"
        "The unified diff of the staged S2 deliverables follows, then the full "
        "current content of the two most load-bearing files (the classifier/parser "
        "and its tests) so you can reason from ground truth, not just the diff.\n\n"
        "## Staged diff (git diff --cached)\n\n```diff\n" + diff + "\n```\n\n"
        "## Full current ai_router/verification.py\n\n```python\n" + verif_py + "\n```\n\n"
        "## Full current ai_router/tests/test_blocking_classifier.py\n\n```python\n"
        + test_py + "\n```\n"
    )

    template = (REPO / "ai_router" / "prompt-templates" / "verification.md").read_text(encoding="utf-8")
    prompt = build_verification_prompt(
        original_task=ORIGINAL_TASK,
        original_response=response,
        task_type="session-verification",
        template=template,
    )

    res = ai_router.query(
        model="gpt-5-4",
        content=prompt,
        task_type="session-verification",
        session_set=str(HERE),
        session_number=2,
    )
    name = "s2-verification.md" if ROUND == 1 else f"s2-verification-round-{ROUND}.md"
    out = HERE / name
    out.write_text(res.content, encoding="utf-8")
    print(f"round {ROUND} -> {out.name} ({len(res.content)} chars, "
          f"model={getattr(res, 'model_name', 'gpt-5-4')}, "
          f"cost={getattr(res, 'cost', 'n/a')})")


if __name__ == "__main__":
    main()
