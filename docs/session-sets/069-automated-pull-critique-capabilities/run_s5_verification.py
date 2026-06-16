"""Set 069 S5 -- cross-provider session verification (Step 6, gated -> REQUIRED).

S5 ships rungs 5-6 of the proposal: the quality-gated ceiling->floor RATCHET
(ai_router/floor_ratchet.py) and the measured REPLACEMENT GATE
(ai_router/replacement_gate.py) + three JSON Schemas + examples + tests. Both
modules are NET-NEW and pure-Python (no metered calls in unit). routed_gate
confirms REQUIRED (blast-radius + multi-module + breadth, 7 files). Orchestrator
is Anthropic/opus; the verifier routes to a different provider.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

NEW_TESTS = 82
TOTAL_PASS = 1938

FILES = [
    "ai_router/floor_ratchet.py",
    "ai_router/replacement_gate.py",
    "docs/candidate-falsifier.schema.json",
    "docs/benchmark-registration.schema.json",
    "docs/replacement-scoreboard.schema.json",
    "ai_router/tests/test_floor_ratchet.py",
    "ai_router/tests/test_replacement_gate.py",
]
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--", *FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

FLOOR = (REPO / "ai_router/floor_ratchet.py").read_text(encoding="utf-8")
REPL = (REPO / "ai_router/replacement_gate.py").read_text(encoding="utf-8")
EVIDENCE = (REPO / "ai_router/evidence_protocol.py").read_text(encoding="utf-8")
CF_SCHEMA = (REPO / "docs/candidate-falsifier.schema.json").read_text(encoding="utf-8")
REG_SCHEMA = (REPO / "docs/benchmark-registration.schema.json").read_text(encoding="utf-8")
SB_SCHEMA = (REPO / "docs/replacement-scoreboard.schema.json").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 5 of 6 of Set 069
(automated pull-critique capabilities) in the dabbler-ai-orchestration repo.
Return the structured verdict.

=== CONVENTIONS / BASELINE (read first; do NOT re-flag the agreed baseline) ===
- Suite baseline BEFORE this session: 1856 passed, 5 skipped (the 5 skips are the
  S4 real-podman regressions, by design). This session ADDS {NEW_TESTS} tests; the
  full ai_router pytest suite is GREEN at this commit ({TOTAL_PASS} passed, 5
  skipped). You are verifying CODE + SCHEMAS + TESTS, not re-running the suite.
- RELEASE CONTRACT: NO release this session. The ai_router PyPI release is
  Session 6; the version is intentionally unchanged. NO Marketplace / extension
  change (spec non-goal: no UI surface this whole set).
- BY-DESIGN SCOPE (Session 5 = "Ceiling -> floor ratchet + measured replacement
  gate", proposal rungs 5-6). IN scope: (a) ai_router/floor_ratchet.py -- a
  candidate-falsifier artifact + the quality-gated admission gate; (b)
  ai_router/replacement_gate.py -- a pre-registered seeded+holdout benchmark + a
  raw scoreboard + a DERIVED score / cadence recommendation; (c) three JSON
  Schemas + example fixtures + the pure-Python validators (L-066-1 parity); (d)
  tests. DEFERRED (do NOT flag as gaps): wiring either gate into close_session.py
  (that close-out seam, if any, is S6); the actual PRODUCTION of these artifacts
  by the pull_critique producer end-to-end; the synthesis-doc update + PyPI
  release + dogfood (all S6). These are net-new library modules + their contracts;
  no existing flow calls them yet, by design.
- ADDITIVITY: both modules are NET-NEW and imported by nothing in the existing
  runtime path. There is NO behavioral change to any existing flow this session.
  Confirm the diff touches only the new files (+ tests), not existing behavior.

=== THE CENTRAL DESIGN CLAIMS TO CHECK ===

A. THE RATCHET IS NEVER-AUTO-MERGE (the load-bearing safety property, the analog
   of S4's "an authored probe can never mint REPRODUCED"). A candidate falsifier
   is ADMITTED to the floor (admission_decision -> status ADMITTED, admitted=True)
   ONLY when EVERY mechanical gate passes AND humanSignoff.status == "approved"
   (with a non-empty `by`). Confirm:
   A.1 build_candidate_from_finding ALWAYS emits humanSignoff={{"status":"pending"}}
       -- it never mints an approval. There is no code path where the builder
       outputs "approved".
   A.2 THE RUBBER-STAMP GUARD: when humanSignoff is "approved" but a mechanical
       gate fails, the decision is REJECTED (admitted=False), NOT admitted. A human
       approval CANNOT override a failing mechanical gate. Confirm there is no path
       where admitted=True without all six gates passing.
   A.3 An explicit "waived" short-circuits the gates (an operator decision not to
       promote) but still admits nothing (admitted=False) and requires a note.

B. THE SIX QUALITY GATES ARE CORRECT (proposal Sec.1.5). In _eval_mechanical_gates:
   B.1 fails-on-old requires failsOnOld.failed is True on a named ref.
   B.2 passes-on-fixed requires passesOnFixed.passed is True on a named ref that
       DIFFERS from failsOnOld.ref (a real differential -- not the same checkout,
       which would be a tautology). Confirm the ref-inequality check is correct.
   B.3 drives-public-contract requires BOTH a public entrypoint kind (one of
       PUBLIC_ENTRYPOINT_KINDS, reusing evidence_protocol; agent_harness rejected)
       AND contractKind == "public_contract". An incidental string/timing assertion
       is rejected EVEN WITH a public entrypoint. Confirm both are required.
   B.4 flake-check requires runs >= min_flake_runs (default 3), stable is True, and
       agreeing a strict majority (agreeing*2 > runs). Confirm an unstable or
       non-majority or too-few-runs check is rejected, and that runs/agreeing being
       bool is rejected (not silently accepted as int).
   B.5 has-owner requires a non-empty owner.

C. THE REPLACEMENT GATE IS HONEST (proposal Sec.1.6 / Sec.4). In replacement_gate:
   C.1 The verdict is DERIVED, never hand-asserted: the scoreboard carries only raw
       outcomes + telemetry (no verdict field); score_benchmark computes
       recall/precision/replay-success/false-REPRODUCED. Confirm the scoreboard
       schema/validator has NO place to write a passing verdict directly.
   C.2 UNDERPOWERED forces meets_thresholds=False: when real_case_count <
       minCasesForPower, meets is False regardless of the metrics, and the cadence
       recommendation is manual-stays-mandatory. Confirm this cannot be bypassed.
   C.3 THE MANUAL RUN IS NEVER RETIRED. The strongest cadence recommendation is
       manual-reduce-to-periodic-backstop; there is NO "retire" value. Confirm.
   C.4 Metrics with a zero denominator are None (reported honestly), NOT coerced to
       0 or 1; and a None metric never satisfies a threshold.
   C.5 score_benchmark REJECTS a scoreboard caseId that is not in the pre-registered
       benchmark (you cannot score against cases the registration did not commit
       to) and REJECTS a benchmarkName != registration.name (identity).
   C.6 precision counts spuriousDetections as the false-positive denominator;
       recall is over the real registered cases; false-REPRODUCED is the integrity
       metric (detections wrongly tagged REPRODUCED). Confirm the arithmetic.
   C.7 the registration REQUIRES at least one holdout case (a recent real miss); a
       seeded-only benchmark is rejected (it cannot measure the real gap).

D. L-066-1 SCHEMA <-> VALIDATOR PARITY. For all THREE artifacts (candidate-
   falsifier, benchmark-registration, replacement-scoreboard): the pure-Python
   validator must not drift LOOSER than the JSON Schema. Confirm specifically:
   D.1 schemaVersion: a float 1.0 or a bool True must be REJECTED (Python's
       1.0 == 1 == True would pass a naive `in (1,)`; the code uses an
       int-not-bool guard). Verify the guard is present in BOTH modules.
   D.2 OPTIONAL fields the schema constrains are type-checked (e.g. defect.severity
       string; case.probeable bool; case.sourceRef string; telemetry numeric
       fields; spuriousDetections non-negative int). A wrong-typed optional must be
       rejected, matching the schema.
   D.3 integer fields use isinstance(x,int) and not isinstance(x,bool) (flakeCheck
       runs/agreeing; minCasesForPower; predicateShouldHaveFiredMisses).
   D.4 the example fixtures (docs/*-schema-example.json) conform to their schema AND
       pass the Python validator (the dual-validation drift guard the tests pin).

E. NEVER RAISES on malformed input. Every validator + admission_decision +
   score_benchmark + reproduced_findings + check_floor_ratchet_coverage must report
   a bad input as not-ok / a reason, never throw -- on non-dict, missing keys,
   wrong types, bad bytes. (build_candidate_from_finding is the one intentional
   exception: it RAISES ValueError on the programmer error of a non-REPRODUCED
   finding -- confirm that is the only raise and it is a guardrail, not an
   input-validation path.) ASCII-only error strings.

F. THE MANDATORY COVERAGE RULE. check_floor_ratchet_coverage: every REPRODUCED
   finding in a path-aware-critique.json (a reproduced probeable defect) must have
   a candidate (admitted/pending/waived) whose defect.findingRef references it; a
   PENDING candidate satisfies the rule (the gate does not block on human review
   latency); only a MISSING candidate is a violation. reproduced_findings extracts
   exactly the REPRODUCED-tier findings (via evidence_protocol.effective_tier).
   Confirm the matching (by "<provider>:<index>" ref OR description) and that a
   reproduced defect with no artifact at all is flagged.

G. TEST ADEQUACY. Do the new tests actually exercise the named behaviors -- the
   never-auto-merge + rubber-stamp guard, each of the six gates, the underpowered
   force, the never-retire cadence, the None-not-zero metrics, the unregistered-
   caseId rejection, the schemaVersion float/bool rejection, the never-raises
   paths, the coverage matching -- or do any pass WITHOUT exercising the behavior
   they name? Is the schema<->validator parity pinned for all three artifacts?

H. CORRECTNESS / DESIGN HOLES. Any logic bug, off-by-one, or inconsistency between
   a module, its schema, and its docstring? Any claim of CURRENT behavior the code
   does not back (L-064-8)? Anything that would let a brittle agent-authored test
   poison the deterministic floor (the worst outcome the proposal names)?

=== ai_router/evidence_protocol.py (Session 1, VERIFIED; reference for the tiers +
PUBLIC_ENTRYPOINT_KINDS the ratchet reuses) ===
{EVIDENCE}

=== ai_router/floor_ratchet.py (NET-NEW this session; full content) ===
{FLOOR}

=== ai_router/replacement_gate.py (NET-NEW this session; full content) ===
{REPL}

=== docs/candidate-falsifier.schema.json (NET-NEW) ===
{CF_SCHEMA}

=== docs/benchmark-registration.schema.json (NET-NEW) ===
{REG_SCHEMA}

=== docs/replacement-scoreboard.schema.json (NET-NEW) ===
{SB_SCHEMA}

=== STAGED DIFF (the two modules + three schemas + two test files) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=85,
        session_set=str(HERE),
        session_number=5,
    )
    out = HERE / "s5-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
