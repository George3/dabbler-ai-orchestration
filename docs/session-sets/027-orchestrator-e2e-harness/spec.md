# Orchestrator end-to-end harness

> **Purpose:** Build a hybrid end-to-end test harness for the
> AI-led-workflow orchestrator that exercises real `start_session` /
> `close_session` CLIs against fixture session sets and verifies both
> the on-disk state and the Session Set Explorer's rendered tree.
> Four sessions: Python integration foundation → extended scenarios
> (cancel/restore, force-close, worktree, version-skew regression) →
> `@vscode/test-electron` tree-provider harness → Playwright Electron
> rendering smoke. Ships `ai_router` v0.3.1 + extension v0.13.16.
>
> **Session Set:** `docs/session-sets/027-orchestrator-e2e-harness/`
> **Created:** 2026-05-16
> **Workflow:** Full
> **Prerequisite:** Set 026 closed. Operator-reported `register_session_start`
> regression in `dabbler-platform` (v0.1.1 installed; preserved-array logic
> ships in v0.2.x onwards) is the proximate motivation — this set adds a
> regression test that pins that exact bug shut, plus a broader harness so
> the next silent display-drift class is caught before it ships.

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: false
requiresE2E: true
uatStyle: ad-hoc
uatScope: none
effort: normal
```

`requiresE2E: true` because Session 4 ships Playwright Electron tests
against the actual VS Code UI — that's E2E by any reasonable definition.
The harness itself is the deliverable; there is no operator-facing UAT.

---

## Motivation

The framework's display layer has accumulated subtle drift classes that
are only caught when an operator notices the tree view says something
wrong. Two recent examples that an E2E harness would have caught at
authoring time:

1. **`completedSessions[]` schema loss across versions.** dabbler-platform
   has `dabbler-ai-router 0.1.1` pinned via a `>=0.1.0` floor. The
   `completedSessions[]` preservation in `register_session_start` was added
   in Set 022 (shipped as 0.2.x). On 0.1.1, every `start_session` call
   wipes the array because the writer doesn't know the field exists.
2. **`status: "completed"` past-participle drift** (the 2026-05-12
   incident). Schema-strict-readers tolerated it via the alias map, but
   the extension showed `N−1/N` until the count derivation was
   canonicalized in v0.13.10.

Both are silent: nothing breaks, the count just slowly goes wrong. The
existing per-module unit tests don't catch them because they exercise
the data flow at the function level — not the end-to-end "operator runs
a session set, watches the tree update" path.

This set builds that path as a permanent CI gate.

---

## Architecture overview

The harness is **three layered test suites** sharing one fixture
generator:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Fixture generator (Python)                                          │
│  ai_router/tests/e2e/fixtures.py                                     │
│  - make_session_set(slug, total_sessions, workflow_tier, ...)        │
│  - drive_session(set_dir, n, scenario={"happy","cancel","force",...})│
│  - tmpdir-scoped; uses manual verification (zero API spend)          │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
        ┌────────────┼──────────────────────────┐
        ▼            ▼                          ▼
┌──────────────┐ ┌────────────────────┐ ┌─────────────────────────────┐
│  Layer 1     │ │  Layer 2           │ │  Layer 3                    │
│  pytest      │ │  @vscode/test-     │ │  Playwright Electron        │
│  Python      │ │  electron (Mocha)  │ │  (TS, vsce-test-host)       │
│              │ │                    │ │                             │
│  Asserts on: │ │  Asserts on:       │ │  Asserts on:                │
│  - state.json│ │  - provider        │ │  - rendered tree label text │
│  - events    │ │    .getChildren()  │ │  - icon class               │
│  - change-log│ │  - bucketing       │ │  - badge presence           │
│  - completed-│ │  - file watcher    │ │  - screenshot baseline      │
│    Sessions[]│ │    debounce        │ │                             │
└──────────────┘ └────────────────────┘ └─────────────────────────────┘
```

Layers cost: Layer 1 ~5s per scenario, Layer 2 ~15s per scenario,
Layer 3 ~30s per scenario (Electron cold start dominates). Layer
choice per assertion is "lowest layer that can see the regression."

---

## Sessions

### Session 1 of 4: Python integration harness foundation

**Goal:** Build the fixture generator and the first end-to-end scenario.
Ship one passing 3-session happy-path test that drives both `start_session`
and `close_session` CLIs against a tmpdir-scoped fixture and asserts on
every state-file invariant.

**Steps:**

1. Create `ai_router/tests/e2e/` directory with:
   - `__init__.py`
   - `fixtures.py` — fixture generator helpers
   - `conftest.py` — pytest fixtures (tmpdir, env-var isolation)
   - `test_happy_3session.py` — first scenario

2. In `fixtures.py`, implement:
   - `make_session_set(tmp_path, slug, total_sessions, workflow_tier="Full") -> Path`
     — creates `<tmp_path>/docs/session-sets/<slug>/spec.md` with a minimal
     spec frontmatter block matching what the orchestrator expects
     (`totalSessions`, `requiresUAT: false`, `requiresE2E: false`,
     `uatStyle: ad-hoc`, `effort: normal`).
   - `drive_start_session(set_dir, session_number, **orchestrator_kwargs)`
     — invokes `python -m ai_router.start_session` via `subprocess.run`,
     captures stdout/stderr, asserts exit 0.
   - `drive_close_session(set_dir, session_number, scenario="happy")`
     — invokes `python -m ai_router.close_session --manual-verify
     --reason-file <tmp>` with a minimal disposition + change-log
     pre-staged. Returns the exit code so scenario tests can assert on
     failure paths too.
   - `make_disposition(set_dir, session_number, status="completed")`
     — writes `session-reviews/session-NNN/disposition.json`.
   - `make_change_log(set_dir, summary="trivial test session")`
     — writes `change-log.md` with the gate-required header. Only
     called on the final session (close-out's
     `check_change_log_fresh` gate fires only on final).
   - `read_state(set_dir) -> dict` and
     `read_events(set_dir) -> list[Event]` — read helpers.

3. In `test_happy_3session.py`, the canonical happy-path scenario:
   - Create a 3-session set.
   - For session N in 1..3:
     - `drive_start_session(set_dir, N)`
     - Assert `state.currentSession == N`, `state.status == "in-progress"`,
       `state.lifecycleState == "work_in_progress"`,
       `state.completedSessions == list(range(1, N))` (or absent on N=1).
     - Assert the events ledger has one `work_started` for N.
     - `make_disposition(set_dir, N)`
     - If N == 3: `make_change_log(set_dir)`.
     - `drive_close_session(set_dir, N)`
     - Assert `state.completedSessions == list(range(1, N+1))`.
     - Assert the events ledger has one `closeout_succeeded` for N.
     - For non-final: assert `state.status == "in-progress"`,
       `state.lifecycleState == "work_in_progress"`.
     - For final (N == 3): assert `state.status == "complete"`,
       `state.lifecycleState == "closed"`, `state.completedAt` not None.

4. Pin the v0.1.1 regression explicitly:
   - Add a `test_register_session_start_preserves_completed_sessions`
     test that:
     - Calls `register_session_start(set_dir, 2, total_sessions=3, ...)`
       on a state with `completedSessions: [1]` already present.
     - Asserts the rewritten state still has `completedSessions: [1]`.
   - This is the regression test for the exact bug operator hit in
     dabbler-platform. Pinning it here prevents the same loss class
     from re-emerging on the canonical writer.

5. Wire the new suite into pytest:
   - `pyproject.toml` already includes the `tests` extra. The new
     directory is auto-discovered. No setup.py change needed.
   - Add a marker `e2e` to the pytest config so the harness can be
     filtered on/off (`pytest -m "not e2e"` for fast pre-commit;
     `pytest -m e2e` for the full harness pass).

**Deliverables:**

- `ai_router/tests/e2e/__init__.py`
- `ai_router/tests/e2e/conftest.py`
- `ai_router/tests/e2e/fixtures.py`
- `ai_router/tests/e2e/test_happy_3session.py`
- `ai_router/tests/e2e/test_register_session_start_regression.py`
- `pyproject.toml` — add `e2e` marker registration

**Acceptance:**

- `pytest ai_router/tests/e2e/ -m e2e` passes both files.
- The `register_session_start` regression test reproduces the v0.1.1 bug
  when temporarily reverted (manual operator check, not a CI assertion).
- Full pytest suite green; no churn in the 427-test baseline.

**Out of scope for Session 1:**

- Cancel/restore, force-close, worktree, multi-set scenarios (Session 2).
- Any TypeScript or VS Code-side test (Sessions 3-4).
- Router-driven scenarios that make real API calls — the harness uses
  `--manual-verify` throughout, period.

---

### Session 2 of 4: Extended Python scenarios

**Goal:** Cover the four remaining "interesting" code paths in the
Python orchestrator: cancel/restore mid-set, force-close, worktree
auto-discovery, and multi-set sequential. Each becomes its own
fixture-driven test file under `ai_router/tests/e2e/`.

**Steps:**

1. `test_cancel_restore_midset.py`:
   - 4-session set. Drive sessions 1 and 2 to completion.
   - At session 3 mid-work: call `dabbler.cancelLifecycle` equivalent
     (write `CANCELLED.md` with a reason via the Python helper
     `ai_router.cancel_lifecycle`).
   - Assert state bucketing-relevant fields: `CANCELLED.md` present,
     state file reflects cancellation marker per Set 008's spec.
   - Restore: write `RESTORED.md`, resume from session 3, complete
     normally through session 4.
   - Assert: final state `completedSessions == [1, 2, 3, 4]`,
     `status == "complete"`, audit trail (both `CANCELLED.md` and
     `RESTORED.md` present).

2. `test_force_close_path.py`:
   - 3-session set. Drive session 1 normally.
   - At session 2: trigger close-out with `--force --reason-file <tmp>`
     before disposition exists.
   - Assert: state has `forceClosed: true`, `status` reflects continued
     in-progress (force on a non-final session does not flip to
     `complete`), events ledger records the bypass.
   - Drive session 3 normally with change-log; final close-out
     succeeds normally (force-flag does not infect subsequent sessions).

3. `test_worktree_discovery.py`:
   - Build a fixture that simulates a sibling worktree layout
     (`<tmp>/repo/` main, `<tmp>/repo-worktrees/feature-x/` sibling).
   - Both contain `docs/session-sets/<slug>/` with state.
   - Assert the **Python-side** worktree-listing helper picks up
     both. (The extension-side discovery is exercised in Session 3.)

4. `test_multiset_sequential.py`:
   - Three session sets in one fixture root: a 3-session, a 4-session,
     and a 3-session (matches the operator's "three session sets with
     3-4 sessions each" framing in the design conversation).
   - Drive them sequentially: complete set A entirely, then set B,
     then set C. After each close-out, assert the *other* sets'
     state files are untouched (boundary-write hygiene).

5. Update `fixtures.py` to support these scenarios:
   - `cancel_set(set_dir, reason="...")` and `restore_set(set_dir)`
     helpers.
   - `drive_close_session(..., force=True)` parameter.
   - Worktree-layout helper: `make_sibling_worktree(main_path, slug)`.

**Deliverables:**

- `ai_router/tests/e2e/test_cancel_restore_midset.py`
- `ai_router/tests/e2e/test_force_close_path.py`
- `ai_router/tests/e2e/test_worktree_discovery.py`
- `ai_router/tests/e2e/test_multiset_sequential.py`
- `ai_router/tests/e2e/fixtures.py` — extended with cancel/restore/force/worktree helpers

**Acceptance:**

- All five Python e2e test files pass under `pytest -m e2e`.
- Total harness runtime under 60s on a development laptop (each scenario
  is ~5-10s; 5 scenarios × 10s = 50s ceiling).
- Each test cleans up its tmpdir; no fixture leakage between tests.

---

### Session 3 of 4: `@vscode/test-electron` tree-provider harness

**Goal:** Add an extension-side test suite that drives the same scenarios
from Session 2 against a real VS Code instance running the
dabbler-ai-orchestration extension, and asserts on `SessionSetsProvider`'s
output. This catches regressions in the bucketing rules, the file watcher,
and the alias-map readers.

**Steps:**

1. Create `tools/dabbler-ai-orchestration/src/test/suite/e2e/`:
   - `e2eHarness.ts` — TypeScript port of the Python fixture generator's
     state-shape helpers (write state.json with given shape, write events,
     etc.). The CLI driving still happens via Python subprocess from
     inside the test; only the *assertion* side runs in TS.
   - `treeProvider-happy.test.ts` — equivalent of
     `test_happy_3session.py`, asserting on `getChildren()`.
   - `treeProvider-cancel.test.ts` — cancel/restore scenario.
   - `treeProvider-force.test.ts` — force-close scenario.
   - `treeProvider-multiset.test.ts` — three-set scenario.
   - `treeProvider-worktree.test.ts` — sibling-worktree scenario.

2. Each TS test:
   - Spawns a tmpdir workspace with the fixture set(s).
   - Activates the extension against that workspace.
   - Drives the Python CLI from `child_process.spawnSync` (the same
     CLI the orchestrator uses in production — no mocking).
   - After each boundary, calls
     `vscode.commands.executeCommand("dabbler.refreshSessionSets")`
     to force a synchronous refresh (the production debounce is
     500ms; tests bypass it for determinism).
   - Asserts on:
     - `provider.getChildren(undefined)` — top-level bucketing
       (Active / Done / Not Started / Cancelled).
     - `provider.getChildren(<bucket>)` — set-level children.
     - Each set node's `label`, `description`, `iconPath`, and
       `contextValue`.

3. Add the harness directory to `index.ts` discovery (Mocha runner
   already auto-discovers `**/*.test.ts`; just verify nothing
   excludes the new subfolder).

4. CI consideration: the existing CI pipeline already runs
   `@vscode/test-electron` via `npm test`. Verify the new e2e
   tests run in CI without operator action. If runtime budget is
   tight, gate behind a separate npm script
   (`npm run test:e2e`) and document in CLAUDE.md.

**Deliverables:**

- `tools/dabbler-ai-orchestration/src/test/suite/e2e/e2eHarness.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/e2e/treeProvider-happy.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/e2e/treeProvider-cancel.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/e2e/treeProvider-force.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/e2e/treeProvider-multiset.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/e2e/treeProvider-worktree.test.ts`
- `package.json` — optional `test:e2e` script if isolating from main test

**Acceptance:**

- `npm test` runs all five new e2e files and the existing 20+ unit tests
  cleanly.
- Each scenario asserts at minimum: bucket assignment, child-set count,
  set label text, set description text. The exhaustive shape-check
  belongs in Session 4 (rendering smoke).
- No new flakiness — three back-to-back runs all green.

---

### Session 4 of 4: Playwright Electron rendering smoke + close-out

**Goal:** Add a Playwright-Electron rendering smoke layer (4-5 critical
paths) that verifies what's *actually painted on screen*, and close out
the set. This is the only layer that catches CSS regressions, icon-class
typos, and text-template bugs that don't show up in the data layer.

**Steps:**

1. Add Playwright to dev deps in
   `tools/dabbler-ai-orchestration/package.json`:
   - `@playwright/test` (provides `_electron.launch`)
   - Initialize `playwright.config.ts` scoped to the
     `src/test/playwright/` directory.

2. Create `tools/dabbler-ai-orchestration/src/test/playwright/`:
   - `electronLaunch.ts` — helper that launches VS Code via
     `_electron.launch({ args: ["--extensionDevelopmentPath=...", "--user-data-dir=...", "<workspace>"] })`.
     Returns the Page handle for the workbench.
   - `treeView.spec.ts` — five test cases:
     1. **Fresh set** — three sets present, all not-started. Assert
        the Not Started section header is visible and lists three
        children with `0/N` text.
     2. **Mid-session** — drive a set to session 2 in flight. Assert
        the Active header is visible; the set's label reads
        `1/N · session 2 in flight`; the set has the "active" icon.
     3. **All done** — drive a set through close-out. Assert it moves
        to Done; label reads `N/N`; the set has the "complete" icon.
     4. **Cancelled** — cancel mid-set. Assert it moves to Cancelled;
        label includes the cancellation reason; the badge surfaces.
     5. **Force-closed** — apply `--force` close. Assert the
        `[FORCED]` badge is visible on the set's label.

3. Each test:
   - Uses the Python fixture generator from Session 1 (subprocess) to
     prepare state.
   - Launches VS Code Electron against the prepared workspace.
   - Triggers `dabbler.refreshSessionSets` via `page.evaluate` →
     `vscode.commands.executeCommand`.
   - Reads the rendered tree via Playwright selectors targeting the
     Session Set Explorer activity-bar view container
     (`.pane[aria-label*="Session Sets"]` or similar — confirm the
     actual ARIA label at implementation time).
   - Asserts on text content and screenshots a baseline image to
     `src/test/playwright/baseline/<test-name>.png`.

4. Decide on screenshot baseline strategy:
   - **Option A**: commit baselines; CI compares against committed PNGs.
     Pro: catches visual drift. Con: every legitimate UI tweak requires
     a baseline refresh PR.
   - **Option B**: text-only assertions; screenshots stored as CI
     artifacts but not compared. Pro: no maintenance churn. Con: misses
     pure visual regressions.
   - **Recommended:** Option B for this set. Layer 1 + 2 catch the data
     regressions; Layer 3's job is "the human sees the right *text*
     in the right *place*." Pure-visual regressions are rare and
     usually caught by manual operator review.

5. Update `CLAUDE.md` with the new test commands:
   - `pytest -m e2e` — Layer 1 (Python).
   - `npm test` — Layer 2 (`@vscode/test-electron`).
   - `npm run test:playwright` — Layer 3 (Playwright Electron).
   - Note runtimes: Layer 1 ~30s, Layer 2 ~90s, Layer 3 ~3min.

6. Update `CHANGELOG.md`:
   - `ai_router` v0.3.1 — adds e2e Python harness.
   - extension v0.13.16 — adds e2e TS tree-provider harness + Playwright
     rendering smoke.

7. Standard close-out:
   - Run cross-provider verification on the full set (1 slice expected;
     verification scope is the spec + the harness suite, not the entire
     repo).
   - Write `change-log.md` and `disposition.json`.
   - `python -m ai_router.close_session` for the final close.

**Deliverables:**

- `tools/dabbler-ai-orchestration/src/test/playwright/electronLaunch.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/treeView.spec.ts`
- `tools/dabbler-ai-orchestration/playwright.config.ts`
- `tools/dabbler-ai-orchestration/package.json` — `@playwright/test`
  dev dep + `test:playwright` script
- `CLAUDE.md` — new test commands documented
- `CHANGELOG.md` — v0.13.16 + v0.3.1 entries
- `pyproject.toml` — version bump to 0.3.1
- `tools/dabbler-ai-orchestration/package.json` — version bump to 0.13.16
- `change-log.md` for the set
- `disposition.json` for Session 4

**Acceptance:**

- `npm run test:playwright` passes all five test cases on a clean
  checkout, ≤3min total.
- All three layers' green-run output captured in the set's
  `change-log.md`.
- Versions bumped; release tags **not** pushed in this session
  (operator runs the release separately, per the standard tag-driven
  workflow established in Set 026).

---

## Cross-provider verification

Each session ends with cross-provider verification per the framework
standard. Verifier choice should be a provider different from the
session's orchestrator (per Set 005's invariant). Empirical scope
estimate based on Set 026:

| Session | Expected scope          | Estimated cost      |
|--------:|-------------------------|---------------------|
| 1       | ~600 LOC Python + spec  | $0.20-$0.40         |
| 2       | ~800 LOC Python         | $0.40-$0.80         |
| 3       | ~1000 LOC TypeScript    | $0.50-$1.00         |
| 4       | ~600 LOC TS + close-out | $0.30-$0.60         |

Set NTE: **$5.00** (well under the repo's $10.00 ceiling from
`budget.yaml`).

---

## Open questions for the implementer

These are deliberately left undecided so the implementing orchestrator
can choose at session-start rather than locking in a guess now:

1. **Layer 1 vs Layer 2 test duplication.** Sessions 2 and 3 both
   exercise the cancel/restore, force, multiset, and worktree paths.
   The Python layer asserts on file contents; the TS layer asserts on
   provider output. Both are valuable, but if Session 3's scope gets
   tight, the multiset and worktree scenarios there can be deferred
   to a follow-up set without loss of regression coverage (Layer 1
   covers the data; Layer 2 mostly catches *additional* bucketing
   regressions, which are caught equally well by Layer 3 in Session 4).
2. **Manual-verify CLI shape.** `close_session --manual-verify`
   currently requires `--interactive` or `--reason-file`. The harness
   will hit `--reason-file` exclusively; verify there are no hidden
   prompts that block headless subprocess invocation, and patch if so.
3. **CI integration.** Whether to gate PRs on Layer 3 (Playwright) or
   run it nightly. Recommend nightly initially (3min adds friction
   to PR review) and promote to PR-gating if it catches enough
   regressions to earn the budget.

---

## Acceptance criteria (set-level)

- [ ] Python e2e harness (`ai_router/tests/e2e/`) ships with five
      scenario files: happy, cancel/restore, force-close, worktree,
      multiset.
- [ ] `register_session_start` regression test pins the v0.1.1
      `completedSessions[]`-loss bug shut.
- [ ] `@vscode/test-electron` e2e suite ships with five scenarios
      asserting on `SessionSetsProvider.getChildren()`.
- [ ] Playwright Electron smoke ships with five rendering-layer
      scenarios.
- [ ] All three layers run green back-to-back; total CI time documented.
- [ ] `ai_router` v0.3.1 + extension v0.13.16 versions bumped (release
      tags pushed by operator post-merge).
- [ ] `CLAUDE.md` documents the three test commands and their
      runtimes.
