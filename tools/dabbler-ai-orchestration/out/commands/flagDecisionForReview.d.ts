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
export declare function registerFlagDecisionForReview(context: vscode.ExtensionContext): void;
