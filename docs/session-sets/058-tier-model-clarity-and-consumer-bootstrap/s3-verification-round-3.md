- **Issue:** None — Follow-up A is closed. The cold-start test now imports `runtime_mode` from `ai_router` alongside `start_session`, so the pre/post assertions read the same `ai_router.runtime_mode` module object that `start_session.main()` mutates. This makes the coupling explicit and no longer depends on the bare-name alias for correctness.  
  **Location:** `ai_router/tests/test_cold_start_acceptance.py`  
  **Fix:** No further change.

- **Issue:** None — Follow-up B is closed. The `drift_guard` documentation now refers to the explicit `ALLOWED_MARKER_FILES` allowlist rather than claiming only “two files” may use markers, matching the current three-entry allowlist.  
  **Location:** `ai_router/scripts/drift_guard.py`  
  **Fix:** No further change.