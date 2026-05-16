import { SessionSet } from "../types";
export interface QueueEntry {
    ts: string;
    reason: string;
    source: "command" | "annotation";
    file: string | null;
    line: number | null;
}
export declare const QUEUE_FILENAME = "decision-review-queue.jsonl";
/**
 * Append one JSON line to `<sessionSetDir>/decision-review-queue.jsonl`.
 *
 * Creates the file if absent. Single `appendFileSync` call; the Python
 * reader (`ai_router/decision_review_queue.py`) skip-with-warns on a
 * partial trailing line so a crash mid-write does not poison reads.
 */
export declare function appendQueueEntry(sessionSetDir: string, entry: QueueEntry): void;
/**
 * Return the absolute path of the in-progress session set, or null if
 * none. Multiple in-progress sets tie-break on `lastTouched` (most
 * recent wins). `provider` is the seam for tests — pass a closure
 * returning a synthetic `SessionSet[]`.
 */
export declare function findActiveSessionSetDir(provider: () => SessionSet[]): string | null;
