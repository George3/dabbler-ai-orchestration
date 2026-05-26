# Set 047 Session 3 — Close-out reason and manual-verify attestation

## Close-out reason

Session 3 is the **migrator phase** of the v4 schema migration per
spec §3.4 (migration sequencing) and §3.8 (formal rollback procedure).
It ships:

- **`python -m ai_router.migrate_v3_to_v4`** — Python CLI subcommand
  in `ai_router/migrate_v3_to_v4.py`. Bulk-walks
  `docs/session-sets/*/session-state.json`; idempotent re-runs (v4
  files return `skipped-v4`); dry-run + apply modes; writes
  `session-state.v3.bak.json` alongside on apply; refuses v1/v2
  files with `skipped-not-v3` (operator runs the v2→v3 migrator
  first); refuses broken-v3 (sessions[] missing) with
  `skipped-malformed`; refuses future-schema (> 4) with
  `skipped-future-schema`; surfaces invariant violations via
  `would-violate`; reports two `failed-backup` subtypes
  distinguishable by whether `backup_path` is set (rollback-needed
  vs. fix-and-retry).
- **`migrateOneSetV4` + `dabblerSessionSets.migrateToV4`** —
  TypeScript mirror at
  `tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts`
  with a new right-click command at
  `tools/dabbler-ai-orchestration/src/commands/migrateSetV4.ts`.
  Same on-disk shape + same backup file as the Python CLI per the
  documented parity contract. Lightweight-tier consumer repos that
  never install `dabbler-ai-router` get the migration via the
  in-process TS path.
- **`docs/v3-to-v4-rollback-procedure.md`** — formal rollback procedure
  (trigger conditions, restore-from-`.bak` steps, validation). The doc
  was tightened post-verifier-Round-A so the trigger conditions
  correctly exclude `would-violate` (no write happened) and the
  no-bak `failed-backup` subcase (state file untouched).
- **`needsMigration` detector expansion** — `fileSystem.ts` now flags
  canonical v3 files (target=4) AND v1/v2/broken-v3 files (target=3)
  via a new `migrationTargetSchemaVersion: 3 | 4 | null` field on
  the `SessionSet` record. The detector block was moved BEFORE the
  `normalizeToV4Shape` call so a normalize failure doesn't lose the
  badge (verifier-Round-A fix). The Set 047 Session 2 deferral
  rationale is now fully unwound.
- **`ActionRegistry` predicate split** — `needsMigrationToV3` (group
  801) and `needsMigrationToV4` (group 802) are mutually exclusive
  by construction (one per row). The "Migrate to v4 schema"
  Command-Palette entry and the right-click menu entry both ship.
- **Unit tests:** 31 Python tests (`test_migrate_v3_to_v4.py`,
  including 2 post-verifier-Round-A additions for the state-write
  failure subcase + the `"done"` alias) + 22 TS tests
  (`migrateSessionStateV4.test.ts`, including the matching backup-fail
  + `"done"` alias coverage) + 6 `needsMigration`/`migrationTarget`
  tests in `fileSystem.test.ts` + 3 ActionRegistry mutex tests in
  `actionRegistry.test.ts`.
- **Layer-3 Playwright smoke** — `migration-cta-v4.spec.ts` asserts
  a canonical v3 set surfaces the `(needs migration)` badge under
  the new detector behavior.

## Cross-provider verification

Routed verification via
`python docs/session-sets/047-state-file-schema-v4-audit/run_s3_verification.py`
against `task_type='session-verification'` (gpt-5-4, tier 3). One
round was sufficient:

- **Round A** — gpt-5-4 (tier 3), 209.1s, $0.2882. Verdict:
  **VERIFIED**. No must-fix critical items. Four IMPORTANT items
  and two NICE-TO-HAVE items, summarized + dispositioned below.

**Total S3 routed cost: $0.2882** ($0.88022 cumulative
S1+S2+S3 of $10 NTE; 8.8%).

### Disposition of verifier IMPORTANT items

All four addressed in-flight per memory
`feedback_dont_hide_behind_out_of_scope`. The verifier's verdict
was already VERIFIED; these are improvements above the bar.

1. **Rollback-procedure scope overstated** — FIXED in
   `docs/v3-to-v4-rollback-procedure.md` (the "When to use" section
   now explicitly excludes `would-violate` and no-bak `failed-backup`)
   AND in
   `tools/dabbler-ai-orchestration/src/commands/migrateSetV4.ts`
   (the `failed-backup` notification now branches on whether
   `result.backupPath` is set, surfacing the rollback procedure only
   when the .bak actually exists).
2. **Detector coupled to normalize success** — FIXED. Moved the
   `needsMigration` + `migrationTargetSchemaVersion` block to run
   IMMEDIATELY after `JSON.parse(rawSd)`, before the
   `normalizeToV4Shape` call. A normalize failure can no longer eat
   the badge.
3. **Python/TS parity contract over-stated for internal field
   names** — DOCS FIX. The TS module's docstring now explicitly
   narrows the parity contract to: (a) on-disk v4 shape, (b) backup
   filename + write order, (c) action enum string values. Internal
   API field names (`set_dir` vs `setDir`, `backup_path` vs
   `backupPath`) follow per-language convention and are explicitly
   out of scope.
4. **Test coverage gaps for state-write failure + `"done"` alias**
   — FIXED. Added
   `TestBackupAndApply::test_state_write_failure_after_backup_signals_rollback_subcase`
   and `TestBackupAndApply::test_done_alias_canonicalized` to the
   Python suite, plus matching TS tests `backup write failure
   aborts` (using a directory at the .bak path to force a real
   `renameSync` failure on both platforms) and `done alias
   canonicalizes to complete on the way out`. The fifth gap
   (cross-language golden parity fixture) is DEFERRED — it would
   need its own test infrastructure addition (shared fixture
   harvester + asserts in both Python and TS suites) and is better
   designed in Sessions 4-5 when the writer flip lands and the
   parity surface is fully exercised by writes too.

### Disposition of verifier NICE-TO-HAVE items

1. **Operator messaging split for the two `failed-backup` subtypes**
   — FIXED via the same edits as Important #1 (extension
   notification + CLI `_print_result_line` both now distinguish the
   two subtypes with separate labels).
2. **Cross-language golden parity test in CI** — DEFERRED (same
   rationale as Important #4 part B).

## Real-world dry-run check

Ran `python -m ai_router.migrate_v3_to_v4 --scan docs/session-sets --json`
against this repo's 48 historical session-set directories:

- 47 sets would migrate cleanly.
- 1 set (`048-lightweight-tier-parity`) returned `would-violate`
  with `[v3 invariant rule 1] sessions[] must be non-empty`. This
  is the audit-stub set whose state file currently carries an empty
  `sessions[]` array (consistent with memory
  `project_set_047_s1_audit_locked`, which records the recurring
  v3-bug tax around empty `sessions[]` from `start_session` on
  freshly-stubbed sets). The migrator's `getProgress`-validation
  step correctly refused — this is the validation working as
  designed, not a regression.

No `--in-place` apply has been performed; the migrator's surface is
ready for Sessions 4-5 to use when the writer flip lands.

## Test posture

- **Python**: 881 passed (850 prior baseline + 31 new
  `test_migrate_v3_to_v4` tests) + 1 skipped (pre-existing). Zero
  regressions across pytest + 11 e2e + 8 e2e-marker.
- **TypeScript**: 593 passed (563 prior baseline + 22 new
  `migrateSessionStateV4` tests + 6 new `fileSystem`
  needsMigration/target tests + 2 new
  `actionRegistry` mutex + count-bump tests). 2 failures
  unchanged from the pre-S3 baseline
  (`configEditor-foundation` ViewColumn stub issue;
  `notificationsSection` disabled-button assertion). Both last-touched
  in Set 026 (2 weeks ago); unrelated to this session's changes.

## What ships in this commit

- `ai_router/migrate_v3_to_v4.py` — Python CLI + `migrate_one_set`
  + `build_v4_on_disk_shape` + `migrate_all` + `discover_session_sets`
  + `main` entry point.
- `tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts`
  — TypeScript mirror with the parity-contract docstring.
- `tools/dabbler-ai-orchestration/src/commands/migrateSetV4.ts` —
  `dabblerSessionSets.migrateToV4` right-click command with branched
  `failed-backup` messaging.
- `tools/dabbler-ai-orchestration/src/extension.ts` — registers
  the new command via `safeRegister`.
- `tools/dabbler-ai-orchestration/package.json` — declares the new
  command in `contributes.commands`.
- `tools/dabbler-ai-orchestration/src/types.ts` — `SessionSet`
  gains `migrationTargetSchemaVersion: 3 | 4 | null`.
- `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts` —
  detector hoisted above `normalizeToV4Shape`; expanded to flag
  canonical v3 with target=4.
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`
  — `needsMigrationToV3` / `needsMigrationToV4` predicate split;
  new group-802 menu entry for the v4 migrator.
- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
  — `COMMAND_ALLOWLIST` extended with `dabblerSessionSets.migrateToV4`.
- `docs/v3-to-v4-rollback-procedure.md` — new formal rollback
  procedure with tightened trigger conditions.
- `ai_router/tests/test_migrate_v3_to_v4.py` — 31 unit tests.
- `tools/dabbler-ai-orchestration/src/test/suite/migrateSessionStateV4.test.ts`
  — 22 TS unit tests.
- `tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts`
  — 6 new `needsMigration` + `migrationTargetSchemaVersion` tests.
- `tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts`
  — 3 new mutex/coverage tests + the 14→15 count bump.
- `tools/dabbler-ai-orchestration/src/test/suite/{flagDecisionForReview,forceClosedBadge,inProgressSetsService,sessionSetsProvider}.test.ts`
  — fixture defaults updated to include `migrationTargetSchemaVersion: null`.
- `tools/dabbler-ai-orchestration/src/test/suite/watcherInventory.test.ts`
  — allowlist line number updated from 147 → 148 (new safeRegister
  block shifted the watcher).
- `tools/dabbler-ai-orchestration/src/test/playwright/migration-cta-v4.spec.ts`
  — Layer-3 smoke for the v3 → v4 badge.
- `docs/session-sets/047-state-file-schema-v4-audit/s3-verification-prompt.md`
  — verification prompt.
- `docs/session-sets/047-state-file-schema-v4-audit/run_s3_verification.py`
  — verification driver.
- `docs/session-sets/047-state-file-schema-v4-audit/s3-verification-result.json`
  — cost / timing meta.
- `docs/session-sets/047-state-file-schema-v4-audit/s3-verification-transcript.md`
  — Round-A transcript (VERIFIED verdict, 4 IMPORTANT, 2 NICE-TO-HAVE).
- `docs/session-sets/047-state-file-schema-v4-audit/activity-log.json`
  with Session 3 steps.
- `docs/session-sets/047-state-file-schema-v4-audit/session-state.json`
  flipped to closed-for-S3.
- `docs/session-sets/047-state-file-schema-v4-audit/session-events.jsonl`
  with the `closeout_succeeded` event.
- `docs/session-sets/047-state-file-schema-v4-audit/disposition.json`
  pointing at Session 4 with the next-orchestrator block.
