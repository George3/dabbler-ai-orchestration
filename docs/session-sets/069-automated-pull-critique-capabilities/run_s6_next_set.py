"""Set 069 S6 -- routed next-SESSION-SET recommendation (Step 9; L-064-6).

The orchestrator never self-opines on what to build next; route it. Set 069 is
complete (the execution-backed evidence layer; ai_router 0.23.0). Ask a tier-1
analysis model what the next session set should be, given the program state.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

PROMPT = """\
You are recommending the NEXT SESSION SET for the dabbler-ai-orchestration repo
(the canonical source of the shared AI-router + session-set workflow). Be concrete
and decisive; recommend ONE next set (with a one-line alternative). Return prose.

=== WHAT JUST SHIPPED (Set 069, ai_router 0.23.0) ===
Set 069 made the automated path-aware-critique ceiling EXECUTABLE -- the automated
`pull_critique` producer can now generate execution-backed, replayable evidence
(it was read-only before, which is why the 0.22.x release missed two Major bugs the
manual run reproduced by running code). Shipped, all additive:
- A single execution-evidence protocol (REPRODUCED/ASSERTED/HYPOTHESIS, orchestrator
  tags, pristine-replay + meta-oracle).
- Trusted-command execution + get_diff + blast-radius-budgeted probing in the producer.
- The probe-template lane (operator-authored versioned harnesses, typed args).
- The Podman model-authored-probe lane (GREEN spike; autonomous, severity-gated;
  authored probes CAP at HYPOTHESIS, never REPRODUCED; human stays the meta-oracle).
- The ceiling->floor RATCHET (quality-gated, never-auto-merged candidate falsifiers)
  + the measured REPLACEMENT GATE (pre-registered seeded+holdout benchmark +
  gated-surface telemetry; the manual run is NEVER retired -- cadence is measured).

=== PROGRAM STATE / KNOWN CANDIDATES ===
- The verification-surface strategy is SETTLED (docs/verification-surface-strategy.md):
  floor (contract gate) / ceiling (path-aware critique, now executable) / gated
  per-session routed. RETIRE of the per-session routed layer was deferred and is
  REOPENABLE ONLY ON TELEMETRY -- the very telemetry the Set 069 replacement gate
  now collects, but which has NOT yet run at scale.
- The Set 069 capabilities rest on SMALL author-seeded instruments (direction
  robust, magnitudes illustrative). The proposal queued real-workload PILOTS: two
  complex projects + the dabbler-access-harvester, gated behind the (now GREEN)
  Podman spike.
- The replacement gate needs a pre-registered benchmark POPULATED with real holdout
  cases (recent real misses) and run, to produce an honest scoreboard.
- Consumer repos consume ai_router via PyPI; none has adopted the 0.23.0 execution
  lanes or written its own probe-template library yet.
- The Podman lane's cage-mechanics regressions run only on Linux CI / WSL.

=== THE QUESTION ===
Given a settled strategy whose central open question (is the gated routed layer
worth keeping?) is now ANSWERABLE ONLY BY TELEMETRY THAT HAS NOT BEEN COLLECTED,
and a set of powerful new capabilities validated only on toy instruments, what is
the highest-leverage next session set? Weigh: (a) a real-workload PILOT/dogfood set
that adopts the 0.23.0 lanes on a consumer repo (e.g. the access-harvester) and
populates+runs the replacement-gate benchmark to collect real telemetry; (b) more
ceiling/floor machinery; (c) something else. State the recommended set's slug-style
name, its 2-4 session shape, what it would produce, and why it beats the
alternatives. Then a one-line second choice. Also recommend the next orchestrator
(engine/provider/model/effort) for that set's first session, with a one-line reason.
"""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=70)
    out = HERE / "next-set-rec.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
