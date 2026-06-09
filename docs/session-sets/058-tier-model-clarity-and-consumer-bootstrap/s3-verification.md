- **Issue:** The required D8 snapshot check is not actually enforced in CI.  
  **Location:** `.github/workflows/test.yml`; `tools/dabbler-ai-orchestration/src/test/suite/coldStartSnapshot.test.ts`  
  **Fix:** Add a CI job/step that installs the extension dependencies and runs the cold-start snapshot test on push/PR. If the full TS unit suite cannot run because of the known unrelated Set-026 failures, invoke this snapshot spec directly rather than leaving the D8 snapshot guard as local-only coverage.

- **Issue:** The D5 “cold-start acceptance” test does not exercise `start_session`; it only checks tier resolution and then mutates state directly via `register_session_start()`. That leaves the actual start-session arg plumbing unproved.  
  **Location:** `ai_router/tests/test_cold_start_acceptance.py` (`test_cold_start_chain`, especially Link 4/5); overclaimed in `tools/dabbler-ai-orchestration/src/test/suite/coldStartSnapshot.test.ts` comments (“drives start_session -> close_session per tier”).  
  **Fix:** Invoke the real `start_session` CLI/runner in the test, with routing/provider internals monkeypatched so no external calls occur. Assert that Full runs the routed path and Lightweight runs the `--no-router` path, then keep the shared-gate close step.

- **Issue:** The stale-framing allow-region escape hatch is unrestricted, so any live doc can suppress the guard. That does not satisfy the claim that only the designated ban-documenting files are exempt.  
  **Location:** `ai_router/scripts/drift_guard.py` (`scan_stale_framing`), `ai_router/tests/test_drift_guard.py` (allow-region tests on arbitrary temp docs), and live markers in `tools/dabbler-ai-orchestration/CHANGELOG.md`  
  **Fix:** Enforce an explicit allowlist of repo-relative files permitted to use `<!-- drift-guard:allow-begin/end -->` markers, and fail if markers appear anywhere else. Remove/reword the changelog quote instead of exempting it, or add it deliberately to that allowlist and update the documentation to match reality.

- **Issue:** `docs/repository-reference.md` is still materially stale despite the Set 058 version-walk update. It documents removed extension surfaces and outdated architecture, so the “repository-reference updated” deliverable is incomplete/correctness-risky.  
  **Location:** `docs/repository-reference.md` (e.g. references to Provider Queues/Heartbeats, `TreeDataProvider`-based Session Sets, obsolete state-derivation descriptions)  
  **Fix:** Reconcile the file to the current product: describe the webview-based Session Sets view, remove retired Provider Queues/Heartbeats references, and update any outdated state/runtime descriptions. If only the release-status section was meant to change, do not leave the rest of the file carrying known-stale internals.