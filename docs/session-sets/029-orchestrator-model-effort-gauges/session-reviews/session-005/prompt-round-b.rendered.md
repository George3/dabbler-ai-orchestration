# Set 029 Session 5 — verification Round B

Round B scope: **`src/commands/setOrchestratorManual.ts`** — the
universal manual-override quickpick (533 LOC). Round A covered the
rest of S5's new surface (Codex watcher, detection, shim commands,
integration diffs).

## Session 5 context

This command (`dabbler.setOrchestrator`) is the primary surface for
all non-Claude orchestrator manual overrides, plus the Claude
fallback when an operator wants to override the SessionStart-hook-
driven signal. It replaces the Session 2 stub.

### Expected behavior

- **Top of quickpick**: MRU tuples (one row per `<provider> + <model>
  + <effort> + <thinking>` combination), most-recent first, sorted
  by recency. Stored at `~/.dabbler/orchestrator-mru.json` (capped at
  8 entries).
- **`(set new combination…)`** row: multi-step picker flow —
  provider → model → effort → thinking-on/off. When invoked via the
  Gemini or Copilot shims, the provider step is skipped (pre-filled
  via `prefillProvider`).
- **`(copy keybindings.json snippet for current selection)`** row
  (appears only when MRU non-empty): copies a `keybindings.json`
  JSON fragment to clipboard pre-filled with the most-recent tuple.
- **Hotkey-bindable**: callers can invoke
  `dabbler.setOrchestrator` with `{provider, model, effort, thinking}`
  to bypass the quickpick. (Force-override prompt still applies.)
- **Force-override semantics**: before any write, read the resolved
  set's existing marker. If there's a fresh `current`-precedence
  signal from another writer (i.e., a live SessionStart hook is
  driving the marker), pop a modal "Override existing live signal
  from <writer>?" confirmation. On accept, pass `--force-override`
  to the helper.
- **Marker write delegation**: spawn `scripts/write-orchestrator-marker.js`
  with `--mode manual --writer manual-override`, JSON payload on
  stdin. Helper handles atomic write + retry-loop + multi-writer
  precedence + writer-log appends.
- **MRU update**: after a successful write, push the tuple to MRU.
  Failed writes do NOT update MRU (verify this).
- **User feedback**: success → info notification with formatted
  tuple label. Failure → error notification quoting exit code +
  stderr trimmed.

### Architecture choices already locked

- The set resolution path (`readCurrentMarkerForWorkspace`)
  replicates the helper script's walk-up resolver in TypeScript to
  read the existing marker for the force-override prompt. We
  *could* invoke the helper in a "read-only" mode, but that's a
  larger change and the duplication is small + isolated.
- The PROVIDER_MODELS list is curated (not exhaustive). New models
  can be added without changing surrounding logic. The marker
  writer's `deriveModelDisplayName` normalizer falls back to the
  raw model id, so unknown models still render correctly.

## What to verify

Respond per question with one of: **VERIFIED** / **MUST-FIX** /
**SUGGEST**. Quote a file:line for MUST-FIX items.

### Q1 — Quickpick flow correctness

- Multi-step flow (provider → model → effort → thinking) handles
  user cancellation (`undefined` return from any step) by aborting
  cleanly with no side effects.
- The MRU + new + hotkey items appear in the right order and only
  when applicable (no hotkey row if MRU is empty).
- The `prefillProvider` path correctly skips the provider step and
  filters MRU entries to surface that provider first.

### Q2 — MRU storage correctness

- `readMru()` is tolerant of: missing file, malformed JSON,
  non-array root, and non-tuple entries (filters them out without
  throwing).
- `pushMru()` de-duplicates by full tuple identity (all four fields
  matching), moves the existing entry to the front, and caps at 8
  entries.
- `mruFilePath()` is computed per-call (not cached at module load)
  so unit tests that redirect `$HOME` work correctly. This is
  load-bearing: caching would cause the live extension to keep
  using whatever home directory was active at first activation.

### Q3 — Force-override prompt correctness

`maybeConfirmForceOverride()`:
- Returns `{proceed: true, force: false}` when no existing marker
  resolves (no in-progress set, or multi-in-progress ambiguity).
- Returns `{proceed: true, force: false}` when the existing marker
  is weaker than `current` precedence (configured-default,
  last-observed, manual — all of which the helper will overwrite
  without ceremony).
- Returns `{proceed: true, force: true}` when the existing marker
  is `current` but STALE (age > stalenessMaxSec / default 8h). The
  helper would overwrite a stale marker unconditionally anyway, so
  prompting would be misleading.
- Pops the modal warning and returns based on the user's choice
  when the existing marker is fresh `current`. On accept,
  `force: true` is passed to `dispatchManualWrite`.

Verify the precedence vs. staleness vs. user-confirmation tree is
correct, and that the prompt text quotes the actual writer name
from the marker (not a generic placeholder).

### Q4 — Marker write dispatch

`dispatchManualWrite()`:
- Spawns `process.execPath` (the node binary) + the helper script
  path + args, with stdio configured for piped stdin (payload).
- Wraps in a Promise that resolves with `{exitCode, stderr}`.
- Passes `--force-override` only when `forceOverride === true`.
- The payload's `effort` block uses the right shape for the
  helper's `mode === "manual"` branch (signalKind: "manual",
  confidence: "high", thinking from tuple, normalized/native from
  tuple).
- Doesn't double-write the marker (one helper invocation per call).

### Q5 — Hotkey-bindable args path

When the command is invoked with a complete args object
(`isCompleteArgs(args) === true`), the quickpick is skipped and
`executeWrite` runs directly. The args are normalized to an
`OrchestratorTuple` and pushed to the same write+MRU path as the
picker.

The `isCompleteArgs` type guard validates all four required fields
are present and of the right type — missing or extra fields fall
back to the quickpick.

### Q6 — Keybindings snippet

`buildKeybindingSnippet()`:
- Emits a 3-field JSON object (`key`, `command`, `args`).
- The default key (`ctrl+shift+alt+o`) is a reasonable starting
  point but the operator is expected to edit it.
- The args object is the literal MRU tuple (no transformation).
- Writes to clipboard via `vscode.env.clipboard.writeText`.

### Q7 — Error paths + user feedback

- Helper not found → user-visible error with the absolute helper
  path quoted.
- Helper exit ≠ 0 → user-visible error with exit code + trimmed
  stderr.
- Helper exit 0 → success notification with `formatTupleLabel`
  result + MRU push.
- MRU file write failure is best-effort (silent), so a failed MRU
  write doesn't surface as a user-visible error.

### Optional — anything else risky

If anything else stands out (concurrency, race conditions, encoding
issues, Windows-specific path bugs, accessibility gaps in the
modal, etc.), flag it.


---

## File 1: src/commands/setOrchestratorManual.ts

```typescript
// Universal manual-override quickpick for the orchestrator indicator.
//
// Replaces the Session 2 stub. Per Set 029 Session 5 spec:
//   - Top section: MRU tuples (provider + model + effort + thinking),
//     most-recent first. Stored in ~/.dabbler/orchestrator-mru.json.
//   - Bottom row: "(set new combination…)" — multi-step flow
//     (provider → model → effort → thinking).
//   - "(create new hotkey binding)" — copies a keybindings.json snippet
//     to the clipboard pre-filled with the most-recent selection.
//   - Hotkey-bindable: accepts {provider, model, effort, thinking}
//     args; bypasses the quickpick and applies directly (with the
//     same force-override confirmation when applicable).
//   - Force-override: if a fresh `current`-precedence marker exists
//     from another writer, prompt "Override existing live signal from
//     <writer>?" before proceeding.
//
// Marker write is delegated to the shared
// `scripts/write-orchestrator-marker.js` helper with `--mode manual`.
// The helper handles atomic write, retry, multi-writer precedence,
// and writer-log appends.

import * as vscode from "vscode";
import * as cp from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

const HELPER_REL = path.join("scripts", "write-orchestrator-marker.js");
const MRU_LIMIT = 8;

// Compute the MRU file path on every call rather than caching at
// module-load: the unit-test suite redirects $HOME / %USERPROFILE%
// per-test, and a cached constant would point at the original home
// for the lifetime of the test runner.
function mruFilePath(): string {
  return path.join(os.homedir(), ".dabbler", "orchestrator-mru.json");
}

export type EffortLevel = "low" | "medium" | "high" | "max";
export type Provider = "anthropic" | "google" | "openai" | "github";

export interface OrchestratorTuple {
  provider: Provider;
  model: string;
  effort: EffortLevel;
  thinking: boolean;
}

interface ProviderModelList {
  provider: Provider;
  providerLabel: string;
  models: { id: string; label: string }[];
}

// Curated per-provider model lists. Matches the marker writer's
// display-name normalizer (deriveModelDisplayName) so manual entries
// render identically to auto-detected ones. Order: flagship-first.
export const PROVIDER_MODELS: ProviderModelList[] = [
  {
    provider: "anthropic",
    providerLabel: "Claude",
    models: [
      { id: "claude-opus-4-7", label: "Opus 4.7" },
      { id: "claude-opus-4-6", label: "Opus 4.6" },
      { id: "claude-sonnet-4-6", label: "Sonnet 4.6" },
      { id: "claude-haiku-4-5", label: "Haiku 4.5" },
    ],
  },
  {
    provider: "google",
    providerLabel: "Gemini",
    models: [
      { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    ],
  },
  {
    provider: "openai",
    providerLabel: "Codex",
    models: [
      { id: "gpt-5-4", label: "GPT-5.4" },
      { id: "gpt-5", label: "GPT-5" },
      { id: "o3", label: "o3" },
      { id: "o1", label: "o1" },
    ],
  },
  {
    provider: "github",
    providerLabel: "Copilot",
    models: [
      { id: "gpt-4o", label: "GPT-4o (Copilot)" },
      { id: "claude-sonnet-4-6", label: "Sonnet 4.6 (Copilot)" },
    ],
  },
];

const EFFORT_LEVELS: { id: EffortLevel; label: string }[] = [
  { id: "low", label: "Low effort" },
  { id: "medium", label: "Medium effort" },
  { id: "high", label: "High effort" },
  { id: "max", label: "Max effort" },
];

// ----- MRU storage -----

export function readMru(): OrchestratorTuple[] {
  try {
    const raw = fs.readFileSync(mruFilePath(), "utf8");
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isTuple);
  } catch {
    return [];
  }
}

function isTuple(x: unknown): x is OrchestratorTuple {
  if (!x || typeof x !== "object") return false;
  const t = x as Partial<OrchestratorTuple>;
  return (
    typeof t.provider === "string" &&
    typeof t.model === "string" &&
    typeof t.effort === "string" &&
    typeof t.thinking === "boolean"
  );
}

export function pushMru(
  tuple: OrchestratorTuple,
  existing: OrchestratorTuple[] = readMru(),
): OrchestratorTuple[] {
  const filtered = existing.filter(
    (t) =>
      !(
        t.provider === tuple.provider &&
        t.model === tuple.model &&
        t.effort === tuple.effort &&
        t.thinking === tuple.thinking
      ),
  );
  const next = [tuple, ...filtered].slice(0, MRU_LIMIT);
  try {
    const file = mruFilePath();
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(next, null, 2) + "\n", { encoding: "utf8" });
  } catch {
    // Best-effort: MRU persistence failure shouldn't block the write.
  }
  return next;
}

// ----- Tuple → human label -----

function findProviderLabel(provider: Provider): string {
  return PROVIDER_MODELS.find((p) => p.provider === provider)?.providerLabel ?? provider;
}

function findModelLabel(provider: Provider, model: string): string {
  const list = PROVIDER_MODELS.find((p) => p.provider === provider)?.models ?? [];
  return list.find((m) => m.id === model)?.label ?? model;
}

export function formatTupleLabel(tuple: OrchestratorTuple): string {
  const provider = findProviderLabel(tuple.provider);
  const model = findModelLabel(tuple.provider, tuple.model);
  const effortLabel = EFFORT_LEVELS.find((e) => e.id === tuple.effort)?.label ?? tuple.effort;
  const thinking = tuple.thinking ? "Thinking on" : "Thinking off";
  return `${provider} ${model} — ${effortLabel}, ${thinking}`;
}

// ----- Marker writer dispatch -----

function helperPathAbs(extensionUri: vscode.Uri): string {
  return vscode.Uri.joinPath(extensionUri, HELPER_REL).fsPath;
}

function readCurrentMarkerForWorkspace(workspaceCwd: string): {
  exists: boolean;
  writer: string | null;
  signalKind: string | null;
  ageSec: number | null;
} {
  // Walk-up to find the per-set marker. We replicate the helper's
  // walk-up logic here just enough to read the current signalKind +
  // writer for the force-override prompt. Returns exists=false if no
  // in-progress set is resolvable.
  let current = path.resolve(workspaceCwd);
  while (true) {
    const candidate = path.join(current, "docs", "session-sets");
    let entries: fs.Dirent[] | null = null;
    try {
      if (fs.statSync(candidate).isDirectory()) {
        entries = fs.readdirSync(candidate, { withFileTypes: true });
      }
    } catch {
      // not a dir; fall through
    }
    if (entries) {
      const inProgress: string[] = [];
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const statePath = path.join(candidate, entry.name, "session-state.json");
        try {
          const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
          if (state && state.status === "in-progress") inProgress.push(entry.name);
        } catch {
          // skip
        }
      }
      if (inProgress.length !== 1) {
        return { exists: false, writer: null, signalKind: null, ageSec: null };
      }
      const markerPath = path.join(candidate, inProgress[0], ".dabbler", "orchestrator.json");
      try {
        const raw = fs.readFileSync(markerPath, "utf8");
        const marker = JSON.parse(raw);
        const ageSec = marker.updatedAt
          ? (Date.now() - Date.parse(marker.updatedAt)) / 1000
          : null;
        return {
          exists: true,
          writer: typeof marker.writer === "string" ? marker.writer : null,
          signalKind: typeof marker.signalKind === "string" ? marker.signalKind : null,
          ageSec,
        };
      } catch {
        return { exists: false, writer: null, signalKind: null, ageSec: null };
      }
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return { exists: false, writer: null, signalKind: null, ageSec: null };
    }
    current = parent;
  }
}

interface WriteContext {
  extensionUri: vscode.Uri;
  workspaceCwd: string;
}

function dispatchManualWrite(
  tuple: OrchestratorTuple,
  ctx: WriteContext,
  forceOverride: boolean,
): Promise<{ exitCode: number; stderr: string }> {
  const helperAbs = helperPathAbs(ctx.extensionUri);
  return new Promise((resolve) => {
    if (!fs.existsSync(helperAbs)) {
      resolve({ exitCode: 127, stderr: `helper not found: ${helperAbs}` });
      return;
    }
    const args = ["--mode", "manual", "--writer", "manual-override"];
    if (forceOverride) args.push("--force-override");
    const child = cp.spawn(process.execPath, [helperAbs, ...args], {
      cwd: ctx.workspaceCwd,
      stdio: ["pipe", "ignore", "pipe"],
    });
    const stderrChunks: Buffer[] = [];
    child.stderr.on("data", (c) => stderrChunks.push(c));
    child.on("error", (err) => resolve({ exitCode: 1, stderr: err.message }));
    child.on("close", (code) =>
      resolve({
        exitCode: code ?? 0,
        stderr: Buffer.concat(stderrChunks).toString("utf8"),
      }),
    );
    const payload = {
      provider: tuple.provider,
      model: tuple.model,
      effort: {
        normalized: tuple.effort,
        native: tuple.effort,
        thinking: tuple.thinking,
        signalKind: "manual",
        confidence: "high",
      },
    };
    try {
      child.stdin.end(JSON.stringify(payload));
    } catch {
      // child may already be dead
    }
  });
}

// ----- Quickpick flows -----

async function pickProvider(): Promise<Provider | undefined> {
  const items = PROVIDER_MODELS.map((p) => ({
    label: p.providerLabel,
    description: p.provider,
    provider: p.provider,
  }));
  const picked = await vscode.window.showQuickPick(items, {
    title: "Set Orchestrator — Provider",
    placeHolder: "Select the provider",
  });
  return picked?.provider;
}

async function pickModel(provider: Provider): Promise<string | undefined> {
  const list = PROVIDER_MODELS.find((p) => p.provider === provider)?.models ?? [];
  const items = list.map((m) => ({ label: m.label, description: m.id, id: m.id }));
  const picked = await vscode.window.showQuickPick(items, {
    title: `Set Orchestrator — ${findProviderLabel(provider)} Model`,
    placeHolder: "Select the model",
  });
  return picked?.id;
}

async function pickEffort(): Promise<EffortLevel | undefined> {
  const items = EFFORT_LEVELS.map((e) => ({ label: e.label, id: e.id }));
  const picked = await vscode.window.showQuickPick(items, {
    title: "Set Orchestrator — Effort",
    placeHolder: "Select effort tier",
  });
  return picked?.id;
}

async function pickThinking(): Promise<boolean | undefined> {
  const items = [
    { label: "Thinking on", value: true },
    { label: "Thinking off", value: false },
  ];
  const picked = await vscode.window.showQuickPick(items, {
    title: "Set Orchestrator — Thinking",
    placeHolder: "Toggle extended thinking",
  });
  return picked?.value;
}

async function runMultiStepFlow(): Promise<OrchestratorTuple | undefined> {
  const provider = await pickProvider();
  if (!provider) return undefined;
  const model = await pickModel(provider);
  if (!model) return undefined;
  const effort = await pickEffort();
  if (!effort) return undefined;
  const thinking = await pickThinking();
  if (thinking === undefined) return undefined;
  return { provider, model, effort, thinking };
}

function buildKeybindingSnippet(tuple: OrchestratorTuple): string {
  return JSON.stringify(
    {
      key: "ctrl+shift+alt+o",
      command: "dabbler.setOrchestrator",
      args: tuple,
    },
    null,
    2,
  );
}

// ----- Force-override prompt -----

async function maybeConfirmForceOverride(
  workspaceCwd: string,
): Promise<{ proceed: boolean; force: boolean }> {
  const existing = readCurrentMarkerForWorkspace(workspaceCwd);
  if (!existing.exists) return { proceed: true, force: false };
  // Only the strongest signal class needs a confirmation; the helper
  // already silently accepts equal-or-stronger overrides without
  // ceremony. "current" is the strongest non-manual class.
  if (existing.signalKind !== "current") return { proceed: true, force: false };
  // Don't prompt on stale signals — the helper will overwrite a stale
  // marker unconditionally, so the prompt would be misleading.
  if (existing.ageSec !== null && existing.ageSec > 28800) {
    return { proceed: true, force: true };
  }
  const writer = existing.writer || "unknown";
  const picked = await vscode.window.showWarningMessage(
    `Override existing live signal from ${writer}?`,
    { modal: true },
    "Override",
  );
  if (picked === "Override") return { proceed: true, force: true };
  return { proceed: false, force: false };
}

// ----- Public command entry -----

interface ManualCommandArgs {
  provider?: Provider;
  model?: string;
  effort?: EffortLevel;
  thinking?: boolean;
  prefillProvider?: Provider;
}

function isCompleteArgs(args: ManualCommandArgs | undefined): args is Required<
  Pick<ManualCommandArgs, "provider" | "model" | "effort" | "thinking">
> {
  if (!args) return false;
  return (
    typeof args.provider === "string" &&
    typeof args.model === "string" &&
    typeof args.effort === "string" &&
    typeof args.thinking === "boolean"
  );
}

async function executeWrite(
  tuple: OrchestratorTuple,
  ctx: WriteContext,
): Promise<void> {
  const force = await maybeConfirmForceOverride(ctx.workspaceCwd);
  if (!force.proceed) return;
  const result = await dispatchManualWrite(tuple, ctx, force.force);
  if (result.exitCode !== 0) {
    vscode.window.showErrorMessage(
      `Manual override failed (exit ${result.exitCode}): ${result.stderr.trim() || "see Writer Log"}`,
    );
    return;
  }
  pushMru(tuple);
  vscode.window.showInformationMessage(
    `Orchestrator set: ${formatTupleLabel(tuple)}`,
  );
}

async function runQuickpick(
  ctx: WriteContext,
  prefillProvider?: Provider,
): Promise<void> {
  const mru = readMru();

  interface PickItem extends vscode.QuickPickItem {
    flow: "mru" | "new" | "hotkey";
    tuple?: OrchestratorTuple;
  }

  const items: PickItem[] = [];

  // If we have a prefill provider (e.g., Gemini/Copilot shim entry),
  // surface the MRU entries for that provider first.
  const orderedMru = prefillProvider
    ? [
        ...mru.filter((t) => t.provider === prefillProvider),
        ...mru.filter((t) => t.provider !== prefillProvider),
      ]
    : mru;

  for (const tuple of orderedMru) {
    items.push({
      flow: "mru",
      tuple,
      label: formatTupleLabel(tuple),
      description: tuple.provider === prefillProvider ? "$(star-full) recent" : "recent",
    });
  }
  items.push({
    flow: "new",
    label: prefillProvider
      ? `$(plus) (set new ${findProviderLabel(prefillProvider)} combination…)`
      : "$(plus) (set new combination…)",
  });
  if (mru.length > 0) {
    items.push({
      flow: "hotkey",
      label: "$(keyboard) (copy keybindings.json snippet for current selection)",
      description: formatTupleLabel(mru[0]),
    });
  }

  const picked = await vscode.window.showQuickPick(items, {
    title: prefillProvider
      ? `Set Orchestrator — ${findProviderLabel(prefillProvider)}`
      : "Set Orchestrator",
    placeHolder: "Pick a recent combination, set a new one, or copy a hotkey snippet",
  });
  if (!picked) return;

  if (picked.flow === "mru" && picked.tuple) {
    await executeWrite(picked.tuple, ctx);
    return;
  }
  if (picked.flow === "hotkey") {
    const snippet = buildKeybindingSnippet(mru[0]);
    await vscode.env.clipboard.writeText(snippet);
    vscode.window.showInformationMessage(
      "Keybindings snippet copied to clipboard. Paste into keybindings.json and adjust the key as desired.",
    );
    return;
  }
  // flow === "new"
  let tuple: OrchestratorTuple | undefined;
  if (prefillProvider) {
    const model = await pickModel(prefillProvider);
    if (!model) return;
    const effort = await pickEffort();
    if (!effort) return;
    const thinking = await pickThinking();
    if (thinking === undefined) return;
    tuple = { provider: prefillProvider, model, effort, thinking };
  } else {
    tuple = await runMultiStepFlow();
  }
  if (!tuple) return;
  await executeWrite(tuple, ctx);
}

export function registerSetOrchestratorManual(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.setOrchestrator",
      async (args?: ManualCommandArgs) => {
        const workspaceCwd =
          vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
        const ctx: WriteContext = { extensionUri: context.extensionUri, workspaceCwd };

        if (isCompleteArgs(args)) {
          await executeWrite(
            {
              provider: args.provider,
              model: args.model,
              effort: args.effort,
              thinking: args.thinking,
            },
            ctx,
          );
          return;
        }
        await runQuickpick(ctx, args?.prefillProvider);
      },
    ),
  );
}

```
