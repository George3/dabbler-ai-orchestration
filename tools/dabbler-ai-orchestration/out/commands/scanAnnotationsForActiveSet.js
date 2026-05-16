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
exports.registerScanAnnotationsForActiveSet = registerScanAnnotationsForActiveSet;
/**
 * `dabbler.scanAnnotationsForActiveSet` — walk the workspace for
 * `@dabbler:outsource-review("...")` annotations and append new findings
 * to the active session set's decision-review queue.
 *
 * Pure helpers live in `./annotationScanner` and `./decisionReviewQueue`
 * so the scanning / dedup / toggle logic can be unit-tested without the
 * @vscode/test-electron harness. This file is the vscode-surface wiring
 * only.
 */
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const annotationParser_1 = require("../configEditor/annotationParser");
const yamlReadWrite_1 = require("../configEditor/yamlReadWrite");
const fileSystem_1 = require("../utils/fileSystem");
const decisionReviewQueue_1 = require("./decisionReviewQueue");
const annotationScanner_1 = require("./annotationScanner");
function defaultReadYaml(absPath) {
    if (!fs.existsSync(absPath))
        return null;
    try {
        const result = (0, yamlReadWrite_1.readYamlFile)(absPath);
        if (result === null)
            return null;
        const json = result.doc.toJSON();
        if (json == null || typeof json !== "object" || Array.isArray(json))
            return null;
        return json;
    }
    catch {
        return null;
    }
}
function registerScanAnnotationsForActiveSet(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.scanAnnotationsForActiveSet", async () => {
        const all = (0, fileSystem_1.readAllSessionSets)();
        const activeDir = (0, decisionReviewQueue_1.findActiveSessionSetDir)(() => all);
        if (!activeDir) {
            vscode.window.showInformationMessage("No active session set to scan against. Start a session set first.");
            return;
        }
        const activeSet = all.find((s) => s.dir === activeDir);
        const workspaceRoot = activeSet?.root ?? path.dirname(path.dirname(activeDir));
        if (!(0, annotationScanner_1.loadHonorAnnotationsToggle)(workspaceRoot, defaultReadYaml)) {
            vscode.window.showInformationMessage("Annotation scanning is disabled for this project " +
                "(local-overrides.yaml → decision_review.honor_annotations: false). " +
                "No queue entries appended.");
            return;
        }
        const uris = await vscode.workspace.findFiles(new vscode.RelativePattern(workspaceRoot, annotationScanner_1.SCAN_GLOB), new vscode.RelativePattern(workspaceRoot, annotationScanner_1.SCAN_EXCLUDE_GLOB));
        const filePaths = uris.map((u) => u.fsPath);
        const annotations = (0, annotationScanner_1.scanFilesForAnnotations)(filePaths, workspaceRoot);
        const existing = (0, annotationScanner_1.loadExistingQueueEntries)(activeDir);
        const fresh = (0, annotationParser_1.deduplicateAnnotations)(annotations, existing);
        if (fresh.length === 0) {
            const msg = annotations.length === 0
                ? "No `@dabbler:outsource-review` annotations found in workspace."
                : `All ${annotations.length} annotation(s) already in the queue — nothing new appended.`;
            vscode.window.showInformationMessage(msg);
            return;
        }
        try {
            for (const ann of fresh) {
                (0, decisionReviewQueue_1.appendQueueEntry)(activeDir, ann);
            }
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(`Failed to append annotation(s) to queue: ${msg}`);
            return;
        }
        const slug = path.basename(activeDir);
        vscode.window.showInformationMessage(`Appended ${fresh.length} new annotation(s) to ${slug}/${decisionReviewQueue_1.QUEUE_FILENAME}.`);
    }));
}
//# sourceMappingURL=scanAnnotationsForActiveSet.js.map