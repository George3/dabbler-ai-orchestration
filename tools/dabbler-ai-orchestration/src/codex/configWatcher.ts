// Codex auto-detection: watches `~/.codex/config.toml` for changes and
// invokes `python -m ai_router.start_session` to record a `codex +
// openai` orchestrator check-out on the workspace's in-progress
// session set.
//
// Set 029 audit Q3 retained the "configured-default" framing — the
// signal is medium-confidence and does not track runtime changes —
// but Set 033 Session 3's H1 verdict moved write authority entirely
// into the canonical `ai_router.start_session` writer. The watcher is
// now an invoker, not a writer; the per-set marker file is retired
// (H2) and the orchestrator block on `session-state.json` is the
// authoritative check-out record.
//
// Hard coordination (H3): the writer REFUSES when a different
// engine+provider already holds the check-out, and the watcher does
// NOT pass `--force` — the operator must explicitly take over via the
// Command Palette "Release Check-Out" action. Refusal noise is
// silent (no toast) because the watcher fires on every config-file
// touch and a noisy toast on every Codex edit would be hostile.
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
const CODEX_ENGINE = "codex";
const CODEX_PROVIDER = "openai";

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
  // setting as "thinking on" so downstream UI surfaces (MRU labels,
  // quickpick) match how other providers render.
  const thinking = effort !== null;
  return { model, effort, thinking };
}

function codexConfigPath(): string {
  return path.join(os.homedir(), CODEX_CONFIG_REL);
}

// Resolve the python executable for the workspace. Mirrors the
// resolvePythonPath logic in checkOutOrchestrator.ts and
// installAiRouterCommands.ts.
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

// Walk up from `workspaceCwd` to find the single in-progress session
// set under `docs/session-sets/`. Sync filesystem APIs are fine here:
// the watcher's debounce already coalesces bursts, and the walk-up
// touches at most ~3 directories per fire on a typical workspace.
// Multi-in-progress is the supported case post-S2, but the watcher
// only fires off a single check-out claim — fail-closed on ambiguity
// (the operator picks via the manual quickpick when this happens).
function resolveSingleInProgressSet(workspaceCwd: string): {
  setDir: string;
  currentSession: number | null;
  existingHolder: { engine?: string; provider?: string } | null;
} | null {
  let current = path.resolve(workspaceCwd);
  while (true) {
    const candidate = path.join(current, "docs", "session-sets");
    let entries: fs.Dirent[] | null = null;
    try {
      if (fs.statSync(candidate).isDirectory()) {
        entries = fs.readdirSync(candidate, { withFileTypes: true });
      }
    } catch {
      // not a dir; fall through to parent walk
    }
    if (entries) {
      const inProgress: {
        setDir: string;
        currentSession: number | null;
        existingHolder: { engine?: string; provider?: string } | null;
      }[] = [];
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        const setDir = path.join(candidate, entry.name);
        const statePath = path.join(setDir, "session-state.json");
        try {
          const raw = fs.readFileSync(statePath, "utf8");
          const state = JSON.parse(raw);
          if (state && state.status === "in-progress") {
            const cs = typeof state.currentSession === "number" ? state.currentSession : null; // noqa: D13: in-flight session number passed verbatim to start_session writer; not a legacy-progress derivation
            inProgress.push({
              setDir,
              currentSession: cs,
              existingHolder: state.orchestrator
                ? {
                    engine: state.orchestrator.engine,
                    provider: state.orchestrator.provider,
                  }
                : null,
            });
          }
        } catch {
          // skip — unreadable / missing / invalid JSON
        }
      }
      if (inProgress.length === 1) return inProgress[0];
      // 0 or >1 → fail-closed; the watcher doesn't claim
      return null;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

interface WriteOpts {
  cwd: string;
}

// Dispatches a check-out claim for the current Codex config snapshot
// via `python -m ai_router.start_session`. Best-effort: silent on
// success AND on H3 refusal (the operator picks override via the
// Command Palette). Errors surface to the writer log via
// start_session's own logging path.
function dispatchCheckOut(snapshot: CodexConfigSnapshot, opts: WriteOpts): void {
  if (!snapshot.model) return;

  const resolved = resolveSingleInProgressSet(opts.cwd);
  if (!resolved) return;

  // Same-holder no-op short-circuit: when codex+openai already holds
  // the slot, `start_session` would idempotently bump `lastActivityAt`,
  // but the watcher fires on every config-file touch; firing dozens of
  // python invocations per second when the operator edits config.toml
  // is wasteful. Skip when the holder is already us.
  if (
    resolved.existingHolder?.engine === CODEX_ENGINE &&
    resolved.existingHolder?.provider === CODEX_PROVIDER
  ) {
    return;
  }

  const python = resolvePythonPath(opts.cwd);
  const args = [
    "-m", "ai_router.start_session",
    "--session-set-dir", resolved.setDir,
    "--engine", CODEX_ENGINE,
    "--provider", CODEX_PROVIDER,
    "--model", snapshot.model,
    "--effort", snapshot.effort ?? "medium",
  ];
  if (resolved.currentSession != null) {
    args.push("--session-number", String(resolved.currentSession));
  }
  // No `--force`: the watcher never overrides an existing different-
  // holder check-out. H3 refusal returns exit 4; we swallow stderr to
  // avoid spamming toasts on every config edit. The operator routes
  // explicit overrides through the Command Palette "Release
  // Check-Out" action.

  const child = cp.spawn(python, args, {
    cwd: opts.cwd,
    stdio: ["ignore", "ignore", "ignore"],
    detached: false,
  });
  child.on("error", () => {
    // Best-effort: spawn failure (python not on PATH, etc.) is
    // silent. The operator notices via the orchestrator indicator
    // not updating; they can run the manual quickpick to claim
    // explicitly.
  });
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
  void context; // Set 033 S3: no longer needs extensionUri (helper retired)
  const codexDir = path.join(os.homedir(), ".codex");
  const workspaceCwd =
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();

  const runOnce = (): void => {
    const snap = readSnapshotSafe();
    if (snap && snap.model) {
      dispatchCheckOut(snap, { cwd: workspaceCwd });
    }
  };

  // Initial scan: if the config exists at activation time, push a
  // check-out claim. The writer's H3 hard coordination skips when a
  // different holder already has the slot.
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
