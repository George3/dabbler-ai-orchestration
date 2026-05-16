# Change Log — 027-orchestrator-e2e-harness

## Summary

Set 027 ships a **three-layer end-to-end harness** for the AI-led-workflow
orchestrator. The motivation: two recent silent display-drift incidents
(the v0.1.1 `register_session_start` `completedSessions[]`-loss bug in
dabbler-platform; the 2026-05-12 `status: "completed"` past-participle
drift) would have been caught at authoring time by an E2E suite that
drives the real `start_session` / `close_session` CLIs end-to-end. This
set builds that suite as a permanent CI gate.

After this set:

- `pytest -m e2e` runs the Layer 1 Python integration harness — 7
  scenarios (happy-path, cancel/restore, force-close, sibling worktree,
  multiset-sequential, force-close-final-session, register-session-start
  regression) against real CLIs and a tmpdir-scoped git working tree
  with bare remote.
- `npm test` (or `npm run test:unit` on Windows hosts where
  test-electron is broken) runs the Layer 2 tree-provider harness — 20
  scenarios that assert on `SessionSetsProvider.getChildren()` output.
- `npm run test:playwright` runs the Layer 3 rendering smoke — 5
  scenarios that launch a real VS Code Electron instance and assert on
  rendered text in the Session Set Explorer.
- Two real drift classes were pinned by the new harness (not fixed —
  pinning the current behavior with explanatory test comments so the
  next reader/writer change is deliberate). Details in Session 3.

## Sessions

### Session 1 — Python integration harness foundation

- Created `ai_router/tests/e2e/` with `conftest.py`, `fixtures.py`
  (~390 LOC), `test_happy_3session.py`, and
  `test_register_session_start_regression.py`.
- The fixture generator builds a real git working tree + sibling bare
  remote per test, auto-commits and pushes between every harness step
  so the close-out gates (`working_tree_clean`, `pushed_to_remote`,
  `activity_log_entry`, `next_orchestrator_present`,
  `change_log_fresh`) pass naturally.
- Registered the `e2e` pytest marker in `pytest.ini`.
- Cross-provider verification via gpt-5-4 ($0.32); 1 Major + 2 Minor
  findings addressed: history-stability event assertions; full
  post-close state-snapshot; regression test correctly un-marked e2e.
- 430 passed + 1 skipped (was 427 + 1; 2 new fast tests + 1 e2e test).

### Session 2 — Extended Python scenarios

- Added four test files: `test_cancel_restore_midset.py`,
  `test_force_close_path.py`, `test_worktree_discovery.py`,
  `test_multiset_sequential.py`.
- Extended `fixtures.py` with `cancel_set`, `restore_set`,
  `make_sibling_worktree`, `make_additional_set`, and a `force=True`
  option on `drive_close_session`.
- Discovered the `--force` / `--manual-verify` incompatibility and
  patched the fixture accordingly (force uses `--reason-file` alone
  + `AI_ROUTER_ALLOW_FORCE_CLOSE_OUT=1` env var; manual-verify path
  is mutually exclusive).
- Cross-provider verification via gpt-5-4 in 3 sub-rounds
  ($0.17 + $0.14 + $0.18 = $0.48) per the split-large-bundles
  memory; Majors addressed: `git add -A` scope hygiene; multiset
  full-state-snapshot equality; force-close final-session pinning.
- 437 passed + 1 skipped (was 430 + 1; 7 new e2e tests).

### Session 3 — Layer 2 tree-provider harness

- Created `ai_router/tests/e2e/harness_cli.py` (305 LOC) — JSON-over-
  stdout Python shim that wraps `fixtures.py` helpers for the TS side.
- Created `tools/dabbler-ai-orchestration/src/test/suite/e2e/e2eHarness.ts`
  (365 LOC) — TS harness with `replaceWorkspaceFolders`, `buildProvider`,
  `driveHappyPath`, and the full fixture API surface.
- Wrote five TS test files: `treeProvider-happy.test.ts`,
  `treeProvider-cancel.test.ts`, `treeProvider-force.test.ts`,
  `treeProvider-multiset.test.ts`, `treeProvider-worktree.test.ts`
  (20 scenarios total).
- Extended Mocha discovery in `src/test/suite/index.ts` to recurse
  into subdirectories with deterministic sort. Extended the
  `vscode-stub.js` shim to support `workspaceFolders`,
  `updateWorkspaceFolders`, and `onDidChangeWorkspaceFolders` so
  `npm run test:unit` can drive the e2e suite. (`npm test` /
  `@vscode/test-electron` is broken on Windows 11 + VS Code 1.120
  for environmental reasons unrelated to this set; documented as
  the lighter `test:unit` path.)
- **Two real drift discoveries pinned by the harness on first run:**
  1. `register_session_start` at `session_state.py:237` omits
     `completedSessions` key when the array is empty, while Set 022's
     `isCurrentSessionInFlight` predicate requires
     `Array.isArray(...)` — so session 1 of a fresh set displays
     `0/N` WITHOUT the in-flight annotation Set 022 promised.
  2. `isMidSetComplete` at `utils/fileSystem.ts:87` downgrades any
     `currentSession < totalSessions` snapshot to in-progress
     regardless of `forceClosed` / `status`, so a force-closed
     mid-set lives in In Progress with the `[FORCED]` badge — NOT
     in Done. Matches the truthful-display invariant from
     `SessionSetsProvider.ts:36`.
- Neither bug fixed in this session — both are reader/writer changes
  deserving Set 026-style care. Tests pin the current shape with
  explanatory comments so the next change is deliberate.
- Cross-provider verification via gpt-5-4 in 3 sub-rounds
  ($0.23 + $0.17 + $0.20 = $0.60). All 6 findings addressed:
  env-passthrough hygiene; `replaceWorkspaceFolders` reject/timeout;
  refresh cache invalidation; tighter negative assertions;
  identity-config seeding determinism; STATE_RANK dedup precedence;
  multiset in-progress sort coverage.
- 326 tests passing on `test:unit` (was 306 + 20 new e2e).

### Session 4 — Playwright Electron rendering smoke + close-out

- Added `@playwright/test ^1.60.0` as a dev dependency.
- Created `playwright.config.ts` (scoped to `src/test/playwright/`,
  90s test timeout, workers=1 for serial Electron launches).
- Created `src/test/playwright/electronLaunch.ts` (~260 LOC) — VS Code
  launcher via `_electron.launch` against the cached `Code.exe`
  binary at `.vscode-test/`, with isolated user-data-dir +
  extensions-dir per launch; harness shim subprocess plumbing
  mirroring the Layer 2 env hygiene rules
  (`GIT_*` / `PYTHONPATH` scrubbed, UTF-8 forced).
- Created `src/test/playwright/treeView.spec.ts` (~200 LOC) — 5
  rendering-layer scenarios:
  1. **Fresh set** — three not-started sets, asserts
     `Not Started (3)` + each set name visible + negative controls
     on Done/In Progress/Cancelled.
  2. **Mid-session in flight** — drives session 1 to completion +
     starts session 2; asserts `In Progress (1)` + `1/3` +
     `session 2 in flight` + no `[FORCED]`.
  3. **All done** — drives 3 sessions through close-out; asserts
     `Done (1)` + `3/3` + no `in flight`.
  4. **Cancelled** — completes session 1 + cancels; asserts
     `Cancelled (1)` group renders.
  5. **Force-closed** — completes session 1 + force-closes session 2;
     asserts `[FORCED]` badge + `In Progress (1)` (NOT Done, per
     the Session 3 truthful-display invariant).
- **Layer 3 environment outcome:** all 5 scenarios passed on first
  clean run (1m24s total — well under the 3-min budget in the spec).
  Playwright's `_electron.launch` against `Code.exe` directly
  bypasses the broken `@vscode/test-electron` path that blocked
  Layer 2 on this Windows host.
- Single selector bug found during the run and fixed:
  `.activitybar [aria-label*="Dabbler AI Orchestration"]` matched
  both the action icon and a hidden badge; narrowed to
  `.action-label[aria-label*=...]` to disambiguate.
- Version bumps: `ai_router` 0.3.0 → 0.3.1; extension 0.13.15 →
  0.13.16.
- Updated `CLAUDE.md` with the Layer 1/2/3 test commands and the
  "lowest layer that can see the regression" guidance.
- Updated both `CHANGELOG.md` files.

## Versions shipped

| Package | Old | New |
|---|---|---|
| `dabbler-ai-router` (PyPI) | 0.3.0 | 0.3.1 |
| `dabbler-ai-orchestration` (Marketplace) | 0.13.15 | 0.13.16 |

Release tags are pushed by the operator post-merge per the standard
tag-driven release workflow.

## Costs

| Session | Verification | Cost |
|---|---|---|
| 1 | gpt-5-4 (single round) | $0.32 |
| 2 | gpt-5-4 (3 sub-rounds, split per memory) | $0.48 |
| 3 | gpt-5-4 (3 sub-rounds, split per memory) | $0.60 |
| 4 | gpt-5-4 (2 sub-rounds: A + B) | $0.46 |
| **Total** | | **$1.86** |

Set NTE was $5.00; came in at **37% of budget**. Well under the
repo-level $10.00 ceiling.

Session 4 verifier returned 2 Major + 5 Minor findings, all addressed
in this session: numeric-version sort for the cached VS Code binary
discovery; separate `_electronEnv()` that preserves Linux GUI session
vars; `F1` cross-platform command-palette shortcut; rewritten
CHANGELOG entries clarifying the `ai_router` 0.3.1 harness is
repo-only (excluded from the published wheel); tightened cancel test
naming; independent best-effort teardown that doesn't skip tmpdir
cleanup on `closeVSCode` failure; per-test `setTimeout(120_000)`
overrides removed so the documented 90s ceiling actually applies.

The Linux GUI-vars fix uncovered a related real-world hazard during
re-run: the new full-env passthrough leaked `ELECTRON_RUN_AS_NODE=1`
plus the `VSCODE_*` IPC protocol vars from the parent VS Code /
Cursor IDE host, flipping Code.exe into CLI-arg-parsing mode (every
launch arg rejected as "bad option", exit code 9). Added an
explicit `_ELECTRON_VAR_BLOCKLIST` (`ELECTRON_RUN_AS_NODE`,
`ATOM_SHELL_INTERNAL_RUN_AS_NODE`) and `VSCODE_` prefix scrub. All
5 Playwright tests pass again at 1m24s. This regression — and the
fix — would have been latent on any host where the harness is
invoked from inside VS Code's integrated terminal; the original
strict-scrub env happened to mask it because no IDE vars leaked at
all.
