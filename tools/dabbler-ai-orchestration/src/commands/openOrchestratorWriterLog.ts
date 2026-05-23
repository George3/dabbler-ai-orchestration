// Opens ~/.dabbler/orchestrator-writer.log for operator diagnostics.
//
// The canonical writer (`python -m ai_router.start_session` —
// Set 033 H1) appends one JSON-lines entry per check-out, refusal,
// and force-override so the operator can see why a claim was
// refused or how a conflict was resolved. The log is best-effort —
// losing it doesn't change behavior, just visibility.

import * as vscode from "vscode";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

export function registerOpenOrchestratorWriterLog(
  context: vscode.ExtensionContext,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("dabbler.openOrchestratorWriterLog", async () => {
      const logPath = path.join(os.homedir(), ".dabbler", "orchestrator-writer.log");
      if (!fs.existsSync(logPath)) {
        vscode.window.showInformationMessage(
          `No writer log yet — ${logPath} hasn't been touched. ` +
          `Logged entries appear on every start_session call: successful ` +
          `check-outs, H3 hard-coordination refusals, and --force overrides.`,
        );
        return;
      }
      const doc = await vscode.workspace.openTextDocument(logPath);
      await vscode.window.showTextDocument(doc);
    }),
  );
}
