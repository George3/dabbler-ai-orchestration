// In-extension v2 → v3 session-state.json migrator.
//
// Replaces the previous Python subprocess path (which spawned
// `python -m ai_router.migrate_session_state` and required the
// `ai_router` package to be installed even for the deterministic
// strategies). Lightweight-tier consumer repos that never install
// ai-router can now migrate too.
//
// Two strategies — both deterministic, no routing:
//
//   * "regex"   — read `### Session N of M: <title>` headings from
//                 spec.md (regex parse); fall back to "Session N" if
//                 a heading is absent. Recommended default.
//   * "generic" — every session titled "Session N". Used when
//                 spec.md headings are malformed / missing / not
//                 desired.
//
// The pre-existing AI strategy is retired here. Any orchestrator
// (Claude, Codex, Gemini, GitHub Copilot, etc.) can perform AI-style
// title refinement in-line as a chat task if the operator wants it —
// outsourcing this through the router is overkill for a few-token
// extraction and prevents Lightweight repos from migrating at all.
//
// TypeScript mirror of the deterministic surface of
// `ai_router/migrate_session_state.py`. Building blocks
// (canonicalizeStatus, extractSessionTitlesFromSpec,
// validateInvariants, SessionStateInvariantError) live in
// `utils/progress.ts` and are shared with the read-time synthesizer.

import * as fs from "fs";
import * as path from "path";
import {
  LIFECYCLE_STATE_CLOSED,
  LIFECYCLE_STATE_WORK_IN_PROGRESS,
  SCHEMA_VERSION_V3,
  SESSION_STATUS_COMPLETE,
  SESSION_STATUS_IN_PROGRESS,
  SESSION_STATUS_NOT_STARTED,
  SessionStateInvariantError,
  canonicalizeStatus,
  extractSessionTitlesFromSpec,
  validateInvariants,
} from "./progress";
import { SessionRecord, SessionStatus } from "../types";

export type MigrationStrategy = "regex" | "generic";

export type MigrationAction =
  | "migrated"
  | "skipped-v3"
  | "skipped-no-state"
  | "skipped-malformed"
  | "skipped-future-schema"
  | "would-violate";

export interface MigrationResult {
  setDir: string;
  action: MigrationAction;
  reason: string;
  error?: string;
}

const SESSION_STATE_FILENAME = "session-state.json";

function isStrictPositiveInt(v: unknown): v is number {
  return (
    typeof v === "number" &&
    Number.isInteger(v) &&
    v > 0 &&
    !Number.isNaN(v)
  );
}

function stripLegacyCompleted(raw: unknown, total: number): number[] {
  if (!Array.isArray(raw)) return [];
  const seen = new Set<number>();
  const out: number[] = [];
  for (const n of raw) {
    if (isStrictPositiveInt(n) && n >= 1 && n <= total && !seen.has(n)) {
      out.push(n);
      seen.add(n);
    }
  }
  out.sort((a, b) => a - b);
  return out;
}

function resolveTotal(
  state: Record<string, unknown>,
  specTitles: Map<number, string>,
): number {
  const candidates: number[] = [];
  if (isStrictPositiveInt(state.totalSessions)) candidates.push(state.totalSessions);
  if (specTitles.size > 0) candidates.push(Math.max(...specTitles.keys()));
  if (isStrictPositiveInt(state.currentSession)) candidates.push(state.currentSession);
  if (Array.isArray(state.completedSessions)) {
    for (const n of state.completedSessions) {
      if (isStrictPositiveInt(n)) candidates.push(n);
    }
  }
  return candidates.length > 0 ? Math.max(...candidates) : 0;
}

function resolveLifecycleState(
  topStatus: string | null,
  raw: unknown,
): string | null {
  if (topStatus === SESSION_STATUS_COMPLETE) return LIFECYCLE_STATE_CLOSED;
  if (topStatus === "cancelled") {
    return typeof raw === "string" && raw.length > 0 ? raw : LIFECYCLE_STATE_CLOSED;
  }
  if (topStatus === SESSION_STATUS_IN_PROGRESS) {
    return typeof raw === "string" && raw.length > 0
      ? raw
      : LIFECYCLE_STATE_WORK_IN_PROGRESS;
  }
  // not-started: keep operator's explicit value (often null).
  return typeof raw === "string" ? raw : null;
}

// Build the v3 sessions[] from a v2 state dict.
//
// Closed-signal path mirrors the Python migrator's Round-A fix: when
// `status: complete` AND (`lifecycleState: closed` OR
// `currentSession >= LEGACY totalSessions`), force-promote every
// session to "complete" so rule 7 holds. The disjunct compares
// against the LEGACY totalSessions field (not the resolved total) —
// a v2 file marked complete against a 3-session plan that spec.md
// later widened to 4 must still close out under the operator's
// original signal.
function buildV3Sessions(
  state: Record<string, unknown>,
  specTitles: Map<number, string>,
  total: number,
  useGenericTitles: boolean,
): SessionRecord[] {
  const topStatus = canonicalizeStatus(state.status as string | undefined);
  const lifecycle = state.lifecycleState;
  const currentInt = isStrictPositiveInt(state.currentSession)
    ? state.currentSession
    : null;
  const legacyTotalInt = isStrictPositiveInt(state.totalSessions)
    ? state.totalSessions
    : null;

  const closedSignal =
    topStatus === SESSION_STATUS_COMPLETE &&
    (lifecycle === LIFECYCLE_STATE_CLOSED ||
      (legacyTotalInt !== null &&
        currentInt !== null &&
        currentInt >= legacyTotalInt));

  const completedLegacy = stripLegacyCompleted(state.completedSessions, total);
  const completedSet = closedSignal
    ? new Set(Array.from({ length: total }, (_, i) => i + 1))
    : new Set(completedLegacy);

  let inProgressNumber: number | null = null;
  if (
    topStatus === SESSION_STATUS_IN_PROGRESS &&
    currentInt !== null &&
    currentInt >= 1 &&
    currentInt <= total &&
    !completedSet.has(currentInt)
  ) {
    inProgressNumber = currentInt;
  }

  const sessions: SessionRecord[] = [];
  for (let n = 1; n <= total; n++) {
    const title =
      useGenericTitles || !specTitles.has(n)
        ? `Session ${n}`
        : specTitles.get(n)!;
    let status: SessionStatus;
    if (inProgressNumber !== null && n === inProgressNumber) {
      status = SESSION_STATUS_IN_PROGRESS;
    } else if (completedSet.has(n)) {
      status = SESSION_STATUS_COMPLETE;
    } else {
      status = SESSION_STATUS_NOT_STARTED;
    }
    sessions.push({ number: n, title, status });
  }
  return sessions;
}

function deriveLegacyTriple(sessions: SessionRecord[]): {
  current: number | null;
  total: number;
  completed: number[];
} {
  let current: number | null = null;
  const completed: number[] = [];
  for (const s of sessions) {
    if (s.status === SESSION_STATUS_IN_PROGRESS) {
      current = s.number;
    } else if (s.status === SESSION_STATUS_COMPLETE) {
      completed.push(s.number);
    }
  }
  completed.sort((a, b) => a - b);
  return { current, total: sessions.length, completed };
}

// Write JSON to *filePath* atomically: write to a sibling tempfile,
// fsync, rename. Survives crash mid-write — readers see either the
// old content or the new content, never a half-written file.
function atomicWriteJson(filePath: string, data: unknown): void {
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  const tmp = path.join(dir, `${base}.tmp.${process.pid}.${Date.now()}`);
  const fd = fs.openSync(tmp, "w");
  try {
    fs.writeSync(fd, JSON.stringify(data, null, 2) + "\n", null, "utf-8");
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, filePath);
}

export interface MigrateOneSetOptions {
  /** Strategy for deriving session titles (default: "regex"). */
  strategy?: MigrationStrategy;
  /** When true, validate + report without writing to disk. */
  dryRun?: boolean;
}

// Migrate one session-set directory's session-state.json to v3.
//
// Idempotent: a v3 file with sessions[] returns "skipped-v3" without
// touching disk. A missing or malformed state file returns a skip
// action with a human-readable reason. This function NEVER throws
// for normal failure cases — structured MigrationResult records are
// returned so the UI can surface them.
export function migrateOneSet(
  setDir: string,
  options: MigrateOneSetOptions = {},
): MigrationResult {
  const strategy = options.strategy ?? "regex";
  const dryRun = options.dryRun ?? false;
  const statePath = path.join(setDir, SESSION_STATE_FILENAME);

  if (!fs.existsSync(statePath)) {
    return {
      setDir,
      action: "skipped-no-state",
      reason: `${SESSION_STATE_FILENAME} not found`,
    };
  }

  let raw: string;
  try {
    raw = fs.readFileSync(statePath, "utf-8");
  } catch (exc) {
    const msg = exc instanceof Error ? exc.message : String(exc);
    return {
      setDir,
      action: "skipped-malformed",
      reason: `failed to read: ${msg}`,
      error: msg,
    };
  }

  let state: unknown;
  try {
    state = JSON.parse(raw);
  } catch (exc) {
    const msg = exc instanceof Error ? exc.message : String(exc);
    return {
      setDir,
      action: "skipped-malformed",
      reason: `failed to parse: ${msg}`,
      error: msg,
    };
  }

  if (
    state === null ||
    typeof state !== "object" ||
    Array.isArray(state)
  ) {
    const t = Array.isArray(state) ? "array" : typeof state;
    return {
      setDir,
      action: "skipped-malformed",
      reason: `top-level JSON is ${t}, expected object`,
    };
  }

  const stateObj = state as Record<string, unknown>;
  const schemaVersion = stateObj.schemaVersion;
  if (typeof schemaVersion === "number" && schemaVersion > SCHEMA_VERSION_V3) {
    return {
      setDir,
      action: "skipped-future-schema",
      reason:
        `schemaVersion=${schemaVersion} is newer than this migrator ` +
        `(v${SCHEMA_VERSION_V3}); refusing to downgrade. Upgrade the ` +
        "migrator or hand-edit the file.",
    };
  }
  if (schemaVersion === SCHEMA_VERSION_V3) {
    if (Array.isArray(stateObj.sessions)) {
      return {
        setDir,
        action: "skipped-v3",
        reason: "already v3 (sessions[] present)",
      };
    }
    // Self-identified v3 but missing/broken sessions[] — refuse to
    // rewrite by re-running v2 inference (which would treat the
    // missing array as a default-not-started signal and obliterate
    // any operator intent recorded by the v3 writer that produced
    // this file).
    return {
      setDir,
      action: "skipped-malformed",
      reason:
        "schemaVersion=3 but sessions[] is missing or not a list; this is " +
        "a broken v3 file, not a v2 file. Hand-repair or restore from git.",
    };
  }

  const specMdPath = path.join(setDir, "spec.md");
  const specTitlesArr = extractSessionTitlesFromSpec(specMdPath);
  const specTitles = new Map<number, string>(
    specTitlesArr.map((t) => [t.number, t.title]),
  );

  const total = resolveTotal(stateObj, specTitles);
  if (total < 1) {
    return {
      setDir,
      action: "would-violate",
      reason:
        "cannot determine totalSessions: no spec.md headings, no legacy " +
        "totalSessions, no completedSessions, no currentSession",
    };
  }

  const sessions = buildV3Sessions(
    stateObj,
    specTitles,
    total,
    strategy === "generic",
  );

  const topStatusRaw = stateObj.status;
  const topStatus = canonicalizeStatus(topStatusRaw as string | undefined);
  const lifecycleState = resolveLifecycleState(topStatus, stateObj.lifecycleState);

  try {
    validateInvariants(sessions, topStatus, lifecycleState);
  } catch (exc) {
    if (exc instanceof SessionStateInvariantError) {
      return {
        setDir,
        action: "would-violate",
        reason: exc.message,
        error: exc.message,
      };
    }
    throw exc;
  }

  const { current, total: derivedTotal, completed } = deriveLegacyTriple(sessions);

  const out: Record<string, unknown> = { ...stateObj };
  out.schemaVersion = SCHEMA_VERSION_V3;
  out.sessions = sessions;
  if (topStatus !== null && topStatus !== topStatusRaw) {
    out.status = topStatus;
  }
  if (lifecycleState !== null || "lifecycleState" in out) {
    out.lifecycleState = lifecycleState;
  }
  out.currentSession = current;
  out.totalSessions = derivedTotal;
  out.completedSessions = completed;

  if (!dryRun) {
    atomicWriteJson(statePath, out);
  }

  return {
    setDir,
    action: "migrated",
    reason: `migrated using ${strategy} strategy`,
  };
}
