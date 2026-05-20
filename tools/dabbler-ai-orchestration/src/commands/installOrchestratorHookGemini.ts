// Gemini Code Assist orchestrator-hook installer.
//
// Per Set 029 audit Q2: Gemini Code Assist exposes no documented
// persisted state we can scrape for an auto-detect path in v1. The
// "install hook" command therefore opens the manual-override quickpick
// with `provider: "google"` pre-selected so the operator gets one
// click to a working Gemini check-out. No actual hook is installed.
//
// Set 033 S3: command id of the manual-override quickpick renamed
// from `dabbler.setOrchestrator` to `dabbler.checkOutOrchestrator`
// alongside the H1+H3+H4 check-out model.
//
// If/when Gemini Code Assist ships a state-marker file (audit Q2 noted
// this as a roadmap item), swap the body for a real installer that
// invokes `python -m ai_router.start_session` directly (per H1).

import * as vscode from "vscode";

export function registerInstallOrchestratorHookGeminiCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.gemini",
      () =>
        vscode.commands.executeCommand("dabbler.checkOutOrchestrator", {
          prefillProvider: "google",
        }),
    ),
  );
}
