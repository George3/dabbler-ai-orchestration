export declare const SESSION_STATE_FILENAME = "session-state.json";
export declare const BACKUP_FILENAME = "session-state.v3.bak.json";
export declare const SWEEP_BACKUP_FILENAME = "session-state.pre-049-sweep.bak.json";
export type MigrationActionV4 = "migrated" | "swept-orchestrator" | "skipped-v4" | "skipped-not-v3" | "skipped-no-state" | "skipped-malformed" | "skipped-future-schema" | "would-violate" | "failed-backup";
export interface MigrationResultV4 {
    setDir: string;
    action: MigrationActionV4;
    reason: string;
    error?: string;
    backupPath?: string;
    before?: unknown;
    after?: unknown;
}
export interface MigrateOneSetV4Options {
    /** When true, validate + report without writing to disk. */
    dryRun?: boolean;
}
/**
 * Strip Set-049-retired keys from a single orchestrator block.
 * Mirrors `_strip_retired_orchestrator_keys` in the Python migrator.
 *
 * Returns `[newBlock, changed]`. Non-object input round-trips unchanged
 * with `changed=false`. A retired key is "present" if it appears in
 * the object regardless of value (including `null`) because the
 * on-disk shape must omit these keys entirely under the omit-null
 * contract.
 */
export declare function stripRetiredOrchestratorKeys(block: unknown): [unknown, boolean];
/**
 * Sweep retired orchestrator-block keys throughout a state file.
 * Mirrors `_sweep_orchestrator_blocks` in the Python migrator.
 *
 * Sweeps both the top-level legacy `orchestrator` field (pre-v4
 * files) AND every per-session ledger entry's `orchestrator` block
 * (v4 shape). Returns `[newState, changed]`. Idempotent: re-running
 * on already-clean state returns the input reference unchanged.
 */
export declare function sweepOrchestratorBlocks(state: Record<string, unknown>): [Record<string, unknown>, boolean];
/**
 * Build the on-disk v4 dict given a normalized read-view + the
 * original v3 state. Mirrors `build_v4_on_disk_shape` in Python.
 *
 * The shim has already promoted v3 top-level metadata onto the
 * per-session `sessions[]` entries and derived the top-level fields
 * for backwards-compatible reading; our job is to strip the
 * derived-redundant fields so the on-disk file is the canonical v4
 * shape.
 */
export declare function buildV4OnDiskShape(normalized: Record<string, unknown>, original: Record<string, unknown>): Record<string, unknown>;
/**
 * Migrate one session-set directory's `session-state.json` from v3 to v4.
 *
 * Idempotent: a v4 file is returned as `skipped-v4` without touching
 * disk. v1/v2 files return `skipped-not-v3` with instructions to run
 * the v2→v3 migrator first. A broken v3 file (schemaVersion=3 but
 * `sessions[]` missing/non-list) returns `skipped-malformed`.
 *
 * Apply mode writes `session-state.v3.bak.json` BEFORE replacing the
 * state file so the rollback procedure has a known-good copy if any
 * subsequent step fails. The migrator NEVER throws for "file isn't
 * there / file is broken" cases — those become structured results so
 * the UI can render kind-specific messages.
 */
export declare function migrateOneSetV4(setDir: string, options?: MigrateOneSetV4Options): MigrationResultV4;
