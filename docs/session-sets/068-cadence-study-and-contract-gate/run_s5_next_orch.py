"""Set 068 S5 -- routed next-orchestrator recommendation for Session 6 (L-064-6)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

PROMPT = """\
Recommend the cheapest-CAPABLE orchestrator (engine + model + effort) for the NEXT
session of an AI-led session set. Reply with a recommendation and one-paragraph
rationale. Available lineup (use ONLY these ids): claude-opus-4-8 and
claude-sonnet-4-6 (Anthropic, via the Claude Code orchestrator), gpt-5.4 (OpenAI,
via Codex CLI), gemini-2.5-pro (Google, via Gemini Code Assist). Effort in
{low, medium, high}.

CONTEXT. This is Set 068 of the dabbler-ai-orchestration repo (a Python package,
ai_router, released to PyPI; plus a VS Code extension that is NOT touched this set).
Session 5 (just finished, run by claude-opus-4-8 high) built + wired + tested the
contract-test / CDC gate (ai_router/contract_gate.py + close_session wiring + 2 JSON
schemas + docs + 93 tests; cross-provider VERIFIED R3 after fixing 3 Majors). Session
6 is the FINAL session: "Synthesis + docs + release + dogfood + close". Its work:
1. Author the verification-surface SYNTHESIS doc (tying Experiment A + the re-grade +
   Experiment B + the routed DEMOTE decision + the contract gate into one strategy,
   superseding the Set 065 proposal's open questions).
2. Update ai_router/docs/ (run_test cage + contract gate), docs/ai-led-session-workflow.md
   (S6 must WIRE the blast-radius gating predicate that flips per-session routed to
   GATED and flip the workflow default -- the S4 transition guard's cut-over step),
   and the guidance lifecycle if a lesson is promoted.
3. Finalize tests; bump ai_router version; ship the PyPI release per the publish
   runbook (green-Test-on-the-tagged-SHA prerequisite; operator pushes tag v*).
4. change-log.md; route the next-session-SET recommendation; cross-provider verify;
   DOGFOOD (pathAwareCritique=required -> produce this set's own path-aware-critique.json
   via the manual flow or the Set 067 automated producer); close_session; set closes.

So S6 is a MIXED session: substantial doc synthesis + some real wiring (the gating
predicate that flips routed to gated -- touches close_session/workflow, real blast
radius) + a PyPI RELEASE (irreversible; the publish runbook must be followed exactly)
+ the dogfood gate. It is doc-and-release-heavy with one genuine implementation piece
(the predicate wiring + flip). A known repo lesson (L-067-1): gpt-5.4 over-probes /
exhausts token budget driving agentic tool-loops, so it is a poor ORCHESTRATOR for
multi-file implementation, though fine as a cross-provider VERIFIER. Anthropic models
(opus/sonnet via Claude Code) and gemini are the viable orchestrators.

Recommend the engine/model/effort for the S6 ORCHESTRATOR and say why, weighing
synthesis-writing + the predicate-wiring blast radius + executing an irreversible PyPI
release against cost. Note the cross-provider session-verification at S6 close must be
a DIFFERENT provider than the orchestrator."""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=55)
    out = HERE / "next-orch-rec-s6.md"
    out.write_text(
        "# Set 068 S5 -- routed next-orchestrator recommendation for Session 6\n\n"
        f"> Routed via route(task_type='analysis'). Model: {getattr(r,'model_used','?')}.\n\n"
        f"{r.content}\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)}, indent=2))


if __name__ == "__main__":
    main()
