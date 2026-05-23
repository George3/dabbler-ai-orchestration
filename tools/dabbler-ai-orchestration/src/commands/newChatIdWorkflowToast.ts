// Set 036 Session 2: the "READMEish snippet" surfaced to operators
// when they invoke the Gemini / Copilot orchestrator-hook installer
// shims. Neither Gemini Code Assist nor GitHub Copilot exposes a
// per-chat session-id surface (Q1 audit), so the Set 036 H4 composite
// identity (engine + provider + chatSessionId) is satisfied via the
// fallback CLI: `python -m ai_router.new_chat_id [--export]`.
//
// The toast is one-time per (workspace, orchestrator) pair. The
// operator dismisses it via a "Don't show again" button that persists
// the suppression to workspaceState; "Copy command" copies the
// canonical export line to the clipboard so the operator can paste it
// straight into their shell.
//
// Shared by `installOrchestratorHookGemini.ts` and
// `installOrchestratorHookCopilot.ts`. If future orchestrators land
// without a native session-id surface, add another suppress-key
// constant rather than reusing an existing one — each orchestrator
// gets its own one-time prompt so operators who set up one
// orchestrator first still see the toast for the second.

import * as vscode from "vscode";

export const NEW_CHAT_ID_TOAST_SUPPRESS_KEY_GEMINI =
  "dabbler.newChatIdWorkflowToast.suppress.gemini";
export const NEW_CHAT_ID_TOAST_SUPPRESS_KEY_COPILOT =
  "dabbler.newChatIdWorkflowToast.suppress.copilot";

// Round B Major fix: `... | eval "$(cat)"` runs eval in a pipeline
// subshell on bash, so the resulting export does not persist in the
// operator's shell. The current-shell `eval "$(cmd)"` form runs in the
// caller's process and the export survives. Same shape for fish via
// `source` (no subshell issue since the file-substitution form is
// expanded by the parent shell). PowerShell's `Invoke-Expression` is
// already current-scope when invoked at the top level.
const COPY_COMMAND_BASH = `eval "$(python -m ai_router.new_chat_id --export --shell bash)"`;
const COPY_COMMAND_POWERSHELL = `python -m ai_router.new_chat_id --export --shell powershell | Invoke-Expression`;
const COPY_COMMAND_FISH = `python -m ai_router.new_chat_id --export --shell fish | source`;

export async function maybeShowNewChatIdWorkflowToast(
  context: vscode.ExtensionContext,
  orchestratorName: string,
  suppressKey: string,
): Promise<void> {
  if (context.workspaceState.get<boolean>(suppressKey)) return;

  const message =
    `${orchestratorName} has no per-chat session-id surface, so the ` +
    `Dabbler workflow uses a fallback CLI to mint a per-chat ` +
    `identifier. Run ` +
    `\`python -m ai_router.new_chat_id --export\` once per chat ` +
    `(piped through your shell's eval/source primitive) to export ` +
    `CHAT_SESSION_ID, then check out the session set as usual. Skip ` +
    `this step and the writer falls back to its legacy tolerance ` +
    `branch (less precise takeover detection).`;

  const choice = await vscode.window.showInformationMessage(
    message,
    "Copy bash command",
    "Copy PowerShell command",
    "Copy fish command",
    "Don't show again",
  );

  if (choice === "Copy bash command") {
    await vscode.env.clipboard.writeText(COPY_COMMAND_BASH);
    vscode.window.setStatusBarMessage(
      "Dabbler: copied new_chat_id bash workflow to clipboard.",
      4000,
    );
  } else if (choice === "Copy PowerShell command") {
    await vscode.env.clipboard.writeText(COPY_COMMAND_POWERSHELL);
    vscode.window.setStatusBarMessage(
      "Dabbler: copied new_chat_id PowerShell workflow to clipboard.",
      4000,
    );
  } else if (choice === "Copy fish command") {
    await vscode.env.clipboard.writeText(COPY_COMMAND_FISH);
    vscode.window.setStatusBarMessage(
      "Dabbler: copied new_chat_id fish workflow to clipboard.",
      4000,
    );
  } else if (choice === "Don't show again") {
    await context.workspaceState.update(suppressKey, true);
  }
}
