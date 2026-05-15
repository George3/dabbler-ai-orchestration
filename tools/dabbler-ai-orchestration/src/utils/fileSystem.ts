import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { listGitWorktrees } from "./git";
import { readStatus } from "./sessionState";
import { isCancelled } from "./cancelLifecycle";
import {
  SessionSet,
  SessionState,
  SessionSetConfig,
  UatSummary,
  LiveSession,
} from "../types";

export const SESSION_SETS_REL = path.join("docs", "session-sets");
export const PLAYWRIGHT_REL_DEFAULT = "tests";

// Cancelled sets sort below all other groups in the merge logic — Set 8
// keeps cancelled state as the lowest precedence so a set that exists in
// two roots (one cancelled, one active) prefers the active copy when
// dedup-merging. Within a single root the file-presence rule still wins
// because readSessionSets has already resolved each entry's state.
const STATE_RANK: Record<SessionState, number> = {
  done: 3,
  "in-progress": 2,
  "not-started": 1,
  cancelled: 0,
};

export function discoverRoots(): string[] {
  const seen = new Map<string, string>();
  const order: string[] = [];
  const add = (p: string | undefined) => {
    if (!p) return;
    const canonical = path.resolve(p);
    const key = canonical.toLowerCase();
    if (seen.has(key) || !fs.existsSync(canonical)) return;
    seen.set(key, canonical);
    order.push(canonical);
  };
  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    add(folder.uri.fsPath);
  }
  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    for (const wt of listGitWorktrees(folder.uri.fsPath)) {
      add(wt);
    }
  }
  return order;
}

// Detect a stale `status: "complete"` snapshot that doesn't actually
// reflect a finished set. Two drift shapes both downgrade to in-progress:
//
//   1. **Count mismatch.** `currentSession < totalSessions`. Pre-0.2.1
//      ai_router flipped to complete after every session, and manual
//      edits / stale consumer snapshots still produce this shape.
//
//   2. **Final-session ledger gap.** `currentSession === totalSessions`
//      and the snapshot claims complete, but `session-events.jsonl`
//      has no `closeout_succeeded` event for the final session. The
//      events ledger is authoritative on Full tier; absent closeout
//      means the writer drifted from the ledger (observed
//      2026-05-12 on unified-master-details-composite: snapshot
//      `status: complete` + `verificationVerdict: VERIFIED` at
//      currentSession=5/5, yet ledger had closeouts for sessions 1-4
//      only). Only fires when the ledger file exists — Lightweight
//      tier has no ledger and we trust the snapshot there.
//
// Returns false on any read/parse failure — trust the canonical status
// rather than second-guessing on garbled input.
export function isMidSetComplete(statePath: string): boolean {
  if (!fs.existsSync(statePath)) return false;
  try {
    const sd = JSON.parse(fs.readFileSync(statePath, "utf8")) as {
      currentSession?: number;
      totalSessions?: number;
    };
    if (typeof sd.currentSession !== "number") return false;
    if (typeof sd.totalSessions !== "number") return false;

    if (sd.currentSession < sd.totalSessions) return true;

    const eventsPath = path.join(path.dirname(statePath), "session-events.jsonl");
    if (fs.existsSync(eventsPath) &&
        !hasCloseoutEventForSession(eventsPath, sd.currentSession)) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

function hasCloseoutEventForSession(
  eventsPath: string,
  sessionNumber: number
): boolean {
  let text: string;
  try {
    text = fs.readFileSync(eventsPath, "utf8");
  } catch {
    return false;
  }
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    try {
      const event = JSON.parse(line) as {
        session_number?: number;
        event_type?: string;
      };
      if (
        event.event_type === "closeout_succeeded" &&
        event.session_number === sessionNumber
      ) {
        return true;
      }
    } catch {
      // skip malformed lines — append-only ledger may carry partial writes
    }
  }
  return false;
}

// Set 022 Session 2: generalization of `hasCloseoutEventForSession` to
// "how many distinct sessions does the ledger record as closed." Used
// as the Full-tier fallback for `sessionsCompleted` when
// `completedSessions[]` is missing from the snapshot (e.g., a set
// that pre-dates Set 022's writer changes and hasn't had its next
// boundary-write heal it yet). Returns 0 on any read/parse failure
// or when the file is absent — the caller treats 0 as "no
// authoritative signal" and falls through to the next derivation
// step rather than asserting "0 sessions done."
export function countDistinctCloseoutSessions(eventsPath: string): number {
  if (!fs.existsSync(eventsPath)) return 0;
  let text: string;
  try {
    text = fs.readFileSync(eventsPath, "utf8");
  } catch {
    return 0;
  }
  const seen = new Set<number>();
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    try {
      const event = JSON.parse(line) as {
        session_number?: number;
        event_type?: string;
      };
      if (
        event.event_type === "closeout_succeeded" &&
        typeof event.session_number === "number"
      ) {
        seen.add(event.session_number);
      }
    } catch {
      // skip malformed lines — append-only ledger may carry partial writes
    }
  }
  return seen.size;
}

export function parseSessionSetConfig(specPath: string): SessionSetConfig {
  const config: SessionSetConfig = {
    requiresUAT: false,
    requiresE2E: false,
    uatScope: "none",
    outsourceMode: null,
  };
  if (!fs.existsSync(specPath)) return config;
  let text: string;
  try {
    text = fs.readFileSync(specPath, "utf8");
  } catch {
    return config;
  }
  const headingMatch = text.match(
    /##\s*Session Set Configuration[\s\S]*?```ya?ml\s*([\s\S]*?)```/i
  );
  // When the canonical `## Session Set Configuration` heading is absent,
  // fall back to scanning the entire spec rather than just the first 4000
  // chars. The line-anchored regexes below (e.g.,
  // `^\s*requiresUAT:\s*(true|false)\s*$`) are specific enough that false
  // positives in prose are very unlikely; a 4000-byte cap was needlessly
  // narrow and missed real declarations in specs that put the config
  // yaml block under a non-canonical heading like `## UAT scope`.
  const block = headingMatch ? headingMatch[1] : text;
  const flagRe = (key: string) =>
    new RegExp(`^\\s*${key}\\s*:\\s*(true|false)\\s*$`, "im");
  const stringRe = (key: string) =>
    new RegExp(`^\\s*${key}\\s*:\\s*([\\w-]+)\\s*$`, "im");

  const uat = block.match(flagRe("requiresUAT"));
  if (uat) config.requiresUAT = uat[1].toLowerCase() === "true";
  const e2e = block.match(flagRe("requiresE2E"));
  if (e2e) config.requiresE2E = e2e[1].toLowerCase() === "true";
  const scope = block.match(stringRe("uatScope"));
  if (scope) config.uatScope = scope[1];
  const mode = block.match(stringRe("outsourceMode"));
  if (mode) {
    const v = mode[1].toLowerCase();
    if (v === "first" || v === "last") config.outsourceMode = v;
  }
  return config;
}

export function parseUatChecklist(checklistPath: string): UatSummary | null {
  if (!fs.existsSync(checklistPath)) return null;
  let data: unknown;
  try {
    data = JSON.parse(fs.readFileSync(checklistPath, "utf8"));
  } catch {
    return null;
  }
  const items: Record<string, unknown>[] = [];
  const collect = (node: unknown) => {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) { for (const v of node) collect(v); return; }
    const obj = node as Record<string, unknown>;
    if (obj["Result"] !== undefined || obj["result"] !== undefined) {
      items.push(obj);
    }
    for (const v of Object.values(obj)) collect(v);
  };
  collect(data);

  const e2eRefs = new Set<string>();
  let pending = 0;
  for (const it of items) {
    const r = (it["Result"] ?? it["result"] ?? "") as string;
    if (r === "" || r === null || /^pending$/i.test(String(r))) pending++;
    const ref = it["E2ETestReference"] || it["e2eTestReference"];
    if (ref) e2eRefs.add(String(ref));
  }
  return { totalItems: items.length, pendingItems: pending, e2eRefs: Array.from(e2eRefs) };
}

export function readSessionSets(root: string): SessionSet[] {
  const sessionSetsDir = path.join(root, SESSION_SETS_REL);
  if (!fs.existsSync(sessionSetsDir)) return [];
  const entries = fs.readdirSync(sessionSetsDir, { withFileTypes: true });
  const sets: SessionSet[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith("_")) continue;
    const dir = path.join(sessionSetsDir, entry.name);
    const specPath = path.join(dir, "spec.md");
    if (!fs.existsSync(specPath)) continue;

    const activityPath = path.join(dir, "activity-log.json");
    const changeLogPath = path.join(dir, "change-log.md");
    const statePath = path.join(dir, "session-state.json");
    const aiAssignmentPath = path.join(dir, "ai-assignment.md");
    const uatChecklistPath = path.join(dir, `${entry.name}-uat-checklist.json`);

    // Set 8: CANCELLED.md presence is the canonical (and only) signal
    // for the cancelled tree state. The spec's detection-rules table in
    // `docs/session-sets/008-cancelled-session-set-status/spec.md` makes
    // the file-presence check the first gate so a partially-completed
    // set that has been cancelled mid-stream renders as Cancelled rather
    // than Done. Once a set is restored, its `RESTORED.md` is "purely
    // an audit artifact" (spec § Detection rules) and the set falls
    // back to whichever of done/in-progress/not-started its other
    // files indicate. The cancelLifecycle helpers keep
    // session-state.json's `status` in lockstep with the markdown file,
    // so we do not consult `status === "cancelled"` as a separate
    // signal — operator manual edits resolve via the file-presence
    // path, matching the spec's "filename presence is what matters"
    // rule.
    let state: SessionState;
    if (isCancelled(dir)) {
      state = "cancelled";
    } else {
      const status = readStatus(dir);
      if (status === "complete") {
        // Defensive: a status of "complete" with currentSession <
        // totalSessions is a stale mid-set close-out — written either
        // by ai_router < 0.2.1 (which flipped to complete after every
        // session), a manual edit, or a snapshot a consumer repo
        // hasn't refreshed yet. Treat as in-progress so the set
        // doesn't briefly show Done in the window between sessions.
        state = isMidSetComplete(statePath) ? "in-progress" : "done";
      } else if (status === "in-progress") {
        state = "in-progress";
      } else {
        state = "not-started";
      }
    }

    let totalSessions: number | null = null;
    let sessionsCompleted = 0;
    let lastTouched: string | null = null;
    let liveSession: LiveSession | null = null;
    const eventsPath = path.join(dir, "session-events.jsonl");

    // Activity log is a step log, not a count source. Set 022 Session 2
    // removed the unique-`sessionNumber` count derivation that used to
    // live here — under the state-first lifecycle protocol,
    // `completedSessions[]` (writer-maintained on Full tier;
    // hand-maintained on Lightweight) is authoritative, with the
    // events ledger as the Full-tier fallback. The activity-log read
    // is retained for two non-count signals: `totalSessions` (which
    // the schema places at the top level of the file) and the
    // per-entry `dateTime` for the `lastTouched` display, which is
    // more granular than the state-file's session-boundary timestamps
    // while a session is mid-flight.
    if (fs.existsSync(activityPath)) {
      try {
        const data = JSON.parse(fs.readFileSync(activityPath, "utf8")) as {
          totalSessions?: number;
          entries?: Array<{ sessionNumber?: number; dateTime?: string }>;
        };
        if (typeof data.totalSessions === "number") totalSessions = data.totalSessions;
        for (const e of data.entries ?? []) {
          if (e.dateTime && (!lastTouched || e.dateTime > lastTouched)) lastTouched = e.dateTime;
        }
      } catch { /* ignore */ }
    }

    if (fs.existsSync(statePath)) {
      try {
        const sd = JSON.parse(fs.readFileSync(statePath, "utf8")) as {
          totalSessions?: number;
          completedSessions?: number[];
          completedAt?: string;
          startedAt?: string;
          currentSession?: number;
          status?: string;
          orchestrator?: { engine?: string; model?: string; effort?: string };
          verificationVerdict?: string;
          forceClosed?: boolean;
        };
        // State file is authoritative for `totalSessions`. The
        // activity-log carries the field at its top level (and we
        // read it above for legacy compatibility), but if both are
        // present the state-file value wins — a Set 022 Session 2
        // round-1 verifier finding caught the inverted preference,
        // which would silently mis-display the fraction whenever a
        // Lightweight-tier set hand-edited one file but not the
        // other.
        if (typeof sd.totalSessions === "number") {
          totalSessions = sd.totalSessions;
        }
        const stateTouched = sd.completedAt || sd.startedAt;
        if (stateTouched && (!lastTouched || stateTouched > lastTouched)) lastTouched = stateTouched;
        liveSession = {
          currentSession: sd.currentSession ?? null,
          status: sd.status ?? null,
          orchestrator: sd.orchestrator ?? null,
          startedAt: sd.startedAt ?? null,
          completedAt: sd.completedAt ?? null,
          verificationVerdict: sd.verificationVerdict ?? null,
          forceClosed: sd.forceClosed ?? null,
          completedSessions: Array.isArray(sd.completedSessions) ? sd.completedSessions : null,
        };
        // sessionsCompleted priority (highest first) — see Set 022
        // spec § "Readers" for the rationale:
        //  1. session-state.json `completedSessions` array —
        //     authoritative under schema v2 + Set 022 protocol.
        //     Hand-maintained on Lightweight tier; written by
        //     ai_router on Full tier on every close.
        //  2. Distinct `closeout_succeeded` session numbers in
        //     `session-events.jsonl` — Full-tier fallback for sets
        //     that pre-date the writer changes and haven't been
        //     healed by their next boundary write yet.
        //  3. `state === "done"` plus `totalSessions` — terminal
        //     state with no granular count signal (e.g., a
        //     Lightweight-tier set marked complete without writing
        //     the array). Using the canonicalized `state` instead
        //     of raw `sd.status` keeps this in lockstep with the
        //     bucketing alias map; also naturally skips the
        //     mid-set-complete drift case where `state` is
        //     downgraded to in-progress.
        //
        // No `currentSession - 1` fallback. Set 022 Session 1's
        // writer protocol guarantees `completedSessions[]` is
        // present after the first boundary write; legacy sets are
        // covered by the events-ledger fallback. The pre-Set-022
        // off-by-one shape ("0/4" stuck displayed while session 1
        // is in flight; "N-1/N" stuck while final session is
        // wrapping up) is eliminated by removing the heuristic
        // rather than refining it.
        if (Array.isArray(sd.completedSessions)) {
          sessionsCompleted = sd.completedSessions.length;
        } else {
          const ledgerCount = countDistinctCloseoutSessions(eventsPath);
          if (ledgerCount > 0) {
            sessionsCompleted = ledgerCount;
          } else if (state === "done" && typeof totalSessions === "number") {
            sessionsCompleted = totalSessions;
          }
        }
      } catch { /* ignore */ }
    }

    const config = parseSessionSetConfig(specPath);
    const uatSummary = config.requiresUAT ? parseUatChecklist(uatChecklistPath) : null;

    sets.push({
      name: entry.name,
      dir,
      specPath,
      activityPath,
      changeLogPath,
      statePath,
      aiAssignmentPath,
      uatChecklistPath,
      state,
      totalSessions,
      sessionsCompleted,
      lastTouched,
      liveSession,
      config,
      uatSummary,
      root,
    });
  }
  // Diagnostic: one-line summary in the dev console showing how the
  // extension bucketed each root. Useful for spotting UI/cache bugs vs.
  // state-derivation bugs without needing a breakpoint.
  if (sets.length > 0) {
    const counts = sets.reduce(
      (acc, s) => {
        acc[s.state] = (acc[s.state] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );
    console.log(
      `[dabbler-ai-orchestration] readSessionSets(${path.basename(root)}): ` +
        `${sets.length} set(s) — ` +
        `done=${counts.done ?? 0}, ` +
        `in-progress=${counts["in-progress"] ?? 0}, ` +
        `not-started=${counts["not-started"] ?? 0}, ` +
        `cancelled=${counts.cancelled ?? 0}`,
    );
  }
  return sets;
}

export function readAllSessionSets(): SessionSet[] {
  const merged = new Map<string, SessionSet>();
  for (const root of discoverRoots()) {
    for (const set of readSessionSets(root)) {
      const prior = merged.get(set.name);
      if (!prior) { merged.set(set.name, set); continue; }
      const newRank = STATE_RANK[set.state] ?? -1;
      const priorRank = STATE_RANK[prior.state] ?? -1;
      if (newRank > priorRank) {
        merged.set(set.name, set);
      } else if (newRank === priorRank) {
        if ((set.lastTouched || "") > (prior.lastTouched || "")) merged.set(set.name, set);
      }
    }
  }
  return Array.from(merged.values());
}
