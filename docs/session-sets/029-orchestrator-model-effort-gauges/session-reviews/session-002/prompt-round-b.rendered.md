# Session 2 verification — Round B (provider + installer)

## Context

Round A (marker writer + CSS visual matrix) was reviewed by gpt-5-4 and
returned with three must-fix items, all applied:

1. **TOCTOU race in `attemptWriteWithPrecedence`** — added re-read-
   immediately-before-rename in `write-orchestrator-marker.js` per
   audit §"Multi-writer precedence" step 3.
2. **UserPromptSubmit merge/bootstrap clobber risk** — added re-read
   in the merge branch; the latest-marker snapshot wins, merging
   effort onto fresher top-level state rather than overwriting it.
3. **Stale stripes were a `background-image` painted BEHIND the SVG,
   not an overlay** — replaced with a `.stale .gauge-cell::before`
   absolute-positioned pseudo-element painting at 45% alpha above
   the gauge artwork.
4. Plus: superseding note added to `audit-summary.md` D3 + spec.md D3
   documenting the operator's 100→150px revision.

Marker writer smoke-test re-run after the fixes: all six paths still
behave correctly. Playwright suite (8 scenarios) still green after
the CSS overlay change. Round A's blockers are addressed.

This is **Round B of two** — focused on the provider (webview rendering)
and the Claude Code hook installer. Code under review:

1. **`src/providers/orchestratorIndicatorProvider.ts`** (~395 LOC) —
   `WebviewViewProvider` for `dabblerOrchestratorIndicator`. Marker
   reader + FileSystemWatcher + 60s poll backstop + 50ms render
   debounce; renderHtml/renderLoaded/renderEmpty + visual-treatment
   class composition + tooltip text composition + effort/tier needle
   angles + display-name + CSP nonce + webview message-passing for
   the install CTA.

2. **`src/commands/installOrchestratorHookClaudeCode.ts`** (~170 LOC) —
   idempotent edit of `~/.claude/settings.json`. Adds SessionStart
   hooks for all four source matchers (startup/resume/clear/compact)
   + one UserPromptSubmit hook. Both pipe their payload to the
   marker writer. Preserves foreign hooks. Atomic write to the
   settings file.

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Provider — visual-treatment matrix wiring.**
   The provider emits CSS classes that the CSS hooks into for the
   visual treatments. `renderLoaded` composes:
   ```
   modelClasses = "gauge-cell tier-<X> signal-<Y>"
   effortClasses = "gauge-cell effort-<Z> signal-<W>"
   ```
   And then conditionally renders:
   - `modelSuffix` = ` <span class="default-pill">DEFAULT</span>` when
     top-level signalKind is `configured-default`
   - `effortSuffix` = `(last ${native} ${age} ago)` div when
     effort.signalKind is `last-observed`, else `(default)` for
     `configured-default`, else `(manual)` for `manual`, else empty
   - `modelOverlay` / `effortOverlay` = clock-icon span for
     `last-observed`, operator-icon span for `manual`, else empty
   Verify the matrix is wired correctly:
   - Does the model gauge's `configured-default` get the DEFAULT
     pill in its sublabel? (Yes — `modelSuffix` is conditional on
     `marker.signalKind === "configured-default"`.)
   - Does the effort gauge get the time-elapsed sublabel when
     `effort.signalKind === "last-observed"`? (Yes.)
   - Does the model gauge get the clock-icon overlay when its
     top-level `signalKind === "last-observed"`, independently of
     effort? (Yes — `modelOverlay` keys off `marker.signalKind`.)
   - Does the effort gauge's color come from `effort.normalized`
     (low/medium/high/etc.) NOT from `marker.tier`? `effortClasses`
     uses `effort-${marker.effort.normalized}` for the color class
     but separately passes `this.effortColorBucket(...)` to
     `renderGaugeSvg` for the data attribute. Cross-check that the
     SVG's color comes from the CSS `.effort-medium .gauge-arc-fill`
     etc. rules — not from the data-tier attribute. (The data-tier
     attribute on the SVG is informational, not styled — the styled
     classes are on the parent `.gauge-cell`. Verify CSS specificity
     resolves the way the provider intends.)

**Q2. Provider — staleness handling.**
   `computeState` reads the marker, parses it, computes `ageSec =
   (Date.now() - Date.parse(marker.updatedAt)) / 1000`, then
   `stale = ageSec > stalenessMaxSec` (defaulting to 28800s = 8h).
   `renderLoaded` adds `.stale` to `.gauges` when stale and renders
   `last updated Xh ago — stale` annotation; otherwise `updated Xs/m/h
   ago` (no "— stale" suffix). Audit Q6 says no-install-CTA on stale
   (only on missing-marker) — the empty-state CTA only renders when
   `state.kind === "empty"`, which happens when the file is absent
   or unparseable, NOT when the file is stale. Correct?

**Q3. Provider — watcher robustness.**
   - The watcher uses
     `vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(MARKER_DIR), "current-orchestrator.json"))`
   - 60s poll backstop via setInterval
   - 50ms render debounce on each trigger
   - `setUpWatchers` calls `tearDownWatchers` first so a re-resolve
     doesn't double-bind
   Any robustness gaps:
   - Watcher fires on create/change/delete; if the marker file is
     atomically replaced (write tmp + rename onto target), Windows
     fires `create` for the tmp file + `change` or `delete+create`
     for the target. The 50ms debounce coalesces these. Adequate?
   - What if `~/.dabbler` doesn't exist yet (e.g., the operator
     has never invoked the hook)? Does `createFileSystemWatcher`
     fail silently on a non-existent base path, or does it watch
     for the directory to appear?
   - The 60s poll is the failsafe for watcher misses. If the
     operator's filesystem is slow (network drive, antivirus
     scanning), a watcher miss could be 60s late. Acceptable?

**Q4. Provider — render pipeline correctness.**
   - `renderHtml` builds a CSP-restricted HTML doc with a per-render
     nonce; the script block uses `acquireVsCodeApi` to expose
     `vscode.postMessage` to the click handlers; the message-passing
     handler dispatches `dabbler.installOrchestratorHook.claudeCode` /
     `dabbler.setOrchestrator` / `dabbler.openOrchestratorWriterLog`
   - `renderEmpty` uses two grey SVG gauges (tier=unknown,
     signalKind=current, needle=0) plus the install-CTA span
   - `renderGaugeSvg` computes SVG arc geometry using cx=35, cy=35,
     radius=28 on a 70×38 viewBox; the SVG is CSS-scaled to 100×54
     (the viewBox preserves aspect, so stroke-width and arc geometry
     scale uniformly)
   - Tooltips embed confidence per the audit matrix: "live signal
     (high confidence)" / "live signal (low confidence — hook payload
     missing model)" / "configured default (medium confidence —
     does not track runtime changes)" / "last observed Xm ago via
     /think (high confidence in detection, but may not reflect
     current message)" / "set manually (high confidence)"
   - `fmtAge` returns "Xs" / "Xm" / "Xh" / "Xd" depending on
     magnitude
   Any correctness issues with the render pipeline?

**Q5. Hook installer — idempotence.**
   `ensureMatcherEntry` iterates the existing entry array, looks for
   one whose matcher matches AND whose `hooks` contains a command
   referencing "write-orchestrator-marker.js"; if found, upgrades the
   command in place; otherwise appends a new entry.
   Trace cases:
   - **First install (no settings.json):** loadClaudeSettings returns
     `{ exists: false, settings: {} }`. We append SessionStart × 4
     matchers + UserPromptSubmit × 1 (no matcher). Writes a fresh
     `~/.claude/settings.json` with the dabbler entries.
   - **Re-install (extension already installed):** existing dabbler
     entries get their commands replaced in place with the current
     helper path; no duplicates added.
   - **Operator has their own SessionStart hook (foreign):** the
     installer iterates entries and only matches when matcher AND
     write-orchestrator-marker.js substring both check. Foreign
     entries pass through untouched.
   - **Operator has renamed the helper script:** the substring check
     misses the renamed entry, so the installer appends a NEW entry
     instead of upgrading the renamed one. Duplicate hooks fire on
     SessionStart. Is this a material concern?

**Q6. Hook installer — source matcher coverage.**
   Installer adds SessionStart hooks for all four source values:
   `startup`, `resume`, `clear`, `compact`. The R7 pre-implementation
   verification confirmed `/clear` fires SessionStart with
   `source: "clear"` AND `/think*` is per-message (so /clear is a
   fresh-session boundary). For `compact` (mid-conversation context
   compression), is treating it as a session boundary correct? The
   compact-time marker write resets effort to Medium and refreshes
   the model — that's correct if the operator's `/model` selection
   carries through compaction (which it should, per Claude Code
   semantics), but the effort reset may be aggressive if the
   operator had `/megathink`-style escalation that they expected to
   carry through the compaction. Is the spec-intended behavior to
   clobber on `compact` or to preserve effort?

**Q7. Hook installer — command quoting + portability.**
   `buildHookCommand` returns `node "${helperAbsPath}" --mode ${mode}`.
   The double-quote wrapping handles paths with spaces (`C:\Users\Some
   Name\...`). Trace edge cases:
   - **Backslashes in helperAbsPath:** on Windows, the path is like
     `C:\Users\denmi\source\repos\dabbler-ai-orchestration\tools\
     dabbler-ai-orchestration\scripts\write-orchestrator-marker.js`.
     The string is embedded raw in JSON — `JSON.stringify` will
     escape backslashes to `\\`, so the JSON-on-disk has `node
     "C:\\\\Users\\\\..."`. When Claude Code reads the JSON and shells
     out the command, the shell sees `node "C:\Users\..."` (single
     backslashes) which Windows handles correctly. Verify the
     escaping round-trip.
   - **Special chars in the path** (single quotes, double quotes,
     dollar signs, ampersands): the operator's HOME path
     theoretically might contain these. The double-quote wrapping
     handles double quotes if escaped, but doesn't handle them if
     unescaped (would close the quoted region). Practical concern,
     or theoretical?
   - **POSIX shell vs. cmd.exe:** Claude Code hook docs say the
     command is invoked via the OS shell. On Windows, that's cmd.exe
     by default, which handles double-quote wrapping but has its own
     escaping rules. Any portability concern?

**Q8. Hook installer — settings.json atomic write.**
   `writeClaudeSettings` writes to a tmp file with `.tmp.<pid>.<rand>`
   suffix then renames. Same atomic pattern as the marker writer.
   `loadClaudeSettings` reads via `fs.readFileSync` (utf8); throws if
   JSON is malformed (user-facing error message, no clobber).
   `mkdirSync(path.dirname(settingsPath), { recursive: true })` to
   handle a first-install case where `~/.claude/` doesn't exist.
   Concerns:
   - Concurrent writes (two installer invocations racing): the
     atomic rename ensures either write lands, but the LATER one
     overwrites the EARLIER one. Should the installer take a file
     lock or check-and-merge? Likely overkill for an installer
     that runs <1× per install, but call it out.
   - Error path: if `writeClaudeSettings` throws, the show-error-
     message surfaces the error to the operator. The error message
     includes the underlying exception's `.message`. Adequate?

**Q9. Provider <-> installer integration.**
   The webview's empty-state CTA calls `dabbler.installOrchestrator
   Hook.claudeCode` via `webview.postMessage`. The provider receives
   it in `onDidReceiveMessage` and dispatches via
   `vscode.commands.executeCommand`. The command is registered by
   `registerInstallOrchestratorHookClaudeCodeCommand` in
   `extension.ts`. Verify end-to-end:
   - Provider HTML's `.install-cta` has `data-command="installHookClaudeCode"`.
   - Script block listens for clicks on `[data-command]`, posts
     `{ command: "installHookClaudeCode" }`.
   - Provider's `onDidReceiveMessage` maps `installHookClaudeCode`
     → `vscode.commands.executeCommand("dabbler.installOrchestratorHook.claudeCode")`.
   - extension.ts registers `dabbler.installOrchestratorHook.claudeCode`.
   - package.json declares the command in `contributes.commands`.
   Any link in this chain that doesn't resolve?

**Q10. Round B overall verdict.**
   Are the provider + installer ready to close out? Smallest concrete
   must-fix items, if any?

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.


---

## File 1: src/providers/orchestratorIndicatorProvider.ts

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
    const effortSuffix = marker.effort.signalKind === "last-observed" && marker.effort.observedAt
      ? `<div class="gauge-suffix">(last ${marker.effort.native || "/think"} ${this.fmtAge(
          (Date.now() - Date.parse(marker.effort.observedAt)) / 1000,
        )} ago)</div>`
      : marker.signalKind === "configured-default"
        ? `<div class="gauge-suffix">(default)</div>`
        : marker.signalKind === "manual"
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
    // 70×38 semi-circle. cx=35, cy=35 puts the center at the bottom-mid
    // and the arc spans from (5,35) to (65,35) going up. Needle origin
    // is (35,35); rotating by needleAngleDeg, where -90° points up,
    // -180° points left (low zone), 0° points right (flagship zone).
    const cx = 35;
    const cy = 35;
    const radius = 28;
    // SVG arc path from leftmost (5,35) to rightmost (65,35) via top.
    const arcBg = `M${cx - radius},${cy} A${radius},${radius} 0 0 1 ${cx + radius},${cy}`;
    // Fill arc clipped from start to needle angle: we approximate by
    // drawing an arc from (cx-radius, cy) to the needle tip projected on
    // the rim, with the largeArc flag set when angle > 90°. needleAngle
    // is measured in degrees from "12 o'clock straight up", positive
    // = clockwise. We convert to the SVG arc endpoint.
    const fillAngleDeg = Math.max(-180, Math.min(0, needleAngleDeg)); // clamp -180..0
    const fillEndX = cx + radius * Math.cos(((180 + fillAngleDeg) * Math.PI) / 180);
    const fillEndY = cy + radius * Math.sin(((180 + fillAngleDeg) * Math.PI) / 180);
    const largeArc = fillAngleDeg > -90 ? 1 : 0;
    const arcFill = `M${cx - radius},${cy} A${radius},${radius} 0 ${largeArc} 1 ${fillEndX.toFixed(2)},${fillEndY.toFixed(2)}`;

    const needleLength = radius - 4;
    const needleTipX = cx + needleLength * Math.cos(((180 + needleAngleDeg) * Math.PI) / 180);
    const needleTipY = cy + needleLength * Math.sin(((180 + needleAngleDeg) * Math.PI) / 180);

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

## File 2: src/commands/installOrchestratorHookClaudeCode.ts

```typescript
// Claude Code orchestrator-hook installer.
//
// Adds (or refreshes) two hooks in ~/.claude/settings.json:
//   - SessionStart  → pipes hook payload into write-orchestrator-marker.js
//                     with --mode session-start (writes the model + Medium
//                     default effort to ~/.dabbler/current-orchestrator.json
//                     per Set 029 Q5 + R7 locked design).
//   - UserPromptSubmit → pipes hook payload into the same helper with
//                     --mode user-prompt-submit (detects /think* prefixes
//                     and updates effort.signalKind to last-observed).
//
// The command is idempotent. It locates an existing dabbler entry by
// matcher AND command-path-substring ("write-orchestrator-marker.js");
// re-running upgrades the command string to the current shipped helper
// path without duplicating entries. Other hooks the operator may have
// installed (independent SessionStart matchers, foreign commands) are
// preserved verbatim.

import * as vscode from "vscode";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const HELPER_REL = path.join("scripts", "write-orchestrator-marker.js");

interface HookCommandEntry {
  type: string;
  command: string;
}
interface HookMatcherEntry {
  matcher?: string;
  hooks: HookCommandEntry[];
}
interface ClaudeSettings {
  hooks?: {
    SessionStart?: HookMatcherEntry[];
    UserPromptSubmit?: HookMatcherEntry[];
    [k: string]: HookMatcherEntry[] | undefined;
  };
  [k: string]: unknown;
}

function helperPathAbs(extensionUri: vscode.Uri): string {
  return vscode.Uri.joinPath(extensionUri, HELPER_REL).fsPath;
}

function buildHookCommand(helperAbsPath: string, mode: "session-start" | "user-prompt-submit"): string {
  // Claude Code hooks invoke a shell command and pipe the JSON payload
  // to its stdin. node + the absolute helper path + --mode flag is the
  // simplest portable invocation across Windows/macOS/Linux.
  // We quote the helper path in case the path contains spaces (e.g.,
  // "C:\Program Files\..." or "C:\Users\Some Name\..."). Backslashes
  // need no escaping inside the double-quoted string for the shell
  // executors Claude Code runs.
  return `node "${helperAbsPath}" --mode ${mode}`;
}

function ensureMatcherEntry(
  entries: HookMatcherEntry[] | undefined,
  matcher: string | undefined,
  command: string,
): HookMatcherEntry[] {
  const list = Array.isArray(entries) ? entries.slice() : [];

  // Find an existing entry: same matcher (or both undefined) AND already
  // points at write-orchestrator-marker.js. Update in place if found.
  for (let i = 0; i < list.length; i++) {
    const entry = list[i];
    const matcherMatches =
      (entry.matcher ?? undefined) === (matcher ?? undefined);
    if (!matcherMatches) continue;
    if (!Array.isArray(entry.hooks)) continue;
    let updated = false;
    const newHooks = entry.hooks.map((h) => {
      if (h.type === "command" && typeof h.command === "string" && h.command.includes("write-orchestrator-marker.js")) {
        updated = true;
        return { type: "command", command };
      }
      return h;
    });
    if (updated) {
      list[i] = { ...entry, hooks: newHooks };
      return list;
    }
  }

  // No existing entry — append a fresh one. Keep matcher only if the
  // caller specified one; Claude Code treats omitted matcher as "match
  // all", which is what UserPromptSubmit wants.
  const newEntry: HookMatcherEntry =
    matcher !== undefined
      ? { matcher, hooks: [{ type: "command", command }] }
      : { hooks: [{ type: "command", command }] };
  list.push(newEntry);
  return list;
}

function loadClaudeSettings(): { settings: ClaudeSettings; path: string; exists: boolean } {
  const settingsPath = path.join(os.homedir(), ".claude", "settings.json");
  if (!fs.existsSync(settingsPath)) {
    return { settings: {}, path: settingsPath, exists: false };
  }
  const raw = fs.readFileSync(settingsPath, "utf8");
  let parsed: ClaudeSettings;
  try {
    parsed = JSON.parse(raw) as ClaudeSettings;
  } catch (err) {
    // Don't clobber a malformed file — bail out with a clear message.
    throw new Error(
      `~/.claude/settings.json contains invalid JSON (${(err as Error).message}). ` +
      `Fix or back up the file, then re-run the install command.`,
    );
  }
  return { settings: parsed || {}, path: settingsPath, exists: true };
}

function writeClaudeSettings(settingsPath: string, settings: ClaudeSettings): void {
  fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
  const text = JSON.stringify(settings, null, 2) + "\n";
  // Atomic write: tmp + rename. Same precaution as the marker writer
  // because ~/.claude/settings.json is sometimes open by other Claude
  // tooling.
  const tmp = `${settingsPath}.tmp.${process.pid}.${Math.floor(Math.random() * 1e9)}`;
  fs.writeFileSync(tmp, text, { encoding: "utf8" });
  fs.renameSync(tmp, settingsPath);
}

export async function installClaudeCodeOrchestratorHook(
  extensionUri: vscode.Uri,
): Promise<void> {
  const helperAbs = helperPathAbs(extensionUri);
  if (!fs.existsSync(helperAbs)) {
    vscode.window.showErrorMessage(
      `Cannot install hook: helper script not found at ${helperAbs}. ` +
      `Re-install the Dabbler AI Orchestration extension.`,
    );
    return;
  }

  let loaded: { settings: ClaudeSettings; path: string; exists: boolean };
  try {
    loaded = loadClaudeSettings();
  } catch (err) {
    vscode.window.showErrorMessage((err as Error).message);
    return;
  }
  const { settings, path: settingsPath, exists } = loaded;

  const sessionStartCmd = buildHookCommand(helperAbs, "session-start");
  const userPromptSubmitCmd = buildHookCommand(helperAbs, "user-prompt-submit");

  settings.hooks = settings.hooks || {};

  // SessionStart: install one entry per source matcher we care about.
  // The Claude Code docs list four source values: startup, resume, clear,
  // compact. We attach to all four so the gauge updates on every session
  // boundary. The matcher field accepts a single value per entry; we
  // create one entry per matcher to keep the resulting settings.json
  // readable and easy to remove by hand.
  for (const matcher of ["startup", "resume", "clear", "compact"]) {
    settings.hooks.SessionStart = ensureMatcherEntry(
      settings.hooks.SessionStart,
      matcher,
      sessionStartCmd,
    );
  }

  // UserPromptSubmit: one entry, no matcher (fire on every prompt). The
  // helper short-circuits non-/think* prompts at zero cost.
  settings.hooks.UserPromptSubmit = ensureMatcherEntry(
    settings.hooks.UserPromptSubmit,
    undefined,
    userPromptSubmitCmd,
  );

  try {
    writeClaudeSettings(settingsPath, settings);
  } catch (err) {
    vscode.window.showErrorMessage(
      `Failed to write ${settingsPath}: ${(err as Error).message}`,
    );
    return;
  }

  const verbWasWord = exists ? "Updated" : "Created";
  vscode.window
    .showInformationMessage(
      `${verbWasWord} ~/.claude/settings.json with Dabbler orchestrator hooks ` +
      `(SessionStart + UserPromptSubmit). Restart Claude Code or run /clear in ` +
      `an active session to populate the indicator.`,
      "Open settings.json",
    )
    .then((picked) => {
      if (picked === "Open settings.json") {
        vscode.workspace.openTextDocument(settingsPath).then(
          (doc) => vscode.window.showTextDocument(doc),
          () => undefined,
        );
      }
    });
}

export function registerInstallOrchestratorHookClaudeCodeCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.claudeCode",
      () => installClaudeCodeOrchestratorHook(context.extensionUri),
    ),
  );
}

```
