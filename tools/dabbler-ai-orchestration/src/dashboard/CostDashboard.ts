import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { readMetrics, readMetricsFromPath, summarizeMetrics, buildSparkline, exportToCsv } from "../utils/metrics";
import { readRouterConfig, computeStaleness, selectCostState } from "../utils/routerConfig";
import {
  noWorkspaceHtml,
  noRouterHtml,
  disabledStateHtml,
  emptyStateHtml,
  stalenessBannerHtml,
  findConfigAnchorLine,
  esc,
} from "./dashboardHtml";

function getNonce(): string {
  let text = "";
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) text += possible.charAt(Math.floor(Math.random() * possible.length));
  return text;
}

export class CostDashboard {
  static currentPanel: CostDashboard | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionUri: vscode.Uri;

  static show(extensionUri: vscode.Uri): void {
    if (CostDashboard.currentPanel) {
      CostDashboard.currentPanel._panel.reveal(vscode.ViewColumn.Two);
      CostDashboard.currentPanel._refresh();
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "dabblerCostDashboard",
      "Dabbler — Cost Dashboard",
      vscode.ViewColumn.Two,
      {
        enableScripts: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "webview")],
      }
    );
    CostDashboard.currentPanel = new CostDashboard(panel, extensionUri);
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;
    this._extensionUri = extensionUri;
    this._refresh();
    this._panel.onDidDispose(() => { CostDashboard.currentPanel = undefined; });
    this._panel.webview.onDidReceiveMessage((msg: { command: string }) => {
      if (msg.command === "exportCsv") this._exportCsv();
      else if (msg.command === "refresh") this._refresh();
      // D6 update-rates action + the disabled-state config link both open
      // router-config.yaml — at the metadata block / metrics knob resp.
      else if (msg.command === "updateRates") void this._openRouterConfig("metadata");
      else if (msg.command === "openConfig") void this._openRouterConfig("metrics");
    });
  }

  private _refresh(): void {
    this._panel.webview.html = this._getHtml();
  }

  private _exportCsv(): void {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) { vscode.window.showErrorMessage("No workspace folder open."); return; }
    const entries = readMetrics(root);
    const csv = exportToCsv(entries);
    const outPath = path.join(root, "ai_router", "cost-export.csv");
    try {
      fs.writeFileSync(outPath, csv, "utf8");
      vscode.commands.executeCommand("vscode.open", vscode.Uri.file(outPath));
    } catch (err) {
      vscode.window.showErrorMessage(`Export failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  private async _openRouterConfig(anchor: "metadata" | "metrics"): Promise<void> {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!root) { vscode.window.showErrorMessage("No workspace folder open."); return; }
    const info = readRouterConfig(root);
    if (!info) {
      vscode.window.showErrorMessage("No ai_router/router-config.yaml found in this workspace.");
      return;
    }
    try {
      const doc = await vscode.workspace.openTextDocument(info.configPath);
      const editor = await vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
      const line = findConfigAnchorLine(doc.getText(), anchor);
      if (line >= 0) {
        const pos = new vscode.Position(line, 0);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.AtTop);
      }
    } catch (err) {
      vscode.window.showErrorMessage(`Could not open router-config.yaml: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  private _getHtml(): string {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const nonce = getNonce();
    const cspSource = this._panel.webview.cspSource;

    if (!root) {
      return noWorkspaceHtml(nonce, cspSource);
    }

    const info = readRouterConfig(root);
    const entries = info ? readMetricsFromPath(info.metricsPath) : [];
    const state = selectCostState(info, entries.length);

    switch (state.kind) {
      case "no-router":
        return noRouterHtml(nonce, cspSource);
      case "disabled":
        return disabledStateHtml(nonce, cspSource, info!.configPath);
      case "empty": {
        const banner = stalenessBannerHtml(computeStaleness(info!));
        return emptyStateHtml(nonce, cspSource, info!.metricsPath, banner);
      }
      case "data":
        return this._dataHtml(nonce, cspSource, info!, entries);
    }
  }

  private _dataHtml(
    nonce: string,
    cspSource: string,
    info: NonNullable<ReturnType<typeof readRouterConfig>>,
    entries: ReturnType<typeof readMetricsFromPath>,
  ): string {
    const summary = summarizeMetrics(entries);
    const sparkline = buildSparkline(summary.dailyCosts);
    const banner = stalenessBannerHtml(computeStaleness(info));

    const htmlPath = vscode.Uri.joinPath(this._extensionUri, "webview", "dashboard.html");
    try {
      let html = fs.readFileSync(htmlPath.fsPath, "utf8");
      const sessionSetRows = Object.entries(summary.bySessionSet)
        .sort(([, a], [, b]) => b.cost - a.cost)
        .map(([slug, d]) =>
          `<tr><td>${esc(slug)}</td><td>${d.sessions}</td><td>$${d.cost.toFixed(3)}</td>` +
          `<td>${d.lastRun ? new Date(d.lastRun).toLocaleDateString("en-CA") : "—"}</td></tr>`
        )
        .join("\n");

      const modelRows = Object.entries(summary.byModel)
        .sort(([, a], [, b]) => b - a)
        .map(([model, cost]) => {
          const pct = summary.totalCost > 0 ? ((cost / summary.totalCost) * 100).toFixed(1) : "0";
          return `<tr><td>${esc(model)}</td><td>$${cost.toFixed(3)}</td><td>${pct}%</td></tr>`;
        })
        .join("\n");

      html = html
        .replace(/{{NONCE}}/g, nonce)
        .replace(/{{CSP_SOURCE}}/g, cspSource)
        .replace("{{BANNER}}", banner)
        .replace("{{TOTAL_COST}}", `$${summary.totalCost.toFixed(3)}`)
        .replace("{{SPARKLINE}}", sparkline)
        .replace("{{SESSION_SET_ROWS}}", sessionSetRows)
        .replace("{{MODEL_ROWS}}", modelRows)
        .replace("{{METRICS_PATH}}", esc(info.metricsPath))
        .replace(
          "{{SPARKLINE_DATES}}",
          `${summary.dailyCosts[0]?.date ?? ""} → ${summary.dailyCosts[29]?.date ?? ""}`
        );
      return html;
    } catch {
      // Template unreadable — fall back to the honest empty state rather
      // than the dead "set a fictional flag" placeholder.
      return emptyStateHtml(nonce, cspSource, info.metricsPath, banner);
    }
  }
}

export function registerCostDashboardCommand(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("dabbler.showCostDashboard", () => {
      CostDashboard.show(context.extensionUri);
    })
  );
}
