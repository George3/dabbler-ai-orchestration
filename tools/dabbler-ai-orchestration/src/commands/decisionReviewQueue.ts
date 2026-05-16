/**
 * Pure helpers backing the significance-flagging commands. No vscode
 * import so these can be unit-tested via plain mocha + ts-node without
 * the @vscode/test-electron harness.
 *
 * The two `register*` commands in this directory import these helpers
 * and add the vscode-surface wiring (input box, notifications, command
 * registration).
 */
import * as fs from "fs";
import * as path from "path";
import { SessionSet } from "../types";

export interface QueueEntry {
  ts: string;
  reason: string;
  source: "command" | "annotation";
  file: string | null;
  line: number | null;
}

export const QUEUE_FILENAME = "decision-review-queue.jsonl";

/**
 * Append one JSON line to `<sessionSetDir>/decision-review-queue.jsonl`.
 *
 * Creates the file if absent. Single `appendFileSync` call; the Python
 * reader (`ai_router/decision_review_queue.py`) skip-with-warns on a
 * partial trailing line so a crash mid-write does not poison reads.
 */
export function appendQueueEntry(sessionSetDir: string, entry: QueueEntry): void {
  const queuePath = path.join(sessionSetDir, QUEUE_FILENAME);
  const line = JSON.stringify(entry) + "\n";
  fs.appendFileSync(queuePath, line, "utf8");
}

/**
 * Return the absolute path of the in-progress session set, or null if
 * none. Multiple in-progress sets tie-break on `lastTouched` (most
 * recent wins). `provider` is the seam for tests — pass a closure
 * returning a synthetic `SessionSet[]`.
 */
export function findActiveSessionSetDir(
  provider: () => SessionSet[],
): string | null {
  const all = provider();
  const inProgress = all.filter((s) => s.state === "in-progress");
  if (inProgress.length === 0) return null;
  inProgress.sort((a, b) => (b.lastTouched ?? "").localeCompare(a.lastTouched ?? ""));
  return inProgress[0].dir;
}
