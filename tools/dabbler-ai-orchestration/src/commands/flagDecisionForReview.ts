/**
 * `dabbler.flagDecisionForReview` — operator-invoked flag for the active
 * session set's decision-review queue.
 *
 * The pure helpers live in `./decisionReviewQueue` so they can be
 * unit-tested without the @vscode/test-electron harness. This file is
 * the vscode-surface wiring only.
 *
 * Flow:
 *  1. Find the active session set. None → info notification, exit.
 *  2. Prompt the operator for a one-line reason.
 *     - Cancelled / empty → silent no-op (mirrors VS Code's
 *       cancel-as-non-event convention).
 *  3. Append a queue entry with `source: "command"`, `file/line: null`.
 *  4. Surface a success notification naming the queue file path.
 */
import * as vscode from "vscode";
import * as path from "path";
import { readAllSessionSets } from "../utils/fileSystem";
import {
  QueueEntry,
  QUEUE_FILENAME,
  appendQueueEntry,
  findActiveSessionSetDir,
} from "./decisionReviewQueue";

export function registerFlagDecisionForReview(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.flagDecisionForReview",
      async () => {
        const activeDir = findActiveSessionSetDir(readAllSessionSets);
        if (!activeDir) {
          vscode.window.showInformationMessage(
            "No active session set to flag against. Start a session set first " +
              "(its state must be 'in-progress' for the flag to attach to it).",
          );
          return;
        }

        const reason = await vscode.window.showInputBox({
          title: "Flag Decision for Cross-Provider Review",
          prompt:
            "One-line reason this decision should get a second-engine read at the next session start.",
          placeHolder: "e.g. budget-tier defaulting choice — confirm with Gemini before shipping",
          ignoreFocusOut: true,
        });
        if (reason === undefined) return;
        const trimmed = reason.trim();
        if (trimmed.length === 0) return;

        const entry: QueueEntry = {
          ts: new Date().toISOString(),
          reason: trimmed,
          source: "command",
          file: null,
          line: null,
        };

        try {
          appendQueueEntry(activeDir, entry);
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          vscode.window.showErrorMessage(
            `Failed to append to decision-review queue: ${msg}`,
          );
          return;
        }

        const slug = path.basename(activeDir);
        vscode.window.showInformationMessage(
          `Flagged for cross-provider review in ${slug}/${QUEUE_FILENAME}. ` +
            `Will surface in the next session's planning checklist.`,
        );
      },
    ),
  );
}
