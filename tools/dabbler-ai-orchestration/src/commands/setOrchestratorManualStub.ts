// Manual-override quickpick stub (Session 2 placeholder).
//
// The full implementation lands in Session 3 (per Set 029 spec) with
// MRU + multi-step flow + hotkey-bindable args + force-override
// confirmation. Session 2 ships the command identifier so the webview's
// install-CTA can dispatch to it via `dabbler.setOrchestrator`.
//
// Until Session 3 ships, the command surfaces a "coming in 0.14.x"
// message rather than a no-op silent failure — operators clicking
// through the empty-state CTA flow shouldn't think they hit a dead end.

import * as vscode from "vscode";

export function registerSetOrchestratorManualStub(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("dabbler.setOrchestrator", async () => {
      const picked = await vscode.window.showInformationMessage(
        "Manual orchestrator override lands in the next release (Session 3 of " +
          "Set 029). For now, install the Claude Code SessionStart hook to get " +
          "live signal, or set the marker file by hand at ~/.dabbler/current-orchestrator.json.",
        "Install Claude Code hook",
      );
      if (picked === "Install Claude Code hook") {
        vscode.commands.executeCommand(
          "dabbler.installOrchestratorHook.claudeCode",
        );
      }
    }),
  );
}
