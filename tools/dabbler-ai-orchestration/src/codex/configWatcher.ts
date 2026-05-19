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
