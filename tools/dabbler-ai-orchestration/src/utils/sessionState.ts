import * as fs from "fs";
import * as path from "path";

import {
  SCHEMA_VERSION_V4,
  extractSessionTitlesFromSpec,
} from "./progress";

// Canonical status strings carried by session-state.json under the Set 7
// invariant. The Python side defines the same set in
// ai_router/session_state.py; the two writers must stay in lockstep.
export type CanonicalStatus =
  | "not-started"
  | "in-progress"
  | "complete"
  | "cancelled";

// Set 047 Session 5 (TS) / Session 4 (Python): writers emit canonical
// v4 on-disk shape per spec §3.1. Top-level state (currentSession,
// totalSessions, completedSessions, orchestrator, startedAt,
// completedAt, verificationVerdict, lifecycleState) is dropped on disk
// and derived at read time via normalizeToV4Shape. Each session entry
// carries per-session startedAt / completedAt / orchestrator /
// verificationVerdict.
const SCHEMA_VERSION = SCHEMA_VERSION_V4;
const SESSION_STATE_FILENAME = "session-state.json";

// Per-session ledger entry under the v4 contract. Mirrors the entry
// shape produced by _build_sessions_array + _apply_v4_per_session_metadata
// in ai_router/session_state.py. Per-session metadata fields default
// to null for not-started / freshly-promoted sessions; the writers
// (register_session_start / mark_session_complete on the Python side)
// override them at the boundary they own.
type LazySessionRecord = {
  number: number;
  title: string;
  status: "not-started" | "in-progress" | "complete";
  startedAt: string | null;
  completedAt: string | null;
  orchestrator: Record<string, unknown> | null;
  verificationVerdict: string | null;
};

function buildSessions(
  totalSessions: number | null,
  topStatus: "not-started" | "in-progress" | "complete",
): LazySessionRecord[] | undefined {
  // Mirror of _not_started_payload / _backfill_payload in Python
  // session_state.py. Per rule 1, sessions[] is omitted when
  // totalSessions is unknown — "any set with a known plan" gets the
  // array; an unknown-plan set legitimately has no ledger.
  if (totalSessions === null || totalSessions <= 0) return undefined;
  const out: LazySessionRecord[] = [];
  for (let n = 1; n <= totalSessions; n++) {
    let status: LazySessionRecord["status"] = "not-started";
    if (topStatus === "complete") {
      status = "complete";
    } else if (topStatus === "in-progress" && n === 1) {
      // Conservative inference: when only activity-log.json is present,
      // we know SOME work has begun but not which session. Default
      // session 1 to in-progress so the snapshot satisfies rule 6.
      status = "in-progress";
    }
    out.push({
      number: n,
      title: `Session ${n}`,
      status,
      startedAt: null,
      completedAt: null,
      orchestrator: null,
      verificationVerdict: null,
    });
  }
  return out;
}

// Tolerant aliases mirroring _STATUS_ALIASES in session_state.py. Pre-Set-7
// state files may carry "completed" or "done" instead of the canonical
// "complete"; we normalize on read so consumers don't regress on existing
// files. Backfill explicitly leaves drifted files untouched, so
// canonicalization happens at the read boundary.
const STATUS_ALIASES: Record<string, string> = {
  completed: "complete",
  done: "complete",
};

function canonicalizeStatus(raw: string): string {
  return STATUS_ALIASES[raw] ?? raw;
}

// Mirror of _read_total_sessions_from_spec in Python. Looser than the
// full YAML parser used in fileSystem.ts:parseSessionSetConfig — that
// function already extracts the configuration block, but we duplicate
// the regex here to keep this module self-contained for the
// lazy-synthesis path (which is only ever exercised when a session
// set has a spec.md but no state file).
//
// Set 047 Session 5 (mirrors Python S4 verifier Critical 2): when the
// Session Set Configuration block has no numeric totalSessions, fall
// back to the highest ``### Session N`` heading in the spec body. A
// headings-only spec is a legitimate plan signal (the audit
// proposals + recurring-session specs are authored this way before
// the configuration block lands).
function readTotalSessionsFromSpec(sessionSetDir: string): number | null {
  const specPath = path.join(sessionSetDir, "spec.md");
  if (!fs.existsSync(specPath)) return null;
  let text: string;
  try {
    text = fs.readFileSync(specPath, "utf8");
  } catch {
    return null;
  }
  const headingMatch = text.match(
    /##\s*Session Set Configuration[\s\S]*?```ya?ml\s*([\s\S]*?)```/i
  );
  const block = headingMatch ? headingMatch[1] : text.slice(0, 4000);
  const totalMatch = block.match(/^\s*totalSessions\s*:\s*(\d+)\s*$/im);
  if (totalMatch) {
    const value = Number.parseInt(totalMatch[1], 10);
    if (Number.isFinite(value) && value > 0) return value;
  }
  // Headings fallback: max(N) over `### Session N — ...` headings.
  const titles = extractSessionTitlesFromSpec(specPath);
  if (titles.length === 0) return null;
  const maxN = titles.reduce((m, t) => (t.number > m ? t.number : m), 0);
  return maxN > 0 ? maxN : null;
}

// Mirror of _not_started_payload in Python. Must produce structurally
// identical content to the Python writer for any folder, since either
// side may be the one that lazy-synthesizes during a sweep.
//
// Set 047 Session 5 (mirrors Python S4): emits canonical v4 on-disk
// shape per spec §3.1. Top-level keys are ``schemaVersion`` /
// ``sessionSetName`` / ``status`` / ``sessions[]``; the dropped v3
// top-level fields (currentSession, totalSessions, completedSessions,
// startedAt, completedAt, orchestrator, verificationVerdict,
// lifecycleState) are derived by the reader via normalizeToV4Shape.
// Each session entry carries per-session metadata defaulted to null.
//
// When totalSessions is unknown (no spec config block, no headings),
// ``sessions[]`` is left absent — a not-started shape without a known
// plan is one of the few cases the invariant rule 1 explicitly allows.
// The next legitimate write (register_session_start) materializes
// ``sessions[]`` when the total is known.
function notStartedPayload(sessionSetDir: string): Record<string, unknown> {
  const totalSessions = readTotalSessionsFromSpec(sessionSetDir);
  const sessions = buildSessions(totalSessions, "not-started");
  const base: Record<string, unknown> = {
    schemaVersion: SCHEMA_VERSION,
    sessionSetName: path.basename(sessionSetDir.replace(/[\\/]+$/, "")),
    status: "not-started",
  };
  if (sessions !== undefined) {
    base.sessions = sessions;
  }
  return base;
}

// Mirror of _backfill_payload in Python. Used by the lazy-synth
// fallback in readStatus so a legacy folder that slipped through Set 7
// Session 1's backfill is classified by the same inference rules as the
// one-shot backfill instead of regressed to "not-started".
//
// Inference rules:
//   - change-log.md present → status: "complete", lifecycleState: "closed"
//   - activity-log.json present → status: "in-progress", lifecycleState: "work_in_progress"
//   - neither → not-started shape
//
// Timestamps (`completedAt`, `startedAt`) are best-effort: the TS path
// uses `change-log.md`'s mtime for completedAt and the earliest valid
// `dateTime` from the activity log for startedAt, mirroring the Python
// helpers _change_log_mtime_iso and _earliest_activity_log_timestamp.
// Drift between the two writers' timestamp formats would not affect
// correctness — `completedAt` and `startedAt` are observability fields,
// not lifecycle drivers — but we keep them aligned so a folder
// synthesized by either side reads the same way.
function backfillPayload(sessionSetDir: string): Record<string, unknown> {
  // Set 030 Session 3 (mirroring Python Session 2): re-derive
  // sessions[] from the inferred top-status so the snapshot satisfies
  // the invariants. change-log present -> all complete;
  // activity-log only -> session 1 in-progress; neither -> all
  // not-started (the notStartedPayload default).
  //
  // Set 047 Session 5 (mirrors Python S4): v4 emission. Top-level
  // status drives bucketing; per-session metadata carries the
  // boundary timestamps. The change-log branch leaves per-session
  // completedAt at null — the change-log mtime is a set-level
  // "when did this finish" heuristic, not a per-session boundary;
  // the shim's read-time derivation surfaces it for the explorer if
  // needed. The activity-log branch writes the earliest log
  // timestamp onto sessions[0].startedAt so the v4 read-view derives
  // a non-null top-level startedAt for the in-flight session.
  //
  // When totalSessions is unknown (no spec config + no headings),
  // buildSessions returns undefined and we CANNOT escalate to
  // complete/in-progress without violating rule 1 (sessions[]
  // required for any set with a known plan). In that case the
  // backfill stays at the not-started shape — the operator's intent
  // (signaled by file presence) is preserved via the file presence
  // itself; the next boundary write with a known plan will re-promote.

  const changelogPath = path.join(sessionSetDir, "change-log.md");
  if (fs.existsSync(changelogPath)) {
    const base = notStartedPayload(sessionSetDir);
    if (!Array.isArray(base.sessions)) {
      // No spec plan — cannot emit a reader-valid `complete` snapshot.
      // Fall through to the not-started shape; preserves operator
      // intent without producing an invariant-violating file.
      return base;
    }
    base.status = "complete";
    const sessions = base.sessions as LazySessionRecord[];
    for (const entry of sessions) {
      entry.status = "complete";
    }
    return base;
  }

  const activityPath = path.join(sessionSetDir, "activity-log.json");
  if (fs.existsSync(activityPath)) {
    const base = notStartedPayload(sessionSetDir);
    if (!Array.isArray(base.sessions) || base.sessions.length === 0) {
      // No spec plan — cannot emit a reader-valid `in-progress`
      // snapshot. Fall through to not-started.
      return base;
    }
    base.status = "in-progress";
    const sessions = base.sessions as LazySessionRecord[];
    sessions[0].status = "in-progress";
    try {
      const data = JSON.parse(fs.readFileSync(activityPath, "utf8")) as {
        entries?: Array<{ dateTime?: unknown }>;
      };
      const timestamps: string[] = [];
      for (const e of data.entries ?? []) {
        if (typeof e.dateTime === "string") timestamps.push(e.dateTime);
      }
      timestamps.sort();
      const earliest = timestamps[0];
      if (earliest !== undefined) {
        sessions[0].startedAt = earliest;
      }
    } catch {
      /* leave per-session startedAt at null */
    }
    return base;
  }

  return notStartedPayload(sessionSetDir);
}

// Atomic write via unique temp file + rename. Mirrors _atomic_write_json
// in Python: a fixed `path + ".tmp"` would let two concurrent writers
// (the Python backfill, this TS path, two extension instances on the
// same workspace) collide on the temp filename. Per-call uniqueness via
// PID + random suffix avoids that without a cross-process lock; both
// writers produce the same not-started shape so last-rename-wins is
// benign.
function atomicWriteJson(filePath: string, payload: unknown): void {
  const directory = path.dirname(filePath);
  const base = path.basename(filePath);
  const tmpPath = path.join(
    directory,
    `.${base}.${process.pid}-${Math.random().toString(36).slice(2, 8)}.tmp`
  );
  try {
    fs.writeFileSync(
      tmpPath,
      JSON.stringify(payload, null, 2) + "\n",
      { encoding: "utf8" }
    );
    fs.renameSync(tmpPath, filePath);
  } catch (err) {
    if (fs.existsSync(tmpPath)) {
      try {
        fs.unlinkSync(tmpPath);
      } catch {
        /* best-effort cleanup */
      }
    }
    throw err;
  }
}

/**
 * Synthesize a not-started session-state.json for *sessionSetDir*.
 *
 * Idempotent: if a state file already exists, returns its path
 * untouched. The caller should not assume the existing file matches
 * the canonical shape — pre-Set-7 drift (e.g. ``status: "completed"``
 * vs the canonical ``"complete"``) is preserved as-is; canonicalization
 * happens at the read boundary in :func:`readStatus`.
 *
 * Mirrors :func:`synthesize_not_started_state` in Python — both writers
 * must produce structurally identical content so a folder can be
 * synthesized by either side without confusing the other.
 *
 * Used at session-set bootstrap time when the caller knows the set
 * truly has not started. Lazy-synth fallback uses
 * :func:`ensureSessionStateFile` instead so a legacy folder is
 * inferred from current file presence rather than regressed to
 * not-started.
 */
export function synthesizeNotStartedState(sessionSetDir: string): string {
  const filePath = path.join(sessionSetDir, SESSION_STATE_FILENAME);
  if (fs.existsSync(filePath)) return filePath;
  atomicWriteJson(filePath, notStartedPayload(sessionSetDir));
  return filePath;
}

/**
 * Idempotently write the inferred ``session-state.json`` for a folder.
 *
 * Differs from :func:`synthesizeNotStartedState` in that the file-absent
 * path uses :func:`backfillPayload` to infer the right shape from
 * current file presence (change-log → complete; activity-log →
 * in-progress; neither → not-started), matching the Python one-shot
 * backfill's behavior. Verifier round 2 (Set 7 / Session 2) flagged
 * the regression: a legacy folder with change-log.md but no
 * session-state.json was being misclassified as "not-started" on
 * first read.
 *
 * Mirrors :func:`ensure_session_state_file` in Python.
 */
export function ensureSessionStateFile(sessionSetDir: string): string {
  const filePath = path.join(sessionSetDir, SESSION_STATE_FILENAME);
  if (fs.existsSync(filePath)) return filePath;
  atomicWriteJson(filePath, backfillPayload(sessionSetDir));
  return filePath;
}

/**
 * Return the canonical ``status`` for *sessionSetDir*.
 *
 * Single entry point for "what state is this set in?" in the extension.
 * Returns one of ``"not-started" | "in-progress" | "complete" |
 * "cancelled"``; pre-Set-7 drift (``"completed"``, ``"done"``) is
 * canonicalized via :data:`STATUS_ALIASES`.
 *
 * Lazy-synthesis fallback: a folder with ``spec.md`` but no
 * ``session-state.json`` triggers :func:`ensureSessionStateFile`,
 * which infers the right initial status from current file presence
 * (``change-log.md`` → ``"complete"``; ``activity-log.json`` →
 * ``"in-progress"``; neither → ``"not-started"``) — same rules as
 * the Python one-shot backfill. The atomic-write pattern keeps
 * concurrent fallback synthesis benign — both Python and TS writers
 * produce the same shape and the last rename wins.
 *
 * Parse errors propagate (consistent with the Python side and the
 * spec's risk section: "the fallback only triggers on file-absent,
 * never on parse-error"). A folder without ``spec.md`` is not a
 * session set; callers must filter those out.
 */
// Shared loader for the file-present branch and the post-synthesis
// re-read in readStatus. Without this, a race where another process
// creates the file between the existence check and the re-read could
// return a raw aliased value or skip the dict / string-status
// validations applied above. Mirrors `_load_canonical_status` in
// Python.
function loadCanonicalStatus(filePath: string): string {
  const raw = fs.readFileSync(filePath, "utf8");
  const parsed = JSON.parse(raw); // intentional: throws on malformed
  if (typeof parsed !== "object" || parsed === null) {
    throw new Error(
      `${filePath}: session-state.json must contain a JSON object`
    );
  }
  const status = (parsed as Record<string, unknown>).status;
  if (typeof status !== "string") {
    throw new Error(
      `${filePath}: session-state.json missing string 'status' field`
    );
  }
  return canonicalizeStatus(status);
}

export function readStatus(sessionSetDir: string): CanonicalStatus | string {
  const filePath = path.join(sessionSetDir, SESSION_STATE_FILENAME);
  if (fs.existsSync(filePath)) {
    return loadCanonicalStatus(filePath);
  }

  // File absent. Use ensureSessionStateFile (not synthesizeNotStarted)
  // so a legacy folder that slipped through Set 7 Session 1's backfill
  // is inferred from current file presence — change-log.md →
  // "complete", activity-log.json → "in-progress" — rather than being
  // regressed to "not-started". Then re-read through the same loader
  // so validation and alias canonicalization apply uniformly under
  // races.
  ensureSessionStateFile(sessionSetDir);
  return loadCanonicalStatus(filePath);
}
