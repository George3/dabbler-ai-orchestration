"""Set 067 S4 - R6 verification of the gate path-canonicalization fix."""
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
TASK = f"""Round 6 targeted verification, Set 067 Session 4 (final code change).
The S4 path-aware dogfood found a path-canonicalization ASYMMETRY: the Set 067
producer (ai_router/pull_critique.py) resolves session_set_dir before stamping
sessionSetName, but ai_router/path_aware_critique.py:validate_path_aware_critique_gate
derived the expected name from the UNRESOLVED basename - so a non-canonical
invocation ('.', trailing slash, symlink) could WRITE an artifact the gate then
REJECTS (wrong/empty expected name), violating the producer's 'refuses to write
a gate-failing artifact' guarantee. FIX: the gate now uses
Path(session_set_dir).resolve().name so producer and gate canonicalize
identically. New tests assert (a) a produced artifact passes the REAL gate
end-to-end, and (b) producer+gate agree on a '.' invocation.

Verify: the gate fix is correct and does NOT weaken the existing identity check
(a genuinely cross-set / wrong-level artifact is still rejected); resolving only
canonicalizes spelling, it does not relax the sessionSetName/level match. Do NOT
re-flag the agreed baseline (suite green; producer opt-in; 068 deferrals;
ASCII-only; caps post-hoc). Small isolated diff.

Reply one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, Findings.

=== DIFF: ai_router/path_aware_critique.py (tracked) ===
{diff('ai_router/path_aware_critique.py')}

=== Relevant NEW tests (untracked file excerpt) ===
{read('ai_router/tests/test_pull_critique.py')}
"""
result = route(TASK, task_type="session-verification", max_tier=3)
out = SET_DIR / "s4-verification-round-6.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars)")
