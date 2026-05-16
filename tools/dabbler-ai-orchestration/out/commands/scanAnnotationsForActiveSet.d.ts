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
import * as vscode from "vscode";
export declare function registerScanAnnotationsForActiveSet(context: vscode.ExtensionContext): void;
