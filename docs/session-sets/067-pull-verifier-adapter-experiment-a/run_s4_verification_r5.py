"""Set 067 S4 - R5 re-verification with CORRECT evidence (L-064-9: pull_critique.py
and its test are UNTRACKED, so git diff showed them empty in R4 -> a false
'fixes absent' negative). Provide full content for the untracked files.
"""
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
TASK = f"""Round 5 verification, Set 067 Session 4. NOTE: Round 4 reported fixes
2-4 'absent from the diff' - that was a FALSE NEGATIVE: ai_router/pull_critique.py
and ai_router/tests/test_pull_critique.py are NEW UNTRACKED files, so git diff
omitted them (L-064-9). Here is their FULL CONTENT. Confirm each fix is present
and correct with no regression. Do NOT re-flag the agreed baseline (suite green
at 1500+; producer opt-in; 068 deferrals; ASCII-only; caps POST-HOC by design -
a single in-flight call may overshoot a ceiling by its own output-capped size).

FIXES TO VERIFY:
1. ai_router/pull_verifier.py (TRACKED, see diff): budget-aware forced verdict -
   pull_route forces submit_verdict when ONE MORE call of the last call's
   measured size (last_call_tokens/last_call_cost) would breach either ceiling
   (adaptive reserve, replacing the R3-flagged fixed fraction). Verify it yields
   a verdict instead of an empty budget stop, does not break the hard-ceiling
   stops, and is honest that caps are post-hoc.
2. ai_router/pull_critique.py produce_path_aware_critique: resolves
   session_set_dir via Path(...).resolve() BEFORE deriving .name (so a '.' /
   trailing-slash / symlink invocation stamps the real sessionSetName, not
   empty). See line ~ 'set_dir = Path(session_set_dir).resolve()'.
3. build_instruction: isinstance-guards a non-string disposition 'summary'
   before str.replace (raw_summary if isinstance(...,str) and .strip() else
   fallback).
4. _main: ASCII-sanitizes the PullCritiqueError path (_ascii(exc)).
Tests for 2 and 3 (and the dot-invocation) are in the full test content below.

Reply one-line VERDICT (VERIFIED or ISSUES_FOUND); if ISSUES_FOUND, Findings.

=== DIFF: ai_router/pull_verifier.py (tracked) ===
{diff('ai_router/pull_verifier.py')}

=== FULL FILE: ai_router/pull_critique.py (untracked) ===
{read('ai_router/pull_critique.py')}

=== FULL FILE: ai_router/tests/test_pull_critique.py (untracked) ===
{read('ai_router/tests/test_pull_critique.py')}
"""
result = route(TASK, task_type="session-verification", max_tier=3)
out = SET_DIR / "s4-verification-round-5.md"
out.write_text(result.content, encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars)")
