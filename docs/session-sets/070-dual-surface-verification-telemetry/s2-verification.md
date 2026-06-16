# ISSUES FOUND

## Issue 1
- **Category:** Validator / Scoring Honesty
- **Severity:** High
- **Issue:** `validate_comparison_artifact()` does not enforce that `provenanceComplete=True` is incompatible with nonzero `pushUnkeyed` / `pullUnkeyed` counts unless an explicit unkeyed finding is also present. A malformed artifact can therefore validate as "complete" while still declaring unmergeable findings. `score_comparison()` then trusts only the boolean flag and clears `upper_bound`, producing a settled tally from incomplete provenance.
- **Location:** `ai_router/dual_surface_verify.py:967-976`, `ai_router/dual_surface_verify.py:1106-1117`
- **Fix:** Reject any artifact where `provenanceComplete is True and (pushUnkeyed != 0 or pullUnkeyed != 0)`. Make `score_comparison()` derive `upper_bound` from both the boolean and the counts so malformed artifacts cannot suppress the honesty warning.

## Issue 2
- **Category:** CLI / Error Discipline / Mode Wiring
- **Severity:** Medium
- **Issue:** `record-mode` can crash on a malformed existing `activity-log.json`. `has_dual_surface_mode_record()` returns `False` on unreadable logs, so `resolve_and_record_dual_surface_mode()` falls through to `record_dual_surface_mode()`, which blindly `json.load()`s and mutates the result. `main()` only catches `ValueError`, so `JSONDecodeError`, `UnicodeError`, or shape errors from non-object logs escape instead of returning a controlled nonzero result.
- **Location:** `ai_router/dual_surface_verify.py:1471-1487`, `ai_router/dual_surface_verify.py:1495-1515`, `ai_router/dual_surface_verify.py:1590-1597`
- **Fix:** Detect unreadable/malformed activity logs before recording and return a controlled exit path. Harden `record_dual_surface_mode()` to validate `log` is a dict and `entries` is a list, and have `main()` catch that failure and return `2` with ASCII-only output.

## Issue 3
- **Category:** Test Adequacy
- **Severity:** Medium
- **Issue:** Multiple tests do not exercise the behavior they claim, leaving the real gaps above unpinned. `test_ordering_both_then_keyed_single_then_unkeyed` only checks provenance labels, so it still passes if the keyed-single and unkeyed trailing entries are swapped because both are `push-only`. `test_record_bad_mode_returns_2` never supplies a bad mode at all; it uses valid `off` and asserts the happy path. There is also no test for `provenanceComplete=True` with nonzero unkeyed counts and no test for `record-mode` against a malformed preexisting activity log.
- **Location:** `ai_router/tests/test_dual_surface_s2.py:101-112`, `ai_router/tests/test_dual_surface_s2.py:670-674`
- **Fix:** Assert ordering on the actual findings/keys rather than only provenance labels; replace the bad-mode test with a truly invalid input path; add explicit tests for `(provenanceComplete=True, pushUnkeyed>0 or pullUnkeyed>0)` rejection and malformed-activity-log handling in `record-mode`.