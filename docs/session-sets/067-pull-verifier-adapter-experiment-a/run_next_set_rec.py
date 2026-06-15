"""Set 067 S4 - route the next-session-set (068) recommendation (L-064-6).

Routed analysis, never self-opined. Writes raw output to disk first (L-064-3).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))

from ai_router import route  # noqa: E402

SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"

PROMPT = """You are advising on the NEXT session set after Set 067 in the
dabbler-ai-orchestration repo (canonical source for shared AI orchestration
infra: the ai_router Python package + a VS Code extension).

Set 067 just SHIPPED (ai_router 0.21.0):
- A first-party tool-loop "pull" verifier adapter (pull_route): the verifier
  drives a read-only tool loop (read_file/grep/list_dir); the orchestrator is a
  deterministic servant returning raw ground truth. Anthropic + OpenAI + Gemini
  bindings; capped, sandbox-confined, instrumented.
- Experiment A (capability): CONFIRMED that path-aware critique catches real
  cross-file defects routed single-shot misses; the edge is context-access not a
  second provider; routed's unique-capability defense is RULED OUT (only its
  CADENCE defense survives); falsifier coverage ~95%.
- An OPT-IN automated producer (python -m ai_router.pull_critique) that writes
  the Set 066 path-aware-critique.json artifact via the adapter.

Set 067's spec explicitly DEFERS the following to Set 068:
1. The disposable-worktree run_test sandbox + the run_test tool (the only tool
   needing a write cage).
2. Experiment B (cadence / staged-snapshot intervention study) - the only
   surviving defense for routed per-session verification.
3. The routed keep / demote / retire decision (gated on Experiment B).
4. The contract-test / CDC gate (Experiment A H4 showed ~95% of defects are
   deterministically falsifiable; reserve the agent for the non-probeable
   residual + for authoring falsifiers).

Recommend the next session set: its slug, a 1-2 sentence goal, an estimated
session count, and the ordering of the four deferred items above (what must come
first and why). Note any dependency (e.g. does the run_test sandbox block
Experiment B?). Be concrete and concise. Reply in plain prose, ASCII-only."""

result = route(PROMPT, task_type="analysis")
out = SET_DIR / "next-set-rec-068.md"
out.write_text(
    f"# Set 067 -> next-session-set (068) recommendation (routed)\n\n"
    f"> Routed via route(task_type='analysis'). Model: "
    f"{getattr(result, 'model', '?')}\n\n{result.content}\n",
    encoding="utf-8",
)
print(f"Wrote {out} ({len(result.content)} chars); model={getattr(result,'model','?')}")
