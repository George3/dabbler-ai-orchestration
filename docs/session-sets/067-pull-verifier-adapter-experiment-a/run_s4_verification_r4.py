"""Set 067 S4 - R4 verification of the dogfood-driven fixes (final code)."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import route  # noqa: E402
SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"
def read(p): return (REPO / p).read_text(encoding="utf-8")
def diff(p):
    return subprocess.run(["git","--no-pager","diff","--",p], cwd=REPO,
                          capture_output=True, text=True).stdout
TASK = f"""Round 4 targeted verification, Set 067 Session 4. The S4 path-aware
DOGFOOD (GPT-5.4, repo-reading) found defects beyond the routed R1-R3 review;
all were folded. Confirm each fix is correct with no regression. Do NOT re-flag
the agreed baseline (suite green at 1500+; producer opt-in; run_test/contract-
gate/Experiment B deferred to 068; ASCII-only; caps are POST-HOC per
tool-contract sec 5 - a single in-flight call may overshoot a ceiling by its own
output-capped size, by design).

FIXES TO VERIFY (all in ai_router/pull_verifier.py and ai_router/pull_critique.py):
1. BUDGET-AWARE FORCED VERDICT (replaces the R3-flagged fixed 0.85 fraction):
   pull_route now forces submit_verdict when ONE MORE call of the LAST call's
   measured size (last_call_tokens/last_call_cost) would breach either ceiling -
   an adaptive headroom reserve. Verify it (a) yields a verdict instead of an
   empty token/cost-budget stop on a verbose prober, (b) does not break the
   existing hard-ceiling stops, (c) bounds overshoot to ~one observed call and
   the code/comment is honest that caps are post-hoc (not a false "guaranteed
   headroom" claim).
2. produce_path_aware_critique resolves session_set_dir BEFORE deriving the set
   name (Path.resolve().name), so a '.' / trailing-slash / symlink invocation no
   longer stamps an empty or wrong sessionSetName.
3. build_instruction isinstance-guards a non-string disposition 'summary' so it
   cannot raise TypeError in str.replace.
4. _main ASCII-sanitizes the PullCritiqueError path (_ascii(exc)).

Reply one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, Findings
(Severity/Category/Location/Description+fix).

=== DIFF: ai_router/pull_verifier.py ===
{diff('ai_router/pull_verifier.py')}

=== DIFF: ai_router/pull_critique.py ===
{diff('ai_router/pull_critique.py')}

=== DIFF: ai_router/tests/test_pull_verifier.py ===
{diff('ai_router/tests/test_pull_verifier.py')}

=== DIFF: ai_router/tests/test_pull_critique.py ===
{diff('ai_router/tests/test_pull_critique.py')}
"""
result = route(TASK, task_type="session-verification", max_tier=3)
out = SET_DIR / "s4-verification-round-4.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars)")
