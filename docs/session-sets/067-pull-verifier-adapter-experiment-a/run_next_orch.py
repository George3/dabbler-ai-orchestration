"""Route the next-orchestrator recommendation for Set 067 Session 2.
Per project-guidance (L-064-6): never self-opine; route via analysis."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route

PROMPT = """\
Recommend the orchestrator engine/model + effort for Set 067 Session 2 of
dabbler-ai-orchestration. Reply ONLY with a JSON object:
{"engine": "...", "provider": "...", "model": "...", "effort": "low|medium|high",
 "reason": "one or two sentences (>= 30 chars)"}

Context:
- Set 067 builds the first-party tool-loop "pull" verifier adapter (pull_route())
  in ai_router, with read-only deterministic-servant tools, sandbox confinement,
  caps, a forced verdict matching the Set 066 path-aware-critique.json shape, and
  tool-call-trace instrumentation. It then runs Experiment A (capability) and
  ships a PyPI release.
- Session 1 (just completed by Claude Code, claude-opus-4-8, medium effort) built
  the loop driver, caps, the Anthropic tool_use binding, the servant + guardrail,
  the forced verdict, the trace, and 62 unit tests. Cross-provider verified
  (gpt-5.4) R1 ISSUES_FOUND (1 Critical grep sandbox breakout + 3 Major) -> all
  remediated -> R2.
- Session 2 work: add the OpenAI (tool_calls / Responses API) and Gemini
  (function_declarations) bindings behind the SAME provider-agnostic loop driver
  (per-provider request/response shaping only), wire a dedicated executor block
  into router-config.yaml, add a small 3-provider headless capability check
  (metered or recorded), and per-binding + config-loader tests. It is
  implementation-heavy provider-API integration work that benefits from continuity
  with the S1 binding interface and the Anthropic reference binding.
- Candidates: claude-opus-4-8 (incumbent, full S1 context continuity), gpt-5.4,
  gemini-2.5-pro. Weigh context-continuity vs fresh-perspective and cost.
  Verification is cross-provider regardless of who orchestrates.
"""

r = route(
    PROMPT,
    task_type="analysis",
    session_set="067-pull-verifier-adapter-experiment-a",
    session_number=1,
)
out = HERE / "next-orchestrator-rec.md"
out.write_text(
    "# Set 067 -> S2 next-orchestrator recommendation (routed)\n\n"
    f"> Routed via route(task_type='analysis'). Model used: {r.model_name} "
    f"({r.model_id})\n\n{r.content}\n",
    encoding="utf-8",
)
print(f"Wrote {out}")
print("model:", r.model_name, r.model_id, "cost:", r.cost_usd)
print(r.content[:1500])
