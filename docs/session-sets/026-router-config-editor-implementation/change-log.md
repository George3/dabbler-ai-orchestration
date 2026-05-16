# Change Log — 026-router-config-editor-implementation

## Summary

Set 026 delivers the **Dabbler Config Editor** as a first-class VS Code panel
and ships `ai_router` 0.3.0 with a clean public surface. The set does two
things: removes the `outsourceMode` / verifier-daemon / queue infrastructure
that accumulated in Sets 001–024, and builds the new config editor that
replaces the pattern of hand-editing YAML files.

After this set:

- `Dabbler: Open Dabbler Config Editor` opens a six-section panel that reads
  and writes `router-config.yaml`, `budget.yaml`, and `local-overrides.yaml`
  with comment preservation and per-save schema validation.
- `dabbler.flagDecisionForReview` and `dabbler.scanAnnotationsForActiveSet`
  allow operators to flag decisions and scan workspace annotations for
  cross-provider review without touching the session-verification flow.
- The `Dabbler: Get Started` wizard now includes a "Configure AI Router"
  button that opens the config editor directly.
- All queue-mediated daemon infrastructure is gone from both the Python
  package and the VS Code extension.

## Sessions

### Session 1 — `outsourceMode` clean-sweep

- Deleted 10 Python modules: `queue_status`, `heartbeat_status`, `queue_db`,
  `queue_verification`, `daemon_pid`, `orchestrator_role`, `restart_role`,
  `role_status`, `capacity`, `verifier_role`
- Deleted `ai_router/docs/two-cli-workflow.md`
- Deleted 19 Python test files + 1 extension test file (`modeBadge.test.ts`)
- Stripped mode-aware branches from `close_session.py`, `start_session.py`,
  `gate_checks.py`, `disposition.py`, `cost_report.py`, `reconciler.py`
- Stripped `outsourceMode:` from `router-config.yaml`, `schemas/disposition.schema.json`,
  and all 26 historical `spec.md` files
- Bumped versions: ai_router 0.3.0; extension 0.13.15
- 385 tests passed

### Session 2 — Budget-dialog simplification (NTE framing)

- Replaced four-tier budget-mapping dialog with single NTE question in
  `docs/adoption-bootstrap.md`
- Collapsed "Cost-budgeted verification modes" to a two-row table in
  `docs/ai-led-session-workflow.md`
- Created `ai_router/budget.yaml` for this repo (threshold_usd: 10,
  verification_nte_usd: 10)
- Added `local-overrides.yaml` to `.gitignore`

### Session 3 — YAML schema + Python reader + resolver abstraction

- Added `display_label`, `enabled`, `routing.outsourcing_mode` fields to
  `router-config.yaml` schema
- Created `ai_router/secret_resolver.py` (env backend, resolve_secret() entry point)
- Created `ai_router/migrate_router_config.py` (idempotent, comment-preserving
  migration; runs on this repo's own config)
- Refactored all env-var lookups through `resolve_secret`
- 7 new test files; 414 tests passed

### Session 4 — Webview foundation

- Added `yaml` (comment-preserving) and `ajv` (schema validation) to extension
  package.json
- Created `src/configEditor/ConfigEditorPanel.ts` (panel singleton, load/save/
  drift-detect, half-batch recovery)
- Created `src/configEditor/yamlReadWrite.ts` (round-trip YAML)
- Created `src/configEditor/schemaValidator.ts` (batch validation for all three files)
- Registered `dabbler.openConfigEditor` command
- Three new test files; tsc clean

### Session 5 — Webview sections

- Created six section files (`routingAndVerificationSection`, `budgetSection`,
  `providersTableSection`, `significanceFlaggingSection`, `notificationsSection`,
  `localOverridesSummarySection`)
- Created `SectionState` interface, `applyPatch` utility, `SectionRenderResult`
- Implemented `(shared)/(local override)` indicator toggle and provider popover
- Implemented half-batch recovery dialog
- 3 e2e tests; 120 pure-unit TS tests; 427 Python tests; tsc clean
- Cross-provider verification: $1.218 (4 tranches, gpt-5-4)

### Session 6 — Significance flagging

- Created `ai_router/decision_review_queue.py` (read_queue, clear_queue, queue_path)
- Created `src/configEditor/annotationParser.ts` (regex parser + deduplication)
- Created `src/commands/decisionReviewQueue.ts` + `annotationScanner.ts` (pure helpers)
- Created `src/commands/flagDecisionForReview.ts` + `scanAnnotationsForActiveSet.ts`
- Wired both commands in `package.json` + `extension.ts`
- Documented significance flagging in `docs/ai-led-session-workflow.md`
- 55 new tests; 427 Python tests; 120 pure-unit TS tests; tsc clean
- Cross-provider verification: $0.426 (2 slices, gpt-5-4)

### Session 7 — Wizard integration + test notification + release prep

- Wizard HTML: inline `onclick` attributes converted to `data-command` +
  `addEventListener` (CSP fix); new "Configure AI Router" button
- WizardPanel.ts: `openConfigEditor` + `openExternal` cases added
- notificationsSection.ts: "Send a test notification now" button enabled
- ConfigEditorPanel.ts: `_handleTestNotification()` implementation (spawns
  Python subprocess calling `ai_router.notifications.send_pushover_notification();
  `spawnErrored` flag prevents duplicate error toasts)
- Docs: `docs/quick-start.md` "Configuring your project" section;
  `docs/adoption-bootstrap.md` "Configuring the AI router visually" closing pointer;
  `CLAUDE.md` version bump + Router-config editor subsection
- CHANGELOG.md [0.13.15] block expanded with Session 7 entries
- Cross-provider verification: $0.358 (1 slice, gpt-5-4)

## Test counts

| Session | Python tests | TS unit tests | Notes |
|--------:|-------------:|---------------:|-------|
| 1       | 385          | —              | Post-deletion baseline |
| 2       | 395          | —              | Budget + NTE tests |
| 3       | 414          | —              | Resolver + migration tests |
| 4       | 414          | ~100           | Foundation tests |
| 5       | 427          | 120            | Section + e2e tests |
| 6       | 427          | 120            | Queue + annotation + command tests |
| 7       | 427          | 120            | tsc clean; no new tests needed |

## Acceptance criteria

- [x] Extension v0.13.15 ships with working `Dabbler: Open Dabbler Config Editor`
  rendering all 6 wireframed sections
- [x] `ai_router` ships v0.3.0 with new schema + resolver abstraction + migration script
- [x] `outsourceMode` and related infrastructure completely removed
- [x] `router-config.yaml` + `budget.yaml` carry new schema; `local-overrides.yaml`
  is gitignored and reading works end-to-end
- [x] Significance flagging works via both command and annotation syntax
- [x] Routing dropdown writes to `routing.outsourcing_mode`; verification dropdown
  writes to `verification_method`
- [x] Wizard includes "Configure AI Router" button wired to the config editor

## Verification spend (Set 026)

| Session | Slices | Cost      | Model    |
|--------:|-------:|----------:|----------|
| 5       | 4      | $1.218    | gpt-5-4  |
| 6       | 2      | $0.426    | gpt-5-4  |
| 7       | 1      | $0.358    | gpt-5-4  |
| **Total** | **7** | **$2.002** |         |

Cumulative NTE: $2.00 of $10.00 used (verification only; Sessions 1–4
used manual verification per the bootstrap plan).

## Pending release steps

1. `git push origin master`
2. Tag `vsix-v0.13.15`: `git tag vsix-v0.13.15 && git push origin vsix-v0.13.15`
   → triggers tag-driven Marketplace deployment; operator approves in GitHub Actions
3. Tag `pypi-v0.3.0`: `git tag pypi-v0.3.0 && git push origin pypi-v0.3.0`
   → triggers tag-driven PyPI release
