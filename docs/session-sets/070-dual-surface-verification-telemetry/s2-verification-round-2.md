# ISSUES FOUND

## Issue 1
- **Category:** CLI / Error Discipline / Mode Wiring
- **Severity:** Medium
- **Issue:** Fix 2 is not complete. `record-mode` still has uncaught traceback paths on parseable-but-malformed `activity-log.json`. If `entries` is non-iterable (for example `1`), `has_dual_surface_mode_record()` iterates it directly and raises `TypeError` before `record_dual_surface_mode()` can repair anything. If `entries` is a list but contains a matching entry with a non-int `stepNumber` (for example `[]`), `record_dual_surface_mode()` raises uncaught `TypeError` via `int(e.get("stepNumber", 0))`. `main()` does not catch `TypeError`, so the CLI still escapes instead of returning controlled exit `2`. The same malformed `entries` shape also affects `read_dual_surface_mode()` / `read-mode`.
- **Location:** `ai_router/dual_surface_verify.py:1471-1487`, `ai_router/dual_surface_verify.py:1547-1584`, `ai_router/dual_surface_verify.py:1609-1626`
- **Fix:** In `has_dual_surface_mode_record()` and `read_dual_surface_mode()`, require `entries` to be a list before iterating. In `record_dual_surface_mode()`, validate `stepNumber` as an int-not-bool before using it, and ignore or raise controlled `ValueError` for bad shapes instead of calling `int(...)` on arbitrary data. Add `TypeError` handling in the CLI branch only as belt-and-suspenders, not as the primary fix.

## Issue 2
- **Category:** Test Adequacy
- **Severity:** Medium
- **Issue:** Fix 3 is not complete for malformed-log handling. `test_record_repairs_non_list_entries` uses `entries="oops"`, which is iterable and therefore does not exercise the still-broken `has_dual_surface_mode_record()` path used by CLI `record-mode`. There is still no test for `record-mode` with a parseable malformed object like `{"entries": 1}` or with a bad `stepNumber` shape, so the uncaught traceback in Issue 1 remains unpinned.
- **Location:** `ai_router/tests/test_dual_surface_s2.py:558-567`, `ai_router/tests/test_dual_surface_s2.py:708-718`
- **Fix:** Add CLI coverage for `main(["record-mode", ...])` with `activity-log.json` containing `{"sessionSetName":"070-set","entries":1}` and with `{"sessionSetName":"070-set","entries":[{"sessionNumber":1,"stepNumber":[]}]} `, and assert controlled exit `2` with ASCII-only output. Add direct reader tests for non-list `entries` as well.