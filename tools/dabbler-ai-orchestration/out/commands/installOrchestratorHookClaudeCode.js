"use strict";
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
exports.installClaudeCodeOrchestratorHook = installClaudeCodeOrchestratorHook;
exports.registerInstallOrchestratorHookClaudeCodeCommand = registerInstallOrchestratorHookClaudeCodeCommand;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const HELPER_REL = path.join("scripts", "write-orchestrator-marker.js");
function helperPathAbs(extensionUri) {
    return vscode.Uri.joinPath(extensionUri, HELPER_REL).fsPath;
}
function buildHookCommand(helperAbsPath, mode) {
    // Claude Code hooks invoke a shell command and pipe the JSON payload
    // to its stdin. node + the absolute helper path + --mode flag is the
    // simplest portable invocation across Windows/macOS/Linux.
    // We quote the helper path in case the path contains spaces (e.g.,
    // "C:\Program Files\..." or "C:\Users\Some Name\..."). Backslashes
    // need no escaping inside the double-quoted string for the shell
    // executors Claude Code runs.
    return `node "${helperAbsPath}" --mode ${mode}`;
}
function ensureMatcherEntry(entries, matcher, command) {
    const list = Array.isArray(entries) ? entries.slice() : [];
    // Find an existing entry: same matcher (or both undefined) AND already
    // points at write-orchestrator-marker.js. Update in place if found.
    for (let i = 0; i < list.length; i++) {
        const entry = list[i];
        const matcherMatches = (entry.matcher ?? undefined) === (matcher ?? undefined);
        if (!matcherMatches)
            continue;
        if (!Array.isArray(entry.hooks))
            continue;
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
    const newEntry = matcher !== undefined
        ? { matcher, hooks: [{ type: "command", command }] }
        : { hooks: [{ type: "command", command }] };
    list.push(newEntry);
    return list;
}
function loadClaudeSettings() {
    const settingsPath = path.join(os.homedir(), ".claude", "settings.json");
    if (!fs.existsSync(settingsPath)) {
        return { settings: {}, path: settingsPath, exists: false };
    }
    const raw = fs.readFileSync(settingsPath, "utf8");
    let parsed;
    try {
        parsed = JSON.parse(raw);
    }
    catch (err) {
        // Don't clobber a malformed file — bail out with a clear message.
        throw new Error(`~/.claude/settings.json contains invalid JSON (${err.message}). ` +
            `Fix or back up the file, then re-run the install command.`);
    }
    return { settings: parsed || {}, path: settingsPath, exists: true };
}
function writeClaudeSettings(settingsPath, settings) {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    const text = JSON.stringify(settings, null, 2) + "\n";
    // Atomic write: tmp + rename. Same precaution as the marker writer
    // because ~/.claude/settings.json is sometimes open by other Claude
    // tooling.
    const tmp = `${settingsPath}.tmp.${process.pid}.${Math.floor(Math.random() * 1e9)}`;
    fs.writeFileSync(tmp, text, { encoding: "utf8" });
    fs.renameSync(tmp, settingsPath);
}
async function installClaudeCodeOrchestratorHook(extensionUri) {
    const helperAbs = helperPathAbs(extensionUri);
    if (!fs.existsSync(helperAbs)) {
        vscode.window.showErrorMessage(`Cannot install hook: helper script not found at ${helperAbs}. ` +
            `Re-install the Dabbler AI Orchestration extension.`);
        return;
    }
    let loaded;
    try {
        loaded = loadClaudeSettings();
    }
    catch (err) {
        vscode.window.showErrorMessage(err.message);
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
        settings.hooks.SessionStart = ensureMatcherEntry(settings.hooks.SessionStart, matcher, sessionStartCmd);
    }
    // UserPromptSubmit: one entry, no matcher (fire on every prompt). The
    // helper short-circuits non-/think* prompts at zero cost.
    settings.hooks.UserPromptSubmit = ensureMatcherEntry(settings.hooks.UserPromptSubmit, undefined, userPromptSubmitCmd);
    try {
        writeClaudeSettings(settingsPath, settings);
    }
    catch (err) {
        vscode.window.showErrorMessage(`Failed to write ${settingsPath}: ${err.message}`);
        return;
    }
    const verbWasWord = exists ? "Updated" : "Created";
    vscode.window
        .showInformationMessage(`${verbWasWord} ~/.claude/settings.json with Dabbler orchestrator hooks ` +
        `(SessionStart + UserPromptSubmit). Restart Claude Code or run /clear in ` +
        `an active session to populate the indicator.`, "Open settings.json")
        .then((picked) => {
        if (picked === "Open settings.json") {
            vscode.workspace.openTextDocument(settingsPath).then((doc) => vscode.window.showTextDocument(doc), () => undefined);
        }
    });
}
function registerInstallOrchestratorHookClaudeCodeCommand(context) {
    context.subscriptions.push(vscode.commands.registerCommand("dabbler.installOrchestratorHook.claudeCode", () => installClaudeCodeOrchestratorHook(context.extensionUri)));
}
//# sourceMappingURL=installOrchestratorHookClaudeCode.js.map