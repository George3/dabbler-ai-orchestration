# Session 2 verification — Round C (confirmation pass on Round A + Round B must-fix items)

## Context

Round A (marker writer + CSS visual matrix) returned with 3 must-fix
items; Round B (provider + installer) returned with 2 must-fix items.
Total 5 must-fix items, all addressed. This Round C is a focused
confirmation pass: did the fixes actually fix the issues, and did the
fixes introduce any new bugs?

## Round A must-fix items + fixes applied

1. **TOCTOU race in `attemptWriteWithPrecedence`** (Q2). The original
   read existing → decide → write pattern had a race window. The fix
   adds a re-read immediately before `fs.renameSync` and re-evaluates
   precedence against that latest snapshot; skips with `reason:
   "weaker-than-existing-on-reread"` if a concurrent writer raced
   ahead with a stronger marker. Code is now in
   `write-orchestrator-marker.js` `attemptWriteWithPrecedence`.

2. **UserPromptSubmit merge/bootstrap clobber risk** (Q6). Both the
   merge-existing and bootstrap-when-missing paths can clobber a
   fresher SessionStart marker that lands between the initial read
   and the rename. Fix: added a re-read inside the
   `mode === "user-prompt-submit"` branch, after the tmp file is
   written but before the rename. If a marker exists at the re-read
   point, the merge uses THAT latest marker as the top-level
   snapshot (preferring fresh top-level signal over the
   bootstrap/initial-snapshot we'd otherwise write).

3. **Stale stripes painted BEHIND the SVG, not as an overlay** (Q8).
   Original: `.stale .gauge-svg { background-image: ... }` paints
   stripes on the SVG's background layer (i.e., behind the SVG
   content). Verifier was right — strokes don't get striped this
   way. Fix: replaced with `.stale .gauge-cell::before` absolute-
   positioned at z-index 2, occupying the gauge's 54px height,
   `pointer-events: none`. Stripe alpha bumped from 0.18 to 0.45
   (closer to the audit's "50% opacity" target).

## Round B must-fix items + fixes applied

4. **Effort suffix keyed off wrong signal** (Q1). Original code in
   `renderLoaded` had the `(default)` / `(manual)` branches checking
   `marker.signalKind` (top-level model signal) instead of
   `marker.effort.signalKind`. This means a Codex `configured-default`
   session with a `/think*` observation would render "(default)" on
   the effort gauge instead of the elapsed-time suffix. Fix: all
   three effort suffix branches now check `marker.effort.signalKind`.

5. **Gauge angle math wrong basis** (Q4). Original code used a
   `(180 + needleAngleDeg)` offset in the `Math.cos`/`Math.sin`
   calls, which inverted the y-axis behavior. At `needleAngleDeg =
   -90`, the offset gave 90°, and `Math.sin(90°) = 1`, so
   `fillEndY = cy + radius * 1 = cy + radius` — BELOW the gauge
   instead of at the top. All needle/fill endpoints were below
   the visible viewBox. Fix: removed the `180 +` offset; the angle
   is now used directly. With SVG's y-axis going down, `sin(-90°) =
   -1` correctly places the endpoint at `cy - radius` (top center).
   Also simplified `largeArc` to always be 0 since all upper-
   semicircle arcs are ≤180°.

## What you're being asked to verify in Round C

Re-bundle: the FULL post-fix versions of the marker writer + provider
+ CSS are inlined below. Round C focuses ONLY on:

**Q1.** For each of the 5 must-fix items above, does the fix
actually address the issue? Trace through the code with the fix in
place against the original concern.

**Q2.** Did any of the fixes introduce a new bug? Specifically:
- The re-read-before-rename in `attemptWriteWithPrecedence` uses
  `Date.now()` for the stale check, while the initial read used
  `nowMs`. Could a stale signal that JUST aged past
  `stalenessMaxSec` during our retry-loop window cause an
  inconsistent decision (initial read says fresh → re-read says
  stale)? If so, what's the worst-case behavior?
- The `user-prompt-submit` merge path now ALWAYS re-reads, even on
  the bootstrap path. If the initial read returned `null` (no
  marker) but the re-read returns a freshly-written
  SessionStart marker, we discard the bootstrap and merge onto the
  latest. Correct? Or is there a corner case where the initial read
  saw a CORRUPT/parse-fail marker and the re-read sees a fresh
  one, and the corrupt-but-parseable-in-one-direction would be
  trickier?
- The new gauge math always uses `largeArc = 0`. For
  `needleAngleDeg = 0` exactly (rightmost), is the arc from
  leftmost (7,35) to rightmost (63,35) at radius 28 with largeArc=0
  actually the correct upper-semicircle path? SVG spec says when
  the chord = 2*radius exactly (true for a diameter), there are
  exactly two arc options (large or small), and `largeArc=0` picks
  the smaller — which for a 180° chord is still 180° (no smaller
  option). Verify SVG-spec-wise this renders the upper arc, not
  the lower.

**Q3.** Spot-check the two doc updates (audit-summary.md D3
superseding note + spec.md D3 update). Are they sufficient to
prevent future maintainers from being confused by the "≤100px"
phrasing in adjacent context that wasn't updated?

**Q4.** Overall: are all 5 must-fix items resolved and no new
must-fix items introduced? Is Session 2 ready to close out?

Short, structured response per question. Skip stylistic nits — this
is the close-out gate.


---

## File 1 (post-fix): scripts/write-orchestrator-marker.js

```javascript
#!/usr/bin/env node
// write-orchestrator-marker.js
//
// Shared marker-file writer for the orchestrator indicator gauges.
// Invoked from:
//   - Claude Code SessionStart hook (mode=session-start, payload via stdin)
//   - Claude Code UserPromptSubmit hook (mode=user-prompt-submit, payload via stdin)
//   - VS Code manual-override quickpick (mode=manual, payload via stdin)
//   - Codex config.toml watcher (mode=configured-default, payload via stdin)
//
// Writes ~/.dabbler/current-orchestrator.json atomically with multi-writer
// precedence and a Windows-file-watcher-aware retry loop.
//
// Per Set 029 audit (audit-summary.md §"Marker file schema" + §"Multi-writer
// precedence" + §"Visual treatment by signalKind"). Locked design — do not
// re-litigate.

const fs = require("fs");
const os = require("os");
const path = require("path");

// Schema + behavior constants (locked by Set 029 Session 1 audit).
const SCHEMA_VERSION = 2;
const DEFAULT_STALENESS_MAX_SEC = 28800; // 8h
const PRECEDENCE = ["current", "manual", "last-observed", "configured-default"];
const RETRY_BACKOFFS_MS = [50, 200, 600, 1200]; // 4 retries after the initial attempt → 5 total

const DABBLER_DIR = path.join(os.homedir(), ".dabbler");
const MARKER_PATH = path.join(DABBLER_DIR, "current-orchestrator.json");
const WRITER_LOG_PATH = path.join(DABBLER_DIR, "orchestrator-writer.log");

function ensureDir() {
  fs.mkdirSync(DABBLER_DIR, { recursive: true });
}

function readStdinSync() {
  try {
    const data = fs.readFileSync(0, "utf8");
    return data;
  } catch {
    return "";
  }
}

function parseArgs(argv) {
  const out = {
    mode: null,
    writer: null,
    forceOverride: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--mode") {
      out.mode = argv[++i];
    } else if (a === "--writer") {
      out.writer = argv[++i];
    } else if (a === "--force-override") {
      out.forceOverride = true;
    }
  }
  return out;
}

function precedenceIndex(signalKind) {
  const idx = PRECEDENCE.indexOf(signalKind);
  return idx === -1 ? PRECEDENCE.length : idx; // unknown sorts last (weakest)
}

function readExistingMarker() {
  try {
    const raw = fs.readFileSync(MARKER_PATH, "utf8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function isStale(marker, nowMs) {
  if (!marker || !marker.updatedAt) return true;
  const ageSec = (nowMs - Date.parse(marker.updatedAt)) / 1000;
  const limit = typeof marker.stalenessMaxSec === "number"
    ? marker.stalenessMaxSec
    : DEFAULT_STALENESS_MAX_SEC;
  return ageSec > limit;
}

function appendWriterLog(entry) {
  try {
    fs.appendFileSync(
      WRITER_LOG_PATH,
      JSON.stringify(entry) + "\n",
      { encoding: "utf8" },
    );
  } catch {
    // Logging is best-effort; never block a write on log-append failure.
  }
}

// Tier classification: 6.4 normalized levels mapped to gauge zones.
// Used by the webview's gauge rendering. Stored in the marker so the
// webview doesn't need a provider×model lookup table on its side.
function classifyTier(provider, model) {
  if (!model) return "unknown";
  const m = model.toLowerCase();
  if (provider === "anthropic" || m.includes("claude")) {
    if (m.includes("opus")) return "flagship";
    if (m.includes("sonnet")) return "mid";
    if (m.includes("haiku")) return "low";
  }
  if (provider === "google" || m.includes("gemini")) {
    if (m.includes("pro")) return "flagship";
    if (m.includes("flash-2") || m.includes("flash 2") || m.includes("2.5")) return "mid";
    if (m.includes("flash")) return "low";
  }
  if (provider === "openai" || m.startsWith("o1") || m.startsWith("o3") || m.includes("gpt")) {
    if (m.startsWith("o1") || m.startsWith("o3") || m.includes("5") || m.includes("gpt-4o") && !m.includes("mini")) return "flagship";
    if (m.includes("mini")) return "low";
    return "mid";
  }
  if (provider === "github" || m.includes("copilot")) return "mid";
  return "unknown";
}

function deriveModelDisplayName(provider, model) {
  if (!model || model === "unknown") {
    const p = provider === "anthropic" ? "Claude"
            : provider === "google"    ? "Gemini"
            : provider === "openai"    ? "Codex"
            : provider === "github"    ? "Copilot"
            : "Orchestrator";
    return `${p} (model unknown)`;
  }
  // Best-effort canonicalization. Marker writers can override by sending
  // `modelDisplayName` explicitly in the payload (the manual-override
  // quickpick does so).
  const m = model;
  if (/^claude-opus-4-?7$/i.test(m)) return "Opus 4.7";
  if (/^claude-opus-4-?6$/i.test(m)) return "Opus 4.6";
  if (/^claude-sonnet-4-?6$/i.test(m)) return "Sonnet 4.6";
  if (/^claude-haiku-4-?5/i.test(m)) return "Haiku 4.5";
  if (/^claude-/i.test(m)) return m.replace(/^claude-/i, "").replace(/-/g, " ");
  return m;
}

function deriveProviderDisplayName(provider) {
  switch (provider) {
    case "anthropic": return "Claude";
    case "google":    return "Gemini";
    case "openai":    return "Codex";
    case "github":    return "Copilot";
    default:          return provider || "Orchestrator";
  }
}

// Build the marker object from a payload. Per Set 029 audit Marker schema v2.
function buildMarker(args, payload, nowIso) {
  const writer = args.writer || payload.writer || "unknown";

  // Mode → top-level signalKind / confidence defaults.
  let signalKind = payload.signalKind;
  let confidence = payload.confidence;

  if (args.mode === "session-start") {
    signalKind = signalKind || "current";
    confidence = confidence || "high";
  } else if (args.mode === "user-prompt-submit") {
    // merge-effort mode handled below; not a fresh top-level write.
  } else if (args.mode === "manual") {
    signalKind = signalKind || "manual";
    confidence = confidence || "high";
  } else if (args.mode === "configured-default") {
    signalKind = signalKind || "configured-default";
    confidence = confidence || "medium";
  } else {
    signalKind = signalKind || "current";
    confidence = confidence || "medium";
  }

  // Confidence-low producer rule (Set 029 audit §"Visual treatment by
  // signalKind"): when the model field is missing/null/unparseable on a
  // Claude SessionStart write, force low confidence + model=unknown.
  let provider = payload.provider || "anthropic";
  let model = payload.model;
  const modelMissing = !model || typeof model !== "string" || model.trim() === "" || /^unknown$/i.test(model);
  if (args.mode === "session-start" && modelMissing) {
    confidence = "low";
    model = "unknown";
  }
  if (!model) model = "unknown";

  const modelDisplayName = payload.modelDisplayName || deriveModelDisplayName(provider, model);
  const providerDisplayName = payload.providerDisplayName || deriveProviderDisplayName(provider);
  const tier = payload.tier || classifyTier(provider, model);

  // Effort sub-object.
  const effortIn = payload.effort || {};
  let effort;
  if (args.mode === "session-start") {
    // SessionStart always resets effort to Medium / current (per Set 029
    // pre-implementation verification — /clear fires SessionStart AND
    // /clear represents a fresh-session boundary).
    effort = {
      normalized: "medium",
      native: "default",
      thinking: false,
      signalKind: "current",
      confidence: confidence, // mirror model confidence (low if model unknown)
    };
  } else if (args.mode === "configured-default") {
    effort = {
      normalized: effortIn.normalized || "medium",
      native: effortIn.native || "default",
      thinking: effortIn.thinking === true,
      signalKind: "configured-default",
      confidence: effortIn.confidence || "medium",
    };
  } else if (args.mode === "manual") {
    effort = {
      normalized: effortIn.normalized || "medium",
      native: effortIn.native || effortIn.normalized || "medium",
      thinking: effortIn.thinking === true,
      signalKind: "manual",
      confidence: "high",
    };
  } else {
    effort = {
      normalized: effortIn.normalized || "medium",
      native: effortIn.native || "default",
      thinking: effortIn.thinking === true,
      signalKind: effortIn.signalKind || "current",
      confidence: effortIn.confidence || "high",
    };
  }
  if (effortIn.observedAt) effort.observedAt = effortIn.observedAt;

  return {
    schemaVersion: SCHEMA_VERSION,
    updatedAt: nowIso,
    writer,
    signalKind,
    confidence,
    provider,
    providerDisplayName,
    model,
    modelDisplayName,
    tier,
    effort,
    stalenessMaxSec: typeof payload.stalenessMaxSec === "number"
      ? payload.stalenessMaxSec
      : DEFAULT_STALENESS_MAX_SEC,
  };
}

// Merge an effort-only update onto an existing marker. Used by the
// UserPromptSubmit hook so a /think* observation can update effort
// without clobbering the model signal.
function mergeEffort(existing, payload, writer, nowIso) {
  const eIn = payload.effort || {};
  const merged = {
    ...existing,
    updatedAt: nowIso,
    writer,
    effort: {
      ...existing.effort,
      normalized: eIn.normalized || existing.effort?.normalized || "medium",
      native: eIn.native || existing.effort?.native || "default",
      signalKind: eIn.signalKind || "last-observed",
      confidence: eIn.confidence || "high",
    },
  };
  if (eIn.observedAt) merged.effort.observedAt = eIn.observedAt;
  if (typeof eIn.thinking === "boolean") merged.effort.thinking = eIn.thinking;
  return merged;
}

// Sleep helper for the retry loop.
function sleepSync(ms) {
  // Node's child_process.execSync is overkill; a busy-wait with hint at
  // the event loop via Atomics.wait on a SharedArrayBuffer is the
  // standard sync-sleep pattern. We don't need cross-realm safety here
  // because the script is short-lived; setTimeout would push us into
  // async land and complicate the retry loop.
  const buf = new SharedArrayBuffer(4);
  const view = new Int32Array(buf);
  Atomics.wait(view, 0, 0, ms);
}

// Atomic write: write to <target>.tmp.<pid>.<rand>, then rename onto target.
// On Windows, rename can throw EPERM/EBUSY when a file watcher has the
// target open; the retry loop wraps this.
function atomicWrite(target, jsonText) {
  const tmp = `${target}.tmp.${process.pid}.${Math.floor(Math.random() * 1e9)}`;
  fs.writeFileSync(tmp, jsonText, { encoding: "utf8" });
  try {
    fs.renameSync(tmp, target);
  } catch (err) {
    // Clean up tmp on failure so we don't leak junk under ~/.dabbler.
    try { fs.unlinkSync(tmp); } catch { /* best effort */ }
    throw err;
  }
}

// Per Set 029 audit §"Multi-writer precedence":
//   1. Read existing marker. Missing → write unconditionally.
//   2. If existing is stale → write unconditionally.
//   3. Re-read immediately before atomic write+rename. If proposed
//      signalKind precedence ≥ existing precedence → proceed.
//   4. Skip otherwise; log to orchestrator-writer.log.
//
// The two-read pattern (initial + re-read-before-rename) closes the
// TOCTOU race: another writer that lands between the initial decision
// and our rename will be caught by the re-read and we'll skip rather
// than clobber a now-stronger marker.
function attemptWriteWithPrecedence(proposed, args, nowMs) {
  ensureDir();

  // Read 1: initial decision pass.
  const initial = readExistingMarker();
  if (initial && !args.forceOverride && !isStale(initial, nowMs)) {
    const proposedRank = precedenceIndex(proposed.signalKind);
    const initialRank = precedenceIndex(initial.signalKind);
    if (proposedRank > initialRank) {
      appendWriterLog({
        timestamp: new Date(nowMs).toISOString(),
        writer: proposed.writer,
        proposed: proposed.signalKind,
        existing: initial.signalKind,
        reason: "weaker-than-existing",
      });
      return { written: false, reason: "weaker-than-existing" };
    }
  }

  // Write tmp file BEFORE the re-read so the rename is as close to the
  // re-read as possible — minimizes the residual race window.
  const jsonText = JSON.stringify(proposed, null, 2) + "\n";
  const tmp = `${MARKER_PATH}.tmp.${process.pid}.${Math.floor(Math.random() * 1e9)}`;
  fs.writeFileSync(tmp, jsonText, { encoding: "utf8" });

  try {
    // Read 2: re-read immediately before rename to catch a writer that
    // raced between Read 1 and now. Audit §"Multi-writer precedence"
    // step 3.
    if (!args.forceOverride) {
      const latest = readExistingMarker();
      if (latest && !isStale(latest, Date.now())) {
        const proposedRank = precedenceIndex(proposed.signalKind);
        const latestRank = precedenceIndex(latest.signalKind);
        if (proposedRank > latestRank) {
          // Concurrent writer landed a stronger marker after Read 1.
          // Skip our write; clean up the tmp file.
          try { fs.unlinkSync(tmp); } catch { /* best effort */ }
          appendWriterLog({
            timestamp: new Date().toISOString(),
            writer: proposed.writer,
            proposed: proposed.signalKind,
            existing: latest.signalKind,
            reason: "weaker-than-existing-on-reread",
          });
          return { written: false, reason: "weaker-than-existing-on-reread" };
        }
      }
    }

    fs.renameSync(tmp, MARKER_PATH);
  } catch (err) {
    try { fs.unlinkSync(tmp); } catch { /* best effort */ }
    throw err;
  }
  return { written: true };
}

function runWithRetries(fn) {
  let lastErr = null;
  for (let attempt = 0; attempt < RETRY_BACKOFFS_MS.length + 1; attempt++) {
    try {
      return fn();
    } catch (err) {
      lastErr = err;
      if (attempt < RETRY_BACKOFFS_MS.length) {
        sleepSync(RETRY_BACKOFFS_MS[attempt]);
      }
    }
  }
  throw lastErr;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.mode) {
    process.stderr.write(
      "write-orchestrator-marker.js: --mode is required " +
      "(session-start | user-prompt-submit | manual | configured-default)\n",
    );
    process.exit(2);
  }

  let payload = {};
  const stdinRaw = readStdinSync();
  if (stdinRaw.trim().length > 0) {
    try {
      payload = JSON.parse(stdinRaw);
    } catch (err) {
      // Defensive parse — per R2 the hook payload format may drift.
      // Emit a confidence-low marker on session-start, abort on others.
      if (args.mode === "session-start") {
        payload = {};
      } else {
        process.stderr.write(
          `write-orchestrator-marker.js: stdin JSON parse failed (${err.message}); ` +
          `aborting in mode=${args.mode}\n`,
        );
        process.exit(3);
      }
    }
  }

  const nowMs = Date.now();
  const nowIso = new Date(nowMs).toISOString();

  // Per-mode payload normalization. SessionStart's payload comes straight
  // from the Claude Code hook (session_id, transcript_path, cwd,
  // permission_mode, hook_event_name, source, model, optional agent_type).
  // UserPromptSubmit's payload adds `prompt` (the message text).
  if (args.mode === "session-start") {
    // Provider is fixed to anthropic for the Claude SessionStart hook.
    payload.provider = payload.provider || "anthropic";
    // payload.model comes through from the hook; trip the confidence-low
    // path inside buildMarker if absent.
    if (!args.writer) args.writer = "claude-code-session-start-hook";
  } else if (args.mode === "user-prompt-submit") {
    if (!args.writer) args.writer = "claude-code-user-prompt-submit-hook";
    // Extract /think* prefix from prompt; build the effort sub-object.
    const promptText = typeof payload.prompt === "string" ? payload.prompt : "";
    const trimmed = promptText.trimStart();
    let native = null;
    let normalized = null;
    if (/^\/ultrathink\b/i.test(trimmed)) { native = "/ultrathink"; normalized = "max"; }
    else if (/^\/megathink\b/i.test(trimmed)) { native = "/megathink"; normalized = "extra-high"; }
    else if (/^\/think\b/i.test(trimmed)) { native = "/think"; normalized = "high"; }
    if (!native) {
      // Not a /think* invocation — nothing to do. Exit cleanly so the
      // hook chain doesn't see a non-zero exit and complain.
      process.exit(0);
    }
    payload.effort = {
      normalized,
      native,
      thinking: true,
      signalKind: "last-observed",
      confidence: "high",
      observedAt: nowIso,
    };
  } else if (args.mode === "manual") {
    if (!args.writer) args.writer = "manual-override";
  } else if (args.mode === "configured-default") {
    if (!args.writer) args.writer = "configured-default";
  }

  try {
    runWithRetries(() => {
      if (args.mode === "user-prompt-submit") {
        // Merge-effort path: preserve top-level, update effort only.
        // Per Round A verifier finding (Q6): this branch must close the
        // same TOCTOU race as attemptWriteWithPrecedence. We re-read
        // the marker immediately before the rename and merge effort
        // onto THAT snapshot — never onto a stale snapshot from the
        // initial existence check.
        const initial = readExistingMarker();

        // Build the tmp file from whichever snapshot we currently have.
        // The re-read below may replace `chosen` with a fresher value.
        let chosen;
        if (initial) {
          chosen = mergeEffort(initial, payload, args.writer, nowIso);
        } else {
          // Bootstrap path: no marker exists, create a Medium-default
          // Claude marker with the just-detected /think* effort.
          const bootstrap = buildMarker(
            { ...args, mode: "session-start" },
            { provider: "anthropic", model: "unknown", writer: args.writer },
            nowIso,
          );
          bootstrap.effort = {
            normalized: payload.effort.normalized,
            native: payload.effort.native,
            thinking: true,
            signalKind: "last-observed",
            confidence: "high",
            observedAt: nowIso,
          };
          chosen = bootstrap;
        }

        const tmp = `${MARKER_PATH}.tmp.${process.pid}.${Math.floor(Math.random() * 1e9)}`;

        // Re-read immediately before the rename. If a SessionStart (or
        // any writer) landed between our initial read and now, prefer
        // merging effort onto THAT fresher snapshot instead of
        // clobbering it with our stale bootstrap/merge.
        const latest = readExistingMarker();
        if (latest) {
          // Always prefer the latest top-level signal: merge our effort
          // onto it. (If `initial` was missing and we built a bootstrap,
          // the bootstrap gets discarded — the latest marker is the
          // honest model signal.)
          chosen = mergeEffort(latest, payload, args.writer, nowIso);
        }

        fs.writeFileSync(tmp, JSON.stringify(chosen, null, 2) + "\n", { encoding: "utf8" });
        try {
          fs.renameSync(tmp, MARKER_PATH);
        } catch (err) {
          try { fs.unlinkSync(tmp); } catch { /* best effort */ }
          throw err;
        }
        return { written: true };
      }
      const marker = buildMarker(args, payload, nowIso);
      return attemptWriteWithPrecedence(marker, args, nowMs);
    });
  } catch (err) {
    process.stderr.write(
      `write-orchestrator-marker.js: write failed after retries (${err.message})\n`,
    );
    appendWriterLog({
      timestamp: nowIso,
      writer: args.writer || "unknown",
      proposed: payload.signalKind || args.mode,
      existing: null,
      reason: `write-failed-after-retries: ${err.message}`,
    });
    process.exit(4);
  }
  process.exit(0);
}

main();

```

---

## File 2 (post-fix): src/providers/orchestratorIndicatorProvider.ts

```typescript
// Orchestrator Indicator webview view provider.
//
// Renders two side-by-side semi-circle CSS gauges (Model + Effort)
// driven by ~/.dabbler/current-orchestrator.json. Per Set 029 audit
// (audit-summary.md §"Visual treatment by signalKind" REVISED
// 2026-05-18 + §Q6 stale-state policy + §"Multi-writer precedence").
//
// Height budget: ≤150px content (revised 2026-05-18 from the
// original ≤100px audit D3 after operator-on-device feedback that
// 100px was too small for legible labels and gauges). Container
// height cannot be guaranteed if the operator has dragged the
// divider — CSS uses overflow:auto so content scrolls if compressed
// (audit S3).
//
// Watching strategy: vscode.workspace.createFileSystemWatcher on the
// absolute marker path. We do NOT use chokidar or fs.watch — the VS
// Code-managed watcher integrates with the host's file-system events
// and avoids the Windows ENOSPC failure modes raw fs.watch is known
// for. A 60s poll backstops the watcher for the rare case where the
// watcher misses an event under aggressive antivirus (per R5).

import * as vscode from "vscode";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const MARKER_DIR = path.join(os.homedir(), ".dabbler");
const MARKER_PATH = path.join(MARKER_DIR, "current-orchestrator.json");
const DEFAULT_STALENESS_MAX_SEC = 28800; // 8h
const POLL_BACKSTOP_MS = 60_000;
const RENDER_DEBOUNCE_MS = 50;

interface OrchestratorMarker {
  schemaVersion: number;
  updatedAt: string;
  writer: string;
  signalKind: "current" | "configured-default" | "last-observed" | "manual";
  confidence: "high" | "medium" | "low";
  provider: string;
  providerDisplayName: string;
  model: string;
  modelDisplayName: string;
  tier: "low" | "mid" | "flagship" | "unknown";
  effort: {
    normalized: "low" | "medium" | "high" | "extra-high" | "max";
    native: string;
    thinking: boolean;
    signalKind: "current" | "configured-default" | "last-observed" | "manual";
    confidence: "high" | "medium" | "low";
    observedAt?: string;
  };
  stalenessMaxSec: number;
}

type RenderState =
  | { kind: "empty" }
  | { kind: "loaded"; marker: OrchestratorMarker; stale: boolean; ageSec: number };

export class OrchestratorIndicatorProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "dabblerOrchestratorIndicator";

  private view: vscode.WebviewView | undefined;
  private watcherDisposable: vscode.Disposable | undefined;
  private pollHandle: NodeJS.Timeout | undefined;
  private renderTimer: NodeJS.Timeout | undefined;

  constructor(private readonly extensionUri: vscode.Uri) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };

    webviewView.webview.onDidReceiveMessage((msg) => {
      if (!msg || typeof msg !== "object") return;
      if (msg.command === "installHookClaudeCode") {
        vscode.commands.executeCommand("dabbler.installOrchestratorHook.claudeCode");
      } else if (msg.command === "setOrchestrator") {
        vscode.commands.executeCommand("dabbler.setOrchestrator");
      } else if (msg.command === "openWriterLog") {
        vscode.commands.executeCommand("dabbler.openOrchestratorWriterLog");
      }
    });

    webviewView.onDidDispose(() => {
      this.tearDownWatchers();
      this.view = undefined;
    });

    this.setUpWatchers();
    this.scheduleRender();
  }

  private setUpWatchers(): void {
    this.tearDownWatchers();

    // VS Code's RelativePattern requires either a workspace folder or an
    // absolute Uri base. We give it the .dabbler dir as the absolute
    // base; the watcher fires for creates/changes/deletes on the marker
    // file regardless of whether the file exists at the time the watcher
    // is created.
    const pattern = new vscode.RelativePattern(
      vscode.Uri.file(MARKER_DIR),
      "current-orchestrator.json",
    );
    const watcher = vscode.workspace.createFileSystemWatcher(pattern);
    const trigger = () => this.scheduleRender();
    watcher.onDidCreate(trigger);
    watcher.onDidChange(trigger);
    watcher.onDidDelete(trigger);

    // Poll backstop: re-evaluate every 60s so even a watcher miss can't
    // leave the gauge displaying days-stale data without the stale
    // overlay kicking in.
    this.pollHandle = setInterval(trigger, POLL_BACKSTOP_MS);

    this.watcherDisposable = watcher;
  }

  private tearDownWatchers(): void {
    this.watcherDisposable?.dispose();
    this.watcherDisposable = undefined;
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
      this.pollHandle = undefined;
    }
    if (this.renderTimer) {
      clearTimeout(this.renderTimer);
      this.renderTimer = undefined;
    }
  }

  private scheduleRender(): void {
    // Atomic writes on Windows can fire create+delete+create in quick
    // succession; debounce so we render once per coalesced burst.
    if (this.renderTimer) clearTimeout(this.renderTimer);
    this.renderTimer = setTimeout(() => this.render(), RENDER_DEBOUNCE_MS);
  }

  public render(): void {
    if (!this.view) return;
    const state = this.computeState();
    this.view.webview.html = this.renderHtml(state);
  }

  private computeState(): RenderState {
    let raw: string;
    try {
      raw = fs.readFileSync(MARKER_PATH, "utf8");
    } catch {
      return { kind: "empty" };
    }
    let marker: OrchestratorMarker;
    try {
      marker = JSON.parse(raw) as OrchestratorMarker;
    } catch {
      // Treat a malformed marker as empty so the operator gets the
      // install-CTA path instead of a frozen gauge. The writer log
      // will have the diagnostic if anyone needs to investigate.
      return { kind: "empty" };
    }
    if (!marker || typeof marker !== "object" || !marker.signalKind) {
      return { kind: "empty" };
    }
    const ageSec = (Date.now() - Date.parse(marker.updatedAt)) / 1000;
    const stalenessMaxSec =
      typeof marker.stalenessMaxSec === "number"
        ? marker.stalenessMaxSec
        : DEFAULT_STALENESS_MAX_SEC;
    const stale = ageSec > stalenessMaxSec;
    return { kind: "loaded", marker, stale, ageSec };
  }

  // ------- rendering helpers -------

  private renderHtml(state: RenderState): string {
    const cssUri = this.view!.webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "orchestrator-indicator", "indicator.css"),
    );
    const nonce = String(Math.floor(Math.random() * 1e16));
    const csp =
      `default-src 'none'; ` +
      `style-src ${this.view!.webview.cspSource}; ` +
      `script-src 'nonce-${nonce}';`;

    const body = state.kind === "empty"
      ? this.renderEmpty()
      : this.renderLoaded(state.marker, state.stale, state.ageSec);

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <link rel="stylesheet" href="${cssUri}">
  <title>Orchestrator</title>
</head>
<body>
  <div class="container">${body}</div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('[data-command]').forEach((el) => {
      el.addEventListener('click', () => {
        vscode.postMessage({ command: el.getAttribute('data-command') });
      });
    });
  </script>
</body>
</html>`;
  }

  private renderEmpty(): string {
    return `<div class="empty-state">
  <div class="grey-gauges">
    ${this.renderGaugeSvg("unknown", "current", 0)}
    ${this.renderGaugeSvg("unknown", "current", 0)}
  </div>
  <span>No signal — </span><span class="install-cta" data-command="installHookClaudeCode">install hook</span>
</div>`;
  }

  private renderLoaded(marker: OrchestratorMarker, stale: boolean, ageSec: number): string {
    const modelClasses = [
      "gauge-cell",
      `tier-${marker.tier || "unknown"}`,
      `signal-${marker.signalKind}`,
    ].join(" ");
    const effortClasses = [
      "gauge-cell",
      `effort-${marker.effort.normalized || "unknown"}`,
      `signal-${marker.effort.signalKind || "current"}`,
    ].join(" ");

    const modelNeedle = this.tierToNeedleAngle(marker.tier);
    const effortNeedle = this.effortToNeedleAngle(marker.effort.normalized);

    const modelSuffix = marker.signalKind === "configured-default"
      ? ` <span class="default-pill">DEFAULT</span>`
      : "";
    // Effort suffix is driven by EFFORT'S signalKind, not the top-level
    // model signalKind. (Round B verifier finding Q1, 2026-05-18: the
    // (default) / (manual) branches were incorrectly keyed off the
    // top-level marker.signalKind, which means a Codex configured-default
    // session with a /think* observation would show "(default)" on the
    // effort gauge instead of the time-elapsed suffix it should show.
    // Effort and model signals are independent axes per audit schema v2.)
    const effortSuffix = marker.effort.signalKind === "last-observed" && marker.effort.observedAt
      ? `<div class="gauge-suffix">(last ${marker.effort.native || "/think"} ${this.fmtAge(
          (Date.now() - Date.parse(marker.effort.observedAt)) / 1000,
        )} ago)</div>`
      : marker.effort.signalKind === "configured-default"
        ? `<div class="gauge-suffix">(default)</div>`
        : marker.effort.signalKind === "manual"
          ? `<div class="gauge-suffix">(manual)</div>`
          : "";

    const modelOverlay = marker.signalKind === "last-observed"
      ? `<span class="clock-overlay" title="last observed signal">⏱</span>`
      : marker.signalKind === "manual"
        ? `<span class="operator-overlay" title="set manually">✋</span>`
        : "";
    const effortOverlay = marker.effort.signalKind === "last-observed"
      ? `<span class="clock-overlay" title="last observed signal">⏱</span>`
      : marker.effort.signalKind === "manual"
        ? `<span class="operator-overlay" title="set manually">✋</span>`
        : "";

    const modelTooltip = this.modelTooltip(marker);
    const effortTooltip = this.effortTooltip(marker);

    const thinkingHidden = marker.effort.thinking === undefined ? "hidden" : "";
    const thinkingOn = marker.effort.thinking ? "on" : "";

    const staleClass = stale ? "stale" : "";
    const staleAnnotation = stale
      ? `<div class="last-updated">last updated ${this.fmtAge(ageSec)} ago — stale</div>`
      : `<div class="last-updated">updated ${this.fmtAge(ageSec)} ago</div>`;

    return `<div class="gauges ${staleClass}">
  <div class="${modelClasses}" title="${this.escAttr(modelTooltip)}">
    ${modelOverlay}
    ${this.renderGaugeSvg(marker.tier, marker.signalKind, modelNeedle)}
    <div class="gauge-sublabel">${this.escHtml(marker.providerDisplayName)} ${this.escHtml(marker.modelDisplayName)}${modelSuffix}</div>
  </div>
  <div class="${effortClasses}" title="${this.escAttr(effortTooltip)}">
    ${effortOverlay}
    ${this.renderGaugeSvg(this.effortColorBucket(marker.effort.normalized), marker.effort.signalKind, effortNeedle)}
    <span class="thinking-led ${thinkingOn} ${thinkingHidden}" title="thinking ${marker.effort.thinking ? "on" : "off"}"></span>
    <div class="gauge-sublabel">${this.escHtml(this.effortDisplayName(marker.effort.normalized))}</div>
    ${effortSuffix}
  </div>
</div>
${staleAnnotation}`;
  }

  private renderGaugeSvg(tier: string, signalKind: string, needleAngleDeg: number): string {
    // 70×38 semi-circle. cx=35, cy=35 puts the needle pivot at the
    // bottom-mid; the arc spans from leftmost (7,35) through top (35,7)
    // to rightmost (63,35). Needle origin is (35,35); rotating by
    // needleAngleDeg, where -90° points up (top center), -180° points
    // left (low zone), 0° points right (flagship zone).
    //
    // Round B verifier finding 2026-05-18 (Q4): the prior implementation
    // used a `180 + angle` adjustment that inverted the y-axis,
    // sending -90° DOWN instead of UP and pushing all needle/fill
    // endpoints below the visible viewBox. Corrected by using the angle
    // directly (no offset). In SVG, y increases downward, so for
    // `needleAngleDeg = -90` (intended: up), Math.sin(-90°) = -1, and
    // `cy + radius * (-1) = cy - radius` correctly places the endpoint
    // at (cx, cy-radius) = top-center.
    const cx = 35;
    const cy = 35;
    const radius = 28;
    const arcBg = `M${cx - radius},${cy} A${radius},${radius} 0 0 1 ${cx + radius},${cy}`;

    // Clamp the angle to the upper semicircle (-180..0). Compute the
    // fill arc's endpoint and the needle tip from that.
    const fillAngleDeg = Math.max(-180, Math.min(0, needleAngleDeg));
    const fillAngleRad = (fillAngleDeg * Math.PI) / 180;
    const fillEndX = cx + radius * Math.cos(fillAngleRad);
    const fillEndY = cy + radius * Math.sin(fillAngleRad);
    // All upper-semicircle arcs from leftmost (-180°) clockwise to any
    // angle in [-180, 0] traverse ≤180° → largeArc=0 always.
    const arcFill = `M${cx - radius},${cy} A${radius},${radius} 0 0 1 ${fillEndX.toFixed(2)},${fillEndY.toFixed(2)}`;

    const needleAngleRad = (needleAngleDeg * Math.PI) / 180;
    const needleLength = radius - 4;
    const needleTipX = cx + needleLength * Math.cos(needleAngleRad);
    const needleTipY = cy + needleLength * Math.sin(needleAngleRad);

    return `<svg class="gauge-svg" viewBox="0 0 70 38" data-tier="${this.escAttr(tier)}" data-signal="${this.escAttr(signalKind)}">
  <path class="gauge-arc-bg" d="${arcBg}" />
  <path class="gauge-arc-fill" d="${arcFill}" />
  <path class="gauge-rim" d="${arcBg}" />
  <line class="gauge-needle" x1="${cx}" y1="${cy}" x2="${needleTipX.toFixed(2)}" y2="${needleTipY.toFixed(2)}" />
  <circle class="gauge-needle-pivot" cx="${cx}" cy="${cy}" r="1.6" />
</svg>`;
  }

  private tierToNeedleAngle(tier: string): number {
    // -180° = leftmost (low), -90° = top-center, 0° = rightmost (flagship).
    switch (tier) {
      case "low":      return -150;
      case "mid":      return -90;
      case "flagship": return -30;
      case "unknown":  return -90;
      default:         return -90;
    }
  }

  private effortToNeedleAngle(effort: string): number {
    // 5-level effort scale where Medium is the operator-facing
    // "default" (audit D6). Place Medium at the gauge center (-90°)
    // so the default state reads as "neutral" (half-filled arc), and
    // spread the escalations Low / High / Extra-High / Max around it.
    // Operator feedback 2026-05-18: Medium at -120° rendered with a
    // too-short color arc that looked "low" against the Model gauge's
    // longer arc — re-centering Medium fixes the visual imbalance
    // while preserving the red→green polarity.
    switch (effort) {
      case "low":        return -150;
      case "medium":     return -90;
      case "high":       return -60;
      case "extra-high": return -35;
      case "max":        return -15;
      default:           return -90;
    }
  }

  private effortColorBucket(effort: string): string {
    // Reuse tier color classes for the effort gauge: map normalized
    // effort → tier-class for the stroke color.
    switch (effort) {
      case "low":        return "low";
      case "medium":     return "mid";
      case "high":       return "mid";
      case "extra-high": return "flagship";
      case "max":        return "flagship";
      default:           return "unknown";
    }
  }

  private effortDisplayName(effort: string): string {
    switch (effort) {
      case "low":        return "Low";
      case "medium":     return "Medium";
      case "high":       return "High";
      case "extra-high": return "Extra-High";
      case "max":        return "Max";
      default:           return "Unknown";
    }
  }

  private modelTooltip(marker: OrchestratorMarker): string {
    const conf = marker.confidence;
    switch (marker.signalKind) {
      case "current":
        return conf === "low"
          ? "live signal (low confidence — hook payload missing model)"
          : `live signal (${conf} confidence)`;
      case "configured-default":
        return "configured default (medium confidence — does not track runtime changes)";
      case "last-observed":
        return "last observed via /think (high confidence in detection, but may not reflect current message)";
      case "manual":
        return "set manually (high confidence)";
      default:
        return "";
    }
  }

  private effortTooltip(marker: OrchestratorMarker): string {
    const eSig = marker.effort.signalKind;
    if (eSig === "last-observed" && marker.effort.observedAt) {
      const age = this.fmtAge((Date.now() - Date.parse(marker.effort.observedAt)) / 1000);
      return `last observed ${age} ago via ${marker.effort.native || "/think"} (high confidence in detection, but may not reflect current message)`;
    }
    if (eSig === "configured-default") {
      return "configured default effort (medium confidence — does not track runtime changes)";
    }
    if (eSig === "manual") {
      return "set manually (high confidence)";
    }
    return `effort: ${this.effortDisplayName(marker.effort.normalized)} (${marker.effort.confidence} confidence)`;
  }

  private fmtAge(seconds: number): string {
    if (!isFinite(seconds) || seconds < 0) return "?";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
  }

  private escHtml(s: string): string {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  private escAttr(s: string): string {
    return this.escHtml(s).replace(/"/g, "&quot;");
  }
}

```

---

## File 3 (post-fix): media/orchestrator-indicator/indicator.css

```css
/*
 * Orchestrator Indicator gauges — semi-circle CSS gauges, two side-by-side.
 *
 * Visual-treatment matrix per Set 029 audit (audit-summary.md §"Visual
 * treatment by signalKind", REVISED 2026-05-18):
 *
 *   current             → solid fill, solid rim, no badge
 *   configured-default  → solid fill ~85% opacity, dashed rim, "DEFAULT" pill
 *   last-observed       → hollow rim + filled needle + clock-icon overlay + time-elapsed suffix
 *   manual              → solid fill + operator-icon overlay
 *   stale (signal-agnostic) → diagonal-stripe overlay at 50% opacity over underlying treatment
 *
 * Height budget: ≤150px total visible content (operator-revised
 * 2026-05-18 from the original ≤100px after seeing the rendered
 * gauges in S2 — too small for legibility). VS Code's standard view
 * header (~22px) sits above this. Container height cannot be
 * guaranteed if the operator has resized; the outer scroll-wrapper
 * enables vertical scroll as the fallback per audit S3.
 */

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  font-family: var(--vscode-font-family);
  font-size: var(--vscode-font-size);
  color: var(--vscode-foreground);
  background: transparent;
}

.container {
  height: 100vh;
  max-height: 150px;
  overflow-y: auto;     /* per audit S3 — scrollable if compressed below 150px */
  overflow-x: hidden;
  padding: 6px 8px 4px 8px;
}

.gauges {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: start;
}

/* Responsive wrap: when the panel is narrow, stack the second gauge
 * below the first instead of squishing both into one row.
 * Threshold 260px reflects the smallest width at which two
 * ~100px-wide gauges still fit side-by-side with sublabel text
 * readable. Operator-flagged 2026-05-18.
 */
@media (max-width: 260px) {
  .gauges {
    grid-template-columns: 1fr;
  }
}

.gauge-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  font-size: 14px;
  line-height: 1.2;
}

/* Semi-circle gauge — a half-circle with a needle.
 * Render order: arc background → colored fill arc (clipped to needle angle)
 * → rim → needle → overlays. We use SVG inside .gauge-svg so the arc
 * geometry is precise across DPI.
 */
.gauge-svg {
  width: 100px;
  height: 54px;          /* 2:1 aspect, semi-circle. ~43% bigger than v0.14.2-initial */
  display: block;
}

.gauge-arc-bg {
  fill: none;
  stroke: var(--vscode-editorWidget-border, #444);
  stroke-width: 7;
  stroke-linecap: butt;
}

.gauge-arc-fill {
  fill: none;
  stroke-width: 7;
  stroke-linecap: butt;
}

.gauge-rim {
  fill: none;
  stroke: var(--vscode-foreground);
  stroke-width: 1;
  stroke-opacity: 0.6;
}

.gauge-needle {
  stroke: var(--vscode-foreground);
  stroke-width: 1.4;
  stroke-linecap: round;
}

.gauge-needle-pivot {
  fill: var(--vscode-foreground);
}

.gauge-sublabel {
  margin-top: 2px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.gauge-suffix {
  font-size: 12px;
  opacity: 0.75;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* Tier color polarity (Set 029 D5): red=low/low-effort, green=flagship/max-effort */
.tier-low      .gauge-arc-fill { stroke: #e06c75; }   /* red */
.tier-mid      .gauge-arc-fill { stroke: #e5c07b; }   /* yellow */
.tier-flagship .gauge-arc-fill { stroke: #98c379; }   /* green */
.tier-unknown  .gauge-arc-fill { stroke: var(--vscode-disabledForeground, #888); }

.effort-low        .gauge-arc-fill { stroke: #e06c75; }
.effort-medium     .gauge-arc-fill { stroke: #d19a66; }   /* orange */
.effort-high       .gauge-arc-fill { stroke: #e5c07b; }   /* yellow */
.effort-extra-high .gauge-arc-fill { stroke: #b5cea8; }   /* light green */
.effort-max        .gauge-arc-fill { stroke: #98c379; }   /* green */
.effort-unknown    .gauge-arc-fill { stroke: var(--vscode-disabledForeground, #888); }

/* signalKind treatments */
.signal-current      .gauge-arc-fill { stroke-opacity: 1; }
.signal-configured-default .gauge-arc-fill { stroke-opacity: 0.85; }
.signal-configured-default .gauge-rim {
  stroke-dasharray: 2 2;
  stroke-opacity: 1;
}
.signal-last-observed .gauge-arc-fill {
  stroke-opacity: 0;        /* hollow rim — no fill */
}
.signal-last-observed .gauge-rim {
  stroke-opacity: 1;
  stroke-width: 1.5;
}
.signal-manual .gauge-arc-fill { stroke-opacity: 1; }

/* Pill badge for configured-default */
.default-pill {
  display: inline-block;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  margin-left: 4px;
  border: 1px solid var(--vscode-foreground);
  border-radius: 4px;
  opacity: 0.8;
  vertical-align: middle;
}

/* Clock-icon overlay for last-observed */
.clock-overlay {
  position: absolute;
  top: 0;
  right: 6px;
  font-size: 14px;
  opacity: 0.85;
  line-height: 1;
}

/* Operator-icon overlay for manual */
.operator-overlay {
  position: absolute;
  top: 0;
  right: 6px;
  font-size: 14px;
  opacity: 0.85;
  line-height: 1;
}

/* Thinking LED — a small dot right of the effort gauge */
.thinking-led {
  position: absolute;
  top: 20px;
  right: -3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--vscode-foreground);
  background: transparent;
  opacity: 0.5;
}
.thinking-led.on {
  background: #98c379;
  opacity: 1;
  box-shadow: 0 0 3px #98c379;
}
.thinking-led.hidden { display: none; }

/* Stale-state overlay — diagonal stripes painted ON TOP of the gauge
 * artwork, not behind it (Round A verifier finding 2026-05-18: a
 * background-image on .gauge-svg paints behind the SVG content and
 * doesn't actually overlay the rendered strokes). Signal-agnostic
 * per audit-summary §Q6 — overlays on top of whatever the underlying
 * signalKind treatment is.
 *
 * Implementation: position the .gauge-cell as a positioning context;
 * a ::before pseudo-element absolute-positioned over the SVG paints
 * the diagonal stripes at higher opacity than the prior background-
 * image approach (~45% vs. the audit's "50%" target).
 */
.stale .gauge-cell {
  /* .gauge-cell is already position: relative; pseudo-element will
   * overlay its bounding box, which is just slightly larger than the
   * SVG itself. */
}
.stale .gauge-cell::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 54px;  /* matches .gauge-svg height — only stripe over the gauge, not the sublabel */
  pointer-events: none;
  z-index: 2;    /* SVG renders at default z-index 0; pseudo above */
  background-image: repeating-linear-gradient(
    -45deg,
    rgba(255, 255, 255, 0.45) 0px,
    rgba(255, 255, 255, 0.45) 4px,
    transparent 4px,
    transparent 10px
  );
}

/* Last-updated annotation under both gauges */
.last-updated {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 2px;
  text-align: center;
}

/* Empty state ("No signal — install hook") */
.empty-state {
  padding: 8px 6px 0 6px;
  font-size: 14px;
  line-height: 1.3;
  text-align: center;
}
.empty-state .grey-gauges {
  display: flex;
  justify-content: center;
  gap: 18px;
  opacity: 0.45;
  margin-bottom: 6px;
}
.empty-state .install-cta {
  display: inline-block;
  color: var(--vscode-textLink-foreground);
  cursor: pointer;
  text-decoration: underline;
}
.empty-state .install-cta:hover { color: var(--vscode-textLink-activeForeground); }

```
