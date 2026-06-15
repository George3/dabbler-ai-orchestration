"""Set 068 S3 cross-provider session-verification.

Independent verifier: gpt-5.4 (openai) -- cross-provider for the Claude
orchestrator. S3 RUNS Experiment B (the cadence study). It ships the harness
(under docs/session-sets/, NOT production ai_router code) + experiment-b-results.md
graded against the FIXED, S2-pre-registered decision rule. Verification target:
(1) does the harness faithfully implement the pre-registration; (2) is the grader
correct (per-repeat, cost model, file-in-surface gating, band rule); (3) is the
verdict correctly read off the FIXED rule (A3 fail / B3 fire), and is the honesty
sound (esp. the adversarial question: are the non-null controls legitimate signal
or a rigged seed?). Persists raw output BEFORE printing (L-064-3).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

EB = HERE / "experiment-b"


def r(p: Path) -> str:
    return p.read_text(encoding="utf-8")


prereg = r(HERE / "experiment-b-preregistration.md")
results = r(HERE / "experiment-b-results.md")
catalogue = r(EB / "catalogue.json")
build = r(EB / "build_snapshots.py")
run_arms = r(EB / "run_arms.py")
grade = r(EB / "grade.py")
cost_model = r(EB / "cost_model.py")
audit = r(EB / "audit.json")
data = r(EB / "experiment-b-data.json")

CONVENTIONS = """\
CONVENTIONS (read first -- do NOT spend findings on these; agreed baseline / by-design scope):

WHAT THIS SESSION IS. Set 068 Session 3 of 6 RUNS Experiment B (the cadence
study). It ships: the harness (experiment-b/{build_snapshots,run_arms,grade}.py +
catalogue.json + audit.json, all under docs/session-sets/) and the analysis doc
experiment-b-results.md. It changes NO production ai_router code and ships NO PyPI
release (the run_test cage was S1; the keep/demote/retire decision is S4; the
contract gate is S5; the release is S6). cost_model.py was PRE-REGISTERED and
already VERIFIED in S2 -- it is unchanged here; do not re-litigate it.

SUITE BASELINE: full ai_router pytest suite GREEN (1548 passed, 1 skipped),
UNCHANGED -- nothing in ai_router/ changed this session (testpaths=ai_router/tests;
the docs/ experiment scripts are not collected). cost_model.py self-tests PASS;
the per-snapshot smoke suite is GREEN (so run_test sees green). Assume green.

THE YARDSTICK IS FIXED. The verdict is graded against experiment-b-preregistration.md
(authored + cross-provider-VERIFIED in S2, BEFORE any data). Your job is to check
FAITHFULNESS to that fixed rule and the harness/grader correctness -- NOT to
propose a different rule or different cost-model constants. If you think the
pre-registered rule itself is flawed, say so as a Minor (it is water under the
bridge for S3), but the Major/Critical bar is: did S3 implement the design
faithfully and read the verdict correctly off the FIXED rule?

CONFLICT OF INTEREST. Authored by the Claude Opus 4.8 orchestrator (Anthropic),
which (a) maintains the workflow under study and (b) is an Anthropic model running
an experiment that bears on routed per-session verification AND on path-aware
critique (which can use an Anthropic provider). The result LEANS demote/retire for
routed. Be adversarial: check it is not steering to a convenient conclusion, AND
that it is not over-selling 'retire' when the data shows a real (if narrow)
cadence effect. Grading is mechanical (deterministic predicates + a symmetric
quoted-mechanism audit) and cross-provider-checked by YOU.

FOCUS your review on:

A. HARNESS FAITHFULNESS to the pre-registration.
   A1. Do build_snapshots.py + catalogue.json realize the taxonomy? Are all 12
       defects correctly classed, with the class<->(d, vis) invariants holding
       (cadence-payoff = d>0 & in-snippet@intro & cross-file@close; coupling-blind
       = d>0 & cross-file@intro; always-visible = d>0 & in-snippet both;
       no-coupling = d=0)? Are the >=3 cadence-payoff / >=2-each-control minimums
       met? Is Q_surface_files pinned as the prereg Sec 3a describes (final diff +
       headline file, omitting early files)?
   A2. Are the seeded bugs REAL and correctly labelled by VISIBILITY? Specifically:
       are the two coupling-blind defects (BD6 aggregate-mean-no-None-filter, BD7
       convert-_VALID-rejects-aliases) genuinely cross-file@intro -- i.e. NOT
       recognizable from the introducing file's own diff alone (the cross-file
       contract must live ONLY in the upstream file, not be leaked in the
       introducing file's docstring)? The results doc Sec 1 claims the pilot caught
       and fixed exactly such a docstring leak -- verify the SHIPPED source no
       longer leaks it (check convert.py's and aggregate.py's docstrings in
       build_snapshots.py).
   A3. Are the cadence-payoff defects genuinely in-snippet@intro (recognizable from
       the introducing file alone, via that file's own docstring contract) AND
       genuinely omitted from Q_surface (cross-file@close)?

B. GRADER CORRECTNESS (grade.py) -- the result hinges on this.
   B1. Is catch-timing PER-REPEAT (c_k), NOT union-over-K, as the prereg requires?
   B2. The FILE-IN-SURFACE gating (_in_surface): an arm can only catch a defect
       whose evidence file is in its surface at that snapshot (R=session_diff[i],
       Q=Q_surface, E=full final tree). Is this CORRECT and FAIR -- does it
       legitimately enforce 'Q structurally misses cadence-payoff' / block spurious
       cross-snapshot token matches, or does it RIG the result by hand-deciding who
       can catch what? Could it wrongly suppress a real catch?
   B3. Is the band rule right (resolved iff |mean_k| > band, band = max_k - min_k;
       median sign-agreement only)? Is the realized-early gate ceil(2K/3)=2-of-3 at
       c_k <= t0+REALIZE_SLACK? Is cost computed via the pinned cost_model with
       n+1 mapped to None (never-caught)?
   B4. Does the symmetric audit (audit.json) apply to ALL arms, and is 'no removals'
       defensible given the quoted evidence?

C. THE VERDICT INFERENCE (experiment-b-results.md Sec 3-4) -- the crux.
   C1. Is A1 (R realizes early window 5/5) and A2 (cadence-payoff g/s resolved &
       concentrated) correctly SUPPORTED by experiment-b-data.json?
   C2. Is A3 correctly judged FAILED and B3 correctly FIRED? I.e. do the controls
       REALLY show a resolved R advantage (no-coupling R-vs-Q s=1.0; always-visible
       R-vs-Q s=3.0)?
   C3. THE KEY ADVERSARIAL QUESTION. The results doc attributes the no-coupling
       residual to BD12 (a d=0 defect that is ALSO Q-invisible -> Q pays the escape
       penalty -> a pure SURFACE-coverage artifact, zero timing component) and the
       always-visible residual to pure 1-snapshot earliness. (i) Is that
       attribution correct? (ii) Is it LEGITIMATE that a no-coupling defect (BD12)
       is Q-invisible -- or is that a SEED-DESIGN error that rigged the no-coupling
       control to be non-null, and should the result instead read 'controls
       inconclusive' rather than 'B3 confound present'? Argue both sides.
   C4. Is the faithful-interpretation call right -- that B3's gloss ('surface
       artifact / pure earliness, not Q-invisible cadence') applies and B1's gloss
       ('no cadence value') does NOT (because B1 is false)? Or is the doc
       under-selling a genuine cadence effect, OR over-selling 'retire'?
   C5. Is the R-vs-E cadence-payoff saving (g~3, s~27-30, R earlier/cheaper than the
       path-aware replacement) correctly identified as R's ONE genuine residual
       value, and is the 'E dominates capability' claim (E 11-12/12 incl the 2
       coupling-blind R misses; R-vs-E coupling-blind s=-6..-12) correct?

D. run_test LIVE USE. The results claim arm E exercised the S1 run_test cage live
   in a metered loop (a turn-8 run_test call, raw, no error, green suite). Is this
   substantiated by the data/trace evidence cited?

E. INTERNAL CONSISTENCY + STATS HONESTY. Do the numbers in experiment-b-results.md
   match experiment-b-data.json exactly? Is the small-n honesty caveat adequate
   (1 unit, 12 defects, K=3, mostly band=0 because catches are near-deterministic)?
   Any arithmetic/citation error? Any claim unsupported by its evidence?
"""

SYSTEM_PROMPT = (
    "You are a senior research-methodology + software-verification reviewer giving "
    "an independent cross-provider verification of a completed experimental session "
    "(Set 068, Session 3: running the Experiment B cadence study and reading its "
    "verdict off a fixed pre-registration). You did not author it. Be rigorous and "
    "concrete: cite the specific claim / number / section / file / line. Judge "
    "experimental-execution faithfulness, grader correctness, and inference honesty "
    "-- not code style. Distinguish a real defect (wrong grade, mis-read verdict, "
    "rigged control, unsupported claim) from a nit. End with a JSON verdict block: "
    '{"verdict":"VERIFIED"|"ISSUES_FOUND","issues":[{"severity":"Critical|Major|'
    'Minor","claim":"<what>","problem":"<why>","fix":"<how>"}]}.'
)

USER = f"""{CONVENTIONS}

=== DELIVERABLE 1: experiment-b-results.md (the cadence verdict -- main target) ===
{results}

=== DELIVERABLE 2: experiment-b-preregistration.md (the FIXED yardstick, S2-verified) ===
{prereg}

=== DELIVERABLE 3: experiment-b/catalogue.json (the seeded defects + pinned surfaces) ===
{catalogue}

=== DELIVERABLE 4: experiment-b/build_snapshots.py (the snapshot builder + embedded bugs) ===
{build}

=== DELIVERABLE 5: experiment-b/grade.py (the deterministic per-repeat grader) ===
{grade}

=== DELIVERABLE 6: experiment-b/run_arms.py (the arm driver) ===
{run_arms}

=== DELIVERABLE 7: experiment-b/cost_model.py (PRE-REGISTERED, unchanged from S2) ===
{cost_model}

=== DELIVERABLE 8: experiment-b/audit.json (the symmetric mechanism audit + quotes) ===
{audit}

=== DELIVERABLE 9: experiment-b/experiment-b-data.json (graded metrics output of grade.py) ===
{data}

Review per the FOCUS list (A-E). Return your findings then the JSON verdict block."""


def main():
    cfg = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))
    pcfg = cfg["providers"]["openai"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gpt-5.4")
    result = providers.call_model(
        provider_name="openai", model_id="gpt-5.4",
        system_prompt=SYSTEM_PROMPT, user_message=USER,
        max_tokens=28000, config=pcfg,
        generation_params={"reasoning_effort": "high"},
    )
    out = HERE / "s3-verification.md"
    out.write_text(
        "# Set 068 S3 -- Cross-provider verification (gpt-5.4)\n\n"
        "> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude\n"
        "> orchestrator. Round 1. Target: the Experiment B run + cadence verdict\n"
        "> against the fixed S2 pre-registration (harness faithfulness, grader\n"
        "> correctness, inference honesty). No production code / no release this session.\n\n"
        f"{result.content}\n",
        encoding="utf-8",
    )
    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print(f"Wrote {out} ({len(result.content)} chars)")
    print(json.dumps({
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cost_usd": round(in_cost + out_cost, 6), "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()
