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
