export interface Annotation {
    /** ISO timestamp when the annotation was discovered. */
    ts: string;
    /** Operator-supplied reason text from inside the parentheses. */
    reason: string;
    /** Always "annotation" for findAnnotations output. */
    source: "annotation";
    /** Workspace-relative path with forward slashes (POSIX style). */
    file: string;
    /** 1-based line number. */
    line: number;
}
/**
 * Find every annotation in `text`. Returns a list with one entry per
 * occurrence, in file order. The `file` field is the caller-supplied
 * `filePath` normalized to POSIX forward slashes; the `line` field is
 * 1-based.
 *
 * `now` is exposed for tests; production callers omit it and accept
 * `new Date().toISOString()`.
 */
export declare function findAnnotations(text: string, filePath: string, now?: () => string): Annotation[];
/**
 * Deduplicate `incoming` annotations against an existing queue. Two
 * entries collide when their `file`, `line`, and `reason` all match —
 * the queue's `ts` and `source` are ignored. Returns only the entries
 * from `incoming` that are not already present.
 *
 * Used by `scanAnnotationsForActiveSet` so repeated scans append each
 * annotation exactly once.
 */
export declare function deduplicateAnnotations(incoming: Annotation[], existing: ReadonlyArray<Pick<Annotation, "file" | "line" | "reason">>): Annotation[];
