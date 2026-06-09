- **Issue:** None — Finding 1 is fixed. The new `template-snapshot` job runs on push/PR, installs the extension dependencies, and executes the targeted TS specs directly, so the D8 cold-start snapshot is now CI-enforced instead of local-only.  
  **Location:** `.github/workflows/test.yml`  
  **Fix:** No further change.

- **Issue:** Finding 2 is not fully closed. `start_session` is imported as `ai_router.start_session`, but the mode reset/resolve/assert calls use bare `runtime_mode`. Those are separate module namespaces (`ai_router.runtime_mode` vs `runtime_mode`), so the test does not reliably prove that `start_session.main()` itself set the routed/no-router mode.  
  **Location:** `ai_router/tests/test_cold_start_acceptance.py` imports and Link 4/5 assertions  
  **Fix:** Import and use the package-qualified runtime module for this test’s start-session assertions, e.g. `from ai_router import runtime_mode as ai_runtime_mode`, then use `ai_runtime_mode.reset_for_tests()`, `ai_runtime_mode.resolve_no_router_mode(...)`, and `ai_runtime_mode.is_no_router_mode()` around the `start_session.main(...)` call.

- **Issue:** None — Finding 3 is functionally fixed. The allow-region escape hatch is now explicitly allowlisted, stray markers are violations, and markers in non-allowlisted files no longer suppress later banned lines.  
  **Location:** `ai_router/scripts/drift_guard.py`; `ai_router/tests/test_drift_guard.py`  
  **Fix:** No further functional change. Optional cleanup: update comments/docstrings in `drift_guard.py` that still say only “two files” may use markers, since `ALLOWED_MARKER_FILES` now contains three paths.

- **Issue:** None for Set 058 S3 — the Finding 4 deferral is reasonable. The stale `repository-reference.md` sections cited in Round 1 predate this set, and the described S3 touch is limited to the version-walk / release-status bump. That is real doc debt, but not a correctness defect in this set’s scoped deliverable.  
  **Location:** `docs/repository-reference.md` vs Set 058 S3 scope  
  **Fix:** Track a separate docs-audit/reconciliation set; no reopen needed for S3.