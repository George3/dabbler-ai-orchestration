"""Route the next-orchestrator recommendation for Set 067 Session 3.
Per project-guidance (L-064-6): never self-opine; route via analysis."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route

PROMPT = """\
Recommend the orchestrator engine/model + effort for Set 067 Session 3 of
dabbler-ai-orchestration. Reply ONLY with a JSON object:
{"engine": "...", "provider": "...", "model": "...", "effort": "low|medium|high",
 "reason": "one or two sentences (>= 30 chars)"}

Context:
- Set 067 builds the first-party tool-loop "pull" verifier adapter (pull_route())
  in ai_router and then runs Experiment A (a controlled capability study) before
  shipping a PyPI release.
- Session 1 (Claude Code, claude-opus-4-8) shipped the loop driver, caps, the
  Anthropic binding, the deterministic-servant guardrail, the forced verdict, and
  the trace. Session 2 (Claude Code, claude-opus-4-8, medium) just added the
  OpenAI (Responses-API function tools) and Gemini (function_declarations)
  bindings behind the same provider-agnostic driver, wired the router-config
  pull_verifier executor block + resolvers, ran a 3-provider headless capability
  check (all three drove the read-only loop, issued real probes, returned
  schema-valid verdicts, and all caught a seeded defect), and added tests
  (pull_verifier suite now 86). Cross-provider verified (gpt-5.4): R1 ISSUES_FOUND
  (3 Minor) -> R2 (1 Minor) -> R3 VERIFIED.
- Session 3 work is DIFFERENT in character: it is an EMPIRICAL EXPERIMENT, not
  API-integration coding. Pre-register Experiment A's success criteria; build a
  seeded-defect mock-repo catalogue (~20-30 defects, probeable-vs-novel labelled)
  + a deterministic falsifier suite; run a 2x2 (context x provider) set of arms
  (routed single-shot vs the new path-aware adapter, GPT and Gemini) with K-repeat
  non-determinism sampling; then analyze into experiment-a-results.md with a
  capability verdict against the pre-registered criteria and an honest effect-size
  note. The reasoning is experimental-design + statistical-honesty heavy.
- Candidates: claude-opus-4-8 (incumbent, full adapter context + experimental-
  design strength), gpt-5.4, gemini-2.5-pro. Weigh experimental-design rigor and
  adapter context vs fresh-perspective and cost. Note the cross-provider verifier
  checks the INFERENCE, not the wet-lab run. Verification is cross-provider
  regardless of who orchestrates.
"""

r = route(
    PROMPT,
    task_type="analysis",
    session_set="067-pull-verifier-adapter-experiment-a",
    session_number=2,
)
out = HERE / "next-orchestrator-rec-s3.md"
out.write_text(
    "# Set 067 -> S3 next-orchestrator recommendation (routed)\n\n"
    f"> Routed via route(task_type='analysis'). Model used: {r.model_name} "
    f"({r.model_id})\n\n{r.content}\n",
    encoding="utf-8",
)
print(f"Wrote {out}")
print("model:", r.model_name, r.model_id, "cost:", r.cost_usd)
print(r.content[:1500])
