"""Set 067 S4 - R2 re-verification of the two R1 fixes."""
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
TASK = f"""Round 2 re-verification, Set 067 Session 4. In Round 1 you returned
ISSUES_FOUND with two findings on ai_router/pull_critique.py. Both were fixed.
Confirm each fix resolves the finding and introduces no regression. This is a
TARGETED re-verify - do not re-flag the agreed baseline (suite 1503 passed/1
skipped; producer is opt-in; run_test/contract-gate/Experiment B deferred to
068; ASCII-only convention).

R1 FINDING 1 (Medium, correctness): the level/--level override could write a
structurally-valid artifact whose pathAwareCritique level disagreed with the
set's recorded policy, which validate_path_aware_critique_gate would then reject
(written-but-gate-rejected), breaking "refuses to write a gate-failing
artifact". FIX: a write-mode gate-identity guard - in write mode the stamped
level MUST equal read_path_aware_critique(set_dir); an override is allowed only
on a dry run (write=False). New/changed tests:
test_explicit_level_override_allowed_only_on_dry_run and
test_write_mode_refuses_level_mismatching_recorded_policy.

R1 FINDING 2 (Low, encoding): the CLI printed unsanitized dynamic text
(providers/skipped/reasons/written_to), violating ASCII-only on cp1252. FIX: an
_ascii() helper (encode ascii backslashreplace) wraps every dynamic CLI field.

Verify both. Reply with a one-line VERDICT (VERIFIED or ISSUES_FOUND); if
ISSUES_FOUND, a Findings list (Severity/Category/Location/Description+fix).

=== DIFF: ai_router/pull_critique.py ===
{diff('ai_router/pull_critique.py')}

=== DIFF: ai_router/tests/test_pull_critique.py ===
{diff('ai_router/tests/test_pull_critique.py')}
"""
result = route(TASK, task_type="session-verification", max_tier=3)
out = SET_DIR / "s4-verification-round-2.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars); model={getattr(result,'model','?')}")
