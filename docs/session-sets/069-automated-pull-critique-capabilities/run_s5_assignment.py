"""Set 069 S5 -- routed next-session / next-orchestrator recommendation (S6).

Rule #17 / L-064-6: never self-opine on which engine is cheapest-capable.
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
capabilities). Session 5 of 6 just shipped, VERIFIED (gpt-5-4 cross-provider, R1
FAIL with the central never-auto-merge safety property + the gate logic already
PASS + 6 findings [all L-066-1 schema<->validator parity drifts + a mandatory-
coverage bug] -> all fixed -> R2 PASS, no regressions, no new defects). S5 shipped
rungs 5-6 of the proposal: (1) ai_router/floor_ratchet.py - the quality-gated
ceiling->floor RATCHET: a reproduced probeable defect yields a CANDIDATE falsifier
artifact (candidate-falsifiers.json) that is NEVER auto-merged; admission requires
all six mechanical gates (fails-on-old, passes-on-fixed differential, drives a
public contract not an incidental string/timing, survives an N-run flake majority,
has an owner) AND humanSignoff==approved; the builder always emits 'pending', and
a rubber-stamp guard REJECTS an approved-but-failing candidate so a human approval
can never override a failing gate (the analog of S4's HYPOTHESIS cap); plus a
mandatory coverage check (every reproduced probeable defect needs a candidate or a
waiver; a rejected candidate does NOT count). (2) ai_router/replacement_gate.py -
the measured REPLACEMENT GATE: a pre-registered seeded+holdout benchmark
(benchmark-registration.json) + a raw scoreboard (replacement-scoreboard.json,
carrying gated-surface telemetry) + score_benchmark() that DERIVES recall /
precision / replay-success / false-REPRODUCED (verdict is derived, never
hand-asserted; the closed top-level schema rejects a smuggled verdict);
underpowered (n < minCasesForPower) forces meets=False; the manual run is NEVER
retired (the strongest cadence recommendation is a periodic backstop). Three JSON
Schemas + example fixtures + 97 tests (incl full schema<->validator parity). Full
ai_router suite GREEN (1953 passed / 5 skipped). No release (PyPI is S6). Both
modules are net-new and pure-Python, imported by no existing runtime path yet.

Session 6 of 6 ("Synthesis + docs + release + dogfood + close") is the FINAL
session. It will: (1) update docs/verification-surface-strategy.md (the
capabilities are now built; record the Podman spike GO outcome) +
ai_router/docs/pull-verifier.md + the proposal's status; promote a lesson if
warranted; (2) finalize tests, bump ai_router, and ship the PyPI RELEASE per the
publish runbook (green-Test-on-the-tagged-SHA prerequisite; verify the tag's
commit == the fixed SHA - the Set 068 lesson; the OPERATOR pushes/approves the
tag); record the publish run id post-release; (3) write change-log.md; route the
next-session-SET recommendation; cross-provider verification; DOGFOOD
(pathAwareCritique: required; contractGate: advisory) AND dogfood the new
execution-capable lanes over this set's own diff; close_session; the set closes.
This is mostly synthesis + careful release mechanics (a well-trodden runbook with
known Set-068 gotchas), plus a multi-provider dogfood critique - moderate
solution-variance, high care-for-release-correctness. Cross-provider verification
REQUIRED (the diff will trip routed_gate). It SHIPS a release.

Candidate engines: Claude (anthropic; opus-4-8 high/medium, sonnet-4-6 high/
medium), Codex (openai; gpt-5.4 high), Gemini (google; gemini-2.5-pro). Judge on
capability-for-the-task and total cost (dollars + rework risk), per
docs/planning/orchestration-strategy.md. NOTE: tier-1 analysis models may return
stale model names; map any stale name to the closest current candidate and say so.
"""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=42,
              session_set=str(HERE), session_number=5)
    out = HERE / "next-session-rec.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
