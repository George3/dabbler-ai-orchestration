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
//
// Set 036 Session 2 (chatSessionId): the Q1 audit confirmed GitHub
// Copilot exposes no per-chat session-id surface either. The Set 036
// H4 composite identity (engine + provider + chatSessionId) is
// therefore satisfied via the fallback CLI rather than any native
// signal — operators run `python -m ai_router.new_chat_id` once per
// chat session, export the printed UUID as CHAT_SESSION_ID, and the
// subsequent `start_session` invocation pins that UUID into the
// orchestrator block. A one-time informational toast surfaces the
// workflow when this command is invoked so first-time operators
// learn about the fallback before they hit a takeover modal.

import * as vscode from "vscode";
import {
  maybeShowNewChatIdWorkflowToast,
  NEW_CHAT_ID_TOAST_SUPPRESS_KEY_COPILOT,
} from "./newChatIdWorkflowToast";

export function registerInstallOrchestratorHookCopilotCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.copilot",
      async () => {
        await maybeShowNewChatIdWorkflowToast(
          context,
          "GitHub Copilot",
          NEW_CHAT_ID_TOAST_SUPPRESS_KEY_COPILOT,
        );
        await vscode.commands.executeCommand(
          "dabbler.checkOutOrchestrator",
          { prefillProvider: "github" },
        );
      },
    ),
  );
}
