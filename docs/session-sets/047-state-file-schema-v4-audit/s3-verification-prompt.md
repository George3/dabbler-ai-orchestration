# Set 047 Session 3 — Cross-provider verification prompt

You are reviewing the **migrator phase** of the Set 047 v3 → v4 state-file
schema migration. The reader-first shim (`normalize_to_v4_shape` /
`normalizeToV4Shape`) shipped in Session 2 and is **not** the subject of
this review — Session 2's audit verdict is already in the close-out.

## Context

Set 047 ships a v4 evolution of `docs/session-sets/<slug>/session-state.json`
that derives top-level state (`currentSession`, `totalSessions`,
`completedSessions`, `orchestrator`, `startedAt`, `completedAt`,
`verificationVerdict`, `lifecycleState`) from a per-session `sessions[]`
ledger where each entry carries its own `startedAt` / `completedAt` /
`orchestrator` / `verificationVerdict`. The migration is phased per
spec §3.4:

- **Phase 1 (Session 2, CLOSED):** reader-first shim that accepts
  v1/v2/v3/v4 input and returns a normalized v4 read-view.
- **Phase 2 (this session, Session 3):** v3 → v4 migrator in Python +
  TypeScript with explicit `session-state.v3.bak.json` rollback file,
  formal rollback procedure doc, and the `needsMigration` detector
  expansion + ActionRegistry split.
- **Phase 3 (Sessions 4-5):** writers emit v4 directly.

This review focuses on **the migrator surface and the detector
expansion** — not the future writer flip.

## What's bundled

The files attached after this prompt:

- `ai_router/migrate_v3_to_v4.py` — Python CLI (`python -m
  ai_router.migrate_v3_to_v4`); `migrate_one_set` /
  `migrate_all` / `discover_session_sets` helpers;
  `build_v4_on_disk_shape` pure function.
- `tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts`
  — TypeScript mirror invoked in-process by the right-click command
  (no Python subprocess; Lightweight-tier consumers without
  `dabbler-ai-router` installed still work).
- `tools/dabbler-ai-orchestration/src/commands/migrateSetV4.ts` —
  registers `dabblerSessionSets.migrateToV4`, the right-click action.
- `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts` (the
  `needsMigration` detector block + the new
  `migrationTargetSchemaVersion` propagation).
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`
  — predicate split (`needsMigrationToV3` / `needsMigrationToV4`) +
  new menu entry at group 802.
- `tools/dabbler-ai-orchestration/src/types.ts` — `SessionSet` shape
  delta (new `migrationTargetSchemaVersion: 3 | 4 | null` field).
- `docs/v3-to-v4-rollback-procedure.md` — formal rollback procedure.
- `ai_router/tests/test_migrate_v3_to_v4.py` — 29 Python tests.
- `tools/dabbler-ai-orchestration/src/test/suite/migrateSessionStateV4.test.ts`
  — 20 TypeScript tests for the migrator.
- `tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts`
  (the new `needsMigration` + `migrationTargetSchemaVersion` suite
  near the bottom).
- `tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts`
  (the new v3/v4 mutex tests).
- `tools/dabbler-ai-orchestration/src/test/playwright/migration-cta-v4.spec.ts`
  — Layer-3 smoke that a canonical v3 set surfaces the badge.

## What I'm asking you to verify

### Critical (must-fix if violated)

1. **On-disk v4 shape contract.** Per spec §3.1, the v4 file
   preserves `schemaVersion: 4`, `sessionSetName`, `sessions[]`, and
   `status` at top level; passthrough `preCancelStatus` and
   `forceClosed` ride along when present; **everything else is
   dropped** (`lifecycleState`, `currentSession`, `totalSessions`,
   `completedSessions`, `startedAt`, `completedAt`, `orchestrator`,
   `verificationVerdict`). Does `build_v4_on_disk_shape` honor this
   in BOTH Python and TypeScript? Does it canonicalize `status`
   aliases (`"completed"` / `"done"`) on the way out?

2. **Round-trip read equivalence.** A canonical v3 file run through
   the migrator must produce a v4 file that the reader-first shim
   reads identically to the original — i.e.,
   `normalize_to_v4_shape(v3_state)` and
   `normalize_to_v4_shape(v4_output)` produce the same `sessions[]`,
   derived top-level fields, etc. The `test_round_trip_through_shim_equivalent`
   tests assert this; is the assertion strong enough, or could a
   real-world v3 file slip through that produces a v4 file whose
   re-read differs from the v3 read? In particular, are there v3
   shapes where the shim promotes orchestrator/startedAt to a
   different per-session entry than the migrator's strip step
   subsequently exposes?

3. **Idempotence.** A v4 file (`schemaVersion >= 4`) returns
   `skipped-v4` without touching disk. A second apply-mode run after
   a successful migration is a no-op (the .bak from run 1 is
   untouched). Confirm both directions.

4. **Backup semantics.** Apply mode writes `session-state.v3.bak.json`
   BEFORE replacing `session-state.json`. The .bak is byte-equivalent
   in content (re-emitted with `indent=2`) to the original v3 file.
   If the .bak write fails, the state file is not touched. If the
   state-file write fails after the .bak is written, the result
   reports `failed-backup` AND the operator can recover via the
   rollback procedure. Are these guarantees actually upheld by the
   code? In particular: is there any window where a partial write
   could leave both files in a half-broken state?

5. **Refusal cases.** v1/v2 files return `skipped-not-v3` with a
   pointer to the v2→v3 migrator. Broken v3 (schemaVersion=3 but no
   `sessions[]`) returns `skipped-malformed`. Future schema returns
   `skipped-future-schema`. Invariant violations (status=complete
   with a not-started session) return `would-violate` and DO NOT
   write to disk. Confirm — and flag any case that could silently
   migrate a file that should be refused.

6. **needsMigration detector.** With Session 3's expansion, the
   Explorer flags a "(needs migration)" badge on canonical v3 files
   (target=4) AND v1/v2/broken-v3 files (target=3). The ActionRegistry
   menu shows "Migrate to v4 schema" XOR "Migrate to v3 schema"
   based on the target — never both. v4 files don't flag. Future
   schema (> 4) doesn't flag (no downgrade). Confirm the
   mutual-exclusion invariant: there is no input shape where both
   menu entries would appear.

### Important (would benefit from being addressed)

7. **Python / TypeScript parity.** The two migrators must produce
   the same on-disk shape for the same input — Lightweight-tier
   consumer repos run only the TS path; Full-tier runs the Python
   CLI for bulk migrations. Any divergence (different key order
   doesn't matter — different keys does) is a bug. Same for action
   enum names and result-shape fields.

8. **Rollback procedure correctness.** Read
   `docs/v3-to-v4-rollback-procedure.md`. Does the procedure
   actually work for the failure modes the migrator surfaces? Are
   the trigger conditions complete? Are the validation steps
   sufficient to verify a successful rollback?

9. **Test coverage of the new code.** 29 Python + ~20 TS tests +
   6 `needsMigration` tests + 3 ActionRegistry mutex tests. Is the
   coverage *sufficient* — or do you see a critical path that's
   not exercised? Specifically: is there a v3 shape variant that
   the migrator handles correctly but no test asserts?

### Nice-to-have

10. **Error messages.** Read the operator-facing strings in
    `migrateSetV4.ts` and the CLI's `_print_result_line`. Are they
    actionable? Would an operator know what to do next after each
    refusal kind?

11. **Maintenance pitfalls.** Anything in the code that's likely to
    rot or become subtly wrong as Sessions 4-5 ship the writer flip?

## Output format

Please return your verdict and findings in this shape:

```
VERDICT: VERIFIED | ISSUES_FOUND

CRITICAL (must-fix):
- (issue 1 ...)
- (issue 2 ...)

IMPORTANT:
- (issue 1 ...)

NICE-TO-HAVE:
- (issue 1 ...)

ATTESTATION:
(one paragraph: which contracts you actually checked vs took on faith,
where you spent the most attention, any limit-of-review caveats)
```

If you find no must-fix critical issues, the verdict is **VERIFIED**
even if you list IMPORTANT or NICE-TO-HAVE follow-ups.
