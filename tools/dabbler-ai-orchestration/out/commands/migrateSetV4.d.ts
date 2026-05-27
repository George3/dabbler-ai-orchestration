/**
 * In-extension lazy migrator for v3 → v4 session-state.json.
 *
 * Set 047 Session 3 deliverable per the audit-locked spec at
 * `docs/session-sets/047-state-file-schema-v4-audit/spec.md` (§3.4
 * migration sequencing; §3.8 formal rollback procedure).
 *
 * Single-set front door reached via the tree-view context menu on any
 * row flagged as needing a v3→v4 migration (i.e.,
 * `set.migrationTargetSchemaVersion === 4`). The migration runs
 * entirely in-process via `utils/migrateSessionStateV4.ts`'s
 * `migrateOneSetV4()` — no Python subprocess, no ai-router dependency.
 * Lightweight-tier consumer repos that never install ai-router can
 * migrate too.
 *
 * No strategy choice: v3 already carries session titles in
 * `sessions[]`, so the v2-era regex/generic decision does not apply.
 * The migrator strips the derived top-level fields (`currentSession`,
 * `totalSessions`, `completedSessions`, `orchestrator`, `startedAt`,
 * `completedAt`, `verificationVerdict`, `lifecycleState`) — the
 * normalize shim re-derives them at read time, so existing readers
 * continue to work.
 *
 * Safety: apply mode writes `session-state.v3.bak.json` alongside the
 * target BEFORE replacing the state file. If anything goes wrong, the
 * operator runs the rollback procedure at
 * `docs/v3-to-v4-rollback-procedure.md` — a one-step rename restores
 * the pre-migration state.
 */
import * as vscode from "vscode";
interface CommandDeps {
    refreshView: () => void;
}
export declare function registerMigrateSetV4Command(context: vscode.ExtensionContext, deps: CommandDeps): void;
export {};
