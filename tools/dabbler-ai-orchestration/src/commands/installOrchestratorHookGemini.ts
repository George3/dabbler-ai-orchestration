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
