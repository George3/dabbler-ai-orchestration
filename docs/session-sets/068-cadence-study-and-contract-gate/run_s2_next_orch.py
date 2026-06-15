"""Set 068 S2 -- routed next-orchestrator recommendation for Session 3 (L-064-6)."""
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

CONTEXT. This is Set 068 of the dabbler-ai-orchestration repo. Session 2 (just
finished, run by claude-opus-4-8 high) was analysis/design only: a symmetric
re-grade of an experiment + the pre-registration of Experiment B. Session 3 is
"Experiment B - the cadence study". Its work:
1. BUILD a staged-snapshot harness ON TOP of an existing disposable-worktree
   run_test execution cage (real Python: build_snapshots.py, run_arms.py, grade.py
   mirroring an existing Experiment A harness), seeding ordered frozen snapshots
   and a catalogue of coupling defects with pre-committed predicates.
2. RUN a metered, blind, K=3, two-provider (gpt-5.4 + gemini-2.5-pro) sweep of
   four arms through route()/pull_route()/the cage, persisting raw outputs, after
   a pilot smoke run.
3. ANALYZE the results into a written cadence verdict against the pre-registered
   decision rule (per-repeat metrics, a binding stability gate, a pinned noise
   band, a deterministic cost model already shipped).
So S3 is substantial PRODUCTION-style harness code + careful experiment execution
+ statistical-honesty analysis. A known repo lesson (L-067-1): gpt-5.4 over-probes
and exhausts budget as a pull-verifier on non-trivial sandboxes, so it is a poor
ORCHESTRATOR choice for driving the agentic loop, though it is fine as one of the
two experiment SUBJECT providers and as the cross-provider verifier.

Recommend the engine/model/effort for the S3 ORCHESTRATOR and say why. Note the
cross-provider session-verification at S3 close must be a DIFFERENT provider than
the orchestrator."""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=55)
    out = HERE / "next-orch-rec-s3.md"
    out.write_text(
        "# Set 068 S2 -- routed next-orchestrator recommendation for Session 3\n\n"
        f"> Routed via route(task_type='analysis'). Model: {getattr(r,'model_used','?')}.\n\n"
        f"{r.content}\n",
        encoding="utf-8",
    )
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)}, indent=2))


if __name__ == "__main__":
    main()
