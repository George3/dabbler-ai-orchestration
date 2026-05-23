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
// Set 036 Session 2 (chatSessionId): the Q1 audit confirmed Gemini
// Code Assist exposes no per-chat session-id surface either. The Set
// 036 H4 composite identity (engine + provider + chatSessionId) is
// therefore satisfied via the fallback CLI rather than any native
// signal — operators run `python -m ai_router.new_chat_id` once per
// chat session, export the printed UUID as CHAT_SESSION_ID, and the
// subsequent `start_session` invocation pins that UUID into the
// orchestrator block. A one-time informational toast surfaces the
// workflow when this command is invoked so first-time operators
// learn about the fallback before they hit a takeover modal.
//
// If/when Gemini Code Assist ships a state-marker file OR a per-chat
// session-id surface (audit Q2 noted these as roadmap items), swap
// the body for a real installer that invokes `python -m
// ai_router.start_session` directly with the native chatSessionId.

import * as vscode from "vscode";
import {
  maybeShowNewChatIdWorkflowToast,
  NEW_CHAT_ID_TOAST_SUPPRESS_KEY_GEMINI,
} from "./newChatIdWorkflowToast";

export function registerInstallOrchestratorHookGeminiCommand(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.installOrchestratorHook.gemini",
      async () => {
        await maybeShowNewChatIdWorkflowToast(
          context,
          "Gemini Code Assist",
          NEW_CHAT_ID_TOAST_SUPPRESS_KEY_GEMINI,
        );
        await vscode.commands.executeCommand(
          "dabbler.checkOutOrchestrator",
          { prefillProvider: "google" },
        );
      },
    ),
  );
}
