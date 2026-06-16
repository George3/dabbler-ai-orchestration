## Verdict
**PASS**

## Round-1 findings

1. **Resolved** — Rejected candidates no longer satisfy mandatory coverage.  
   - **Code:** `ai_router/floor_ratchet.py:751-775` skips `ADMIT_REJECTED` when building `covered_refs`; coverage only counts admitted/pending/waived candidates.  
   - **Test:** `ai_router/tests/test_floor_ratchet.py:443-455` directly constructs an approved-but-mechanically-failing candidate for `openai:0` and asserts coverage fails with `cov.rejected == 1`.

2. **Resolved** — Builder code/doc/tests now agree on the two-raise contract.  
   - **Code/doc:** `ai_router/floor_ratchet.py:612-630` documents exactly two `ValueError` guardrails; `ai_router/floor_ratchet.py:632-642` implements them for non-`REPRODUCED` and missing/non-dict transcript.  
   - **Tests:** `ai_router/tests/test_floor_ratchet.py:373-384` pins both raises.

3. **Resolved** — Candidate artifact validator now matches schema strictness.  
   - **Code:**  
     - Closed top-level keys: `ai_router/floor_ratchet.py:121-124`, enforced at `ai_router/floor_ratchet.py:562-569`  
     - `notes` type check: `ai_router/floor_ratchet.py:568-569`  
     - `entrypoint.kind` enum enforcement: `ai_router/floor_ratchet.py:439-455`  
     - Optional typed subfields: `ai_router/floor_ratchet.py:466-503`  
   - **Tests:**  
     - Unknown top-level key: `ai_router/tests/test_floor_ratchet.py:284-290`  
     - Wrong-typed `notes`: `ai_router/tests/test_floor_ratchet.py:292-294`  
     - `entrypoint.kind` enum parity (`agent_harness`, `arbitrary`, `""`): `ai_router/tests/test_floor_ratchet.py:296-301`  
     - `flakeCheck.runs=True`: `ai_router/tests/test_floor_ratchet.py:303-308`  
     - `flakeCheck.stable=1`: `ai_router/tests/test_floor_ratchet.py:310-314`  
     - `failsOnOld.failed` wrong type: `ai_router/tests/test_floor_ratchet.py:316-320`  
     - `humanSignoff.note=7`: `ai_router/tests/test_floor_ratchet.py:322-326`

4. **Resolved** — Replacement validators now match schema strictness; verdict-field loophole closed.  
   - **Code:**  
     - Closed registration/scoreboard top-level keys: `ai_router/replacement_gate.py:80-91`, enforced at `ai_router/replacement_gate.py:194-198` and `ai_router/replacement_gate.py:347-355`  
     - `notes` type checks: `ai_router/replacement_gate.py:197-198`, `ai_router/replacement_gate.py:356-357`  
     - Non-negative timing enforcement: `ai_router/replacement_gate.py:298-307`  
   - **Tests:**  
     - Registration unknown top-level key + wrong-typed `notes`: `ai_router/tests/test_replacement_gate.py:168-174`  
     - Scoreboard rejects `verdict` / `meets_thresholds` / `cadence_recommendation`: `ai_router/tests/test_replacement_gate.py:220-226`  
     - Scoreboard wrong-typed `notes`: `ai_router/tests/test_replacement_gate.py:228-230`  
     - Negative timing rejection: `ai_router/tests/test_replacement_gate.py:232-236`

5. **Resolved** — New tests are substantive, not vacuous.  
   - **Floor ratchet:** tests start from a valid `_good_candidate()`/artifact and mutate only the targeted field/condition before asserting failure, e.g. `ai_router/tests/test_floor_ratchet.py:284-326`, `ai_router/tests/test_floor_ratchet.py:443-455`.  
   - **Replacement gate:** same pattern for registration/scoreboard validators, e.g. `ai_router/tests/test_replacement_gate.py:168-174`, `ai_router/tests/test_replacement_gate.py:220-236`.  
   - These tests exercise the named behaviors directly, not via unrelated invalidity.

## Regression check

- **A — never-auto-merge + rubber-stamp guard:** **PASS**  
  - Builder still emits pending only: `ai_router/floor_ratchet.py:622-624`, `ai_router/floor_ratchet.py:655-670`  
  - Admission still requires human approval and still rejects approved-but-failing candidates: `ai_router/floor_ratchet.py:275-285`, `ai_router/floor_ratchet.py:324-348`  
  - Tests: `ai_router/tests/test_floor_ratchet.py:354-371`, `ai_router/tests/test_floor_ratchet.py:182-187`

- **B — six gate checks:** **PASS**  
  - Gate logic unchanged/intact: `ai_router/floor_ratchet.py:167-260`, `ai_router/floor_ratchet.py:319-364`  
  - Tests cover each gate path: `ai_router/tests/test_floor_ratchet.py:128-180`

- **C — underpowered-forces-not-met + never-retire cadence + None-not-zero metrics + unregistered-caseId rejection:** **PASS**  
  - Underpowered forces `meets_thresholds=False`: `ai_router/replacement_gate.py:488-523`  
  - Never-retire cadence preserved: `ai_router/replacement_gate.py:64-68`, `ai_router/replacement_gate.py:511-523`  
  - Metrics remain `None` on zero denominator: `ai_router/replacement_gate.py:415-418`, `ai_router/replacement_gate.py:483-486`  
  - Unregistered `caseId` still hard-fails scoring: `ai_router/replacement_gate.py:461-478`  
  - Tests: `ai_router/tests/test_replacement_gate.py:254-312`

- **E — never-raises-on-malformed-input:** **PASS**  
  - Floor ratchet validator/coverage/admission remain non-raising on malformed input: `ai_router/floor_ratchet.py:285`, `ai_router/floor_ratchet.py:526-593`, `ai_router/floor_ratchet.py:731-806`  
  - Replacement validators/scoring remain non-raising on malformed input: `ai_router/replacement_gate.py:166`, `ai_router/replacement_gate.py:317-320`, `ai_router/replacement_gate.py:424`, `ai_router/replacement_gate.py:441-478`  
  - CLI bad-bytes reporting tests: `ai_router/tests/test_floor_ratchet.py:493-499`, `ai_router/tests/test_replacement_gate.py:349-355`

- **Example fixtures still conform to schema and stricter Python validators:** **PASS**  
  - Floor ratchet: `ai_router/tests/test_floor_ratchet.py:67-76`  
  - Replacement gate: `ai_router/tests/test_replacement_gate.py:85-96`

## New defects introduced by fixes
- **None found**