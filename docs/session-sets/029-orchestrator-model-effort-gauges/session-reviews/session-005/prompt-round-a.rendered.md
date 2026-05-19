# Set 029 Session 5 — verification Round A

Round A scope: **detection + Codex watcher + shim commands + the
small integration diffs** in OrchestratorAccordion and
CustomSessionSetsView. Round B covers the universal manual-override
quickpick (`setOrchestratorManual.ts`, 533 LOC) as its own bundle.

## Session 5 context

This is the multi-provider feature-complete session for Set 029. The
deliverables are:

1. **Codex auto-detect** via a `~/.codex/config.toml` watcher (writes
   `signalKind: "configured-default"`, `confidence: "medium"`).
2. **Universal manual-override quickpick** (`dabbler.setOrchestrator`)
   — replaces the Session 2 stub. MRU tuples at the top, multi-step
   provider→model→effort→thinking flow, hotkey-bindable args,
   force-override confirmation. (Verified in Round B.)
3. **Gemini Code Assist + GitHub Copilot installer shims** — manual
   only per audit Q2/Q4. Both open the manual-override quickpick
   with `prefillProvider` pre-set.
4. **Smart empty-state CTA** — webview detects which orchestrators
   are installed locally (Claude Code via `~/.claude/`, Codex via
   `~/.codex/`, Gemini Code Assist + GitHub Copilot via the VS Code
   extension registry) and surfaces the right install/preset link.
   MRU-biased when applicable; priority order otherwise.
5. **Version bump 0.16.0 → 0.17.0**; CLAUDE.md + CHANGELOG updated.
6. **Playwright smoke + Layer-2 unit tests** added.

Locked decisions per the audit (do not re-litigate): Codex
auto-detect is config-watcher-only (no installer command);
Gemini + Copilot are manual-only; the manual-override quickpick
delegates marker writes to `scripts/write-orchestrator-marker.js`
via `--mode manual` and that helper handles atomic write +
retry-loop + multi-writer precedence. The empty-state CTA falls
back to the Claude Code installer if no orchestrators are detected.

## What to verify

Respond per question with one of: **VERIFIED** / **MUST-FIX** /
**SUGGEST**. Quote a file:line for MUST-FIX items.

### Q1 — Codex config watcher correctness

Look at `src/codex/configWatcher.ts`. The watcher:
- Reads `~/.codex/config.toml` on extension activate and on file
  events under `~/.codex/`.
- Parses the top-level `model` and `model_reasoning_effort` keys
  with `extractTopLevelScalar` (a hand-rolled regex extractor — full
  TOML parser would balloon the VSIX).
- Spawns the shared marker-writer with `--mode configured-default`,
  passing the parsed snapshot as JSON on stdin.
- Debounces file events to one dispatch per 500 ms.

Verify:
- The TOML extractor handles the formats Codex actually writes
  (quoted, single-quoted, bare, leading whitespace, trailing
  comment). It skips values inside `[sections]`. Edge cases
  hostile to the regex don't false-positive.
- The watcher doesn't crash if `~/.codex/` doesn't exist
  (best-effort silent skip).
- The marker write goes through the helper (so the precedence rules
  apply automatically); the watcher itself doesn't bypass
  precedence.
- The debouncer + dispose path don't leak timers.

### Q2 — Gemini + Copilot shim commands

`src/commands/installOrchestratorHookGemini.ts` and
`installOrchestratorHookCopilot.ts` each register a single command
that invokes `dabbler.setOrchestrator` with `{prefillProvider}` set.
No real hook is installed — per audit Q2/Q4 those orchestrator
surfaces have no documented persisted state to scrape in v1.

Verify:
- The command IDs match the package.json contributes (`dabbler.installOrchestratorHook.gemini`
  and `.copilot`).
- The `prefillProvider` value matches what `setOrchestratorManual`
  expects (`"google"` / `"github"`).
- The shims don't accidentally install any file/setting on the
  user's machine (they should be 100% delegation).

### Q3 — Empty-state CTA detection logic

`src/providers/detectOrchestrators.ts` decides which install/preset
link the "No signal — …" CTA points at:

- Detection: `~/.claude/` directory for Claude Code, `~/.codex/` for
  Codex, `vscode.extensions.getExtension(...)` for Gemini Code
  Assist and GitHub Copilot.
- Ordering: when no MRU is populated, fall back to priority order
  (claude → codex → gemini → copilot). When MRU exists, surface
  the most-recent installed provider first; append other installed
  providers in priority order behind it.
- `pickEmptyStateCta` returns the CTA for the first installed
  provider or `null` (caller falls back to the Claude installer
  default).

Verify:
- The MRU-bias logic correctly ignores MRU entries whose provider
  isn't currently installed.
- Priority-order fallback is `["anthropic", "openai", "google", "github"]`.
- The CTA payloads match the expected command IDs (Claude →
  installer; Codex → `dabbler.setOrchestrator` with
  `{prefillProvider: "openai"}`; Gemini → installer-shim; Copilot →
  installer-shim).
- The detection helpers are best-effort (no thrown exceptions on
  missing directories or absent extensions).

### Q4 — Accordion empty-state plumbing

`src/providers/OrchestratorAccordion.ts` was extended so
`RenderState`'s `empty` variant carries an optional `cta: EmptyCta`.
`renderAccordionEmpty(cta?)` substitutes the passed CTA's command ID
+ label into the "No signal — <label>" link; if `cta?.args` is
present, it's JSON-stringified into a `data-command-args` attribute
on the button. Falls back to the Claude installer when no CTA is
passed (preserves v0.16.0 behavior).

Verify:
- The CTA's command ID and label flow through `escAttr`/`escHtml`
  correctly (no XSS opening if someone seeds a malicious label —
  not currently possible since the labels are hardcoded, but the
  escape path should still apply defensively).
- The `data-command-args` attribute round-trips through
  `JSON.stringify` cleanly.
- The fallback path (`cta === null`) still renders the Claude
  installer link verbatim.

### Q5 — CustomSessionSetsView wiring

`src/providers/CustomSessionSetsView.ts` was changed in three
places:
1. New import of `pickEmptyStateCta`.
2. The command allowlist (`COMMAND_ALLOWLIST`) added the Gemini and
   Copilot installer command IDs.
3. In `scheduleRender()` / `postSnapshot()` (around the marker
   snapshot read), when `snap.state.kind === "empty"` AND
   `snap.resolution.kind === "resolved"`, we call `pickEmptyStateCta()`
   and pass the result into the render state.

Verify:
- The allowlist additions are present and correctly spelled.
- The detection is only invoked when the resolved set actually has
  an empty marker state (don't run detection on every render for
  non-resolved rows).
- The detection result flows through to `renderAccordionBody` as
  expected — the empty-state HTML embeds the detected CTA.

### Q6 — Webview client `data-command-args` forwarding

`media/session-sets-tree/client.js` was extended so the
`[data-command]` click handler reads an optional
`data-command-args` attribute, JSON-parses it, and forwards it as
the `args` field of the `executeCommand` postMessage. The host
already passes `args` through to `vscode.commands.executeCommand`
when present (see `CustomSessionSetsView.dispatchCommand`).

Verify:
- JSON parse errors don't throw — they fall back to `args: undefined`.
- The parsed value must be an array (matches the host's
  `args?: unknown[]` expectation) — non-array values get nulled out.
- The forwarding doesn't break the existing buttons that have no
  `data-command-args` attribute.

### Q7 — Test coverage

Three Playwright scenarios were added:
- configured-default Codex marker → `signal-configured-default`
  class present on at least one gauge cell + "Codex" sublabel.
- Manual Gemini marker → `signal-manual` class present + "Gemini"
  sublabel.
- Empty state (no seeded marker) → "No signal" prefix + an
  `acc-link` button visible (label content varies by host install).

Six new Layer-2 unit suites cover the TOML extractor, MRU
push/dedupe/cap, formatTupleLabel, MRU readers (malformed JSON,
non-tuple filtering), detection priority + MRU-bias, and CTA
selection.

Verify the test coverage matches the spec's mandates (configured-
default visual, manual visual, MRU reordering logic, precedence,
multi-writer skip). Where the spec called for Playwright but the
implementation moved to Layer 2 (MRU reordering, force-override,
multi-writer-skip — all logic-level invariants), confirm that
trade-off is sound vs. the painted-on-screen split established in
S4 (data assertions → unit tests; pixels → Playwright).

### Optional — anything else risky

If anything else stands out as a correctness issue, flag it.


---

## File 1: src/codex/configWatcher.ts

```typescript
// Codex auto-detection: watches `~/.codex/config.toml` for changes and
// writes a `configured-default` marker via the shared writer helper.
//
// Per Set 029 audit Q3 (configured-default signal, medium confidence —
// does not track runtime changes). The watcher fires on extension
// activation and on subsequent file events. The actual write is
// performed by `scripts/write-orchestrator-marker.js` with
// `--mode configured-default`, which honors the multi-writer precedence
// rules (a fresh `current`/`manual`/`last-observed` signal blocks the
// `configured-default` write — see `attemptWriteWithPrecedence` in the
// helper).
//
// The TOML parse is intentionally minimal: only the top-level `model`
// and `model_reasoning_effort` keys are read. A full TOML parser is
// overkill for two scalar fields, and shipping `@iarna/toml` (the
// nearest dependency-light option) would balloon the extension VSIX
// for ~50 LOC of behavior. The regex-based extractor below tolerates
// both quoted and bare values, leading whitespace, and trailing
// comments — the formats Codex actually writes.

import * as vscode from "vscode";
import * as cp from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const CODEX_CONFIG_REL = path.join(".codex", "config.toml");
const HELPER_REL = path.join("scripts", "write-orchestrator-marker.js");

interface CodexConfigSnapshot {
  model: string | null;
  effort: "low" | "medium" | "high" | null;
  thinking: boolean;
}

// Extract a top-level scalar key from a TOML body. We only look at lines
// that aren't inside a `[section]`, which is where Codex puts `model` and
// `model_reasoning_effort` per its CLI defaults. Returns the raw string
// value (without quotes) or null if not present.
export function extractTopLevelScalar(toml: string, key: string): string | null {
  const lines = toml.split(/\r?\n/);
  const keyRe = new RegExp(`^\\s*${key}\\s*=\\s*(.+?)\\s*(#.*)?$`);
  let inSection = false;
  for (const rawLine of lines) {
    const line = rawLine.replace(/^\s+/, "");
    if (line.startsWith("[")) {
      inSection = true;
      continue;
    }
    if (inSection) continue;
    const m = keyRe.exec(rawLine);
    if (!m) continue;
    let value = m[1].trim();
    // Strip a trailing inline comment that the regex's optional group
    // didn't catch (e.g., when the value itself contains the `#`).
    // Trim surrounding quotes (single or double).
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    return value;
  }
  return null;
}

export function parseCodexConfig(toml: string): CodexConfigSnapshot {
  const model = extractTopLevelScalar(toml, "model");
  const rawEffort = extractTopLevelScalar(toml, "model_reasoning_effort");
  let effort: CodexConfigSnapshot["effort"] = null;
  if (rawEffort) {
    const lower = rawEffort.toLowerCase();
    if (lower === "low" || lower === "medium" || lower === "high") {
      effort = lower;
    }
  }
  // Codex doesn't expose a thinking-on/off boolean in config.toml; the
  // reasoning-effort tier IS the thinking control. Treat any effort
  // setting as "thinking on" for the marker so the gauge shows the
  // thinking-state indicator consistently with other providers.
  const thinking = effort !== null;
  return { model, effort, thinking };
}

function helperPathAbs(extensionUri: vscode.Uri): string {
  return vscode.Uri.joinPath(extensionUri, HELPER_REL).fsPath;
}

function codexConfigPath(): string {
  return path.join(os.homedir(), CODEX_CONFIG_REL);
}

interface WriteOpts {
  extensionUri: vscode.Uri;
  cwd: string;
}

// Dispatches a configured-default marker write for the current Codex
// config snapshot. Best-effort: silent on success, logs to the writer
// log on failure via the helper's own logging path.
function dispatchMarkerWrite(snapshot: CodexConfigSnapshot, opts: WriteOpts): void {
  if (!snapshot.model) return;
  const helperAbs = helperPathAbs(opts.extensionUri);
  if (!fs.existsSync(helperAbs)) return;

  const payload = {
    provider: "openai",
    model: snapshot.model,
    effort: snapshot.effort
      ? {
          normalized: snapshot.effort,
          native: snapshot.effort,
          thinking: snapshot.thinking,
          signalKind: "configured-default",
          confidence: "medium",
        }
      : {
          normalized: "medium",
          native: "default",
          thinking: false,
          signalKind: "configured-default",
          confidence: "medium",
        },
    writer: "codex-config-watcher",
  };

  const child = cp.spawn(
    process.execPath,
    [helperAbs, "--mode", "configured-default", "--writer", "codex-config-watcher"],
    { cwd: opts.cwd, stdio: ["pipe", "ignore", "ignore"], detached: false },
  );
  child.on("error", () => {
    // Best-effort: the helper logs its own failures to
    // ~/.dabbler/orchestrator-writer.log; we don't want a spawn error
    // to surface as a user-visible notification.
  });
  try {
    child.stdin.end(JSON.stringify(payload));
  } catch {
    // stdin may already be closed if spawn errored synchronously.
  }
}

function readSnapshotSafe(): CodexConfigSnapshot | null {
  const p = codexConfigPath();
  let toml: string;
  try {
    toml = fs.readFileSync(p, "utf8");
  } catch {
    return null;
  }
  return parseCodexConfig(toml);
}

// Activates the watcher: runs an initial scan, then watches the parent
// directory of `~/.codex/config.toml` for change/create/delete events.
// We watch the directory rather than the file itself so we still see
// `config.toml` first appearing after the operator runs `codex init`
// post-extension-activation. Returns a Disposable the caller pushes to
// `context.subscriptions`.
export function activateCodexConfigWatcher(
  context: vscode.ExtensionContext,
): vscode.Disposable {
  const codexDir = path.join(os.homedir(), ".codex");
  const workspaceCwd =
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();

  const runOnce = (): void => {
    const snap = readSnapshotSafe();
    if (snap && snap.model) {
      dispatchMarkerWrite(snap, {
        extensionUri: context.extensionUri,
        cwd: workspaceCwd,
      });
    }
  };

  // Initial scan: if the config exists at activation time, push a
  // marker. The helper's precedence check will skip the write if a
  // fresher current-signal exists.
  runOnce();

  // Watch the parent directory so `config.toml` appearing later (e.g.,
  // after `codex init`) is also picked up. fs.watch is best-effort and
  // can emit duplicate events on some platforms; we debounce to a
  // single dispatch per 500ms quiet window.
  let debounceTimer: NodeJS.Timeout | null = null;
  let watcher: fs.FSWatcher | null = null;
  try {
    if (fs.existsSync(codexDir)) {
      watcher = fs.watch(codexDir, { persistent: false }, (_event, filename) => {
        if (filename && filename.toString() !== "config.toml") return;
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(runOnce, 500);
      });
    }
  } catch {
    // ~/.codex/ doesn't exist or isn't watchable. Silent — the watcher
    // is best-effort; absence of Codex install is a normal state.
  }

  return {
    dispose(): void {
      if (debounceTimer) clearTimeout(debounceTimer);
      try {
        watcher?.close();
      } catch {
        // best effort
      }
    },
  };
}

```


---

## File 2: src/commands/installOrchestratorHookGemini.ts

```typescript
// Gemini Code Assist orchestrator-hook installer.
//
// Per Set 029 audit Q2: Gemini Code Assist exposes no documented
// persisted state we can scrape for an auto-detect path in v1. The
// "install hook" command therefore opens the manual-override quickpick
// with `provider: "google"` pre-selected so the operator gets one
// click to a working Gemini marker. No actual hook is installed.
//
// If/when Gemini Code Assist ships a state-marker file (audit Q2 noted
// this as a roadmap item), swap the body for a real installer following
// the Claude Code shape.

import * as vscode from "vscode";

export function registerInstallOrchestratorHookGeminiCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.gemini",
      () =>
        vscode.commands.executeCommand("dabbler.setOrchestrator", {
          prefillProvider: "google",
        }),
    ),
  );
}

```


---

## File 3: src/commands/installOrchestratorHookCopilot.ts

```typescript
// GitHub Copilot orchestrator-hook installer.
//
// Per Set 029 audit Q4: GitHub Copilot's old settings keys for the
// active chat model were deprecated and no current public key replaces
// them. Auto-detection isn't viable in v1. The "install hook" command
// opens the manual-override quickpick with `provider: "github"`
// pre-selected so the operator gets one click to a working Copilot
// marker. No actual hook is installed.

import * as vscode from "vscode";

export function registerInstallOrchestratorHookCopilotCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.copilot",
      () =>
        vscode.commands.executeCommand("dabbler.setOrchestrator", {
          prefillProvider: "github",
        }),
    ),
  );
}

```


---

## File 4: src/providers/detectOrchestrators.ts

```typescript
// Smart empty-state CTA: detect which orchestrators are installed
// locally and pick the best link to surface in the "No signal" hint.
//
// Per Set 029 Session 5 step 5: "Webview detects which orchestrator
// extensions/CLIs are installed (presence of Claude Code, Gemini Code
// Assist extension, Codex CLI on PATH, GitHub Copilot extension) and
// surfaces the *right* installer/preset command in the 'No signal'
// CTA — not a generic 'install hook' link. If multiple are detected,
// show the most-recently-used per MRU."

import * as vscode from "vscode";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import type { EmptyCta } from "./OrchestratorAccordion";
import { readMru, type Provider } from "../commands/setOrchestratorManual";

interface ProviderCta {
  provider: Provider;
  cta: EmptyCta;
}

const CLAUDE_CTA: EmptyCta = {
  commandId: "dabbler.installOrchestratorHook.claudeCode",
  label: "install Claude Code hook",
};
const CODEX_CTA: EmptyCta = {
  // Codex auto-detect is a watcher activated at extension start; the
  // CTA points at the manual override pre-filled with Codex so an
  // operator who hasn't yet set ~/.codex/config.toml still gets a
  // signal in one click.
  commandId: "dabbler.setOrchestrator",
  label: "set Codex orchestrator",
  args: [{ prefillProvider: "openai" }],
};
const GEMINI_CTA: EmptyCta = {
  commandId: "dabbler.installOrchestratorHook.gemini",
  label: "set Gemini orchestrator",
};
const COPILOT_CTA: EmptyCta = {
  commandId: "dabbler.installOrchestratorHook.copilot",
  label: "set Copilot orchestrator",
};

const PROVIDER_TO_CTA: Record<Provider, EmptyCta> = {
  anthropic: CLAUDE_CTA,
  openai: CODEX_CTA,
  google: GEMINI_CTA,
  github: COPILOT_CTA,
};

// ----- Per-provider presence checks -----

// Claude Code: looks for ~/.claude/ (the directory the Claude Code CLI
// creates on first run, where settings.json and credentials live).
export function claudeCodeInstalled(): boolean {
  try {
    return fs.statSync(path.join(os.homedir(), ".claude")).isDirectory();
  } catch {
    return false;
  }
}

// Codex CLI: ~/.codex/ exists (created on first `codex` invocation).
// We don't probe PATH because spawning `which codex` on every render
// would be wasteful; the directory check is a strong-enough proxy.
export function codexInstalled(): boolean {
  try {
    return fs.statSync(path.join(os.homedir(), ".codex")).isDirectory();
  } catch {
    return false;
  }
}

// Gemini Code Assist: VS Code extension. Publisher.extensionId per the
// Marketplace listing.
export function geminiInstalled(): boolean {
  return vscode.extensions.getExtension("Google.geminicodeassist") !== undefined;
}

// GitHub Copilot: VS Code extension. The chat surface is shipped as a
// sibling extension (GitHub.copilot-chat), so we accept either.
export function copilotInstalled(): boolean {
  return (
    vscode.extensions.getExtension("GitHub.copilot") !== undefined ||
    vscode.extensions.getExtension("GitHub.copilot-chat") !== undefined
  );
}

// ----- Detection roll-up -----

export interface DetectionResult {
  // Ordered installed providers, MRU-first when MRU is non-empty,
  // otherwise priority-ordered (claude → codex → gemini → copilot).
  installed: Provider[];
}

export function detectInstalledOrchestrators(): DetectionResult {
  const installed: Provider[] = [];
  if (claudeCodeInstalled()) installed.push("anthropic");
  if (codexInstalled()) installed.push("openai");
  if (geminiInstalled()) installed.push("google");
  if (copilotInstalled()) installed.push("github");

  // Re-order by MRU first if any of the installed providers appear in
  // the operator's MRU tuples.
  const mru = readMru();
  if (mru.length === 0) return { installed };
  const mruOrder: Provider[] = [];
  for (const tuple of mru) {
    if (installed.includes(tuple.provider) && !mruOrder.includes(tuple.provider)) {
      mruOrder.push(tuple.provider);
    }
  }
  // Append any installed providers the MRU didn't mention.
  for (const provider of installed) {
    if (!mruOrder.includes(provider)) mruOrder.push(provider);
  }
  return { installed: mruOrder };
}

// Returns the CTA to surface, or null to fall back to the legacy
// hard-coded Claude Code installer link (the accordion render helper
// substitutes its own default in that case).
export function pickEmptyStateCta(
  detection: DetectionResult = detectInstalledOrchestrators(),
): EmptyCta | null {
  if (detection.installed.length === 0) return null;
  return PROVIDER_TO_CTA[detection.installed[0]];
}

// Exposed for tests + the Gemini/Copilot CTA labels in the accordion
// (in case S6 wants a different surfacing).
export const PROVIDER_CTAS: ReadonlyArray<ProviderCta> = (
  Object.entries(PROVIDER_TO_CTA) as [Provider, EmptyCta][]
).map(([provider, cta]) => ({ provider, cta }));

```


---

## Snippet 5: src/providers/OrchestratorAccordion.ts — empty-state changes

```typescript
// Empty state for the accordion: marker not present for the resolved
// in-progress set. Renders grey gauges + the three indicator-action
// buttons (install hook / set orchestrator / writer log). Per S4 M8,
// these three affordances MUST be in the accordion body before the
// dabblerOrchestratorIndicator view retires.
//
// Buttons fire via `data-command` attributes; the webview client.js
// captures clicks and posts `{ type: "executeCommand", commandId }` to
// the host. The host dispatches via vscode.commands.executeCommand.
//
// Session 5 (smart CTA): the "install hook" link's target is no longer
// hardcoded to Claude. The caller passes an optional `cta` based on
// what's actually installed locally (Claude Code, Codex CLI, Gemini
// Code Assist extension, GitHub Copilot extension) and the operator's
// MRU. If `cta` is null/undefined we fall back to the v0.16.0 behavior
// (link to the Claude Code installer) so existing callers and the
// empty-workspace case keep working unchanged.
const DEFAULT_CTA: EmptyCta = {
  commandId: "dabbler.installOrchestratorHook.claudeCode",
  label: "install Claude Code hook",
};

export function renderAccordionEmpty(cta?: EmptyCta | null): string {
  const effectiveCta = cta || DEFAULT_CTA;
  const argsAttr =
    effectiveCta.args !== undefined
      ? ` data-command-args="${escAttr(JSON.stringify(effectiveCta.args))}"`
      : "";
  return `<div class="acc-empty">
  <div class="grey-gauges">
    <div class="gauge-svg-wrap">${renderGaugeSvg("unknown", "current", 0)}</div>
    <div class="gauge-svg-wrap">${renderGaugeSvg("unknown", "current", 0)}</div>
  </div>
  <div class="acc-empty-cta">
    <span>No signal — </span>
    <button class="acc-link" type="button" data-command="${escAttr(effectiveCta.commandId)}"${argsAttr}>${escHtml(effectiveCta.label)}</button>
  </div>
  <div class="acc-actions">
    <button class="acc-action" type="button" data-command="dabbler.setOrchestrator">Set Orchestrator…</button>
    <button class="acc-action" type="button" data-command="dabbler.openOrchestratorWriterLog">Writer Log</button>
  </div>
</div>`;
}


```


---

## Snippet 6: src/providers/CustomSessionSetsView.ts — wiring changes

```typescript
// Allowlist for executeCommand dispatch from the webview. Defense-
// in-depth: even if a malicious string slipped through the protocol
// type check, only these commands fire. Includes all 14 row-context
// actions + 3 indicator-action buttons.
const COMMAND_ALLOWLIST: ReadonlySet<string> = new Set([
  // 14 row-context actions
  "dabblerSessionSets.openSpec",
  "dabblerSessionSets.openActivityLog",
  "dabblerSessionSets.openChangeLog",
  "dabblerSessionSets.openAiAssignment",
  "dabblerSessionSets.openUatChecklist",
  "dabblerSessionSets.revealPlaywrightTests",
  "dabblerSessionSets.openSessionState",
  "dabblerSessionSets.openFolder",
  "dabblerSessionSets.copyStartCommand.default",
  "dabblerSessionSets.copyStartCommand.parallel",
  "dabblerSessionSets.copySlug",
  "dabblerSessionSets.migrate",
  "dabblerSessionSets.cancel",
  "dabblerSessionSets.restore",
  // Indicator-action buttons (Session 4 + Session 5 multi-provider)
  "dabbler.installOrchestratorHook.claudeCode",
  "dabbler.installOrchestratorHook.gemini",
  "dabbler.installOrchestratorHook.copilot",
  "dabbler.setOrchestrator",
  "dabbler.openOrchestratorWriterLog",
]);


```


---

## Snippet 7: media/session-sets-tree/client.js — data-command-args dispatch

```javascript
// Buttons inside accordion / banner with data-command. Optional
    // data-command-args is a JSON-encoded array of args appended to
    // the executeCommand call (Session 5 — used by the smart CTA to
    // pass `prefillProvider` to dabbler.setOrchestrator).
    Array.from(root.querySelectorAll('[data-command]')).forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const commandId = btn.getAttribute("data-command");
        if (!commandId) return;
        const argsAttr = btn.getAttribute("data-command-args");
        let args;
        if (argsAttr) {
          try {
            const parsed = JSON.parse(argsAttr);
            args = Array.isArray(parsed) ? parsed : undefined;
          } catch (_e) {
            args = undefined;
          }
        }
        vscode.postMessage({
          type: "executeCommand",
          commandId: commandId,
          args: args,
        });
      });
    });
  
```
