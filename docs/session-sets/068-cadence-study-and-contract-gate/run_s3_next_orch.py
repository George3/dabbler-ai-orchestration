"""Set 068 S3 -- routed next-orchestrator recommendation for Session 4 (L-064-6)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route

PROMPT = """\
Recommend the cheapest-CAPABLE orchestrator (engine + model + effort) for the NEXT
session of an AI-led session set. Reply with a recommendation and one-paragraph
rationale. Available lineup (use ONLY these ids): claude-opus-4-8 and
claude-sonnet-4-6 (Anthropic, via the Claude Code orchestrator), gpt-5.4 (OpenAI,
via Codex CLI), gemini-2.5-pro (Google, via Gemini Code Assist). Effort in
{low, medium, high}.

CONTEXT. This is Set 068 of the dabbler-ai-orchestration repo. Session 3 (just
finished, run by claude-opus-4-8 high) BUILT + RAN Experiment B (the cadence
study) and wrote a cross-provider-verified cadence verdict. Session 4 is the
"Routed keep / demote / retire decision". Its work:
1. ROUTE the keep/demote/retire decision through cross-provider CONSENSUS
   (the project's decision-time-consensus mechanism), given Experiment A (capability
   ruled out) + Experiment B's verdict, then have the OPERATOR confirm the call.
2. IMPLEMENT the chosen outcome: a small router-config.yaml / workflow-doc /
   close-out change the decision implies (which may be "no code change - keep",
   recorded with rationale). The routed-verification status changes ONLY here.
3. Cross-provider verify the implementation; close.

So S4 is primarily a DECISION + a SMALL, well-scoped config/doc implementation +
a written rationale - NOT a large coding session. The hard analysis (the cadence
verdict) is already done and verified; S4 consumes it. The Experiment B verdict was
NUANCED (cadence mechanism real but confounded; "does not hold" via the control
clause, leaning demote/retire but with a genuine narrow rework-timing edge for
routed), so the decision needs careful, honest weighing - statistical-honesty
matters. A known repo lesson (L-067-1): gpt-5.4 over-probes/exhausts budget driving
agentic loops, so it is a poor ORCHESTRATOR for tool-loop work (S4 has little of
that), though fine as a consensus participant and cross-provider verifier.

Recommend the engine/model/effort for the S4 ORCHESTRATOR and say why. Note the
cross-provider session-verification at S4 close must be a DIFFERENT provider than
the orchestrator, and the decision itself must be routed to multiple providers."""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=50)
    out = HERE / "next-orch-rec-s4.md"
    out.write_text(
        "# Set 068 S3 -- routed next-orchestrator recommendation for Session 4\n\n"
        f"> Routed via route(task_type='analysis'). Model: {getattr(r,'model_used','?')}.\n\n"
        f"{r.content}\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)}, indent=2))


if __name__ == "__main__":
    main()
