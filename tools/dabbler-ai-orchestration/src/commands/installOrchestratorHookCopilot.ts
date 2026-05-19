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
