// Opens ~/.dabbler/orchestrator-writer.log for operator diagnostics.
//
// The marker writer (scripts/write-orchestrator-marker.js) appends one
// JSON-lines entry per skipped write so the operator can see why a
// configured-default Codex signal didn't make it through (or why a
// manual quickpick was overridden by a live SessionStart). The log is
// best-effort — losing it doesn't change behavior, just visibility.

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
          `Logged entries appear when a marker write is skipped (e.g., ` +
          `a configured-default Codex signal blocked by a fresh Claude SessionStart).`,
        );
        return;
      }
      const doc = await vscode.workspace.openTextDocument(logPath);
      await vscode.window.showTextDocument(doc);
    }),
  );
}
