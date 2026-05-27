"use strict";
// In-extension v3 → v4 session-state.json migrator.
//
// TypeScript mirror of `ai_router/migrate_v3_to_v4.py`. Lives in the
// extension so Lightweight-tier consumer repos that never install
// `dabbler-ai-router` can still right-click → "Migrate to v4 schema"
// from the Session Sets view.
//
// **Parity contract (Python ↔ TypeScript).** The two implementations
// must agree on three things:
//
//   1. the on-disk v4 shape (preserved / dropped / passthrough keys
//      described in `progress.ts` / `progress.py`) — the same input
//      v3 file produces the same v4 file regardless of which
//      migrator wrote it;
//   2. the backup filename `session-state.v3.bak.json` and write
//      order (backup first, then state file replacement) so the
//      rollback procedure at `docs/v3-to-v4-rollback-procedure.md`
//      works regardless of which migrator wrote the .bak;
//   3. the action enum string values (`"migrated"`, `"skipped-v4"`,
//      `"skipped-not-v3"`, `"skipped-no-state"`, `"skipped-malformed"`,
//      `"skipped-future-schema"`, `"would-violate"`, `"failed-backup"`)
//      so consumers that parse either side's output get the same
//      vocabulary.
//
// Internal API field names (`set_dir` vs `setDir`, `backup_path` vs
// `backupPath`) follow per-language convention and are explicitly
// OUT of scope for the parity contract — these are private to each
// runtime's callers.
//
// Strategy choice (v2→v3 had regex/generic) does not apply here — a
// v3 file already has session titles in `sessions[]`. The migrator is
// a thin wrapper around `normalizeToV4Shape`: the shim does the
// per-session metadata promotion and the top-level derivation; this
// module's job is to strip the derived top-level fields and write
// the trimmed result to disk.
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
exports.SWEEP_BACKUP_FILENAME = exports.BACKUP_FILENAME = exports.SESSION_STATE_FILENAME = void 0;
exports.stripRetiredOrchestratorKeys = stripRetiredOrchestratorKeys;
exports.sweepOrchestratorBlocks = sweepOrchestratorBlocks;
exports.buildV4OnDiskShape = buildV4OnDiskShape;
exports.migrateOneSetV4 = migrateOneSetV4;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const progress_1 = require("./progress");
exports.SESSION_STATE_FILENAME = "session-state.json";
exports.BACKUP_FILENAME = "session-state.v3.bak.json";
exports.SWEEP_BACKUP_FILENAME = "session-state.pre-049-sweep.bak.json";
// Set 049 T4: orchestrator-block keys retired by the coordination-layer
// rip. The sweep+normalize pass strips these from every orchestrator
// block on disk — both the legacy top-level `orchestrator` field
// (pre-v4 files migrated forward) and the per-session ledger blocks
// (v4 shape). Mirrors `_RETIRED_ORCHESTRATOR_KEYS` in the Python
// migrator.
const RETIRED_ORCHESTRATOR_KEYS = [
    "chatSessionId",
    "checkedOutAt",
    "lastActivityAt",
];
// Fields the on-disk v4 shape drops from the top level — the
// normalize shim re-derives them at read time. Mirrors
// _V4_TOP_LEVEL_DROPPED_KEYS in the Python migrator.
const V4_TOP_LEVEL_DROPPED_KEYS = [
    "lifecycleState",
    "currentSession",
    "totalSessions",
    "completedSessions",
    "startedAt",
    "completedAt",
    "orchestrator",
    "verificationVerdict",
];
// Preserved at top level in canonical insertion order. `status` is
// canonicalized on the way out. `sessions` carries the per-session
// metadata produced by the normalize shim.
const V4_TOP_LEVEL_PRESERVED_KEYS = [
    "schemaVersion",
    "sessionSetName",
    "status",
    "sessions",
];
// Passthrough fields the cancellation lifecycle and the [FORCED]
// badge still consume. Carried only when present in the source v3.
const V4_TOP_LEVEL_PASSTHROUGH_KEYS = [
    "preCancelStatus",
    "forceClosed",
];
/**
 * Strip Set-049-retired keys from a single orchestrator block.
 * Mirrors `_strip_retired_orchestrator_keys` in the Python migrator.
 *
 * Returns `[newBlock, changed]`. Non-object input round-trips unchanged
 * with `changed=false`. A retired key is "present" if it appears in
 * the object regardless of value (including `null`) because the
 * on-disk shape must omit these keys entirely under the omit-null
 * contract.
 */
function stripRetiredOrchestratorKeys(block) {
    if (block === null || typeof block !== "object" || Array.isArray(block)) {
        return [block, false];
    }
    const obj = block;
    let changed = false;
    const out = {};
    for (const [key, value] of Object.entries(obj)) {
        if (RETIRED_ORCHESTRATOR_KEYS.includes(key)) {
            changed = true;
            continue;
        }
        out[key] = value;
    }
    return [out, changed];
}
/**
 * Sweep retired orchestrator-block keys throughout a state file.
 * Mirrors `_sweep_orchestrator_blocks` in the Python migrator.
 *
 * Sweeps both the top-level legacy `orchestrator` field (pre-v4
 * files) AND every per-session ledger entry's `orchestrator` block
 * (v4 shape). Returns `[newState, changed]`. Idempotent: re-running
 * on already-clean state returns the input reference unchanged.
 */
function sweepOrchestratorBlocks(state) {
    let changed = false;
    let newState = state;
    const topOrch = state.orchestrator;
    if (topOrch !== null && typeof topOrch === "object" && !Array.isArray(topOrch)) {
        const [swept, topChanged] = stripRetiredOrchestratorKeys(topOrch);
        if (topChanged) {
            newState = { ...state };
            newState.orchestrator = swept;
            changed = true;
        }
    }
    const sessions = state.sessions;
    if (Array.isArray(sessions)) {
        const newSessions = [];
        let sessionsChanged = false;
        for (const entry of sessions) {
            if (entry === null || typeof entry !== "object" || Array.isArray(entry)) {
                newSessions.push(entry);
                continue;
            }
            const entryObj = entry;
            const [swept, entryChanged] = stripRetiredOrchestratorKeys(entryObj.orchestrator);
            if (entryChanged) {
                newSessions.push({ ...entryObj, orchestrator: swept });
                sessionsChanged = true;
            }
            else {
                newSessions.push(entry);
            }
        }
        if (sessionsChanged) {
            if (newState === state) {
                newState = { ...state };
            }
            newState.sessions = newSessions;
            changed = true;
        }
    }
    return [newState, changed];
}
/**
 * Build the on-disk v4 dict given a normalized read-view + the
 * original v3 state. Mirrors `build_v4_on_disk_shape` in Python.
 *
 * The shim has already promoted v3 top-level metadata onto the
 * per-session `sessions[]` entries and derived the top-level fields
 * for backwards-compatible reading; our job is to strip the
 * derived-redundant fields so the on-disk file is the canonical v4
 * shape.
 */
function buildV4OnDiskShape(normalized, original) {
    const out = {};
    for (const key of V4_TOP_LEVEL_PRESERVED_KEYS) {
        if (key === "schemaVersion") {
            out[key] = progress_1.SCHEMA_VERSION_V4;
        }
        else if (key === "status") {
            const canon = (0, progress_1.canonicalizeStatus)(normalized.status ?? null);
            out[key] = canon ?? normalized.status ?? null;
        }
        else if (key === "sessions") {
            out[key] = normalized.sessions ?? [];
        }
        else {
            out[key] = normalized[key] ?? null;
        }
    }
    for (const key of V4_TOP_LEVEL_PASSTHROUGH_KEYS) {
        if (key in original) {
            out[key] = original[key];
        }
    }
    // Defensive: ensure no dropped key sneaks through (paranoia + a
    // useful invariant for tests).
    for (const key of V4_TOP_LEVEL_DROPPED_KEYS) {
        delete out[key];
    }
    return out;
}
// Atomic write of *data* as pretty-printed JSON to *filePath*.
// Mirrors `_atomic_write_json` in the Python migrator. The temp file
// is created in the same directory as the target so `fs.renameSync`
// is a same-volume rename (atomic on POSIX and Windows).
function atomicWriteJson(filePath, data) {
    const dir = path.dirname(filePath);
    const base = path.basename(filePath);
    const tmp = path.join(dir, `.${base}.tmp.${process.pid}.${Date.now()}`);
    const fd = fs.openSync(tmp, "w");
    try {
        fs.writeSync(fd, JSON.stringify(data, null, 2) + "\n", null, "utf-8");
        fs.fsyncSync(fd);
    }
    finally {
        fs.closeSync(fd);
    }
    try {
        fs.renameSync(tmp, filePath);
    }
    catch (exc) {
        try {
            fs.unlinkSync(tmp);
        }
        catch {
            // best-effort cleanup
        }
        throw exc;
    }
}
// Re-parse + re-emit so the .bak has the same indent=2 formatting as
// the v4 file we're about to write — easier to diff for the rollback
// procedure. Mirrors `_atomic_copy_json` in Python.
function atomicCopyJson(src, dst) {
    const raw = JSON.parse(fs.readFileSync(src, "utf-8"));
    atomicWriteJson(dst, raw);
}
/**
 * Migrate one session-set directory's `session-state.json` from v3 to v4.
 *
 * Idempotent: a v4 file is returned as `skipped-v4` without touching
 * disk. v1/v2 files return `skipped-not-v3` with instructions to run
 * the v2→v3 migrator first. A broken v3 file (schemaVersion=3 but
 * `sessions[]` missing/non-list) returns `skipped-malformed`.
 *
 * Apply mode writes `session-state.v3.bak.json` BEFORE replacing the
 * state file so the rollback procedure has a known-good copy if any
 * subsequent step fails. The migrator NEVER throws for "file isn't
 * there / file is broken" cases — those become structured results so
 * the UI can render kind-specific messages.
 */
function migrateOneSetV4(setDir, options = {}) {
    const dryRun = options.dryRun ?? false;
    const statePath = path.join(setDir, exports.SESSION_STATE_FILENAME);
    const backupPath = path.join(setDir, exports.BACKUP_FILENAME);
    if (!fs.existsSync(statePath)) {
        return {
            setDir,
            action: "skipped-no-state",
            reason: `${exports.SESSION_STATE_FILENAME} not found`,
        };
    }
    let raw;
    try {
        raw = fs.readFileSync(statePath, "utf-8");
    }
    catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        return {
            setDir,
            action: "skipped-malformed",
            reason: `failed to read: ${msg}`,
            error: msg,
        };
    }
    let state;
    try {
        state = JSON.parse(raw);
    }
    catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        return {
            setDir,
            action: "skipped-malformed",
            reason: `failed to parse: ${msg}`,
            error: msg,
        };
    }
    if (state === null || typeof state !== "object" || Array.isArray(state)) {
        const t = Array.isArray(state) ? "array" : typeof state;
        return {
            setDir,
            action: "skipped-malformed",
            reason: `top-level JSON is ${t}, expected object`,
        };
    }
    const stateObj = state;
    const schemaVersion = stateObj.schemaVersion;
    if (typeof schemaVersion === "number" && schemaVersion > progress_1.SCHEMA_VERSION_V4) {
        return {
            setDir,
            action: "skipped-future-schema",
            reason: `schemaVersion=${schemaVersion} is newer than this migrator ` +
                `(v${progress_1.SCHEMA_VERSION_V4}); refusing to downgrade. Upgrade the ` +
                "migrator or hand-edit the file.",
            before: state,
        };
    }
    // Already-v4 branch. Set 049 T4 added an orchestrator-block sweep
    // pass that strips three retired keys (chatSessionId / checkedOutAt
    // / lastActivityAt) from any orchestrator block on disk. Mirrors
    // the Python migrator. Pre-Set-049 v4 files written by Set 047
    // carry those keys; the sweep catches them on the next migrator
    // run. On already-clean v4 files the sweep is a no-op and we keep
    // the existing skip semantics.
    if (typeof schemaVersion === "number" && schemaVersion >= progress_1.SCHEMA_VERSION_V4) {
        const [sweptState, swept] = sweepOrchestratorBlocks(stateObj);
        if (!swept) {
            return {
                setDir,
                action: "skipped-v4",
                reason: `already v4 (schemaVersion=${schemaVersion})`,
                before: state,
                after: state,
            };
        }
        if (dryRun) {
            return {
                setDir,
                action: "swept-orchestrator",
                reason: "v4 → v4 (orchestrator-block sweep: stripping " +
                    `${RETIRED_ORCHESTRATOR_KEYS.join(", ")}; ` +
                    "dry-run, no write performed)",
                before: state,
                after: sweptState,
            };
        }
        // Apply mode: use the Set-049-specific backup filename so the
        // rollback affordance distinguishes a v3→v4 .bak (existing) from
        // a v4-sweep .bak (new).
        const sweepBackupPath = path.join(setDir, exports.SWEEP_BACKUP_FILENAME);
        try {
            atomicCopyJson(statePath, sweepBackupPath);
        }
        catch (exc) {
            const msg = exc instanceof Error ? exc.message : String(exc);
            return {
                setDir,
                action: "failed-backup",
                reason: `could not write backup at ${sweepBackupPath}: ${msg}`,
                error: msg,
                before: state,
            };
        }
        try {
            atomicWriteJson(statePath, sweptState);
        }
        catch (exc) {
            const msg = exc instanceof Error ? exc.message : String(exc);
            return {
                setDir,
                action: "failed-backup",
                reason: `backup written at ${sweepBackupPath} but state-file write ` +
                    `failed: ${msg}. Restore the backup via the rollback procedure ` +
                    "at docs/v3-to-v4-rollback-procedure.md.",
                error: msg,
                before: state,
                backupPath: sweepBackupPath,
            };
        }
        return {
            setDir,
            action: "swept-orchestrator",
            reason: "v4 → v4 (orchestrator-block sweep: stripped " +
                `${RETIRED_ORCHESTRATOR_KEYS.join(", ")})`,
            before: state,
            after: sweptState,
            backupPath: sweepBackupPath,
        };
    }
    if (!(typeof schemaVersion === "number" && schemaVersion === progress_1.SCHEMA_VERSION_V3)) {
        return {
            setDir,
            action: "skipped-not-v3",
            reason: `schemaVersion=${JSON.stringify(schemaVersion)} is not v${progress_1.SCHEMA_VERSION_V3}; ` +
                "the v3→v4 migrator only operates on v3 input. Right-click " +
                "the row and run \"Migrate to v3 schema\" first, then re-run " +
                "\"Migrate to v4 schema\".",
            before: state,
        };
    }
    if (!Array.isArray(stateObj.sessions)) {
        return {
            setDir,
            action: "skipped-malformed",
            reason: "schemaVersion=3 but sessions[] is missing or not a list; this " +
                "is a broken v3 file, not a downgrade candidate. Hand-repair " +
                "or restore from git, then re-run.",
            before: state,
        };
    }
    const specMdPath = path.join(setDir, "spec.md");
    let normalized;
    try {
        normalized = (0, progress_1.normalizeToV4Shape)(stateObj, specMdPath);
    }
    catch (exc) {
        if (exc instanceof progress_1.SessionStateInvariantError) {
            return {
                setDir,
                action: "would-violate",
                reason: exc.message,
                error: exc.message,
                before: state,
            };
        }
        const msg = exc instanceof Error ? exc.message : String(exc);
        return {
            setDir,
            action: "skipped-malformed",
            reason: `normalizeToV4Shape rejected the input: ${msg}`,
            error: msg,
            before: state,
        };
    }
    // The shim is the reader-first contract from S2; it builds the v4
    // view without enforcing the 8 invariants. The migrator additionally
    // validates through `getProgress` so a v3 file whose status doesn't
    // match its sessions[] (e.g., status=complete with a not-started
    // session) surfaces as a would-violate rather than silently
    // producing an invalid v4 file.
    try {
        (0, progress_1.getProgress)(normalized);
    }
    catch (exc) {
        if (exc instanceof progress_1.SessionStateInvariantError) {
            return {
                setDir,
                action: "would-violate",
                reason: exc.message,
                error: exc.message,
                before: state,
            };
        }
        throw exc;
    }
    let newState = buildV4OnDiskShape(normalized, stateObj);
    // Set 049 T4: strip retired orchestrator-block keys from the v4
    // output. The v3 input may have carried them on the top-level
    // legacy `orchestrator` field (which the shim promotes into
    // per-session entries), so the sweep applies after the v4 shape is
    // assembled. Idempotent for v3 files without the retired keys.
    // Mirrors the Python migrator.
    const [sweptNewState] = sweepOrchestratorBlocks(newState);
    newState = sweptNewState;
    if (dryRun) {
        return {
            setDir,
            action: "migrated",
            reason: "v3 → v4 (dry-run; no write performed)",
            before: state,
            after: newState,
        };
    }
    // Apply path: backup first, then write the v4 file. If the backup
    // write fails, abort without touching the state file. If the state
    // write fails after the backup, surface the .bak path so the
    // operator knows where to roll back from.
    try {
        atomicCopyJson(statePath, backupPath);
    }
    catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        return {
            setDir,
            action: "failed-backup",
            reason: `could not write backup at ${backupPath}: ${msg}`,
            error: msg,
            before: state,
        };
    }
    try {
        atomicWriteJson(statePath, newState);
    }
    catch (exc) {
        const msg = exc instanceof Error ? exc.message : String(exc);
        return {
            setDir,
            action: "failed-backup",
            reason: `backup written at ${backupPath} but state-file write failed: ` +
                `${msg}. Restore the backup via the rollback procedure at ` +
                `docs/v3-to-v4-rollback-procedure.md.`,
            error: msg,
            before: state,
            backupPath,
        };
    }
    return {
        setDir,
        action: "migrated",
        reason: "v3 → v4",
        before: state,
        after: newState,
        backupPath,
    };
}
//# sourceMappingURL=migrateSessionStateV4.js.map