"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerFlagDecisionForReview = registerFlagDecisionForReview;
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
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fileSystem_1 = require("../utils/fileSystem");
const decisionReviewQueue_1 = require("./decisionReviewQueue");
function registerFlagDecisionForReview(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.flagDecisionForReview", async () => {
        const activeDir = (0, decisionReviewQueue_1.findActiveSessionSetDir)(fileSystem_1.readAllSessionSets);
        if (!activeDir) {
            vscode.window.showInformationMessage("No active session set to flag against. Start a session set first " +
                "(its state must be 'in-progress' for the flag to attach to it).");
            return;
        }
        const reason = await vscode.window.showInputBox({
            title: "Flag Decision for Cross-Provider Review",
            prompt: "One-line reason this decision should get a second-engine read at the next session start.",
            placeHolder: "e.g. budget-tier defaulting choice — confirm with Gemini before shipping",
            ignoreFocusOut: true,
        });
        if (reason === undefined)
            return;
        const trimmed = reason.trim();
        if (trimmed.length === 0)
            return;
        const entry = {
            ts: new Date().toISOString(),
            reason: trimmed,
            source: "command",
            file: null,
            line: null,
        };
        try {
            (0, decisionReviewQueue_1.appendQueueEntry)(activeDir, entry);
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(`Failed to append to decision-review queue: ${msg}`);
            return;
        }
        const slug = path.basename(activeDir);
        vscode.window.showInformationMessage(`Flagged for cross-provider review in ${slug}/${decisionReviewQueue_1.QUEUE_FILENAME}. ` +
            `Will surface in the next session's planning checklist.`);
    }));
}
//# sourceMappingURL=flagDecisionForReview.js.map