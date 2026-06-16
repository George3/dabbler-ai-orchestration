VERDICT: ISSUES_FOUND

## Findings

1. **Severity:** Major
   **Category:** correctness
   **Location:** `ai_router/run_test_sandbox.py:418`
   **Description:** `run_test_in_cage` promises to tear the cage down on every exit path and to return a `RunTestResult` for cage-setup failures, but temp-parent creation happens before the protected `try`/`finally`. If `tempfile.mkdtemp(..., dir=worktrees_parent)` fails, the function raises before it can convert the failure into a raw `error` result or run teardown. I reproduced this on the current code by calling `run_test_in_cage(..., worktrees_parent=Path("does-not-exist") / "nested")`; it raises `FileNotFoundError [WinError 3]` instead of returning a cage error. That contradicts the pinned contract's claim that a cage that cannot be created reports an explicit `ERROR:` rather than proceeding. **Fix:** move temp-directory creation under the protected block, initialize the teardown variables defensively, and convert pre-worktree setup failures into a `RunTestResult(error=...)` instead of letting the exception escape.

2. **Severity:** Major
   **Category:** correctness
   **Location:** `ai_router/contract_gate.py:_load_json_artifact`
   **Description:** `_load_json_artifact` opens artifact files as UTF-8 but catches only `OSError` and `json.JSONDecodeError` (`ai_router/contract_gate.py:493-495`). Invalid UTF-8 bytes therefore raise `UnicodeDecodeError` through `validate_contract_manifest`, `validate_contract_floor_result`, and transitively `validate_contract_gate`, even though those functions explicitly promise never-raising behavior (`ai_router/contract_gate.py:569`, `ai_router/contract_gate.py:1007`). I reproduced this on the current code by writing `b"\x80\x81not-utf8"` to both `contract-manifest.json` and `contract-floor-result.json`; both validators raise `UnicodeDecodeError` instead of returning `ok=False` / `unreadable`. A corrupt artifact can therefore crash close-out instead of yielding the documented gate failure/warning path. **Fix:** catch `UnicodeError` in `_load_json_artifact`, then add validator and close-out tests covering invalid-UTF-8 manifest and floor-result files.

3. **Severity:** Minor
   **Category:** false-confidence
   **Location:** `ai_router/__init__.py:953`
   **Description:** The public export note for `run_test` still says "the real tree is never mutated," but the pinned cage contract explicitly narrows the guarantee to disposable-CWD isolation for a trusted command and says deliberate absolute-path writes, committed-symlink escapes, main-worktree discovery, or detached children can still reach the real filesystem (`docs/session-sets/068-cadence-study-and-contract-gate/run-test-contract.md`, scope section). That package-level wording overstates the containment guarantee and conflicts with the contract's own threat-model disclaimer. **Fix:** replace the absolute wording with the bounded guarantee from the contract (ordinary working-directory writes land in the disposable worktree; this is not an OS sandbox) and align any duplicated package/changelog phrasing to the same language.