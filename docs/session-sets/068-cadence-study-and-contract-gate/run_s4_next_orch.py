"""Set 068 S4 -- routed next-orchestrator recommendation for Session 5 (L-064-6)."""
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
ai_router). Session 4 (just finished, run by claude-opus-4-8 high) made the routed
keep/demote/retire DECISION (operator-confirmed DEMOTE, transition-guarded) - a
decision + doc/config session with no production-code logic change. Session 5 is the
"Contract-test / CDC gate". Its work is REAL PYTHON IMPLEMENTATION:
1. Implement a deterministic contract-test / CDC gate: a module that runs a set's
   declared contract/falsifier tests (the cheap reproducible floor) and reports
   coverage of the seeded/known defect classes, reserving the path-aware agent for
   the non-probeable residual. Define how a set DECLARES its contract tests.
2. Wire the gate into close_session.py and/or router-config.yaml, mirroring the
   Set 066 path-aware gate's posture model (hard-block on TTY / soft-warn headless).
3. Write tests for the gate's pass/fail + coverage reporting.
4. Cross-provider verify; close.

So S5 is a SUBSTANTIAL coding session: new module + close_session wiring + a JSON
schema/declaration surface + a real test suite, touching the shared close-out path
(blast-radius is real - a buggy gate could wrongly block or wrongly pass set
close-outs). It is implementation-heavy, NOT a light decision/doc session. A known
repo lesson (L-067-1): gpt-5.4 over-probes/exhausts token budget when driving
agentic tool-loops, so it is a poor ORCHESTRATOR for multi-file implementation,
though fine as a cross-provider VERIFIER. Anthropic models (opus/sonnet via Claude
Code) and gemini are the viable orchestrators.

Recommend the engine/model/effort for the S5 ORCHESTRATOR and say why, weighing
capability on multi-file Python implementation + close-out wiring against cost.
Note the cross-provider session-verification at S5 close must be a DIFFERENT
provider than the orchestrator."""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=55)
    out = HERE / "next-orch-rec-s5.md"
    out.write_text(
        "# Set 068 S4 -- routed next-orchestrator recommendation for Session 5\n\n"
        f"> Routed via route(task_type='analysis'). Model: {getattr(r,'model_used','?')}.\n\n"
        f"{r.content}\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)}, indent=2))


if __name__ == "__main__":
    main()
