"""Set 067 S4 - route the next-orchestrator recommendation for Set 068 S1."""
from __future__ import annotations
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))
from ai_router import route  # noqa: E402
SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"
PROMPT = """Recommend the orchestrator engine/model/effort for Set 068 Session 1
in the dabbler-ai-orchestration repo. Set 067 just shipped (ai_router 0.21.0:
the pull-verifier adapter + Experiment A capability study + an opt-in
path-aware-critique producer). Set 068 Session 1 is expected to implement the
disposable-worktree run_test sandbox + run_test tool: a write-caged execution
capability (git worktree isolation, sandboxed test runs) that is the hard
prerequisite for Experiment B (the cadence study), the routed
keep/demote/retire decision, and the contract-test gate. This S1 is real
production code with security-sensitive sandboxing (write isolation, worktree
lifecycle). Available engines: claude-code (Anthropic: claude-opus-4-8,
claude-sonnet-4-6), codex (OpenAI: gpt-5.4), gemini (google: gemini-2.5-pro).
Reply ONLY with a JSON object: {"engine","provider","model","effort","reason"}
where effort is one of low|medium|high. ASCII-only."""
result = route(PROMPT, task_type="analysis")
out = SET_DIR / "next-orchestrator-rec.md"
out.write_text(
    "# Set 067 -> Set 068 S1 next-orchestrator recommendation (routed)\n\n"
    f"> Routed via route(task_type='analysis'). Model: {getattr(result,'model','?')}\n\n"
    f"```json\n{result.content}\n```\n", encoding="utf-8")
print(f"Wrote {out} ({len(result.content)} chars)")
print(result.content)
