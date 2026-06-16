"""Set 069 S1 -- routed next-session / next-orchestrator recommendation.

Rule #17 / L-064-6: never self-opine on which engine is cheapest-capable. Route
the recommendation through analysis.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

PROMPT = """\
Recommend the cheapest-CAPABLE orchestrator engine + reasoning effort for the
NEXT session of this session set, and a one-paragraph rationale. Return a short
structured recommendation (engine, model tier, effort, why), nothing else.

Context: dabbler-ai-orchestration, Set 069 (automated pull-critique
capabilities). Session 1 just shipped the execution-evidence PROTOCOL + the
evidence-tiered findings SCHEMA (ai_router/evidence_protocol.py: REPRODUCED /
ASSERTED / HYPOTHESIS tiers; the orchestrator-applies-the-tag rule; the
servant-captured transcript shape with a pristine-replay requirement and the
meta-oracle public-entrypoint rule; validate_transcript / validate_finding_evidence /
authoritative_tier) and extended the Set 066 path-aware-critique artifact validator
+ JSON Schema to carry + enforce evidence-tiered findings (a REPRODUCED finding
without a valid falsifier transcript invalidates the artifact). It was VERIFIED
cross-provider (gpt-5-4) after a 4-round parity-hardening loop (L-066-1 class:
Python validator vs JSON Schema parity, incl. a whitespace-only divergence).

Session 2 of 6 ("Trusted-command execution + diff-awareness + deeper probing")
will: wire TRIGGER-ONLY execution into ai_router/pull_critique.py (the critic may
trigger operator-authored command ids in the existing run_test cage -- no
model-authored argv; fresh checkout; caps); add a get_diff tool (raw unified diff
+ changed paths, deterministic-servant, not model-summarized); and add a
blast-radius-budgeted multi-turn read->run->read loop (turn/token caps). Findings
from a triggered run must flow through the Session 1 evidence protocol
(orchestrator-tagged, transcript-backed). This is real coding in the shared pull
adapter (pull_verifier.py / pull_critique.py) + the run_test cage
(run_test_sandbox.py), with cross-provider verification REQUIRED (the diff trips
the routed_gate predicate). Tests run trivial deterministic commands in the cage;
no metered calls in unit.

Candidate engines: Claude (anthropic; opus-4-8 high / sonnet-4-6 medium), Codex
(openai; gpt-5.4 high), Gemini (google; gemini-2.5-pro). Judge on
capability-for-the-task and total cost (dollars + rework risk), per
docs/planning/orchestration-strategy.md.
"""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=40,
              session_set=str(HERE), session_number=1)
    out = HERE / "next-session-rec.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
