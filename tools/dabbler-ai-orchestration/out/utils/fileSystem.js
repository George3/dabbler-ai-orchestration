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
exports.PLAYWRIGHT_REL_DEFAULT = exports.SESSION_SETS_REL = void 0;
exports.discoverRoots = discoverRoots;
exports.isMidSetComplete = isMidSetComplete;
exports.parseSessionSetConfig = parseSessionSetConfig;
exports.parseUatChecklist = parseUatChecklist;
exports.readSessionSets = readSessionSets;
exports.readAllSessionSets = readAllSessionSets;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const git_1 = require("./git");
const sessionState_1 = require("./sessionState");
const cancelLifecycle_1 = require("./cancelLifecycle");
exports.SESSION_SETS_REL = path.join("docs", "session-sets");
exports.PLAYWRIGHT_REL_DEFAULT = "tests";
// Cancelled sets sort below all other groups in the merge logic — Set 8
// keeps cancelled state as the lowest precedence so a set that exists in
// two roots (one cancelled, one active) prefers the active copy when
// dedup-merging. Within a single root the file-presence rule still wins
// because readSessionSets has already resolved each entry's state.
const STATE_RANK = {
    done: 3,
    "in-progress": 2,
    "not-started": 1,
    cancelled: 0,
};
function discoverRoots() {
    const seen = new Map();
    const order = [];
    const add = (p) => {
        if (!p)
            return;
        const canonical = path.resolve(p);
        const key = canonical.toLowerCase();
        if (seen.has(key) || !fs.existsSync(canonical))
            return;
        seen.set(key, canonical);
        order.push(canonical);
    };
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        add(folder.uri.fsPath);
    }
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        for (const wt of (0, git_1.listGitWorktrees)(folder.uri.fsPath)) {
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
function isMidSetComplete(statePath) {
    if (!fs.existsSync(statePath))
        return false;
    try {
        const sd = JSON.parse(fs.readFileSync(statePath, "utf8"));
        if (typeof sd.currentSession !== "number")
            return false;
        if (typeof sd.totalSessions !== "number")
            return false;
        if (sd.currentSession < sd.totalSessions)
            return true;
        const eventsPath = path.join(path.dirname(statePath), "session-events.jsonl");
        if (fs.existsSync(eventsPath) &&
            !hasCloseoutEventForSession(eventsPath, sd.currentSession)) {
            return true;
        }
        return false;
    }
    catch {
        return false;
    }
}
function hasCloseoutEventForSession(eventsPath, sessionNumber) {
    let text;
    try {
        text = fs.readFileSync(eventsPath, "utf8");
    }
    catch {
        return false;
    }
    for (const raw of text.split(/\r?\n/)) {
        const line = raw.trim();
        if (!line)
            continue;
        try {
            const event = JSON.parse(line);
            if (event.event_type === "closeout_succeeded" &&
                event.session_number === sessionNumber) {
                return true;
            }
        }
        catch {
            // skip malformed lines — append-only ledger may carry partial writes
        }
    }
    return false;
}
function parseSessionSetConfig(specPath) {
    const config = {
        requiresUAT: false,
        requiresE2E: false,
        uatScope: "none",
        outsourceMode: null,
    };
    if (!fs.existsSync(specPath))
        return config;
    let text;
    try {
        text = fs.readFileSync(specPath, "utf8");
    }
    catch {
        return config;
    }
    const headingMatch = text.match(/##\s*Session Set Configuration[\s\S]*?```ya?ml\s*([\s\S]*?)```/i);
    // When the canonical `## Session Set Configuration` heading is absent,
    // fall back to scanning the entire spec rather than just the first 4000
    // chars. The line-anchored regexes below (e.g.,
    // `^\s*requiresUAT:\s*(true|false)\s*$`) are specific enough that false
    // positives in prose are very unlikely; a 4000-byte cap was needlessly
    // narrow and missed real declarations in specs that put the config
    // yaml block under a non-canonical heading like `## UAT scope`.
    const block = headingMatch ? headingMatch[1] : text;
    const flagRe = (key) => new RegExp(`^\\s*${key}\\s*:\\s*(true|false)\\s*$`, "im");
    const stringRe = (key) => new RegExp(`^\\s*${key}\\s*:\\s*([\\w-]+)\\s*$`, "im");
    const uat = block.match(flagRe("requiresUAT"));
    if (uat)
        config.requiresUAT = uat[1].toLowerCase() === "true";
    const e2e = block.match(flagRe("requiresE2E"));
    if (e2e)
        config.requiresE2E = e2e[1].toLowerCase() === "true";
    const scope = block.match(stringRe("uatScope"));
    if (scope)
        config.uatScope = scope[1];
    const mode = block.match(stringRe("outsourceMode"));
    if (mode) {
        const v = mode[1].toLowerCase();
        if (v === "first" || v === "last")
            config.outsourceMode = v;
    }
    return config;
}
function parseUatChecklist(checklistPath) {
    if (!fs.existsSync(checklistPath))
        return null;
    let data;
    try {
        data = JSON.parse(fs.readFileSync(checklistPath, "utf8"));
    }
    catch {
        return null;
    }
    const items = [];
    const collect = (node) => {
        if (!node || typeof node !== "object")
            return;
        if (Array.isArray(node)) {
            for (const v of node)
                collect(v);
            return;
        }
        const obj = node;
        if (obj["Result"] !== undefined || obj["result"] !== undefined) {
            items.push(obj);
        }
        for (const v of Object.values(obj))
            collect(v);
    };
    collect(data);
    const e2eRefs = new Set();
    let pending = 0;
    for (const it of items) {
        const r = (it["Result"] ?? it["result"] ?? "");
        if (r === "" || r === null || /^pending$/i.test(String(r)))
            pending++;
        const ref = it["E2ETestReference"] || it["e2eTestReference"];
        if (ref)
            e2eRefs.add(String(ref));
    }
    return { totalItems: items.length, pendingItems: pending, e2eRefs: Array.from(e2eRefs) };
}
function readSessionSets(root) {
    const sessionSetsDir = path.join(root, exports.SESSION_SETS_REL);
    if (!fs.existsSync(sessionSetsDir))
        return [];
    const entries = fs.readdirSync(sessionSetsDir, { withFileTypes: true });
    const sets = [];
    for (const entry of entries) {
        if (!entry.isDirectory() || entry.name.startsWith("_"))
            continue;
        const dir = path.join(sessionSetsDir, entry.name);
        const specPath = path.join(dir, "spec.md");
        if (!fs.existsSync(specPath))
            continue;
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
        let state;
        if ((0, cancelLifecycle_1.isCancelled)(dir)) {
            state = "cancelled";
        }
        else {
            const status = (0, sessionState_1.readStatus)(dir);
            if (status === "complete") {
                // Defensive: a status of "complete" with currentSession <
                // totalSessions is a stale mid-set close-out — written either
                // by ai_router < 0.2.1 (which flipped to complete after every
                // session), a manual edit, or a snapshot a consumer repo
                // hasn't refreshed yet. Treat as in-progress so the set
                // doesn't briefly show Done in the window between sessions.
                state = isMidSetComplete(statePath) ? "in-progress" : "done";
            }
            else if (status === "in-progress") {
                state = "in-progress";
            }
            else {
                state = "not-started";
            }
        }
        let totalSessions = null;
        let sessionsCompleted = 0;
        let lastTouched = null;
        let liveSession = null;
        if (fs.existsSync(activityPath)) {
            try {
                const data = JSON.parse(fs.readFileSync(activityPath, "utf8"));
                if (typeof data.totalSessions === "number")
                    totalSessions = data.totalSessions;
                const completedSet = new Set();
                for (const e of data.entries ?? []) {
                    if (typeof e.sessionNumber === "number")
                        completedSet.add(e.sessionNumber);
                    if (e.dateTime && (!lastTouched || e.dateTime > lastTouched))
                        lastTouched = e.dateTime;
                }
                sessionsCompleted = completedSet.size;
            }
            catch { /* ignore */ }
        }
        if (fs.existsSync(statePath)) {
            try {
                const sd = JSON.parse(fs.readFileSync(statePath, "utf8"));
                if (totalSessions === null && typeof sd.totalSessions === "number") {
                    totalSessions = sd.totalSessions;
                }
                const stateTouched = sd.completedAt || sd.startedAt;
                if (stateTouched && (!lastTouched || stateTouched > lastTouched))
                    lastTouched = stateTouched;
                liveSession = {
                    currentSession: sd.currentSession ?? null,
                    status: sd.status ?? null,
                    orchestrator: sd.orchestrator ?? null,
                    startedAt: sd.startedAt ?? null,
                    completedAt: sd.completedAt ?? null,
                    verificationVerdict: sd.verificationVerdict ?? null,
                    forceClosed: sd.forceClosed ?? null,
                };
                // sessionsCompleted priority (highest first):
                //  1. session-state.json `completedSessions` array — authoritative
                //     under schema v2. Hand-maintained on Lightweight tier;
                //     written by ai_router on Full tier.
                //  2. activity-log.json unique sessionNumbers (set above).
                //  3. Derived from `state` + currentSession when neither exists.
                //     - state="done" => all sessions done; count = totalSessions.
                //       Using the already-canonicalized `state` (via readStatus)
                //       instead of raw `sd.status` ensures the same alias map
                //       ("completed", "done" -> "complete") applies here as it
                //       does for Done/Active bucketing. A pre-Set-7 state file
                //       carrying `status: "completed"` would otherwise fall
                //       through to the currentSession-1 fallback and display
                //       N-1/N. Also naturally skips the mid-set-complete case,
                //       where state is downgraded to "in-progress".
                //     - currentSession>1 (non-done) => assume the current session
                //       is in progress, so currentSession-1 are done. This can
                //       be off by one when the latest session is itself complete
                //       and the set is still open; only used when no more
                //       precise signal is available.
                if (Array.isArray(sd.completedSessions)) {
                    sessionsCompleted = sd.completedSessions.length;
                }
                else if (sessionsCompleted === 0) {
                    if (state === "done" && typeof totalSessions === "number") {
                        sessionsCompleted = totalSessions;
                    }
                    else if (typeof sd.currentSession === "number" && sd.currentSession > 1) {
                        sessionsCompleted = sd.currentSession - 1;
                    }
                }
            }
            catch { /* ignore */ }
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
        const counts = sets.reduce((acc, s) => {
            acc[s.state] = (acc[s.state] ?? 0) + 1;
            return acc;
        }, {});
        console.log(`[dabbler-ai-orchestration] readSessionSets(${path.basename(root)}): ` +
            `${sets.length} set(s) — ` +
            `done=${counts.done ?? 0}, ` +
            `in-progress=${counts["in-progress"] ?? 0}, ` +
            `not-started=${counts["not-started"] ?? 0}, ` +
            `cancelled=${counts.cancelled ?? 0}`);
    }
    return sets;
}
function readAllSessionSets() {
    const merged = new Map();
    for (const root of discoverRoots()) {
        for (const set of readSessionSets(root)) {
            const prior = merged.get(set.name);
            if (!prior) {
                merged.set(set.name, set);
                continue;
            }
            const newRank = STATE_RANK[set.state] ?? -1;
            const priorRank = STATE_RANK[prior.state] ?? -1;
            if (newRank > priorRank) {
                merged.set(set.name, set);
            }
            else if (newRank === priorRank) {
                if ((set.lastTouched || "") > (prior.lastTouched || ""))
                    merged.set(set.name, set);
            }
        }
    }
    return Array.from(merged.values());
}
//# sourceMappingURL=fileSystem.js.map