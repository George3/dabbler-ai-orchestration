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
import { SessionSet } from "../types";
import {
  MigrationResultV4,
  migrateOneSetV4,
} from "../utils/migrateSessionStateV4";

interface CommandDeps {
  refreshView: () => void;
}

export function registerMigrateSetV4Command(
  context: vscode.ExtensionContext,
  deps: CommandDeps,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabblerSessionSets.migrateToV4",
      async (treeItem?: { set?: SessionSet }) => {
        const set = treeItem?.set;
        if (!set) {
          vscode.window.showErrorMessage(
            "Migrate to v4 schema must be invoked from a session-set row " +
              "in the Session Sets view. Right-click a row marked " +
              "'(needs migration)' to use this command.",
          );
          return;
        }
        if (set.migrationTargetSchemaVersion !== 4) {
          if (set.migrationTargetSchemaVersion === 3) {
            vscode.window.showInformationMessage(
              `${set.name} is at v1/v2 (or broken v3) — run "Migrate to v3 ` +
                `schema" first, then re-run this command.`,
            );
          } else {
            vscode.window.showInformationMessage(
              `${set.name} is already on schema v4 — nothing to migrate.`,
            );
          }
          return;
        }

        const confirm = await vscode.window.showInformationMessage(
          `Migrate ${set.name} to v4 schema? This will rewrite ` +
            `session-state.json in v4 shape and write a backup at ` +
            `session-state.v3.bak.json alongside it for rollback.`,
          { modal: true },
          "Migrate",
        );
        if (confirm !== "Migrate") return;

        await runMigratorV4(set, deps);
      },
    ),
  );
}

async function runMigratorV4(
  set: SessionSet,
  deps: CommandDeps,
): Promise<void> {
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `Migrating ${set.name} to v4 schema…`,
      cancellable: false,
    },
    async () => {
      let result: MigrationResultV4;
      try {
        result = migrateOneSetV4(set.dir, { dryRun: false });
      } catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        vscode.window.showErrorMessage(
          `Migration of ${set.name} to v4 failed with an unexpected error: ${msg}`,
        );
        return;
      }
      handleMigrationResultV4(set, result, deps);
    },
  );
}

function handleMigrationResultV4(
  set: SessionSet,
  result: MigrationResultV4,
  deps: CommandDeps,
): void {
  if (result.action === "migrated") {
    vscode.window.showInformationMessage(
      `${set.name} migrated to v4 schema. Backup at ` +
        `session-state.v3.bak.json. The tree will refresh shortly; ` +
        `the (needs migration) badge clears on the next read.`,
    );
    deps.refreshView();
    return;
  }
  if (result.action === "skipped-v4") {
    vscode.window.showInformationMessage(
      `${set.name} is already v4 — no changes written.`,
    );
    deps.refreshView();
    return;
  }
  if (result.action === "skipped-not-v3") {
    vscode.window.showWarningMessage(
      `Migration of ${set.name} to v4 was skipped: ${result.reason}`,
    );
    return;
  }
  if (result.action === "would-violate") {
    vscode.window.showWarningMessage(
      `Migration of ${set.name} stopped: the resulting v4 file would ` +
        `violate schema invariants. Reason: ${result.reason}. Hand-repair ` +
        `the state file before retrying.`,
    );
    return;
  }
  if (result.action === "failed-backup") {
    // Two sub-cases:
    //   * `result.backupPath` is set: the backup WAS written, then
    //     the state-file write failed. The state file may be in a
    //     partially-replaced state; point the operator at the
    //     rollback procedure.
    //   * `result.backupPath` is undefined: the backup write itself
    //     failed; the state file is untouched. The operator should
    //     fix the filesystem condition (permissions, disk space)
    //     and re-run — no rollback needed.
    if (result.backupPath) {
      vscode.window.showErrorMessage(
        `Migration of ${set.name} failed AFTER backup was written ` +
          `at ${result.backupPath}. ${result.reason} See ` +
          `docs/v3-to-v4-rollback-procedure.md to restore.`,
      );
    } else {
      vscode.window.showErrorMessage(
        `Migration of ${set.name} could not write its backup: ${result.reason}. ` +
          `The state file was not modified — fix the filesystem issue ` +
          `(permissions / disk space) and re-run. No rollback needed.`,
      );
    }
    return;
  }
  // skipped-malformed / skipped-no-state / skipped-future-schema
  vscode.window.showWarningMessage(
    `Migration of ${set.name} skipped (${result.action}): ${result.reason}.`,
  );
}
