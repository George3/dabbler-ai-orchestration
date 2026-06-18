"""Set 071 S1 cross-provider verification (REQUIRED: contract-uncovered + high-blast)."""
import sys
sys.path.insert(0, "ai_router")
import ai_router
from ai_router import RouteResult, verify

diff = open("C:/tmp/s1_diff.txt", encoding="utf-8").read()

original_task = """\
== CONVENTIONS / BASELINE (read first) ==
- Suite baseline BEFORE this session: 2079 passed, 5 skipped. AFTER: 2126 passed, 5 skipped
  (+47, all additive: the new parametrized materiality + framing pins). No tracked failures.
- Session 1 of 3 ships NO release and NO version bump (the PyPI bump is Session 3).
  No verification.py code change in S1 (the blocking classifier is Session 2).
- This set is strictly ADDITIVE over Set 070's strong adversarial framing. L-069-2 is a
  HARD constraint: the devil's-advocate phrases ("devil's advocate", "assume the work is
  flawed", "rubber-stamp") and the dual_surface_verify._ADVERSARIAL_MARKERS must stay
  verbatim. A change that drops a strong-framing phrase is INVALID.
- Only Layer-1 (pytest) coverage is in scope for S1; no UI/UAT/E2E surface.

== TASK BEING VERIFIED (Set 071 Session 1) ==
Add a materiality + anti-nitpick layer to BOTH reviewer templates so the strong
adversarial verifier stops manufacturing immaterial Minor/false-positive findings
(the observed pytest-vs-`python -m pytest -v` churn) WITHOUT weakening the framing.

Required deliverables for S1:
1. verification.md (push template): a materiality "so what?" three-part blocking test
   (violation / impact / evidence; a finding lacking all three is a nit, not a blocker);
   an anti-nitpick clause (a correct+complete response SHOULD be VERIFIED; manufacturing
   a Minor to avoid a rubber-stamp is itself a false-positive failure; judge SEMANTIC
   equivalence not textual identity, with the `pytest` vs `python -m pytest -v` example
   named as a worthless finding); a severity anchor (Major = changes a reasonable merge
   decision) + plausible-path-to-harm escalation (anti-laundering); a non-blocking NITS
   output section. PRESERVE: the _ADVERSARIAL_MARKERS phrases, the {original_task}/
   {task_type}/{original_response} placeholders, the VERIFIED / ISSUES FOUND tokens.
2. Mirror the SAME layer into path-aware-critique.md, fitting its
   VERDICT: VERIFIED | ISSUES_FOUND + Findings (Severity/Category/Location) grammar
   (add a NITS subsection).
3. Extend test_verification_framing.py: keep all Set 070 strong-framing pins; add
   (a) materiality/anti-nitpick language present in BOTH templates, and (b) a test that
   classify_framing_strength returns ADVERSARIAL for both edited templates (additivity /
   dual-surface-equality proof).

Verify the diff below against these requirements. Attack it: is the layer actually
additive (framing intact)? Are the placeholders/tokens preserved? Does the anti-nitpick
guidance risk LAUNDERING a real defect into an ignored Minor (does the merge-impact +
plausible-path-to-harm guardrail actually counter that)? Are the test pins load-bearing
(would they catch a real weakening), or could they pass on a degenerate template? Is the
materiality language consistent across BOTH templates (L-065-1 echo discipline)? Are the
claimed suite counts plausible given the diff?
"""

response = (
    "I made the edits below. Suite after edits: 2126 passed, 5 skipped "
    "(was 2079/5; +47). The framing-pin test file test_verification_framing.py "
    "grew from 9 to 56 test cases (all additive; +47, matching the suite delta).\n"
    "The pins include full inversion-resistant clauses and a STRUCTURAL ordered-triad "
    "test ANCHORED to the Materiality section (violation->impact->evidence in order). "
    "Parser-compatibility regression tests (no verification.py change in S1): "
    "VERIFIED-with-trailing-NITS parses clean (verdict VERIFIED, zero issues); "
    "ISSUES-FOUND-with-trailing-NITS preserves verdict AND issue-count vs the no-NITS "
    "baseline (the existing parser folds trailing text into the last issue's "
    "description, so this is verdict/count compatibility, NOT byte-identical parsing; "
    "tightening that capture is scoped to S2).\n\n"
    "Unified diff of the three changed files:\n\n```diff\n" + diff + "\n```\n"
)

rr = RouteResult(
    content=response,
    model_name="opus",
    model_id="opus",
    tier=3,
    input_tokens=0, output_tokens=0, cost_usd=0.0, total_cost_usd=0.0,
    complexity_score=0, escalated=False, escalation_history=[],
    elapsed_seconds=0.0, truncated=False, verification=None,
)

res = verify(
    rr,
    original_task=original_task,
    task_type="session-verification",
    session_set="071-verifier-materiality-and-nitpick-discipline",
    session_number=1,
)

print("VERIFIER:", res.verifier_provider, res.verifier_model)
print("VERDICT:", res.verdict, "| verified:", res.verified)
print("ISSUES:", len(res.issues))
print("COST_USD:", res.verifier_cost_usd)
print("=" * 70)
print(res.raw_response)
