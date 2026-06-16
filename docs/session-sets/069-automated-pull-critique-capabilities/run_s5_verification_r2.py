"""Set 069 S5 -- cross-provider verification ROUND 2 (re-verify the R1 fixes).

R1 (gpt-5-4) returned FAIL with the central never-auto-merge property (A) and the
gate logic (B) already PASS, plus six findings (all L-066-1 parity / a coverage
bug). All are now fixed; this round re-verifies ONLY the fixes (and that they
introduced no regression), pinned to the verifier's own tier so a wording-only
short response cannot auto-escalate cross-provider (L-064-7).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

FILES = [
    "ai_router/floor_ratchet.py",
    "ai_router/replacement_gate.py",
    "ai_router/tests/test_floor_ratchet.py",
    "ai_router/tests/test_replacement_gate.py",
]
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--", *FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

FLOOR = (REPO / "ai_router/floor_ratchet.py").read_text(encoding="utf-8")
REPL = (REPO / "ai_router/replacement_gate.py").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 5 of 6 of Set 069
(automated pull-critique capabilities). This is ROUND 2: re-verify ONLY the fixes
to your Round-1 findings. Round 1 returned FAIL; claims A (never-auto-merge +
rubber-stamp guard) and B (the six gate checks) were already PASS and are
UNCHANGED. The full ai_router suite is GREEN (1953 passed / 5 skipped; the 5 skips
are the S4 real-podman regressions, by design). NO release this session (S6).
Return the structured verdict.

Confirm each Round-1 finding is resolved (cite file:line); flag ONLY a NEW defect
introduced by a fix, not the agreed baseline. Both modules are net-new, pure-
Python, imported by no existing runtime path (additive).

R1 FINDING 1 -> Rejected candidates incorrectly satisfied mandatory coverage.
  FIX: check_floor_ratchet_coverage now zips candidates with their Admission
  decisions and adds a candidate's findingRef to covered_refs ONLY when its status
  is admitted / pending / waived - a REJECTED candidate (human-approved but failing
  a mechanical gate) is skipped, so the reproduced defect stays uncovered (a broken
  candidate, not a done one). New test test_rejected_candidate_does_not_satisfy_
  coverage asserts coverage FAILS when the only matching candidate is approved-but-
  failing. Confirm.

R1 FINDING 2 -> build_candidate_from_finding raised on missing/non-dict transcript
  too, not only on non-REPRODUCED, contradicting the stated one-raise contract.
  FIX: the docstring now states the intended contract is TWO guardrail raises
  (a non-REPRODUCED finding OR a REPRODUCED finding with no transcript dict to
  extract the trusted falsifier from) - both are inconsistent programmer-error
  inputs the ratchet never sees in normal flow (the S1 protocol guarantees a
  REPRODUCED finding carries a valid transcript); every MALFORMED-ARTIFACT path is
  handled by validate_candidate_falsifiers_artifact, which never raises. The two
  builder tests already pin both raises. Confirm the code/doc/tests now agree.

R1 FINDING 3 -> Candidate artifact validator looser than its schema.
  FIX in floor_ratchet (_validate_candidate_structure + validate_candidate_
  falsifiers_artifact): (a) top-level closed-key set _ARTIFACT_TOP_KEYS rejects
  unknown top-level keys (the schema's additionalProperties:false), incl a smuggled
  verdict; (b) top-level notes is type-checked (string); (c) entrypoint.kind is now
  enum-checked structurally against the PUBLIC kinds (agent_harness / arbitrary
  rejected at the artifact level, not just at admission); (d) the optional typed
  sub-fields are checked: failsOnOld.ref/failed/outputHash, passesOnFixed.ref/
  passed, flakeCheck.runs/agreeing (int-not-bool) / stable (bool), humanSignoff.
  by/at/note (string). New parity tests cover agent_harness/arbitrary kind,
  flakeCheck.runs:true, flakeCheck.stable:1, humanSignoff.note:7, failsOnOld.failed
  wrong type, unknown top-level key, wrong-typed notes. Confirm parity now holds.

R1 FINDING 4 -> Replacement validators looser than their schemas, incl a verdict-
  field loophole (C.1).
  FIX in replacement_gate: (a) _REGISTRATION_TOP_KEYS and _SCOREBOARD_TOP_KEYS
  reject unknown top-level keys; the scoreboard set deliberately has NO verdict /
  meets_thresholds / cadence key, so a hand-written passing verdict is REJECTED
  (the load-bearing C.1 "the verdict is derived, never asserted" rule is now
  enforced by the validator, not just the schema); (b) top-level notes is
  type-checked on both artifacts; (c) telemetry.timing.introStageCatches /
  endOfSetCatches are now required to be non-negative (the schema's minimum:0). New
  tests: scoreboard rejects verdict/meets_thresholds/cadence_recommendation top-
  level fields; wrong-typed notes; negative timing; registration rejects unknown
  top-level key + wrong-typed notes. Confirm the loophole is closed.

R1 FINDING 5 -> Tests did not pin the failing behaviors.
  FIX: +15 tests added across the two test files for exactly the above (the
  rejected-coverage case, the entrypoint enum, the wrong-typed optionals, the
  scoreboard verdict-field rejection, the wrong-typed notes, the negative timing).
  Confirm the new tests exercise the behaviors they name (not vacuous passes).

Also confirm NO regression: the never-auto-merge + rubber-stamp guard (A), the six
gates (B), the underpowered-forces-not-met + never-retire cadence + None-not-zero
metrics + unregistered-caseId rejection (C), and never-raises-on-malformed-input
(E) are all still intact after these edits; and the example fixtures
(docs/*-schema-example.json) still conform to schema AND pass the stricter Python
validators.

=== ai_router/floor_ratchet.py (full current content) ===
{FLOOR}

=== ai_router/replacement_gate.py (full current content) ===
{REPL}

=== STAGED DIFF since R1 (both modules + both test files) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=70,
        max_tier=3,
        session_set=str(HERE),
        session_number=5,
    )
    out = HERE / "s5-verification-round-2.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
