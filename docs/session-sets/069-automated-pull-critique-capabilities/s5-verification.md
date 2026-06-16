## Verdict

**FAIL**

## Scope

- **PASS** — additive-only diff: new `ai_router/floor_ratchet.py`, `ai_router/replacement_gate.py`, three schemas, and new tests. No existing runtime-path behavior is changed.

## Claim Check

| Claim | Status | Note |
|---|---|---|
| A | PASS | Never-auto-merge, rubber-stamp guard, and waiver behavior are implemented. |
| B | PASS | The gate logic matches the stated checks. |
| C | FAIL | `validate_scoreboard()` is looser than the schema, so a raw scoreboard can still carry hand-authored verdict-like top-level fields. |
| D | FAIL | The Python validators drift looser than the JSON Schemas in multiple load-bearing places. |
| E | FAIL | `build_candidate_from_finding()` raises on missing/non-dict transcript, not only on non-REPRODUCED input. |
| F | FAIL | `check_floor_ratchet_coverage()` lets rejected candidates satisfy coverage. |
| G | FAIL | Tests miss the validator drift and rejected-coverage bug, and they encode the extra builder raise. |
| H | FAIL | The above are real contract/logic holes. |

## Issues

### Issue → Rejected candidates incorrectly satisfy mandatory coverage
**Location** → `ai_router/floor_ratchet.py::check_floor_ratchet_coverage`

**Fix** → Only treat a candidate as covering a finding when its corresponding `AdmissionDecision.status` is one of:
- `admitted`
- `pending`
- `waived`

Exclude `rejected` from `covered_refs`. Add a test where the only matching candidate is approved-but-failing and assert coverage fails.

---

### Issue → `build_candidate_from_finding()` violates the stated raise contract
**Location** → `ai_router/floor_ratchet.py::build_candidate_from_finding`

**Fix** → Align code/doc/tests so the function has exactly the intended exception behavior. Current code raises both:
- on non-REPRODUCED input
- on REPRODUCED input with missing/non-dict transcript

The session contract says only the first should raise. Either:
- make missing/invalid transcript non-raising and let validator/admission reject the built stub, or
- explicitly change the stated contract/doc/tests if two guardrail raises are actually intended.

---

### Issue → Candidate artifact validator is looser than its schema
**Location** → `ai_router/floor_ratchet.py::_validate_candidate_structure`, `validate_candidate_falsifiers_artifact`

**Fix** → Enforce schema parity, including:
- top-level `additionalProperties: false`
- top-level `notes` type
- `entrypoint.kind` enum, not just non-empty string
- optional typed fields in `failsOnOld`, `passesOnFixed`, `flakeCheck`, `humanSignoff`
- `int`-not-`bool` guards for `flakeCheck.runs` / `flakeCheck.agreeing`

Concrete currently-accepted schema-invalid examples include:
- `entrypoint.kind: "agent_harness"` or arbitrary string
- `flakeCheck.runs: true`
- `flakeCheck.stable: 1`
- `humanSignoff.note: 7`
- extra unexpected top-level keys

Add parity tests for those cases.

---

### Issue → Replacement validators are looser than their schemas, including a verdict-field loophole
**Location** → `ai_router/replacement_gate.py::validate_benchmark_registration`, `validate_scoreboard`, `_validate_telemetry`

**Fix** → Enforce:
- top-level `additionalProperties: false` for both artifacts
- top-level `notes` type for both artifacts
- rejection of extra scoreboard fields such as `verdict`, `meets_thresholds`, or `cadence_recommendation`
- non-negative integer minima for `telemetry.timing.introStageCatches` and `endOfSetCatches`

This is the load-bearing C.1 gap: the schema has no verdict field, but the Python validator currently allows one via unchecked extra top-level properties.

Add tests for:
- extra top-level verdict-like fields on scoreboard
- wrong-typed `notes`
- negative timing counts

---

### Issue → Test coverage does not pin the failing behaviors
**Location** → `ai_router/tests/test_floor_ratchet.py`, `ai_router/tests/test_replacement_gate.py`

**Fix** → Add tests for:
- rejected candidate does **not** satisfy coverage
- candidate validator rejects schema-invalid `entrypoint.kind`
- candidate validator rejects wrong-typed optional fields in `failsOnOld` / `passesOnFixed` / `flakeCheck` / `humanSignoff`
- scoreboard validator rejects extra top-level verdict-like fields
- benchmark/scoreboard validators reject wrong-typed top-level `notes`
- scoreboard validator rejects negative timing counts

Also update the builder tests to match the intended raise contract.