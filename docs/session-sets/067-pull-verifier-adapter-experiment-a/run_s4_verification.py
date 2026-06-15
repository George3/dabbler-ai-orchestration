"""Set 067 S4 - cross-provider session verification of the producer + release."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import route  # noqa: E402
SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"

def read(p):
    return (REPO / p).read_text(encoding="utf-8")

def diff(p):
    return subprocess.run(["git", "--no-pager", "diff", "--", p], cwd=REPO,
                          capture_output=True, text=True).stdout

CONVENTIONS = """## Up-front conventions (read first; do not re-flag these)

- SUITE BASELINE: full Python suite is GREEN at 1503 passed / 1 skipped. The 1
  skip is long-standing (pre-existing). 11 of the passing tests are new this
  session (test_pull_critique.py). No metered API calls run in unit tests.
- RELEASE CONTRACT: this session bumps ai_router 0.20.0 -> 0.21.0 and publishes
  to PyPI (tag v0.21.0) via the green-Test-on-tagged-SHA runbook. NO Marketplace
  bump (no extension change). Routed per-session verification is UNCHANGED by
  design.
- BY-DESIGN SCOPE: the producer is STRICTLY OPT-IN (nothing in the normal
  session flow invokes it; the manual GitHub-Copilot flow stays the default).
  No UI / Explorer surface (deferred). The run_test sandbox, contract-test gate,
  Experiment B, and the routed keep/demote/retire decision are deliberately
  DEFERRED to Set 068 - do not flag their absence.
- This is Session 4 of 4 (final). Experiment A (S3, already cross-provider
  verified) CONFIRMED path-aware capability, which is why S4 wires the producer.
- ASCII-only terminal output is a project convention (Windows cp1252)."""

TASK = f"""You are the cross-provider session verifier for Set 067 Session 4
(final) of dabbler-ai-orchestration. The session wired the first-party pull
verifier (ai_router/pull_verifier.py, shipped S1-S2) as an OPT-IN automated
PRODUCER of the Set 066 path-aware-critique.json artifact, plus docs + an
ai_router 0.21.0 release.

{CONVENTIONS}

## What to verify

Confirm the producer is correct and cannot emit a gate-passing-but-bogus
artifact (or refuse a valid one). Specifically:
1. Multi-provider invariant: produce_path_aware_critique must REFUSE to write
   when fewer than 2 DISTINCT providers return a usable verdict; distinctness is
   keyed off the adapter-stamped critique.provider, not the requested provider.
2. Identity stamping: the artifact stamps sessionSetName (= set dir name) and
   the recorded pathAwareCritique level, so validate_path_aware_critique_gate's
   identity check accepts it for THIS set under THIS policy.
3. The assembled envelope is validated with the SAME runtime validator the gate
   uses (validate_path_aware_critique_artifact) BEFORE writing.
4. A failing/raising provider run is SKIPPED, not fatal to the others.
5. L-064-3 (write utf-8 to disk), ASCII-only CLI status, no metered calls in
   tests.
6. The __init__ export, the version bump, the CHANGELOG entry, and the docs are
   consistent with the code.

Reply with a one-line VERDICT (VERIFIED or ISSUES_FOUND) then, if ISSUES_FOUND,
a Findings list (Severity / Category / Location file:line / Description with the
ground truth and the fix). Only substantiated defects.

=== NEW FILE: ai_router/pull_critique.py ===
{read('ai_router/pull_critique.py')}

=== NEW FILE: ai_router/tests/test_pull_critique.py ===
{read('ai_router/tests/test_pull_critique.py')}

=== DIFF: ai_router/__init__.py ===
{diff('ai_router/__init__.py')}

=== DIFF: pyproject.toml ===
{diff('pyproject.toml')}

=== DIFF: ai_router/CHANGELOG.md ===
{diff('ai_router/CHANGELOG.md')}

=== DIFF: docs/path-aware-critique-schema.md ===
{diff('docs/path-aware-critique-schema.md')}

=== NEW FILE: ai_router/docs/pull-verifier.md ===
{read('ai_router/docs/pull-verifier.md')}

For context, the contract this producer targets is
ai_router/path_aware_critique.py (validate_path_aware_critique_artifact /
validate_path_aware_critique_gate) and the adapter is
ai_router/pull_verifier.py (pull_route / PullResult / PullCritique)."""

result = route(TASK, task_type="session-verification")
out = SET_DIR / "s4-verification.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars); model={getattr(result,'model','?')}")
