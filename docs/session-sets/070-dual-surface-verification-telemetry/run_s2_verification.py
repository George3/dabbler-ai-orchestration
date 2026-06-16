"""Set 070 S2 -- cross-provider session verification (Step 6, gated -> REQUIRED).

S2's diff adds the provenance merge + comparison artifact/validator + JSON Schema
+ the fair-shake scoring + the dual-surface verificationMode-pattern option + CLI
to ai_router/dual_surface_verify.py, plus a new test file + a schema + an example,
spanning ai_router + docs. routed_gate trips REQUIRED (blast-radius cross-artifact,
shared-schema, multi-module). The orchestrator is Anthropic/opus-4-8; the verifier
routes to a different provider. Strong adversarial (devil's-advocate) framing -- the
verification.md template this set ships now deploys at that strength.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

DIFF = subprocess.run(
    ["git", "diff", "--cached", "--",
     "ai_router/dual_surface_verify.py",
     "ai_router/tests/test_dual_surface_s2.py"],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

SCHEMA = (REPO / "docs/dual-surface-comparison.schema.json").read_text(encoding="utf-8")
EXAMPLE = (REPO / "docs/dual-surface-comparison-schema-example.json").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 2 of 3 of Set 070
(dual-surface verification + push fair-shake telemetry) in the
dabbler-ai-orchestration repo. Be a genuine devil's advocate: ASSUME the work is
flawed and try to PROVE it; a rubber-stamp is a failure. Return the structured
verdict (VERIFIED or ISSUES FOUND, with Issue N / Category / Severity).

=== CONVENTIONS / BASELINE (read first; do NOT re-flag the agreed baseline) ===
- Suite baseline BEFORE this session: 1988 passed, 5 skipped (the 5 are Set 069 S4
  real-Podman-on-Windows skips, by design). This session ADDS 66 unit tests; the
  full ai_router pytest suite is GREEN at this commit (2054 passed, 5 skipped). You
  are verifying CODE + SCHEMA, not re-running the suite.
- RELEASE CONTRACT: NO release this session. The ai_router PyPI release + the
  synthesis docs + the dogfood (running the dual-surface mode over this set's own
  diff) are Session 3; the version is intentionally unchanged. NO Marketplace /
  extension change (spec non-goal: no UI surface this whole set).
- BY-DESIGN SCOPE (Session 2 = "Provenance merge + the fair-shake telemetry + mode
  wiring"). IN scope: (a) the provenance MERGE (merge_findings); (b) the comparison
  artifact + pure-Python validator + JSON Schema (docs/dual-surface-comparison.
  schema.json); (c) the fair-shake SCORING (score_comparison, score_against_
  benchmark, aggregate_retire_telemetry); (d) the dual-surface verificationMode-
  pattern option (read/record/resolve/should_run) + CLI. The Session-1 two-arm
  runner (run_dual_surface, classify_framing_strength, the arm dataclasses) was
  VERIFIED in S1 -- verify only that S2 builds on it correctly, do NOT re-audit it.
  DEFERRED (do NOT flag as gaps): the PyPI release, the synthesis doc updates, the
  change-log, and the live dogfood run -- all Session 3. No metered LLM call is unit
  -tested (the scorers/merge/validator are pure; the mode writers touch only a tmp
  activity-log); that is by design.
- ADDITIVITY: these are NET-NEW functions + a new artifact kind. Absent the new
  config (no dualSurfaceMode record, no comparison artifact), every existing flow
  is byte-for-byte unchanged. The mode reader defaults to 'off'.

=== THE LOAD-BEARING PROPERTIES TO ATTACK (cite file:line for any finding) ===

1. PROVENANCE MERGE: DESCRIPTION IS NOT IDENTITY (the Set 069 S6 floor-ratchet
   lesson). In merge_findings: two findings merge to 'both' ONLY when they share a
   non-empty, explicit defectKey -- NEVER on free-text wording. Try to break this:
   is there ANY path where two distinct defects collapse to one 'both' (which would
   HIDE a push-unique catch and bias the RETIRE telemetry toward retiring push --
   "throwing out the baby")? Is the SAFE DIRECTION right -- an unkeyed defect both
   arms caught becomes TWO single-surface entries (over-split, conservative), and
   the result HONESTLY flags provenance_complete=False + the unkeyed counts? Check
   intra-arm duplicate keys (must not double-count one arm), non-dict findings,
   and that the most-severe severity + first-non-empty category are chosen.

2. L-066-1 VALIDATOR/SCHEMA PARITY (the headline risk). validate_comparison_artifact
   vs docs/dual-surface-comparison.schema.json. Enumerate EVERY schema-constrained
   field (required AND optional) and confirm the Python validator checks each with a
   matching type. Specifically: does schemaVersion reject 1.0 (float) and True
   (bool) like the schema's "integer"? Do pushUnkeyed/pullUnkeyed reject bool? Are
   the closed top-level / contributor / merged-finding key sets EXACTLY the schema's
   additionalProperties:false sets (no drift looser)? Are the CROSS-FIELD invariants
   the schema cannot express actually enforced: a 'both' finding's contributors MUST
   cover both surfaces AND carry a defectKey; a 'push-only'/'pull-only' finding's
   contributors must be exactly that one surface; provenanceComplete=true is
   INCONSISTENT with any unkeyed finding? Is the example
   (docs/dual-surface-comparison-schema-example.json) valid under BOTH? Is there a
   malformed artifact the Python validator ACCEPTS but the JSON Schema REJECTS (the
   exact L-066-1 failure mode -- it is uncovered, not failing)?

3. SCORING HONESTY (never hand-asserted; underpowered -> inconclusive). In
   score_comparison + score_against_benchmark: are the high-severity tallies DERIVED
   (Critical/Major only via is_high_severity)? When provenance is incomplete, is the
   unique tally reported as an UPPER BOUND, never a settled partition? In the
   benchmark scorer: is "real" decided ONLY by ground truth (defectKey is a
   REGISTERED case via replacement_gate.validate_benchmark_registration)? Does
   underpowered (real_case_count < minCasesForPower) FORCE verdict==inconclusive
   even when push_unique_real>0? Is an unkeyed high-sev finding correctly EXCLUDED
   from the real tally (can't be scored against ground truth)? Is the gated push
   layer NEVER retired here (the verdict is a recommendation, not a decision)?

4. NEVER POOL SAMPLED WITH OPT-IN (the honesty standard). aggregate_retire_telemetry
   must REFUSE (ok=False) a mixed-tag input. Confirm it cannot silently pool a
   'sampled' (unbiased telemetry) run with an 'opt-in' (operational, self-selected
   high-risk) run. Does min_runs_for_power + any-underpowered-constituent correctly
   keep the pool inconclusive?

5. MODE WIRING IMMUTABILITY (the verificationMode pattern). resolve_and_record_dual_
   surface_mode must record ONCE at set start and be immutable thereafter -- a later
   '--mode off' must NOT silently disarm a sampling/opt-in choice the set started
   under. Confirm: cli_choice precedence over spec seed; records nothing without a
   source; bad cli_choice always raises; read_dual_surface_mode and
   has_..._record NEVER raise on a corrupt/invalid-UTF-8 activity log (the L-069-1
   sibling-reader class) yet dual_surface_mode_record_unreadable surfaces the corrupt
   case; "last valid entry wins". Is the entry kind ("dual_surface_mode") distinct so
   it never overloads the Set 057 verification_mode / Set 066 path_aware_critique
   enums?

6. should_run_dual_surface DETERMINISM. The random draw is INJECTED (sample_value),
   never drawn inside (hermetic). Confirm: off never runs; opt-in runs ONLY with
   opt_in=True; sampled runs when sample_value < sample_rate (tag 'sampled') but an
   explicit opt_in=True under sampled mode returns the OPERATIONAL 'opt-in' tag (not
   folded into telemetry); unknown mode treated as off; sample_rate clamped to [0,1].
   Any off-by-one or boundary bug (sample_value==rate)?

7. CLI + ERROR DISCIPLINE. main()'s record-mode / read-mode / score subcommands:
   ASCII-only output, never prints unwritten paid output, an inconclusive/not-met
   result is a verdict (exit 0) while only an invalid/unreadable artifact is non-zero.
   build_comparison_artifact raises ValueError on a bad run_tag (programmer error).
   Any crash path on a malformed comparison/registration/activity-log?

8. TEST ADEQUACY. Do the 66 new tests actually EXERCISE the named behaviors (the
   description-is-not-identity merge, the L-066-1 float/bool rejections, the cross
   -field provenance invariants, the underpowered->inconclusive, the mixed-tag
   refusal, the immutability, the injected-draw sampling), or do any pass WITHOUT
   exercising the behavior they name? Is the schema<->validator<->example parity
   actually pinned by jsonschema in the tests?

=== docs/dual-surface-comparison.schema.json ===
{SCHEMA}

=== docs/dual-surface-comparison-schema-example.json ===
{EXAMPLE}

=== STAGED DIFF (dual_surface_verify.py + test_dual_surface_s2.py) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=78,
        session_set=str(HERE),
        session_number=2,
    )
    out = HERE / "s2-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
