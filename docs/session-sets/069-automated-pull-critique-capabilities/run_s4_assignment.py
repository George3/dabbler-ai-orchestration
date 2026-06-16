"""Set 069 S4 -- routed next-session / next-orchestrator recommendation (S5).

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
capabilities). Session 4 of 6 just shipped, VERIFIED (gpt-5-4 cross-provider,
R1 NEEDS_FIX with the central safety claim already PASS + 4 findings -> all 4
fixed -> R2 PASS): the Podman model-authored-probe lane (proposal rung b),
GATED on a GREEN spike (6/6 criteria). Concretely - a NET-NEW
ai_router/podman_sandbox.py (run_test_sandbox's sibling: the `podman run` cage
with --network=none, read-only /repo mount, tmpfs scratch, --cap-drop=ALL,
crash-safe force-remove teardown, lane-labeled disk-footprint hygiene, the three
spike findings carried: cgroup-v2-only resource caps, ~10s timeout teardown,
stdout/stderr separation) + a graduated digest-pin-documented Containerfile; a
run_authored_probe tool wired into pull_verifier.pull_route (the ONE lane where
the model AUTHORS the probe body, so it runs only in the container - the
container is the boundary; autonomous + severity-gated; a TRIAGE-ONLY safety
check that may reject/escalate but NEVER approve); the CENTRAL SAFETY PROPERTY
that a model-authored probe can NEVER mint REPRODUCED (it caps at HYPOTHESIS; the
S5 human-gated ratchet promotes it); threaded through the pull_critique producer
+ --podman-lane CLI + a router-config caps block. Full ai_router suite GREEN
(1856 passed / 5 skipped; the 4 new skips are real-podman regressions that skip
on the Windows host, by design). No release (PyPI is S6).

Session 5 of 6 ("Ceiling -> floor ratchet + measured replacement gate") will
build: (1) the QUALITY-GATED RATCHET - a reproduced probeable defect yields a
CANDIDATE falsifier artifact (never auto-merged); admission requires
fails-on-old, passes-on-fixed, drives a PUBLIC contract (not an incidental
string/timing), survives an N-run flake check, has an owner, and carries HUMAN
sign-off (mandatory for reproduced probeable defects or an explicit waiver);
(2) the MEASURED REPLACEMENT GATE - a pre-registered SEEDED + HOLDOUT (recent
real misses) benchmark scoring recall / precision / replay-success /
false-REPRODUCED rate, plus a telemetry record of the gated verification surface
(escaped-defect rate, intro-stage vs end-of-set timing, rework saved,
false-positive churn, predicate-should-have-fired misses) - the data the Set 068
DEMOTE decision said RETIRE reopens on; the manual run's cadence is DECIDED by
this scoreboard, not retired on faith. This is design-heavy work with real
solution-variance (what makes a good candidate-falsifier admission gate; how to
pre-register an honest benchmark with small-n; what telemetry schema) plus
careful implementation in ai_router. Cross-provider verification REQUIRED (the
diff will trip routed_gate). No release (that is S6). It is NOT an experiment.

Candidate engines: Claude (anthropic; opus-4-8 high / sonnet-4-6 high/medium),
Codex (openai; gpt-5.4 high), Gemini (google; gemini-2.5-pro). Judge on
capability-for-the-task and total cost (dollars + rework risk), per
docs/planning/orchestration-strategy.md. NOTE: tier-1 analysis models may return
stale model names; map any stale name to the closest current candidate and say so.
"""


def main():
    r = route(PROMPT, task_type="analysis", complexity_hint=45,
              session_set=str(HERE), session_number=4)
    out = HERE / "next-session-rec.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
