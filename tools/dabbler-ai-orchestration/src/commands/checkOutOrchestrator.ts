// Universal "Check Out As…" quickpick — the manual path for an
// operator to claim the orchestrator check-out on the in-progress
// session set.
//
// Set 033 Session 3 (H1 + H2 + H3 + H4 migration): replaces the
// `dabbler.setOrchestrator` command and its marker-writer dispatch.
//
//   - Top section: MRU tuples (provider + model + effort + thinking),
//     most-recent first. Stored in ~/.dabbler/orchestrator-mru.json.
//   - Bottom row: "(set new combination…)" — multi-step flow
//     (provider → model → effort → thinking).
//   - "(create new hotkey binding)" — copies a keybindings.json snippet
//     to the clipboard pre-filled with the most-recent selection.
//   - Hotkey-bindable: accepts {provider, model, effort, thinking}
//     args; bypasses the quickpick and applies directly (with the
//     same force-override confirmation when applicable).
//   - Force-override: if the in-progress set's `orchestrator` block
//     (per S1's check-out record) names a DIFFERENT `engine + provider`
//     composite (H4 identity), prompt "Override existing check-out
//     held by <holder>?" before proceeding.
//
// Per H1 ("hooks become invokers, not writers"), this command no
// longer dispatches to a Node marker-writer. It invokes
// `python -m ai_router.start_session` — the canonical writer that
// enforces H3 hard coordination and writes the `orchestrator` block
// on `session-state.json`. The `thinking` boolean is preserved in the
// MRU (it tunes the quickpick UX) but is NOT written to
// `session-state.json`'s orchestrator block (which has no `thinking`
// field per the S1 schema delta).

import * as vscode from "vscode";
import * as cp from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

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

// Curated per-provider model lists. Order: flagship-first.
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

// Per-provider "engine brand" used as the H4 identity field on
// `session-state.json`'s orchestrator block. The H4 verdict pins
// identity to (engine + provider) — model is a mutable field, so
// two Claude models from anthropic count as the same holder by
// design (R3 in the Set 033 spec).
const PROVIDER_TO_ENGINE: Record<Provider, string> = {
  anthropic: "claude",
  openai: "codex",
  google: "gemini",
  github: "copilot",
};

export function providerToEngine(provider: Provider): string {
  return PROVIDER_TO_ENGINE[provider];
}

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

// ----- In-progress set resolution -----

export interface InProgressSet {
  slug: string;
  setDir: string;
  state: {
    currentSession: number | null;
    orchestrator: {
      engine?: string;
      provider?: string;
      model?: string;
      effort?: string;
    } | null;
  };
}

// Walk up from `workspaceCwd` to find `docs/session-sets/`. Return ALL
// in-progress sets (multi-in-progress is the supported case per S2's
// reader migration — H2 retired the single-in-progress fail-closed
// posture). Empty array means no in-progress set was found.
export async function listInProgressSetsAt(
  workspaceCwd: string,
): Promise<InProgressSet[]> {
  let current = path.resolve(workspaceCwd);
  while (true) {
    const candidate = path.join(current, "docs", "session-sets");
    let entries: fs.Dirent[] | null = null;
    try {
      const st = await fs.promises.stat(candidate);
      if (st.isDirectory()) {
        entries = await fs.promises.readdir(candidate, { withFileTypes: true });
      }
    } catch {
      // not a dir; fall through to parent walk
    }
    if (entries) {
      const found: InProgressSet[] = [];
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const setDir = path.join(candidate, entry.name);
        const statePath = path.join(setDir, "session-state.json");
        try {
          const raw = await fs.promises.readFile(statePath, "utf8");
          const state = JSON.parse(raw);
          if (state && state.status === "in-progress") {
            const cs = typeof state.currentSession === "number" ? state.currentSession : null; // noqa: D13: in-flight session number passed verbatim to start_session writer; not a legacy-progress derivation
            found.push({
              slug: entry.name,
              setDir,
              state: {
                currentSession: cs,
                orchestrator: state.orchestrator ?? null,
              },
            });
          }
        } catch {
          // skip — unreadable / missing / invalid JSON
        }
      }
      return found;
    }
    const parent = path.dirname(current);
    if (parent === current) return [];
    current = parent;
  }
}

// Prompt the operator to pick a target set when multiple are in
// progress; auto-resolve when there's only one; show an error and
// return null when there are none. Used by both the manual quickpick
// and the Release Check-Out command so the resolution UX is identical.
export async function pickTargetInProgressSet(
  workspaceCwd: string,
  pickerTitle: string,
): Promise<InProgressSet | null> {
  const sets = await listInProgressSetsAt(workspaceCwd);
  if (sets.length === 0) {
    vscode.window.showErrorMessage(
      "No in-progress session set in this workspace. Run `python -m ai_router.start_session` to begin one before checking out an orchestrator.",
    );
    return null;
  }
  if (sets.length === 1) return sets[0];
  const items = sets.map((s) => {
    const holder = s.state.orchestrator
      ? `${s.state.orchestrator.engine ?? "?"} + ${s.state.orchestrator.provider ?? "?"}`
      : "unclaimed";
    return {
      label: s.slug,
      description: `held by ${holder}`,
      set: s,
    };
  });
  const picked = await vscode.window.showQuickPick(items, {
    title: pickerTitle,
    placeHolder: "Multiple in-progress session sets; pick one",
  });
  return picked?.set ?? null;
}

// ----- start_session dispatch -----

interface WriteContext {
  extensionUri: vscode.Uri;
  workspaceCwd: string;
}

// Resolve the python executable for the workspace. Mirrors the
// resolvePythonPath logic in installAiRouterCommands.ts: prefer the
// operator's explicit `dabblerSessionSets.pythonPath` setting,
// otherwise fall back to bare `python` on PATH. The setting can be an
// absolute path, a workspace-relative path, or a bare executable
// name.
function resolvePythonPath(workspaceCwd: string): string {
  const cfg = vscode.workspace.getConfiguration("dabblerSessionSets");
  const inspected = cfg.inspect<string>("pythonPath");
  const explicit =
    inspected?.workspaceFolderValue ??
    inspected?.workspaceValue ??
    inspected?.globalValue;
  const raw = (explicit ?? "python").trim();
  if (!raw) return "python";
  if (path.isAbsolute(raw)) return raw;
  if (raw.includes(path.sep) || raw.includes("/")) {
    return path.resolve(workspaceCwd, raw);
  }
  return raw;
}

export interface DispatchResult {
  exitCode: number;
  stderr: string;
}

// Spawn `python -m ai_router.start_session` with the resolved args.
// `setDir` is absolute (resolved from the workspace walk-up).
// `--force` is passed only when the operator has confirmed an override
// of an existing different-holder check-out.
export function dispatchCheckOut(
  tuple: OrchestratorTuple,
  set: InProgressSet,
  ctx: WriteContext,
  force: boolean,
): Promise<DispatchResult> {
  const python = resolvePythonPath(ctx.workspaceCwd);
  const args = [
    "-m", "ai_router.start_session",
    "--session-set-dir", set.setDir,
    "--engine", providerToEngine(tuple.provider),
    "--provider", tuple.provider,
    "--model", tuple.model,
    "--effort", tuple.effort,
  ];
  if (set.state.currentSession != null) { // noqa: D13: in-flight session number passed verbatim to start_session writer; not a legacy-progress derivation
    args.push("--session-number", String(set.state.currentSession)); // noqa: D13: same as above
  }
  if (force) args.push("--force");
  return new Promise((resolve) => {
    const child = cp.spawn(python, args, {
      cwd: ctx.workspaceCwd,
      stdio: ["ignore", "ignore", "pipe"],
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
    title: "Check Out As — Provider",
    placeHolder: "Select the provider",
  });
  return picked?.provider;
}

async function pickModel(provider: Provider): Promise<string | undefined> {
  const list = PROVIDER_MODELS.find((p) => p.provider === provider)?.models ?? [];
  const items = list.map((m) => ({ label: m.label, description: m.id, id: m.id }));
  const picked = await vscode.window.showQuickPick(items, {
    title: `Check Out As — ${findProviderLabel(provider)} Model`,
    placeHolder: "Select the model",
  });
  return picked?.id;
}

async function pickEffort(): Promise<EffortLevel | undefined> {
  const items = EFFORT_LEVELS.map((e) => ({ label: e.label, id: e.id }));
  const picked = await vscode.window.showQuickPick(items, {
    title: "Check Out As — Effort",
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
    title: "Check Out As — Thinking",
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
      command: "dabbler.checkOutOrchestrator",
      args: tuple,
    },
    null,
    2,
  );
}

// ----- Force-override prompt -----

// Per H4: identity is (engine + provider). When the existing
// orchestrator block names a different composite than the operator's
// chosen tuple, prompt for force-override before proceeding. Same
// composite (or unclaimed) → no prompt; start_session's same-holder
// re-attach (S1) bumps lastActivityAt without disrupting anything.
async function maybeConfirmForceOverride(
  tuple: OrchestratorTuple,
  set: InProgressSet,
): Promise<{ proceed: boolean; force: boolean }> {
  const existing = set.state.orchestrator;
  if (!existing) return { proceed: true, force: false };
  const newEngine = providerToEngine(tuple.provider);
  if (existing.engine === newEngine && existing.provider === tuple.provider) {
    return { proceed: true, force: false };
  }
  const heldBy = `${existing.engine ?? "?"} + ${existing.provider ?? "?"}`;
  const picked = await vscode.window.showWarningMessage(
    `Override existing check-out on "${set.slug}" held by ${heldBy}?`,
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
  // Set 033 S3: when releaseCheckOut launches the quickpick, it pre-
  // selects the in-progress set the operator already confirmed they
  // want to release. Bypasses the picker step.
  targetSet?: InProgressSet;
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

async function executeCheckOut(
  tuple: OrchestratorTuple,
  set: InProgressSet,
  ctx: WriteContext,
): Promise<void> {
  const decision = await maybeConfirmForceOverride(tuple, set);
  if (!decision.proceed) return;
  const result = await dispatchCheckOut(tuple, set, ctx, decision.force);
  if (result.exitCode !== 0) {
    vscode.window.showErrorMessage(
      `Check-out failed (exit ${result.exitCode}): ${result.stderr.trim() || "see writer log"}`,
    );
    return;
  }
  pushMru(tuple);
  const forceNote = decision.force ? " (forced override)" : "";
  vscode.window.showInformationMessage(
    `Checked out as ${formatTupleLabel(tuple)} on "${set.slug}"${forceNote}.`,
  );
}

async function runQuickpick(
  ctx: WriteContext,
  set: InProgressSet,
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
      ? `Check Out As — ${findProviderLabel(prefillProvider)} (${set.slug})`
      : `Check Out As (${set.slug})`,
    placeHolder: "Pick a recent combination, set a new one, or copy a hotkey snippet",
  });
  if (!picked) return;

  if (picked.flow === "mru" && picked.tuple) {
    await executeCheckOut(picked.tuple, set, ctx);
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
  await executeCheckOut(tuple, set, ctx);
}

export function registerCheckOutOrchestrator(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.checkOutOrchestrator",
      async (args?: ManualCommandArgs) => {
        const workspaceCwd =
          vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
        const ctx: WriteContext = { extensionUri: context.extensionUri, workspaceCwd };

        const set = args?.targetSet
          ?? (await pickTargetInProgressSet(workspaceCwd, "Check Out As — Session Set"));
        if (!set) return;

        if (isCompleteArgs(args)) {
          await executeCheckOut(
            {
              provider: args.provider,
              model: args.model,
              effort: args.effort,
              thinking: args.thinking,
            },
            set,
            ctx,
          );
          return;
        }
        await runQuickpick(ctx, set, args?.prefillProvider);
      },
    ),
  );
}
