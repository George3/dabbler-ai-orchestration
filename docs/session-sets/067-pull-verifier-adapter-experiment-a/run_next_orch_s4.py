"""Route the next-orchestrator recommendation for Set 067 Session 4 (final).
Per project-guidance (L-064-6): never self-opine; route via analysis."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route

PROMPT = """\
Recommend the orchestrator engine/model + effort for Set 067 Session 4 of 4
(FINAL) of dabbler-ai-orchestration. Reply ONLY with a JSON object:
{"engine": "...", "provider": "...", "model": "...", "effort": "low|medium|high",
 "reason": "one or two sentences (>= 30 chars)"}

Context:
- Set 067 builds the first-party tool-loop "pull" verifier adapter (pull_route())
  in ai_router. S1 shipped the loop driver + Anthropic binding + deterministic-
  servant guardrail; S2 added OpenAI + Gemini bindings + router-config executor
  wiring; S3 just ran Experiment A (a controlled capability study) and the
  cross-provider-verified verdict is: path-aware CAPABILITY CONFIRMED (path-aware
  caught 5 cross-file defects incl 2 Criticals that routed single-shot missed on
  identical code; routed caught nothing path-aware missed; the edge is context-
  access not a second provider; a deterministic falsifier suite covered 19/20).
- Session 4 (FINAL) work: because Experiment A confirmed capability, wire the
  adapter as an OPTIONAL automated producer of the Set 066 path-aware-critique.json
  artifact (a CLI/seam; manual stays the default, producer opt-in); update docs
  (the adapter doc + a Set-066 'automated alternative (opt-in)' note); finalize
  tests; bump the ai_router version and SHIP a PyPI release following the publish
  runbook (green-Test-on-the-tagged-SHA prerequisite, tag v*); author change-log.md;
  route the next-session-set recommendation (expected Set 068 = run_test sandbox +
  Experiment B cadence + the keep/demote/retire decision + contract-test/CDC gate);
  cross-provider verification; DOGFOOD this set's own path-aware-critique.json
  (pathAwareCritique: required) at the set-terminal close; close the set.
- This is production-code + release-engineering work (CLI/seam wiring, packaging,
  publish runbook, the close-out gate), distinct from S3's experiment. It needs
  full adapter + artifact-contract context and release discipline.
- Candidates: claude-opus-4-8 (incumbent, full Set-066/067 context + release
  runbook familiarity), gpt-5.4, gemini-2.5-pro. Weigh release-engineering
  reliability and context against fresh-perspective and cost. Verification is
  cross-provider regardless of who orchestrates.
"""

r = route(
    PROMPT,
    task_type="analysis",
    session_set="067-pull-verifier-adapter-experiment-a",
    session_number=3,
)
out = HERE / "next-orchestrator-rec-s4.md"
out.write_text(
    "# Set 067 -> S4 next-orchestrator recommendation (routed)\n\n"
    f"> Routed via route(task_type='analysis'). Model used: {r.model_name} "
    f"({r.model_id})\n\n{r.content}\n",
    encoding="utf-8",
)
print(f"Wrote {out}")
print("model:", r.model_name, r.model_id, "cost:", r.cost_usd)
print(r.content[:1500])
