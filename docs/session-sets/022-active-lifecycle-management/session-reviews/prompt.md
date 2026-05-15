# Set 022 Session 2 — TypeScript extension reader changes

## Decisions confirmed (do not re-litigate)

## Decisions confirmed with the human (do not re-litigate)

These came from a design round on 2026-05-15 with GPT 5.4 (Codex) and
Gemini Pro. Both engines were given the same prompt; their proposals
overlapped heavily, and where they diverged GPT's framing won on
schema invariants and separation of concerns.

1. **`completedSessions[]` is the authoritative progress ledger** on
   both tiers, maintained on every session close (not just the final
   one). The schema doc's "currently optional but planned" status for
   Full tier becomes "always written."

2. **Mid-set `lifecycleState` stays `work_in_progress`.** Only the
   final close flips it to `closed` (alongside `status: complete`).
   This preserves the v2 schema's pairing rule and keeps the v0.13.11
   guard's semantics intact. Gemini's "flip to closed mid-set" was
   rejected — it would resurrect the exact drift class v0.13.11
   defends against.

3. **State invariant (load-bearing — every writer and reader follows
   this):**
   ```
   currentSession not in completedSessions[]              → session currentSession is in flight
   currentSession in completedSessions[] AND status="in-progress"  → between sessions
   status = "complete"                                    → set done
   ```
   The extension's bucketing rule and the orchestrator's
   "start/close" semantics both derive from this.

4. **`activity-log.json` is a step log only, not a count source.**
   GPT's stricter framing: the activity log records work steps the
   orchestrator took during a session — it must not be polluted with
   synthetic "session N started" entries, and the extension must
   stop using unique `sessionNumber`s in the activity log as a
   count-fallback path. This is a small refactor in
   `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts` that
   yields a cleaner invariant.

5. **Extension stays passive.** No "Start Session" / "Close Session"
   context-menu commands — those would make the IDE a hidden
   dependency. The extension reads state and refreshes when files
   change; it never writes lifecycle state itself.

6. **CLI-driven on Full tier; hand-write on Lightweight.** The
   orchestrator runs `python -m ai_router.start_session <slug>`
   (Full) or hand-writes the same shape to `session-state.json`
   (Lightweight). Same fields, same invariants, different writer
   underneath.

7. **Fraction convention stays `sessionsCompleted / totalSessions`.**
   `1/4` means "one session fully closed, three remaining." UI
   localization can add a "Done" annotation (`1/4 Done`) if
   operator confusion warrants — but the math doesn't change.

8. **Failure mode: passive recovery.** A stranded session
   (`work_in_progress`, currentSession not in completedSessions[],
   no close event) is its own marker. The orchestrator resumes by
   re-reading state and continuing. No new daemon, no automatic
   sweeper for this case. The repair tool covers the manual
   forensic recovery.

---

## Architecture context

## Architecture

### Writers

```
                  ┌──────────────────────────────────┐
                  │ compute_effective_completed_     │
                  │ sessions(session_set_dir)        │
                  │  - reads completedSessions[]     │
                  │  - cross-references events       │
                  │    ledger (Full tier)            │
                  │  - last-resort legacy heuristics │
                  └──────────────┬───────────────────┘
                                 │ shared helper called by every boundary write
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
  start_session (CLI)     close_session (CLI)         --repair --apply
  Full tier writer        Full tier writer            healing path
                                                       (backfills
                                                        completedSessions[]
                                                        and missing
                                                        closeout events)
```

Lightweight tier: the orchestrator writes the same fields by hand,
per the protocol below. No router code runs.

### Readers

```
  Extension tree view → fileSystem.ts:readSessionSets()
       │
       ├─ canonical status via readStatus()        (existing)
       ├─ isMidSetComplete() guard                 (v0.13.11)
       ├─ completedSessions.length                 (primary count)
       ├─ events-ledger closeout count             (fallback, Full only)
       └─ state file totalSessions                 (last-resort fallback)

  NOT a count source:
   - activity-log.json unique sessionNumbers ❌
```

### The protocol (tier-symmetric)

**Session start** (orchestrator does this *before any work*):

| Field                    | Value at start                                     |
|--------------------------|----------------------------------------------------|
| `currentSession`         | next session number (max(completedSessions)+1 or 1)|
| `status`                 | `"in-progress"`                                    |
| `lifecycleState`         | `"work_in_progress"`                               |
| `startedAt`              | now (only if previously null)                      |
| `completedAt`            | null (cleared if was set)                          |
| `verificationVerdict`    | null (cleared if was set)                          |
| `completedSessions[]`    | preserved from prior state                         |
| `orchestrator`           | refreshed for this session                         |
| **Events ledger** (Full) | append exactly one `work_started` for this session |
| **Activity log**         | nothing — first real step adds the first entry     |

**Session close** (after verification, before notify):

| Field                    | Value at close (non-final)                | Value at close (final)            |
|--------------------------|-------------------------------------------|-----------------------------------|
| `completedSessions[]`    | append currentSession (sorted, unique)    | append currentSession (sorted, unique) |
| `currentSession`         | unchanged (= just-closed session)         | unchanged (= totalSessions)       |
| `status`                 | `"in-progress"`                           | `"complete"`                      |
| `lifecycleState`         | `"work_in_progress"`                      | `"closed"`                        |
| `completedAt`            | null                                      | now                               |
| `verificationVerdict`    | latest verdict (Full) / unchanged         | latest verdict (Full) / unchanged |
| **Events ledger** (Full) | `closeout_requested` + `closeout_succeeded` for currentSession | same                              |

The "final" branch is reached when, *after appending currentSession*,
`len(completedSessions) == totalSessions`. This is the only place
`status` flips to `complete` and `lifecycleState` flips to `closed`.

---

## Session 2 contract (what this session was supposed to deliver)

### Session 2 of 3: Extension reader changes
**Goal:** Make the tree view reflect the new invariant. Drop
activity-log as a count source. Add file watchers if missing.
Localize the fraction display.

**Steps:**
1. In `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`,
   remove the activity-log unique-sessionNumber path from
   `readSessionSets`. The count derivation order becomes:
   1. `completedSessions.length` (primary).
   2. Distinct `closeout_succeeded` session numbers from
      `session-events.jsonl` (Full tier fallback — new path; same
      logic the v0.13.11 `hasCloseoutEventForSession` helper uses,
      generalized to "count distinct sessions").
   3. State file `totalSessions` when `status === "complete"`
      (existing fallback).
   4. No more `currentSession - 1` fallback — the helper from
      Session 1 makes this unnecessary on the writer side, and
      removing the reader-side fallback eliminates an off-by-one
      class.
2. Verify `extension.ts` activation registers a
   `vscode.workspace.createFileSystemWatcher` for
   `**/session-state.json`, `**/session-events.jsonl`, and
   `**/CANCELLED.md` that fires `SessionSetsProvider.refresh()`.
   Add if missing; verify event coverage if present.
3. Update `progressText` in
   `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`:
   - For `state === "done"` rows: append " Done" annotation
     (`4/4 Done`).
   - For in-flight rows where `currentSession` is set and
     `currentSession not in completedSessions[]` (the helper's "in
     flight" predicate, computed in TypeScript): annotate the
     fraction (`0/4 · session 1 in flight`). This is the cosmetic
     fix for "0/4 looks stale during early session 1."
4. Tests:
   - Update existing fileSystem test fixtures that relied on
     activity-log counts to assert the new ordering.
   - Add a regression test: a set with no `completedSessions[]` but
     with `closeout_succeeded` events for sessions 1-3 reads as
     `sessionsCompleted: 3` (verifies the events-ledger fallback).
   - Add a UI-text regression test on `progressText` for the
     in-flight annotation and Done annotation.
5. Bump extension to v0.13.12 (package.json + package-lock.json +
   CHANGELOG.md + CLAUDE.md).
6. Compile + smoke-test against a real session set.

**Creates:** none

**Touches:** `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`,
`tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`,
`tools/dabbler-ai-orchestration/src/extension.ts` (if watcher add
needed), `tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts`,
`tools/dabbler-ai-orchestration/package.json`,
`tools/dabbler-ai-orchestration/package-lock.json`,
`tools/dabbler-ai-orchestration/CHANGELOG.md`, `CLAUDE.md`

**Ends with:** Extension reflects the new invariant; tree view
auto-refreshes on any state-file change; in-flight rows visibly
distinguish "session 1 in flight" from "no work started yet."

**Progress keys:** `session-002/drop-activitylog-count`,
`session-002/file-watcher-verify`, `session-002/progress-text`,
`session-002/tests`, `session-002/version-bump`,
`session-002/smoke-test`, `session-002/verification`

---

---

## Files in this session's commit


### `tools/dabbler-ai-orchestration/src/types.ts` — TypeScript types — LiveSession.completedSessions added

```
export type SessionState = "done" | "in-progress" | "not-started" | "cancelled";

export type OutsourceMode = "first" | "last";

export interface SessionSetConfig {
  requiresUAT: boolean;
  requiresE2E: boolean;
  uatScope: string;
  outsourceMode: OutsourceMode | null;
}

export interface UatSummary {
  totalItems: number;
  pendingItems: number;
  e2eRefs: string[];
}

export interface OrchestratorInfo {
  engine?: string;
  model?: string;
  effort?: string;
}

export interface LiveSession {
  currentSession: number | null;
  status: string | null;
  orchestrator: OrchestratorInfo | null;
  startedAt: string | null;
  completedAt: string | null;
  verificationVerdict: string | null;
  // Set 9 Session 3 (D-2 hard-scoping): true when the close-out path
  // was bypassed via ``--force`` / ``mark_session_complete(force=True)``.
  // Surfaced as a ``[FORCED]`` badge on the Session Set Explorer row so
  // reviewers can spot emergency-bypass close-outs at a glance. Absent
  // or false on every snapshot written by a normal close-out.
  forceClosed: boolean | null;
  // Set 022 Session 2: completedSessions[] is the authoritative
  // progress ledger under the state-first lifecycle protocol. Surfaced
  // here so the tree-view can compute the "currentSession is in flight"
  // predicate (currentSession not in completedSessions[]) without
  // re-reading the state file. Null when the snapshot pre-dates the
  // array (legacy sets); empty array when the protocol has been
  // applied but no session has closed yet.
  completedSessions: number[] | null;
}

export interface SessionSet {
  name: string;
  dir: string;
  specPath: string;
  activityPath: string;
  changeLogPath: string;
  statePath: string;
  aiAssignmentPath: string;
  uatChecklistPath: string;
  state: SessionState;
  totalSessions: number | null;
  sessionsCompleted: number;
  lastTouched: string | null;
  liveSession: LiveSession | null;
  config: SessionSetConfig;
  uatSummary: UatSummary | null;
  root: string;
}

export interface MetricsEntry {
  session_set: string;
  session_num: number;
  model: string;
  effort: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  timestamp: string;
}

export interface CostSummary {
  totalCost: number;
  bySessionSet: Record<string, { sessions: number; cost: number; lastRun: string }>;
  byModel: Record<string, number>;
  dailyCosts: Array<{ date: string; cost: number }>;
}

```


### `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts` — Reader: count derivation rewrite + countDistinctCloseoutSessions helper

```
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
        if (totalSessions === null && typeof sd.totalSessions === "number") {
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

```


### `tools/dabbler-ai-orchestration/src/extension.ts` — File watcher: pattern extended to include session-events.jsonl + CANCELLED.md

```
import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { SessionSetsProvider } from "./providers/SessionSetsProvider";
import { ProviderQueuesProvider } from "./providers/ProviderQueuesProvider";
import {
  ProviderHeartbeatsProvider,
  HEARTBEAT_FOOTER,
} from "./providers/ProviderHeartbeatsProvider";
import { discoverRoots, readAllSessionSets } from "./utils/fileSystem";
import { registerOpenFileCommands } from "./commands/openFile";
import { registerCopyCommands } from "./commands/copyCommand";
import { registerGitScaffoldCommand } from "./commands/gitScaffold";
import { registerCopyAdoptionBootstrapPromptCommand } from "./commands/copyAdoptionBootstrapPrompt";
import { registerTroubleshootCommand } from "./commands/troubleshoot";
import { registerQueueActionCommands } from "./commands/queueActions";
import { registerCancelLifecycleCommands } from "./commands/cancelLifecycleCommands";
import { registerInstallAiRouterCommands } from "./commands/installAiRouterCommands";
import { registerWizardCommands } from "./wizard/WizardPanel";
import { registerCostDashboardCommand } from "./dashboard/CostDashboard";
import { SessionSet } from "./types";

const SESSION_SETS_REL = path.join("docs", "session-sets");

function evaluateSupportContextKeys(allSets: SessionSet[]): void {
  const cfg = vscode.workspace.getConfiguration("dabblerSessionSets");
  const uatPref = cfg.get<string>("uatSupport.enabled", "auto");
  const e2ePref = cfg.get<string>("e2eSupport.enabled", "auto");

  const anyUat = allSets.some((s) => s.config?.requiresUAT);
  const anyE2e = allSets.some((s) => s.config?.requiresE2E);

  const uatActive = uatPref === "always" || (uatPref === "auto" && anyUat);
  const e2eActive = e2ePref === "always" || (e2ePref === "auto" && anyE2e);

  vscode.commands.executeCommand("setContext", "dabblerSessionSets.uatSupportActive", uatActive);
  vscode.commands.executeCommand("setContext", "dabblerSessionSets.e2eSupportActive", e2eActive);
}

export function activate(context: vscode.ExtensionContext): void {
  if (!vscode.workspace.workspaceFolders?.length) return;

  const provider = new SessionSetsProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("dabblerSessionSets", provider)
  );

  const evaluateContextKeys = () => {
    evaluateSupportContextKeys(provider._cache ?? readAllSessionSets());
  };

  const originalRefresh = provider.refresh.bind(provider);
  provider.refresh = () => {
    originalRefresh();
    setImmediate(evaluateContextKeys);
  };
  // v0.13.2: defensive — `evaluateContextKeys()` calls `readAllSessionSets()`
  // which iterates every session set's session-state.json. A single
  // malformed file would otherwise propagate up and abort activation
  // before any feature commands register. Catch + log instead so the
  // tree may render with stale context-key flags (UAT / E2E menu
  // visibility) but the rest of the extension stays alive.
  try {
    evaluateContextKeys();
  } catch (err) {
    console.error(
      "[dabbler-ai-orchestration] activation: evaluateContextKeys() threw — " +
        "context keys (UAT/E2E support flags) may be stale, but command " +
        "registration continues. Investigate via the dev console stack trace.",
      err,
    );
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (
        e.affectsConfiguration("dabblerSessionSets.uatSupport.enabled") ||
        e.affectsConfiguration("dabblerSessionSets.e2eSupport.enabled")
      ) {
        evaluateContextKeys();
      }
    })
  );

  // --- File watchers ---
  let watcherSubs: vscode.Disposable[] = [];
  let boundRoots = new Set<string>();

  function bindWatchers(): void {
    const roots = discoverRoots();
    const want = new Set(roots.map((r) => r.toLowerCase()));
    if (
      want.size === boundRoots.size &&
      [...want].every((r) => boundRoots.has(r))
    ) {
      return;
    }
    for (const sub of watcherSubs) sub.dispose();
    watcherSubs = [];
    boundRoots = want;
    for (const root of roots) {
      const sessionSetsAbs = path.join(root, SESSION_SETS_REL);
      // Set 022 Session 2 added `session-events.jsonl` and
      // `CANCELLED.md` to the watch list. The events ledger drives
      // the new Full-tier sessionsCompleted fallback when
      // `completedSessions[]` is absent, and the boundary writes from
      // `start_session` / `close_session` only touch the ledger and
      // the state file (not the activity-log) — without the ledger in
      // the watch list, a Not Started → In Progress bucket-flip on
      // session 1 of a fresh set would wait for the 30s poll loop
      // instead of triggering the immediate watcher debounce.
      // `CANCELLED.md` is the canonical signal for the cancelled
      // tree-state (Set 8 spec § Detection rules); the cancelled
      // commands write it directly, so the watcher must see it to
      // refresh the bucket the moment a set is cancelled / restored.
      const pattern = new vscode.RelativePattern(
        sessionSetsAbs,
        "**/{spec.md,session-state.json,session-events.jsonl,activity-log.json,change-log.md,CANCELLED.md,*-uat-checklist.json}"
      );
      const watcher = vscode.workspace.createFileSystemWatcher(pattern);
      const onEvent = () => provider.refresh();
      watcher.onDidCreate(onEvent);
      watcher.onDidDelete(onEvent);
      watcher.onDidChange(onEvent);
      watcherSubs.push(watcher);
      context.subscriptions.push(watcher);
    }
  }

  const refreshAll = () => {
    bindWatchers();
    provider.refresh();
  };

  // Defensive: bindWatchers iterates roots and creates filesystem
  // watchers; a thrown error from createFileSystemWatcher (e.g., a
  // permission issue on a workspace folder) shouldn't kill activation.
  try {
    bindWatchers();
  } catch (err) {
    console.error(
      "[dabbler-ai-orchestration] activation: bindWatchers() threw — " +
        "live tree-refresh on file changes may not work, but command " +
        "registration continues. Manual refresh via " +
        "`Dabbler: Refresh Session Sets` still functions.",
      err,
    );
  }
  context.subscriptions.push(vscode.workspace.onDidChangeWorkspaceFolders(refreshAll));
  const pollHandle = setInterval(refreshAll, 30000);
  context.subscriptions.push({ dispose: () => clearInterval(pollHandle) });

  context.subscriptions.push(
    vscode.commands.registerCommand("dabblerSessionSets.refresh", refreshAll)
  );

  // --- Provider Queues view ---
  const queuesProvider = new ProviderQueuesProvider({
    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
  });
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("dabblerProviderQueues", queuesProvider),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("dabblerProviderQueues.refresh", () =>
      queuesProvider.refresh(),
    ),
  );

  // Auto-refresh; settings-configurable, 0 disables.
  let queuesPoll: NodeJS.Timeout | undefined;
  const rebindQueuesPoll = () => {
    if (queuesPoll) clearInterval(queuesPoll);
    const seconds = vscode.workspace
      .getConfiguration("dabblerProviderQueues")
      .get<number>("autoRefreshSeconds", 15);
    if (seconds > 0) {
      queuesPoll = setInterval(() => queuesProvider.refresh(), seconds * 1000);
    } else {
      queuesPoll = undefined;
    }
  };
  rebindQueuesPoll();
  context.subscriptions.push({
    dispose: () => {
      if (queuesPoll) clearInterval(queuesPoll);
    },
  });
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("dabblerProviderQueues.autoRefreshSeconds")) {
        rebindQueuesPoll();
      }
    }),
  );

  registerQueueActionCommands(context, {
    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
    refreshView: () => queuesProvider.refresh(),
  });

  // --- Provider Heartbeats view ---
  const heartbeatsProvider = new ProviderHeartbeatsProvider({
    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
  });
  // The footer makes the observational framing impossible to miss; it
  // sits in the view header at all times so a user can't skim past it.
  const heartbeatsTreeView = vscode.window.createTreeView("dabblerProviderHeartbeats", {
    treeDataProvider: heartbeatsProvider,
    showCollapseAll: false,
  });
  heartbeatsTreeView.description = HEARTBEAT_FOOTER;
  context.subscriptions.push(heartbeatsTreeView);
  context.subscriptions.push(
    vscode.commands.registerCommand("dabblerProviderHeartbeats.refresh", () =>
      heartbeatsProvider.refresh(),
    ),
  );

  let heartbeatsPoll: NodeJS.Timeout | undefined;
  const rebindHeartbeatsPoll = () => {
    if (heartbeatsPoll) clearInterval(heartbeatsPoll);
    const seconds = vscode.workspace
      .getConfiguration("dabblerProviderHeartbeats")
      .get<number>("autoRefreshSeconds", 15);
    if (seconds > 0) {
      heartbeatsPoll = setInterval(
        () => heartbeatsProvider.refresh(),
        seconds * 1000,
      );
    } else {
      heartbeatsPoll = undefined;
    }
  };
  rebindHeartbeatsPoll();
  context.subscriptions.push({
    dispose: () => {
      if (heartbeatsPoll) clearInterval(heartbeatsPoll);
    },
  });
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      // Only the polling-interval setting actually requires rebinding the
      // setInterval; the other two only affect what the next refresh pulls.
      const affectsTiming = e.affectsConfiguration(
        "dabblerProviderHeartbeats.autoRefreshSeconds",
      );
      const affectsContent =
        e.affectsConfiguration("dabblerProviderHeartbeats.lookbackMinutes") ||
        e.affectsConfiguration("dabblerProviderHeartbeats.silentWarningMinutes");
      if (affectsTiming) rebindHeartbeatsPoll();
      if (affectsTiming || affectsContent) heartbeatsProvider.refresh();
    }),
  );

  // --- Register feature command groups ---
  //
  // Each register*Commands call is wrapped in its own try/catch so a
  // throw in one group does not silently skip the registrations that
  // follow. v0.13.1 shipped without these wrappers; in dabbler-platform
  // workspaces some users hit "command 'dabbler.showCostDashboard' not
  // found" because an earlier register call threw and the cascade
  // skipped the cost-dashboard + wizard + install-ai-router
  // registrations. Defensive logging via console.error means a future
  // similar failure surfaces in `Help → Toggle Developer Tools →
  // Console` with the exact group name, instead of presenting as
  // an opaque command-not-found at click time.
  const safeRegister = (name: string, fn: () => void): void => {
    try {
      fn();
    } catch (err) {
      console.error(
        `[dabbler-ai-orchestration] activation failed in ${name} — ` +
          `subsequent commands still attempt to register; the failed ` +
          `group's commands will not be available until the underlying ` +
          `error is fixed.`,
        err,
      );
    }
  };

  safeRegister("registerOpenFileCommands", () => registerOpenFileCommands(context));
  safeRegister("registerCopyCommands", () => registerCopyCommands(context));
  safeRegister("registerGitScaffoldCommand", () => registerGitScaffoldCommand(context));
  safeRegister("registerCopyAdoptionBootstrapPromptCommand", () =>
    registerCopyAdoptionBootstrapPromptCommand(context),
  );
  safeRegister("registerTroubleshootCommand", () => registerTroubleshootCommand(context));
  safeRegister("registerWizardCommands", () => registerWizardCommands(context));
  safeRegister("registerCostDashboardCommand", () => registerCostDashboardCommand(context));
  safeRegister("registerCancelLifecycleCommands", () =>
    registerCancelLifecycleCommands(context, { refreshView: refreshAll }),
  );
  safeRegister("registerInstallAiRouterCommands", () =>
    registerInstallAiRouterCommands(context),
  );

  // Show onboarding on first activation in a workspace with no session sets
  const hasSeenOnboarding = context.workspaceState.get<boolean>("hasSeenOnboarding", false);
  if (!hasSeenOnboarding) {
    const roots = discoverRoots();
    const hasSessionSets = roots.some((r) => {
      try {
        return fs.existsSync(path.join(r, SESSION_SETS_REL));
      } catch {
        return false;
      }
    });
    if (!hasSessionSets) {
      context.workspaceState.update("hasSeenOnboarding", true);
      vscode.commands.executeCommand("dabbler.getStarted");
    }
  }
}

export function deactivate(): void {}

```


### `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts` — progressText + isCurrentSessionInFlight predicate

```
import * as vscode from "vscode";
import * as path from "path";
import { readAllSessionSets, discoverRoots } from "../utils/fileSystem";
import { SessionSet, SessionState } from "../types";

const ICON_FILES: Record<SessionState, string> = {
  done: "done.svg",
  "in-progress": "in-progress.svg",
  "not-started": "not-started.svg",
  cancelled: "cancelled.svg",
};

function iconUriFor(
  extensionUri: vscode.Uri,
  state: SessionState
): vscode.Uri | undefined {
  const file = ICON_FILES[state];
  return file ? vscode.Uri.joinPath(extensionUri, "media", file) : undefined;
}

// Set 022 Session 2: the "currentSession is in flight" predicate from
// the lifecycle spec's state invariant. Returns true when the snapshot
// declares a current session and that session is not yet in
// `completedSessions[]` — i.e., session N has started but not closed.
// Requires the array to be present; legacy snapshots without it return
// false so a fresh-set Not Started row doesn't gain a stray
// annotation. Exported for unit-test reuse.
export function isCurrentSessionInFlight(set: SessionSet): boolean {
  const ls = set.liveSession;
  if (!ls) return false;
  if (typeof ls.currentSession !== "number") return false;
  if (!Array.isArray(ls.completedSessions)) return false;
  return !ls.completedSessions.includes(ls.currentSession);
}

export function progressText(set: SessionSet): string {
  // Always show X/total. The earlier "X/X" shape on done sets assumed
  // completed === total, which masks bugs like a SET-level flip to
  // "complete" that fires before all sessions ran. Truthful display
  // surfaces the discrepancy at a glance.
  //
  // Set 022 Session 2 added two annotations to disambiguate the row:
  //   * `N/N Done` on done rows — operator-facing "yes this really
  //     reached terminal state" cue. Distinguishes a healthy final
  //     close from a stale `N/N` snapshot that's about to be
  //     downgraded by isMidSetComplete.
  //   * `0/N · session 1 in flight` on rows where session N has
  //     started but not yet closed. Removes the operator confusion
  //     of "I started session 1 — why does it still say 0/4?"
  //     Both lifecycle endpoints (0/N at start of session 1; N/N
  //     between session N's start and its close on the final
  //     session) used to be indistinguishable from their "no work
  //     started yet" / "set is done" siblings.
  const base = set.totalSessions && set.totalSessions > 0
    ? `${set.sessionsCompleted}/${set.totalSessions}`
    : set.sessionsCompleted > 0
      ? `${set.sessionsCompleted} done`
      : "";

  if (set.state === "done" && base) {
    return `${base} Done`;
  }
  if (set.state === "in-progress" && isCurrentSessionInFlight(set)) {
    const n = set.liveSession?.currentSession;
    const annotation = `session ${n} in flight`;
    return base ? `${base} · ${annotation}` : annotation;
  }
  return base;
}

function touchedDate(set: SessionSet): string {
  if (!set.lastTouched) return "";
  return new Date(set.lastTouched).toLocaleDateString("en-CA");
}

function uatBadge(set: SessionSet): string {
  if (!set.config?.requiresUAT || !set.uatSummary) return "";
  if (set.uatSummary.pendingItems > 0) return `[UAT ${set.uatSummary.pendingItems}]`;
  if (set.uatSummary.totalItems > 0) return "[UAT done]";
  return "";
}

// Set 9 Session 3 (D-2 hard-scoping of ``--force``): the badge surfaces
// the rare case where a session set was closed via the hard-scoped
// ``--force`` bypass instead of the deterministic gate. The flag is
// written by ``_flip_state_to_closed(forced=True)`` in
// ``ai_router/session_state.py``; absent or false on every snapshot
// written by a normal close-out, so the badge never appears for
// healthy sets.
export function forceClosedBadge(set: SessionSet): string {
  return set.liveSession?.forceClosed === true ? "[FORCED]" : "";
}

// Outsource-first vs. outsource-last is a routing choice that lives in
// each spec.md's `Session Set Configuration` block. v0.13.1 removed the
// always-visible badge text — when 99% of sets use the default
// `outsourceMode: first`, the badge becomes visual noise that doesn't
// differentiate anything. The mode still surfaces in the row tooltip
// (`configTooltipLines` adds `Mode: outsource-<x>` on hover) for
// diagnostic purposes, and the AI router still consumes the field —
// only the badge text was removed. Function kept (returning empty) so
// existing imports / tests don't need to change shape.
export function modeBadge(_set: SessionSet): string {
  return "";
}

function liveSessionTooltipLines(set: SessionSet): string[] {
  if (!set.liveSession) return [];
  const ls = set.liveSession;
  const lines: string[] = [];
  if (typeof ls.currentSession === "number") {
    const total = set.totalSessions ? `/${set.totalSessions}` : "";
    const status = ls.status ? ` (${ls.status})` : "";
    lines.push(`Session: ${ls.currentSession}${total}${status}`);
  }
  if (ls.orchestrator) {
    const o = ls.orchestrator;
    const parts = [o.engine, o.model].filter(Boolean).join(" · ");
    const effort = o.effort && o.effort !== "unknown" ? ` @ effort=${o.effort}` : "";
    if (parts) lines.push(`Orchestrator: ${parts}${effort}`);
  }
  if (ls.verificationVerdict) {
    lines.push(`Verifier: ${ls.verificationVerdict}`);
  }
  if (ls.forceClosed === true) {
    lines.push(
      "Force-closed: gate bypassed via --force (incident recovery). " +
        "See closeout_force_used in session-events.jsonl for the operator's reason."
    );
  }
  return lines;
}

function configTooltipLines(set: SessionSet): string[] {
  if (!set.config) return [];
  const flags: string[] = [];
  if (set.config.requiresUAT) flags.push("UAT");
  if (set.config.requiresE2E) flags.push("E2E");
  const lines: string[] = [];
  lines.push(`Gates: ${flags.length ? flags.join(" + ") : "none"}`);
  if (set.config.outsourceMode) {
    lines.push(`Mode: outsource-${set.config.outsourceMode}`);
  }
  if (set.config.requiresUAT && set.uatSummary) {
    const u = set.uatSummary;
    if (u.totalItems > 0) {
      lines.push(`UAT items: ${u.pendingItems} pending / ${u.totalItems} total`);
    } else {
      lines.push("UAT checklist: not yet authored");
    }
  }
  return lines;
}

function folderTooltip(set: SessionSet): string {
  const roots = discoverRoots();
  const rel = path.relative(set.root, set.dir);
  return roots.length > 1 ? `${path.basename(set.root)} / ${rel}` : rel;
}

function contextValueFor(set: SessionSet): string {
  const parts = [`sessionSet:${set.state}`];
  if (set.config?.requiresUAT) parts.push("uat");
  if (set.config?.requiresE2E) parts.push("e2e");
  return parts.join(":");
}

interface GroupItem extends vscode.TreeItem {
  contextValue: "group";
  groupKey: SessionState;
}

interface SetItem extends vscode.TreeItem {
  set: SessionSet;
}

export class SessionSetsProvider
  implements vscode.TreeDataProvider<vscode.TreeItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    vscode.TreeItem | undefined | null | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  _cache: SessionSet[] | null = null;

  constructor(private readonly extensionUri: vscode.Uri) {}

  refresh(): void {
    this._cache = null;
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: vscode.TreeItem): vscode.TreeItem[] {
    if (!vscode.workspace.workspaceFolders?.length) return [];

    if (!this._cache) {
      this._cache = readAllSessionSets();
    }
    const all = this._cache;

    if (!element) {
      // v0.13.1: when the workspace has no session sets at all, return an
      // empty array so VS Code renders the `viewsWelcome` content
      // (configured in package.json under `contributes.viewsWelcome`).
      // The welcome content shows a Copy-adoption-bootstrap-prompt link
      // and a Get Started pointer — the discoverable starting point for
      // first-time users sits at the empty state itself rather than
      // hiding behind context-menu actions on rows that don't exist
      // yet. Once any session set exists in the workspace, the groups
      // below render and the welcome content suppresses automatically.
      if (all.length === 0) {
        return [];
      }
      const inProgress = all.filter((s) => s.state === "in-progress");
      const notStarted = all.filter((s) => s.state === "not-started");
      const done = all.filter((s) => s.state === "done");
      const cancelled = all.filter((s) => s.state === "cancelled");
      const groups: GroupItem[] = [
        this.makeGroup("In Progress", "in-progress", inProgress.length),
        this.makeGroup("Not Started", "not-started", notStarted.length),
        this.makeGroup("Done", "done", done.length),
      ];
      // Set 8: the Cancelled group only renders when ≥ 1 cancelled set
      // exists (parallels the existing spec rule for not-emitting empty
      // groups noted in spec.md scope). A repo that never cancels a set
      // should not see the group at all.
      if (cancelled.length > 0) {
        groups.push(this.makeGroup("Cancelled", "cancelled", cancelled.length));
      }
      return groups;
    }

    const group = element as GroupItem;
    if (group.contextValue === "group") {
      const subset = all.filter((s) => s.state === group.groupKey);
      if (
        group.groupKey === "in-progress" ||
        group.groupKey === "done" ||
        group.groupKey === "cancelled"
      ) {
        subset.sort((a, b) =>
          (b.lastTouched || "").localeCompare(a.lastTouched || "")
        );
      } else {
        subset.sort((a, b) => a.name.localeCompare(b.name));
      }
      return subset.map((s) => this.makeSetItem(s));
    }

    return [];
  }

  private makeGroup(label: string, groupKey: SessionState, count: number): GroupItem {
    const item = new vscode.TreeItem(
      `${label}  (${count})`,
      count > 0
        ? vscode.TreeItemCollapsibleState.Expanded
        : vscode.TreeItemCollapsibleState.Collapsed
    ) as GroupItem;
    item.iconPath = iconUriFor(this.extensionUri, groupKey);
    item.contextValue = "group";
    item.groupKey = groupKey;
    return item;
  }

  private makeSetItem(set: SessionSet): SetItem {
    const item = new vscode.TreeItem(
      set.name,
      vscode.TreeItemCollapsibleState.None
    ) as SetItem;
    const bits = [
      progressText(set),
      touchedDate(set),
      modeBadge(set),
      uatBadge(set),
      forceClosedBadge(set),
    ].filter(Boolean);
    item.description = bits.join("  ·  ");
    item.tooltip = new vscode.MarkdownString(
      [
        `**${set.name}**`,
        `State: ${set.state}`,
        bits.length ? `Progress: ${bits.join(" · ")}` : null,
        ...configTooltipLines(set),
        ...liveSessionTooltipLines(set),
        `Folder: \`${folderTooltip(set)}\``,
      ]
        .filter(Boolean)
        .join("\n\n")
    );
    item.contextValue = contextValueFor(set);
    item.set = set;
    item.iconPath = iconUriFor(this.extensionUri, set.state);
    item.command = {
      command: "dabblerSessionSets.openSpec",
      title: "Open Spec",
      arguments: [item],
    };
    return item;
  }
}

```


### `tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts` — Reader regression tests

```
import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  countDistinctCloseoutSessions,
  parseSessionSetConfig,
  parseUatChecklist,
  readSessionSets,
} from "../../utils/fileSystem";

function makeTmpDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "dabbler-test-"));
}

suite("fileSystem — parseSessionSetConfig", () => {
  test("returns safe defaults when spec is missing", () => {
    const cfg = parseSessionSetConfig("/nonexistent/spec.md");
    assert.strictEqual(cfg.requiresUAT, false);
    assert.strictEqual(cfg.requiresE2E, false);
    assert.strictEqual(cfg.uatScope, "none");
  });

  test("parses requiresUAT and requiresE2E from yaml block", () => {
    const dir = makeTmpDir();
    const specPath = path.join(dir, "spec.md");
    fs.writeFileSync(specPath, `## Session Set Configuration\n\`\`\`yaml\nrequiresUAT: true\nrequiresE2E: false\n\`\`\``);
    const cfg = parseSessionSetConfig(specPath);
    assert.strictEqual(cfg.requiresUAT, true);
    assert.strictEqual(cfg.requiresE2E, false);
    fs.rmSync(dir, { recursive: true });
  });

  test("falls back to scanning plain text when no yaml block", () => {
    const dir = makeTmpDir();
    const specPath = path.join(dir, "spec.md");
    fs.writeFileSync(specPath, "# My Spec\n\nrequiresUAT: true\n");
    const cfg = parseSessionSetConfig(specPath);
    assert.strictEqual(cfg.requiresUAT, true);
    fs.rmSync(dir, { recursive: true });
  });

  // Regression test for Set 015 Session 3 (2026-05-06): platform specs
  // that put the config yaml block under a non-canonical heading like
  // `## UAT scope` AND have enough upstream prose to push the yaml past
  // 4000 bytes were silently treated as `requiresUAT: false`. The parser
  // now scans the whole file when the canonical heading is absent.
  test("detects requiresUAT in yaml block past 4000 bytes when canonical heading absent", () => {
    const dir = makeTmpDir();
    const specPath = path.join(dir, "spec.md");
    const padding = "x".repeat(4500);  // push the yaml block past the old cutoff
    const content = `# Some Spec\n\n${padding}\n\n## UAT scope\n\n\`\`\`yaml\nrequiresUAT: true\nrequiresE2E: false\nuatScope: full\n\`\`\`\n`;
    fs.writeFileSync(specPath, content);
    const cfg = parseSessionSetConfig(specPath);
    assert.strictEqual(cfg.requiresUAT, true);
    assert.strictEqual(cfg.requiresE2E, false);
    assert.strictEqual(cfg.uatScope, "full");
    fs.rmSync(dir, { recursive: true });
  });

  // Negative case: spec that doesn't declare requiresUAT anywhere remains
  // false. Guards against an over-broad fix that might match prose
  // mentions of "requiresUAT" that aren't on their own line.
  test("returns false when requiresUAT is not declared anywhere", () => {
    const dir = makeTmpDir();
    const specPath = path.join(dir, "spec.md");
    const content = `# Some Spec\n\nThis spec does not declare requiresUAT or requiresE2E.\nIt mentions them in prose but never on a standalone line.\n`;
    fs.writeFileSync(specPath, content);
    const cfg = parseSessionSetConfig(specPath);
    assert.strictEqual(cfg.requiresUAT, false);
    assert.strictEqual(cfg.requiresE2E, false);
    fs.rmSync(dir, { recursive: true });
  });
});

suite("fileSystem — parseUatChecklist", () => {
  test("returns null when file is missing", () => {
    const result = parseUatChecklist("/nonexistent/checklist.json");
    assert.strictEqual(result, null);
  });

  test("counts pending items", () => {
    const dir = makeTmpDir();
    const checklistPath = path.join(dir, "checklist.json");
    fs.writeFileSync(checklistPath, JSON.stringify({
      items: [
        { Result: "" },
        { Result: "pass" },
        { Result: "pending" },
      ],
    }));
    const result = parseUatChecklist(checklistPath);
    assert.ok(result);
    assert.strictEqual(result.pendingItems, 2);
    assert.strictEqual(result.totalItems, 3);
    fs.rmSync(dir, { recursive: true });
  });
});

suite("fileSystem — readSessionSets", () => {
  test("returns empty array when docs/session-sets does not exist", () => {
    const sets = readSessionSets("/nonexistent");
    assert.deepStrictEqual(sets, []);
  });

  // Set 7: state is read directly from session-state.json's `status`,
  // not derived from file presence. Each fixture writes the canonical
  // not-started / in-progress / complete status string and asserts the
  // tree-view label maps it correctly. The "spec.md only" fixture
  // exercises the lazy-synth fallback (readStatus writes the
  // not-started shape on the fly when the file is absent).

  test("reads a not-started set via lazy-synth (spec.md only)", () => {
    const dir = makeTmpDir();
    const slug = "my-feature";
    const setDir = path.join(dir, "docs", "session-sets", slug);
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# my-feature\n");
    const sets = readSessionSets(dir);
    assert.strictEqual(sets.length, 1);
    assert.strictEqual(sets[0].name, slug);
    assert.strictEqual(sets[0].state, "not-started");
    // Lazy-synth wrote the file as a side effect of readStatus.
    assert.ok(fs.existsSync(path.join(setDir, "session-state.json")));
    fs.rmSync(dir, { recursive: true });
  });

  test("reads in-progress from session-state.json status", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "feature-a");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# feature-a\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({ schemaVersion: 2, status: "in-progress" })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "in-progress");
    fs.rmSync(dir, { recursive: true });
  });

  test("reads done from session-state.json status='complete'", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "feature-b");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# feature-b\n");
    fs.writeFileSync(path.join(setDir, "change-log.md"), "# Changes\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({ schemaVersion: 2, status: "complete" })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    fs.rmSync(dir, { recursive: true });
  });

  test("canonicalizes pre-Set-7 'completed' alias to done", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "feature-c");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# feature-c\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({ schemaVersion: 2, status: "completed" })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    fs.rmSync(dir, { recursive: true });
  });

  // Defensive: pre-0.2.1 ai_router flipped status to "complete" after
  // every session's close-out, not just the last. Stale snapshots and
  // consumer repos that haven't upgraded yet still produce that shape,
  // which would briefly render the set as Done between sessions. The
  // extension cross-checks currentSession vs totalSessions and treats
  // a mid-set "complete" as in-progress instead.
  test("status='complete' with currentSession < totalSessions reads as in-progress", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "mid-set-stale");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# mid-set-stale\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "complete",
        currentSession: 3,
        totalSessions: 5,
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "in-progress");
    fs.rmSync(dir, { recursive: true });
  });

  // Authoritative source for sessionsCompleted in schema v2:
  // `completedSessions` array. The earlier `currentSession - 1`
  // fallback was wrong whenever the latest session was itself
  // complete (off-by-one low). Lightweight-tier repos that
  // hand-maintain session-state.json rely on this field.
  test("sessionsCompleted reads completedSessions.length from state file", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "completed-array");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# completed-array\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "in-progress",
        currentSession: 3,
        totalSessions: 4,
        completedSessions: [1, 2, 3],
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].sessionsCompleted, 3);
    fs.rmSync(dir, { recursive: true });
  });

  test("status='complete' with no completedSessions array falls back to totalSessions", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "complete-no-array");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# complete-no-array\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "complete",
        currentSession: 4,
        totalSessions: 4,
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].sessionsCompleted, 4);
    fs.rmSync(dir, { recursive: true });
  });

  // Regression for ctelr-spec drift (2026-05-12): a Lightweight-tier
  // consumer hand-wrote `status: "completed"` (past participle) instead
  // of the canonical `"complete"`. readStatus() aliased it for bucketing
  // (so the set landed in Done), but the count-derivation branch used
  // raw `sd.status` and missed the alias, falling through to
  // currentSession-1 and displaying N-1/N. Using `state` (already
  // canonicalized via readStatus) keeps both reads in lockstep.
  test("status='completed' alias flips count to totalSessions, not currentSession-1", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "completed-alias");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# completed-alias\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "completed",
        currentSession: 3,
        totalSessions: 3,
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    assert.strictEqual(sets[0].sessionsCompleted, 3);
    fs.rmSync(dir, { recursive: true });
  });

  test("status='complete' with currentSession === totalSessions reads as done", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "real-done");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# real-done\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "complete",
        currentSession: 5,
        totalSessions: 5,
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    fs.rmSync(dir, { recursive: true });
  });

  // Regression for unified-master-details-composite drift (2026-05-12):
  // snapshot claimed `status: complete` with `verificationVerdict:
  // VERIFIED` at currentSession=5/totalSessions=5, yet
  // `session-events.jsonl` had `closeout_succeeded` events for sessions
  // 1-4 only — session 5 never actually closed. The pre-existing
  // currentSession<totalSessions guard didn't catch this (5 is not <5);
  // the set rendered as Done with no real evidence the final session
  // ran. The expanded guard cross-checks the events ledger: if the
  // ledger exists and has no closeout event for `currentSession`, the
  // snapshot drifted from the authoritative ledger and we downgrade
  // bucketing to in-progress.
  test("status='complete' with no closeout event for final session reads as in-progress", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "ledger-gap");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# ledger-gap\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "complete",
        currentSession: 5,
        totalSessions: 5,
        verificationVerdict: "VERIFIED",
      })
    );
    // Closeouts logged for sessions 1-4 only; session 5 never closed.
    const events = [
      { timestamp: "2026-05-12T00:41:53Z", session_number: 1, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T07:04:10Z", session_number: 2, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T08:26:28Z", session_number: 3, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T11:40:49Z", session_number: 4, event_type: "closeout_succeeded" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(path.join(setDir, "session-events.jsonl"), events);
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "in-progress");
    fs.rmSync(dir, { recursive: true });
  });

  // Sibling to the previous test: when the events ledger DOES record a
  // closeout for the final session, the bucketing is Done. Locks in
  // that the guard is reading the ledger for a real signal, not just
  // any presence of the file.
  test("status='complete' with closeout event for final session reads as done", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "ledger-complete");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# ledger-complete\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "complete",
        currentSession: 3,
        totalSessions: 3,
      })
    );
    const events = [
      { timestamp: "2026-05-12T01:00:00Z", session_number: 1, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T02:00:00Z", session_number: 2, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T03:00:00Z", session_number: 3, event_type: "closeout_succeeded" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(path.join(setDir, "session-events.jsonl"), events);
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    fs.rmSync(dir, { recursive: true });
  });

  // Set 7: the canonical contract is "status beats file presence."
  // These contradictory fixtures lock that in — without them, the old
  // file-presence implementation could still pass the basic in-progress
  // and done tests above (they have both the legacy presence signal AND
  // a matching status). Round-1 verifier flagged this gap.

  test("status='complete' beats activity-log.json presence", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "contradict-1");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# contradict-1\n");
    fs.writeFileSync(path.join(setDir, "activity-log.json"), JSON.stringify({ entries: [] }));
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({ schemaVersion: 2, status: "complete" })
    );
    const sets = readSessionSets(dir);
    // Old file-presence rule: change-log absent + activity-log present
    // = "in-progress". Set 7 rule: status overrides → "done".
    assert.strictEqual(sets[0].state, "done");
    fs.rmSync(dir, { recursive: true });
  });

  test("status='in-progress' beats change-log.md presence", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "contradict-2");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# contradict-2\n");
    fs.writeFileSync(path.join(setDir, "change-log.md"), "# Changes\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({ schemaVersion: 2, status: "in-progress" })
    );
    const sets = readSessionSets(dir);
    // Old file-presence rule: change-log present = "done". Set 7 rule:
    // status overrides → "in-progress". The contradiction itself is
    // unusual (it would mean a new session was opened after a previous
    // one's change-log was authored); this test locks in the precedence.
    assert.strictEqual(sets[0].state, "in-progress");
    fs.rmSync(dir, { recursive: true });
  });

  // Verifier round 2 regression: lazy-synth on a legacy folder with
  // change-log.md or activity-log.json but no session-state.json must
  // infer the right initial state from those files (not regress to
  // not-started). readStatus now routes the file-absent path through
  // ensureSessionStateFile, mirroring the Python helper.

  test("lazy-synth infers 'done' from legacy change-log.md presence", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "legacy-done");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# legacy-done\n");
    fs.writeFileSync(path.join(setDir, "change-log.md"), "# Changes\n");
    // Deliberately no session-state.json — exercises the lazy-synth path.
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "done");
    // Side effect: a state file was written with the inferred shape.
    const written = JSON.parse(
      fs.readFileSync(path.join(setDir, "session-state.json"), "utf8")
    );
    assert.strictEqual(written.status, "complete");
    assert.strictEqual(written.lifecycleState, "closed");
    fs.rmSync(dir, { recursive: true });
  });

  test("lazy-synth infers 'in-progress' from legacy activity-log.json", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "legacy-active");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# legacy-active\n");
    fs.writeFileSync(
      path.join(setDir, "activity-log.json"),
      JSON.stringify({
        entries: [{ sessionNumber: 1, dateTime: "2026-01-01T00:00:00-04:00" }],
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].state, "in-progress");
    const written = JSON.parse(
      fs.readFileSync(path.join(setDir, "session-state.json"), "utf8")
    );
    assert.strictEqual(written.status, "in-progress");
    assert.strictEqual(written.startedAt, "2026-01-01T00:00:00-04:00");
    fs.rmSync(dir, { recursive: true });
  });

  test("skips directories starting with underscore", () => {
    const dir = makeTmpDir();
    const archivedDir = path.join(dir, "docs", "session-sets", "_archived");
    fs.mkdirSync(archivedDir, { recursive: true });
    fs.writeFileSync(path.join(archivedDir, "spec.md"), "# archived\n");
    const sets = readSessionSets(dir);
    assert.strictEqual(sets.length, 0);
    fs.rmSync(dir, { recursive: true });
  });

  // Set 022 Session 2: the events ledger is the Full-tier fallback
  // for `sessionsCompleted` when `completedSessions[]` is absent. A
  // pre-Set-022 set whose snapshot hasn't been healed by a boundary
  // write yet should still render the correct fraction from the
  // ledger's closeout_succeeded events. Distinct session_numbers are
  // counted so a session with multiple closeout_succeeded events
  // (the dedupe path under register_session_start) doesn't inflate
  // the count.
  test("sessionsCompleted falls back to distinct closeout_succeeded events when completedSessions[] absent", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "ledger-fallback");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# ledger-fallback\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "in-progress",
        currentSession: 4,
        totalSessions: 5,
        // Note: no completedSessions array.
      })
    );
    const events = [
      { timestamp: "2026-05-12T01:00:00Z", session_number: 1, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T02:00:00Z", session_number: 2, event_type: "closeout_succeeded" },
      { timestamp: "2026-05-12T03:00:00Z", session_number: 3, event_type: "closeout_succeeded" },
      // Duplicate event for session 3 — must not inflate the count.
      { timestamp: "2026-05-12T03:01:00Z", session_number: 3, event_type: "closeout_succeeded" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(path.join(setDir, "session-events.jsonl"), events);
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].sessionsCompleted, 3);
    fs.rmSync(dir, { recursive: true });
  });

  // Set 022 Session 2: the `currentSession - 1` fallback was removed
  // because it produced off-by-one displays at both endpoints of the
  // session lifecycle. With it gone, an in-flight set that has neither
  // `completedSessions[]` nor a Full-tier events ledger renders as
  // `0/N` (truthful — we have no evidence any session closed). This
  // is the path Lightweight-tier sets that pre-date the Set 022
  // protocol fall through, and the schema doc now requires those sets
  // to hand-maintain `completedSessions[]`. Locking the new behavior
  // in: a fresh-shape set with currentSession=2 but no array and no
  // ledger no longer inflates to 1/4.
  test("sessionsCompleted is 0 (not currentSession-1) when no completedSessions[] and no ledger", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "no-array-no-ledger");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# no-array-no-ledger\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "in-progress",
        currentSession: 3,
        totalSessions: 4,
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].sessionsCompleted, 0);
    assert.strictEqual(sets[0].totalSessions, 4);
    fs.rmSync(dir, { recursive: true });
  });

  // Set 022 Session 2: confirm activity-log is no longer a count
  // source. A set whose activity-log records steps for sessions 1-3
  // (3 distinct sessionNumbers) but whose state file has empty
  // `completedSessions: []` should render `0/4`, not the old `3/4`
  // the activity-log path would have produced. The Lightweight-tier
  // contract is now: maintain `completedSessions[]` or accept a
  // truthful `0/N` display.
  test("sessionsCompleted is 0 when activity-log has entries but completedSessions[] is empty", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "activity-log-ignored");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# activity-log-ignored\n");
    fs.writeFileSync(
      path.join(setDir, "activity-log.json"),
      JSON.stringify({
        totalSessions: 4,
        entries: [
          { sessionNumber: 1, dateTime: "2026-05-12T01:00:00-04:00" },
          { sessionNumber: 2, dateTime: "2026-05-12T02:00:00-04:00" },
          { sessionNumber: 3, dateTime: "2026-05-12T03:00:00-04:00" },
        ],
      })
    );
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "in-progress",
        currentSession: 4,
        totalSessions: 4,
        completedSessions: [],
      })
    );
    const sets = readSessionSets(dir);
    assert.strictEqual(sets[0].sessionsCompleted, 0);
    assert.strictEqual(sets[0].totalSessions, 4);
    fs.rmSync(dir, { recursive: true });
  });

  // Set 022 Session 2: surface `completedSessions[]` through the
  // LiveSession model so the tree-view's in-flight predicate can
  // compute without re-reading the state file.
  test("liveSession.completedSessions is surfaced from the state snapshot", () => {
    const dir = makeTmpDir();
    const setDir = path.join(dir, "docs", "session-sets", "in-flight");
    fs.mkdirSync(setDir, { recursive: true });
    fs.writeFileSync(path.join(setDir, "spec.md"), "# in-flight\n");
    fs.writeFileSync(
      path.join(setDir, "session-state.json"),
      JSON.stringify({
        schemaVersion: 2,
        status: "in-progress",
        currentSession: 2,
        totalSessions: 3,
        completedSessions: [1],
      })
    );
    const sets = readSessionSets(dir);
    assert.deepStrictEqual(sets[0].liveSession?.completedSessions, [1]);
    assert.strictEqual(sets[0].liveSession?.currentSession, 2);
    fs.rmSync(dir, { recursive: true });
  });
});

suite("fileSystem — countDistinctCloseoutSessions", () => {
  // Set 022 Session 2: generalization of hasCloseoutEventForSession.
  // Treated as 0 for any read failure (missing file, malformed JSON,
  // permission error) so callers fall through to the next derivation
  // step rather than asserting "no sessions done" on garbled input.
  test("returns 0 when the events file is missing", () => {
    assert.strictEqual(
      countDistinctCloseoutSessions("/nonexistent/session-events.jsonl"),
      0,
    );
  });

  test("counts distinct closeout_succeeded session numbers", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const events = [
      { session_number: 1, event_type: "work_started" },
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 2, event_type: "work_started" },
      { session_number: 2, event_type: "closeout_succeeded" },
      // Non-closeout events with the same session_number must not count.
      { session_number: 3, event_type: "work_started" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(eventsPath, events);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });

  test("dedupes duplicate closeout_succeeded events for the same session", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const events = [
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 1, event_type: "closeout_succeeded" },
      { session_number: 2, event_type: "closeout_succeeded" },
    ].map((e) => JSON.stringify(e)).join("\n") + "\n";
    fs.writeFileSync(eventsPath, events);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });

  test("tolerates malformed lines in the append-only ledger", () => {
    const dir = makeTmpDir();
    const eventsPath = path.join(dir, "session-events.jsonl");
    const lines = [
      JSON.stringify({ session_number: 1, event_type: "closeout_succeeded" }),
      "not json",
      JSON.stringify({ session_number: 2, event_type: "closeout_succeeded" }),
    ].join("\n") + "\n";
    fs.writeFileSync(eventsPath, lines);
    assert.strictEqual(countDistinctCloseoutSessions(eventsPath), 2);
    fs.rmSync(dir, { recursive: true });
  });
});

```


### `tools/dabbler-ai-orchestration/src/test/suite/sessionSetsProvider.test.ts` — Provider unit tests (new file)

```
import * as assert from "assert";
import {
  isCurrentSessionInFlight,
  progressText,
} from "../../providers/SessionSetsProvider";
import { LiveSession, SessionSet } from "../../types";

function fakeLive(over: Partial<LiveSession> = {}): LiveSession {
  return {
    currentSession: null,
    status: null,
    orchestrator: null,
    startedAt: null,
    completedAt: null,
    verificationVerdict: null,
    forceClosed: null,
    completedSessions: null,
    ...over,
  };
}

function fakeSet(over: Partial<SessionSet> = {}): SessionSet {
  return {
    name: "x",
    dir: "/x",
    specPath: "/x/spec.md",
    activityPath: "/x/activity-log.json",
    changeLogPath: "/x/change-log.md",
    statePath: "/x/session-state.json",
    aiAssignmentPath: "/x/ai-assignment.md",
    uatChecklistPath: "/x/x-uat-checklist.json",
    state: "not-started",
    totalSessions: null,
    sessionsCompleted: 0,
    lastTouched: null,
    liveSession: null,
    config: {
      requiresUAT: false,
      requiresE2E: false,
      uatScope: "none",
      outsourceMode: "first",
    },
    uatSummary: null,
    root: "/x",
    ...over,
  };
}

suite("SessionSetsProvider — isCurrentSessionInFlight", () => {
  // Set 022 Session 2: the "currentSession in flight" predicate from
  // the state invariant — `currentSession not in completedSessions[]`
  // means session N has started but not closed. Drives the in-flight
  // progressText annotation; locked here so the predicate cannot
  // silently change shape.

  test("returns false when liveSession is null", () => {
    assert.strictEqual(isCurrentSessionInFlight(fakeSet({ liveSession: null })), false);
  });

  test("returns false when currentSession is null", () => {
    assert.strictEqual(
      isCurrentSessionInFlight(fakeSet({
        liveSession: fakeLive({ currentSession: null, completedSessions: [] }),
      })),
      false,
    );
  });

  test("returns false when completedSessions array is absent (legacy snapshot)", () => {
    // Legacy sets without the array shouldn't gain a stray annotation.
    assert.strictEqual(
      isCurrentSessionInFlight(fakeSet({
        liveSession: fakeLive({ currentSession: 1, completedSessions: null }),
      })),
      false,
    );
  });

  test("returns true when currentSession is not in completedSessions[]", () => {
    assert.strictEqual(
      isCurrentSessionInFlight(fakeSet({
        liveSession: fakeLive({ currentSession: 2, completedSessions: [1] }),
      })),
      true,
    );
  });

  test("returns true for session 1 of a fresh set (completedSessions: [])", () => {
    // The endpoint the Set 022 spec called out specifically: "0/4
    // stuck displayed while session 1 is in flight." With the array
    // present-but-empty, the predicate fires and progressText adds
    // the "session 1 in flight" annotation.
    assert.strictEqual(
      isCurrentSessionInFlight(fakeSet({
        liveSession: fakeLive({ currentSession: 1, completedSessions: [] }),
      })),
      true,
    );
  });

  test("returns false when currentSession is in completedSessions[] (between sessions)", () => {
    // currentSession == 1 and completedSessions == [1] is the
    // "session 1 just closed; session 2 hasn't started" interlude.
    // Spec invariant: status="in-progress" + currentSession in
    // completedSessions[] means between sessions, not in flight.
    assert.strictEqual(
      isCurrentSessionInFlight(fakeSet({
        liveSession: fakeLive({ currentSession: 1, completedSessions: [1] }),
      })),
      false,
    );
  });
});

suite("SessionSetsProvider — progressText", () => {
  // Set 022 Session 2: the two new annotations make the lifecycle
  // visible at a glance without operator hover.

  test("renders 'N/total' for an in-progress row between sessions (no annotation)", () => {
    // Just-closed session 1; session 2 not yet started.
    // completedSessions: [1], currentSession: 1 → between sessions.
    const text = progressText(fakeSet({
      state: "in-progress",
      sessionsCompleted: 1,
      totalSessions: 4,
      liveSession: fakeLive({ currentSession: 1, completedSessions: [1], status: "in-progress" }),
    }));
    assert.strictEqual(text, "1/4");
  });

  test("appends 'session N in flight' annotation when currentSession not in completedSessions[]", () => {
    const text = progressText(fakeSet({
      state: "in-progress",
      sessionsCompleted: 0,
      totalSessions: 4,
      liveSession: fakeLive({ currentSession: 1, completedSessions: [], status: "in-progress" }),
    }));
    assert.strictEqual(text, "0/4 · session 1 in flight");
  });

  test("appends 'session N in flight' on a mid-set in-flight row", () => {
    // Sessions 1-2 closed, session 3 in flight.
    const text = progressText(fakeSet({
      state: "in-progress",
      sessionsCompleted: 2,
      totalSessions: 4,
      liveSession: fakeLive({ currentSession: 3, completedSessions: [1, 2], status: "in-progress" }),
    }));
    assert.strictEqual(text, "2/4 · session 3 in flight");
  });

  test("appends 'Done' annotation on a done row", () => {
    const text = progressText(fakeSet({
      state: "done",
      sessionsCompleted: 4,
      totalSessions: 4,
      liveSession: fakeLive({
        currentSession: 4,
        completedSessions: [1, 2, 3, 4],
        status: "complete",
      }),
    }));
    assert.strictEqual(text, "4/4 Done");
  });

  test("not-started rows render as '0/N' with no annotation", () => {
    const text = progressText(fakeSet({
      state: "not-started",
      sessionsCompleted: 0,
      totalSessions: 4,
      liveSession: null,
    }));
    assert.strictEqual(text, "0/4");
  });

  test("renders empty string when totalSessions is missing and no progress", () => {
    const text = progressText(fakeSet({
      state: "not-started",
      sessionsCompleted: 0,
      totalSessions: null,
      liveSession: null,
    }));
    assert.strictEqual(text, "");
  });

  test("legacy in-flight row (no completedSessions[]) renders 'N/total' without annotation", () => {
    // Predicate guards against legacy snapshots: no completedSessions
    // array means no authoritative in-flight signal, so no annotation
    // is added. The base fraction still renders.
    const text = progressText(fakeSet({
      state: "in-progress",
      sessionsCompleted: 1,
      totalSessions: 3,
      liveSession: fakeLive({
        currentSession: 2,
        completedSessions: null,
        status: "in-progress",
      }),
    }));
    assert.strictEqual(text, "1/3");
  });
});

```


### `tools/dabbler-ai-orchestration/CHANGELOG.md` — v0.13.12 entry

```
# Changelog

All notable changes to Dabbler AI Orchestration are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.13.12] — 2026-05-15

### Changed
- **Tree-view bucketing and progress display follow the new state-first
  lifecycle protocol shipped in `ai_router 0.2.3` (Set 022 Session 1).**
  The Session Set Explorer reflects four behavior changes:

  1. **`completedSessions[]` is the primary count source.** Reader
     priority is now `completedSessions.length` → distinct
     `closeout_succeeded` session numbers in `session-events.jsonl`
     (new Full-tier fallback) → `totalSessions` when `state === "done"`.
     The pre-existing `currentSession - 1` fallback was removed; the
     writer protocol from Session 1 guarantees the array is present
     after the first boundary write, and the events-ledger fallback
     covers legacy sets that haven't been healed by their next
     boundary write yet. Removing the heuristic eliminates the
     off-by-one classes at both lifecycle endpoints (stuck `0/N`
     at start of session 1; stuck `N-1/N` while the final session is
     wrapping up).

  2. **`activity-log.json` is no longer a count source.** Schema-wise,
     it's a step log, not a progress ledger — and the activity log
     was producing inflated counts on Lightweight-tier sets that
     hand-maintained step entries but no `completedSessions[]`. The
     activity-log read is retained for the `totalSessions` field
     (which the schema places at the file's top level) and per-entry
     `dateTime` (which still informs the `lastTouched` display
     because step-level timestamps are more granular than the
     state-file's session-boundary timestamps while a session is
     mid-flight).

  3. **In-flight row annotation: `0/4 · session 1 in flight`.** A new
     `isCurrentSessionInFlight` predicate in
     `src/providers/SessionSetsProvider.ts` implements the spec
     invariant — `currentSession not in completedSessions[]` means
     session N has started but not closed. When that predicate fires,
     `progressText` appends the annotation so the row visibly
     distinguishes "session 1 in flight" from "no work started yet."
     The predicate requires `completedSessions[]` to be present;
     legacy snapshots without the array stay annotation-free.

  4. **Done row annotation: `4/4 Done`.** The trailing " Done" label
     on done rows distinguishes a healthy final close from a stale
     `N/N` snapshot that's about to be downgraded by
     `isMidSetComplete`. Done is now visibly Done.

- **File watcher coverage extended to `session-events.jsonl` and
  `CANCELLED.md`.** The new Full-tier sessionsCompleted fallback
  reads the events ledger directly, and the boundary writes from
  `start_session` / `close_session` only touch the ledger and the
  state file (not `activity-log.json`) — without the ledger in the
  watcher pattern, a Not Started → In Progress bucket-flip on
  session 1 of a fresh set would wait for the 30-second poll loop.
  `CANCELLED.md` is the canonical signal for the cancelled
  tree-state under Set 8's spec; the watcher now refreshes
  immediately when a cancel/restore command writes it.

- **`LiveSession.completedSessions` exposed through the type
  system.** The tree-view's in-flight predicate computes from
  `liveSession.currentSession` and `liveSession.completedSessions`
  without re-reading the state file. Surfaced as `number[] | null`:
  null for legacy snapshots that pre-date the array; empty array
  when the protocol has been applied but no session has closed yet.

  Set 022 Session 2 / consumer-facing spec:
  `docs/session-sets/022-active-lifecycle-management/spec.md`.

## [0.13.11] — 2026-05-13

### Fixed
- **Tree view no longer shows Done for sets whose final session never
  closed.** The v0.13.8 defensive guard caught the
  `currentSession < totalSessions` drift shape (pre-0.2.1 ai_router and
  manual edits). It missed a different shape observed on
  `unified-master-details-composite` (2026-05-12): snapshot claimed
  `status: complete` with `verificationVerdict: VERIFIED` at
  `currentSession=5/totalSessions=5`, but `session-events.jsonl` had
  `closeout_succeeded` events for sessions 1-4 only — session 5 never
  closed. The pre-existing guard didn't fire (5 is not <5) and the set
  appeared in Done. `isMidSetComplete` in
  `src/utils/fileSystem.ts` now also cross-checks the events ledger: if
  the ledger file exists and has no `closeout_succeeded` event for
  `currentSession`, the snapshot has drifted from the authoritative
  ledger and bucketing downgrades to in-progress. The ledger-existence
  check is critical so Lightweight-tier consumers (no router writer,
  no ledger file) are unaffected — there, the snapshot remains
  authoritative. Two regression tests added in
  `src/test/suite/fileSystem.test.ts`: ledger-gap (downgrades) and
  ledger-complete (remains Done). The root-cause writer bug — how the
  snapshot got written without a corresponding closeout event — is a
  separate ai_router investigation; the tree-view fix defends against
  whatever path produced the drift.

## [0.13.3] — 2026-05-06

### Fixed
- **`requiresUAT` / `requiresE2E` detection no longer silently fails
  for specs with non-canonical headings.** `parseSessionSetConfig`
  in `src/utils/fileSystem.ts` previously fell back to scanning only
  the first 4000 bytes of a spec when the canonical
  `## Session Set Configuration` heading was absent. Specs that put
  their config yaml block under a non-canonical heading like
  `## UAT scope` and had enough upstream prose to push the yaml
  past the 4000-byte cutoff were silently treated as
  `requiresUAT: false`, suppressing UAT badges, the
  "Open UAT Checklist" context-menu item, and any other
  UAT-conditional affordance for the affected sets. Fix: scan the
  entire spec when the canonical heading is absent. The line-
  anchored regex (`^\s*requiresUAT\s*:\s*(true|false)\s*$`) is
  specific enough that false positives from prose mentions are very
  unlikely. Two regression tests added in
  `src/test/suite/fileSystem.test.ts` (positive and negative case).
  Surfaced and fixed during dabbler-ai-orchestration Set 015
  Session 3 (consumer-repo alignment) on `dabbler-platform`'s
  `admin-user-creation-flow` and `admin-users-cross-links` specs.

## [0.13.2] — 2026-05-05

### Fixed
- **Marketplace listing image now displays.** The hero screenshot
  was referenced via a relative path (`media/...`); vsce's
  relative-to-absolute URL rewrite based on `repository.url` did
  not consistently apply on the Marketplace render. The image
  reference now uses an absolute `raw.githubusercontent.com` URL
  so the Marketplace listing renders the screenshot reliably.

### Added
- **Defensive activation wrappers.** Each `register*Commands` call
  in `extension.ts` is now wrapped in its own try/catch with
  `console.error` logging via a `safeRegister` helper. v0.13.1
  shipped without these wrappers; in some workspaces a throw in
  one register group silently skipped the registrations that
  followed (causing "command 'dabbler.showCostDashboard' not
  found" because an earlier register call threw and the cost-
  dashboard / wizard / install-ai-router registrations were
  skipped). The wrappers ensure independent failures and surface
  the exact failing group + error in `Help → Toggle Developer
  Tools → Console` rather than presenting as opaque
  command-not-found at click time. The early-activation steps
  `evaluateContextKeys()` and `bindWatchers()` are also wrapped
  for the same reason.
- **Diagnostic state-bucketing log.** `readSessionSets()` now logs
  a one-line summary per root to the dev console:
  `[dabbler-ai-orchestration] readSessionSets(<root>): N set(s) — done=X, in-progress=Y, not-started=Z, cancelled=W`.
  Helps pinpoint cache / worktree-merge / file-read drift when a
  session set's bucket disagrees with its on-disk
  `session-state.json` status.

### Changed
- **Evidence-based bucketing for "in-progress" status.** A session
  set whose `session-state.json` claims `status: "in-progress"`
  is now bucketed as In Progress only when there's positive
  corroborating evidence — either `session-events.jsonl` contains
  at least one `work_started` event, or `activity-log.json` has
  at least one entry. Without corroboration the status decays to
  Not Started. Implements the principle: "default Not Started;
  require positive evidence to escalate to In Progress / Done /
  Cancelled" (Done is already gated by `change-log.md` presence
  via close_session; Cancelled is gated by `CANCELLED.md`; In
  Progress now joins them). Handles two failure modes: stale
  `in-progress` status from past partial work that was abandoned
  without closing, and migrations / manual edits that flipped the
  status field prematurely.

## [0.13.1] — 2026-05-05

### Fixed
- **Marketplace publish workflow now ships the correct VSIX.** The
  `vsix-v0.13.0` release run inadvertently published the prior
  `0.12.1` VSIX to the Marketplace because two VSIX files were present
  in the build directory at tag-checkout time (the just-built one and
  the canonical sideload artifact committed in Set 014); the upload
  step's `*.vsix` glob captured both, and the publish step's
  lexicographic `head -n1` picked the older one. Workflow now
  version-pins the upload and publish paths to the exact tag-derived
  filename, plus a new defensive build-step gate that fails if any
  extra VSIX is present alongside the just-built one. Marketplace
  v0.13.0 was never actually published; v0.13.1 is the corrected
  release with the v0.13.0 payload (Marketplace-publish workflow,
  runbook, `maxoutClaude` removal).

### Added
- **Empty-state Get Started prompt in the Session Set Explorer.** When
  the active workspace has no `docs/session-sets/` directory or the
  directory is empty, the Session Set Explorer view shows a concise
  welcome message with a one-click **Copy adoption bootstrap prompt**
  link and a pointer at the Get Started wizard. Once any session set
  exists, the welcome content suppresses automatically. Previous
  behavior (relying on the activity-bar Get Started icon and the
  context-menu actions) put the discoverable starting point too far
  from where a first-time user is looking; this change makes the
  empty-state itself a teachable moment.

### Changed
- **`[FIRST]` and `[LAST]` mode badges removed from session-set tree
  rows.** When 99% of sets use the default `outsourceMode: first`, the
  badge becomes visual noise that doesn't differentiate anything. The
  mode still surfaces in the row tooltip on hover for diagnostic
  purposes, and the AI router still consumes the `outsourceMode`
  field from each spec — only the always-visible badge text was
  removed.
- **Marketplace listing README rewritten for the listing page
  audience.** The extension-local README that the Marketplace serves
  on the listing page is now lean, visual-led, and points at the
  GitHub repo for technical depth — replaces the ~600-line technical
  reference that was previously the listing copy. The repo's deep
  documentation is unchanged (still at `docs/repository-reference.md`
  in the source tree); this is purely the Marketplace-facing front
  door.

## [0.13.0] — 2026-05-04

### Added
- **Marketplace-publish-ready release.** This is the first VSIX
  designated for publication to the VS Code Marketplace as
  `DarndestDabbler.dabbler-ai-orchestration`. The publishing
  infrastructure (workflow + runbook) lands in this commit; the
  one-time human-driven publisher account setup + first
  `vsix-v0.13.0` tag push are operator-driven steps that may have
  not yet completed at the time the VSIX is built. Once the publish
  lands, `code --install-extension
  DarndestDabbler.dabbler-ai-orchestration` will resolve from the
  Marketplace.
- `.github/workflows/publish-vscode.yml` — tag-driven publish workflow
  for the VS Code Marketplace and Open VSX Registry. Triggered on
  `vsix-vX.Y.Z` (publish) and `vsix-vX.Y.Z-rcN` (build-only) tags.
  See `docs/planning/marketplace-release-process.md` for one-time
  setup, the per-release checklist, rollback paths, and the
  failure-modes table.

### Removed
- `Dabbler: Copy: Start next session — maxout Claude` command (and the
  matching session-set context-menu entry). The "maxout" suffix as a
  per-session token-window override is no longer surfaced as a
  one-click affordance; the broader `— maxout <engine>` workflow
  concept remains documented in `docs/ai-led-session-workflow.md` for
  operators who want to type the suffix manually.

## [0.12.1] — 2026-05-04

### Added
- `Dabbler: Copy adoption bootstrap prompt` command. Copies a short
  prompt to the clipboard that points an arbitrary AI assistant
  (Claude Code, Gemini Code Assist, GPT-based tools) at the canonical
  online instructions at
  [docs/adoption-bootstrap.md](https://raw.githubusercontent.com/darndestdabbler/dabbler-ai-orchestration/master/docs/adoption-bootstrap.md).
  The pasted prompt instructs the AI to gather all decisions in dialog
  with the human, then present a numbered checklist of intended writes
  and configs for batch approval before executing — no per-write
  confirmation prompts. The canonical doc is engine-agnostic
  (capabilities-term tools, no Claude-specific tool names) and runs a
  9-step interactive flow: detect VS Code state, fast-path detection,
  in-flow education, **budget-threshold dialog with four tiers**
  (zero / less than ~$20 / $20–$99 / $100+, mapping to verification
  modes from manual-via-other-engine through outsource-first with full
  API automation), plan alignment, action checklist, execute, and
  closing pointers (budget monitoring, cost dashboard, more-info
  links, next-session trigger phrase).
- `adoption`, `bootstrap`, `onboarding` keywords for Marketplace
  search.
- Extension description now mentions the bootstrap entry point.

### Notes
- This is a single new top-level command with no logic changes to any
  existing command — version bump is a patch (0.12.0 → 0.12.1). The
  next release (Set 012 Session 2's planned Marketplace publish) will
  bump 0.12.1 → 0.13.0.
- This release ships the file format for `ai_router/budget.yaml`
  (documented in the canonical doc) but does not yet enforce
  thresholds or warn on approaching spend — automated enforcement is
  a follow-up set. The bootstrap flow tells the human that monitoring
  is currently manual via `python -m ai_router.report --since
  YYYY-MM-DD` and the cost dashboard.

## [0.11.0] — 2026-04-30

### Added
- `Provider Heartbeats` tree view (Set 5 / Session 3). Reads
  `python -m ai_router.heartbeat_status --format json`. Shows per-provider
  last-completion timestamp and lookback-window completions/tokens. Silent
  providers (no completions in `silentWarningMinutes`, default 30) are
  flagged with a warning icon. The view's description footer carries a
  permanent observational-only disclaimer to discourage misreading the
  view as a routing or capacity signal.
- Mode badges (`[FIRST]` / `[LAST]`) on session-set tree items, derived
  from each spec's `outsourceMode` field. Backward-compat default is
  `first` when the field is absent. Mode also surfaces in the row tooltip.
- Auto-refresh for the heartbeats view (15s default, configurable;
  `0` disables) with rebind on settings change.

## [0.10.0] — 2026-04-30

### Added
- `Provider Queues` and `Provider Heartbeats` view containers in the
  activity-bar (Set 5 / Session 1). Tree implementations land in
  Sessions 2–3; this release wires the manifest-side scaffold so the
  extension still loads while the providers are stubbed.
- Configuration settings for both views: `dabblerProviderQueues.*`
  (auto-refresh interval, Python path, message limit) and
  `dabblerProviderHeartbeats.*` (auto-refresh interval, lookback
  window, silent-provider warning threshold).
- Command IDs for queue refresh, payload inspection, mark-failed,
  force-reclaim, and heartbeat refresh. The extension shells out to
  two new helpers — `python -m ai_router.queue_status` and
  `python -m ai_router.heartbeat_status` — rather than embedding a
  SQLite client of its own.

## [0.9.0] — 2026-04-29

### Added
- TypeScript rewrite with esbuild bundler and strict mode
- Project wizard panel (`Dabbler: Get Started`) — onboarding overview,
  prerequisites checklist, and first-steps guide
- `Dabbler: Set Up New Project` command — git init, folder scaffold,
  optional worktree setup via simple-git
- `Dabbler: Import Project Plan` command — file picker with preview,
  copies plan to `docs/planning/project-plan.md`
- `Dabbler: Generate Session-Set Prompt` command — builds and copies
  an AI prompt to translate a project plan into session-set specs
- `Dabbler: Troubleshoot` command — diagnostic QuickPick covering
  common failure modes (activation, state machine, worktrees, API keys)
- `Dabbler: Show Cost Dashboard` command and toolbar button — reads
  `ai-router/metrics.jsonl`, shows cumulative totals, per-session-set
  breakdown, ASCII sparkline, model mix, and CSV export
- Expense-awareness callout in onboarding panel and after
  session-set prompt generation
- `category: "Dabbler"` on all commands for clean command-palette grouping
- `simple-git` dependency for typed git operations
- Mocha + @vscode/test-electron test infrastructure
- GitHub Actions CI (build + lint + test on push/PR)
- VS Code Marketplace metadata (icon, homepage, bugs, repository, keywords)

### Changed
- Extension renamed from `dabbler-session-sets` / "Session Set Explorer"
  to `dabbler-ai-orchestration` / "Dabbler AI Orchestration"
- Folder renamed from `tools/vscode-session-sets/` to
  `tools/dabbler-ai-orchestration/`
- `engines.vscode` bumped from `^1.70.0` to `^1.85.0`
- Activity-bar container title updated to "Dabbler AI Orchestration"
- All command IDs and setting keys retain the `dabblerSessionSets.*`
  prefix for backwards compatibility with existing consumer repos

### Preserved (no logic changes)
- Session-set tree view (In Progress / Not Started / Done groups)
- State derivation from file presence
- Git worktree auto-discovery
- UAT checklist parsing and badge rendering
- Playwright test discovery
- All existing right-click context-menu commands
- 30-second auto-refresh poll and file watchers
- All three `dabblerSessionSets.*` settings

## [0.8.1] — 2026-04-27

### Fixed
- Version bump for VSIX distribution

## [0.8.0] — 2026-04-27

### Added
- Merged harvester 0.7.1 feature set with platform-specific UAT/E2E gating
- `requiresUAT` and `requiresE2E` spec-level flags
- UAT checklist parsing, pending badge, Open UAT Checklist command
- Playwright test discovery command
- "Copy: Start next session — maxout Claude" variant
- Multi-root / worktree state merging (done > in-progress > not-started)

## [0.7.1] — 2026-04-15

### Added
- Initial harvester session-set explorer
- Git worktree auto-discovery
- Copy trigger-phrase commands

```


---

## Verification scope

Evaluate whether the code matches the Session 2 contract:
1. Activity-log is no longer a count source — confirmed in fileSystem.ts?
2. New count order: completedSessions.length → events-ledger fallback → totalSessions when done?
3. currentSession - 1 fallback removed?
4. countDistinctCloseoutSessions correctly handles missing file / malformed lines / dedupe?
5. File watcher pattern includes session-events.jsonl + CANCELLED.md?
6. progressText adds 'Done' on done rows, 'session N in flight' when predicate fires?
7. isCurrentSessionInFlight implements the spec invariant correctly, including legacy-snapshot guard?
8. Regression tests cover the new behavior including the dedupe + malformed-line tolerance?
9. Any logic that would silently regress the v0.13.11 isMidSetComplete guard from Set 022?
10. Any off-by-one, null-handling, or type-system issues?

### Response format (REQUIRED JSON)

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {"category": "Correctness|Completeness|False Positive", "severity": "Critical|Major|Minor", "description": "...", "location": "file:line or function name"}
  ]
}
```

If VERIFIED, `issues` must be an empty array.