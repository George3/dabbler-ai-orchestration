// GitHub Copilot orchestrator-hook installer.
//
// Per Set 029 audit Q4: GitHub Copilot's old settings keys for the
// active chat model were deprecated and no current public key replaces
// them. Auto-detection isn't viable in v1. The "install hook" command
// opens the manual-override quickpick with `provider: "github"`
// pre-selected so the operator gets one click to a working Copilot
// check-out. No actual hook is installed.
//
// Set 033 S3: command id of the manual-override quickpick renamed
// from `dabbler.setOrchestrator` to `dabbler.checkOutOrchestrator`
// alongside the H1+H3+H4 check-out model.

import * as vscode from "vscode";

export function registerInstallOrchestratorHookCopilotCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.copilot",
      () =>
        vscode.commands.executeCommand("dabbler.checkOutOrchestrator", {
          prefillProvider: "github",
        }),
    ),
  );
}
