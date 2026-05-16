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
exports.QUEUE_FILENAME = void 0;
exports.appendQueueEntry = appendQueueEntry;
exports.findActiveSessionSetDir = findActiveSessionSetDir;
/**
 * Pure helpers backing the significance-flagging commands. No vscode
 * import so these can be unit-tested via plain mocha + ts-node without
 * the @vscode/test-electron harness.
 *
 * The two `register*` commands in this directory import these helpers
 * and add the vscode-surface wiring (input box, notifications, command
 * registration).
 */
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
exports.QUEUE_FILENAME = "decision-review-queue.jsonl";
/**
 * Append one JSON line to `<sessionSetDir>/decision-review-queue.jsonl`.
 *
 * Creates the file if absent. Single `appendFileSync` call; the Python
 * reader (`ai_router/decision_review_queue.py`) skip-with-warns on a
 * partial trailing line so a crash mid-write does not poison reads.
 */
function appendQueueEntry(sessionSetDir, entry) {
    const queuePath = path.join(sessionSetDir, exports.QUEUE_FILENAME);
    const line = JSON.stringify(entry) + "\n";
    fs.appendFileSync(queuePath, line, "utf8");
}
/**
 * Return the absolute path of the in-progress session set, or null if
 * none. Multiple in-progress sets tie-break on `lastTouched` (most
 * recent wins). `provider` is the seam for tests — pass a closure
 * returning a synthetic `SessionSet[]`.
 */
function findActiveSessionSetDir(provider) {
    const all = provider();
    const inProgress = all.filter((s) => s.state === "in-progress");
    if (inProgress.length === 0)
        return null;
    inProgress.sort((a, b) => (b.lastTouched ?? "").localeCompare(a.lastTouched ?? ""));
    return inProgress[0].dir;
}
//# sourceMappingURL=decisionReviewQueue.js.map