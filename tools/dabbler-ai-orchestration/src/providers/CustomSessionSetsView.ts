// Custom-tree WebviewViewProvider for `dabblerSessionSets`. Set 029
// Session 4 ship — replaces the v0.15.0 native TreeView. Consumes:
//   - SessionSetsModel (pure scan/bucket/sort/text helpers)
//   - MarkerWatchService (per-set marker reader + watchers)
//   - OrchestratorAccordion (pure render helpers)
//   - ActionRegistry (typed action-applicability predicates per row)
//   - suppressionState (manual-collapse persistence reducer)
//   - ScanState (loading/ready phase from extension.ts)
//   - sessionSetsWebviewProtocol (typed messages with monotonic version)
//
// Per S4 audit GPT-5.4 M4: this file owns lifecycle + message
// protocol + snapshot serialization. It does NOT own kbd nav (that's
// in media/session-sets-tree/client.js). It does NOT own gauge
// rendering (that's in OrchestratorAccordion).
//
// Per S4 audit GPT-5.4 M3: every render message carries a monotonic
// version. Out-of-order messages are dropped by the webview client.

import * as vscode from "vscode";
import * as path from "path";
import { readAllSessionSets } from "../utils/fileSystem";
import { SessionSet } from "../types";
import { ScanState } from "./scanState";
import {
  bucketSets,
  forceClosedBadge,
  ICON_FILES,
  isCurrentSessionInFlight,
  needsMigrationBadge,
  progressText,
  sortBucket,
  touchedDate,
  uatBadge,
} from "./SessionSetsModel";
import {
  MarkerWatchService,
  MarkerSnapshot,
  SetResolution,
} from "./MarkerWatchService";
import {
  renderAccordionBody,
  RenderState,
} from "./OrchestratorAccordion";
import {
  applicableActions,
  ActionSupports,
} from "./ActionRegistry";
import {
  SuppressionState,
  clearSuppression,
  prune,
  suppress,
} from "./suppressionState";
import {
  BucketPayload,
  HostToWebview,
  RowPayload,
  ScanState as ProtocolScanState,
  SnapshotPayload,
  WebviewToHost,
} from "../types/sessionSetsWebviewProtocol";

const SUPPRESSION_KEY = "dabbler.sessionSets.suppressedExpand";
const RENDER_DEBOUNCE_MS = 50;

// Allowlist for executeCommand dispatch from the webview. Defense-
// in-depth: even if a malicious string slipped through the protocol
// type check, only these commands fire. Includes all 14 row-context
// actions + 3 indicator-action buttons.
const COMMAND_ALLOWLIST: ReadonlySet<string> = new Set([
  // 14 row-context actions
  "dabblerSessionSets.openSpec",
  "dabblerSessionSets.openActivityLog",
  "dabblerSessionSets.openChangeLog",
  "dabblerSessionSets.openAiAssignment",
  "dabblerSessionSets.openUatChecklist",
  "dabblerSessionSets.revealPlaywrightTests",
  "dabblerSessionSets.openSessionState",
  "dabblerSessionSets.openFolder",
  "dabblerSessionSets.copyStartCommand.default",
  "dabblerSessionSets.copyStartCommand.parallel",
  "dabblerSessionSets.copySlug",
  "dabblerSessionSets.migrate",
  "dabblerSessionSets.cancel",
  "dabblerSessionSets.restore",
  // 3 indicator-action buttons (per S4 M8 indicator-action parity)
  "dabbler.installOrchestratorHook.claudeCode",
  "dabbler.setOrchestrator",
  "dabbler.openOrchestratorWriterLog",
]);

interface RowResolutionInputs {
  resolution: SetResolution;
  state: RenderState;
}

function contextValueFor(set: SessionSet): string {
  const parts = [`sessionSet:${set.state}`];
  if (set.config?.requiresUAT) parts.push("uat");
  if (set.config?.requiresE2E) parts.push("e2e");
  if (set.needsMigration) parts.push("needs-migration");
  return parts.join(":");
}

function descriptionFor(set: SessionSet): string {
  const bits = [
    progressText(set),
    touchedDate(set),
    uatBadge(set),
    forceClosedBadge(set),
    needsMigrationBadge(set),
  ].filter(Boolean);
  return bits.join("  ·  ");
}

export class CustomSessionSetsView implements vscode.WebviewViewProvider, vscode.Disposable {
  public static readonly viewType = "dabblerSessionSets";

  private view: vscode.WebviewView | undefined;
  private version = 0;
  private renderTimer: NodeJS.Timeout | undefined;
  private cache: SessionSet[] | null = null;
  private welcomeHtml: string;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly scanState: ScanState,
    private readonly marker: MarkerWatchService,
  ) {
    this.welcomeHtml = this.loadWelcomeHtmlFromPackageJson();
    this.marker.start();
    this.context.subscriptions.push(
      this.marker.onDidChange(() => this.scheduleRender()),
      this.scanState.onDidChange(() => this.postScanState()),
    );
  }

  public dispose(): void {
    if (this.renderTimer) {
      clearTimeout(this.renderTimer);
      this.renderTimer = undefined;
    }
  }

  public refresh(): void {
    this.cache = null;
    this.scheduleRender();
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this.view = webviewView;
    const webview = webviewView.webview;
    webview.options = {
      enableScripts: true,
      enableCommandUris: true,
      localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, "media")],
    };
    webview.onDidReceiveMessage((msg: WebviewToHost) => this.onMessage(msg));
    webviewView.onDidDispose(() => {
      this.view = undefined;
    });
    webview.html = this.renderShell();
    // First snapshot fires after the ready handshake from client.js
    // (see onMessage("ready") below).
  }

  // ----- Message dispatch (webview → host) -----

  private onMessage(msg: WebviewToHost): void {
    if (!msg || typeof msg !== "object") return;
    switch (msg.type) {
      case "ready":
        this.postSuppressionEcho();
        this.scheduleRender();
        return;
      case "executeCommand":
        this.dispatchCommand(msg.commandId, msg.args);
        return;
      case "showRowContextMenu":
        void this.showContextMenu(msg.slug);
        return;
      case "toggleRow":
        this.handleToggle(msg.slug, msg.expanded, msg.markerUpdatedAt);
        return;
      case "activateRow":
        // Default activation: openSpec (per S4 step 3 / GPT M3).
        this.dispatchCommand("dabblerSessionSets.openSpec", [{ set: this.findSetBySlug(msg.slug) }]);
        return;
    }
  }

  private dispatchCommand(commandId: string, args?: unknown[]): void {
    if (!COMMAND_ALLOWLIST.has(commandId)) {
      console.warn(`[CustomSessionSetsView] rejected command "${commandId}" — not in allowlist`);
      return;
    }
    void vscode.commands.executeCommand(commandId, ...(args ?? []));
  }

  private async showContextMenu(slug: string): Promise<void> {
    const set = this.findSetBySlug(slug);
    if (!set) return;
    const supports: ActionSupports = await this.readSupports();
    const actions = applicableActions(set, supports);
    if (actions.length === 0) return;
    const picked = await vscode.window.showQuickPick(
      actions.map((a) => ({ label: a.label, id: a.id })),
      {
        placeHolder: `${set.name} — choose an action`,
        matchOnDescription: false,
      },
    );
    if (!picked) return;
    this.dispatchCommand(picked.id, [{ set }]);
  }

  private async readSupports(): Promise<ActionSupports> {
    // Context keys live in vscode's contextKeyService which is not
    // directly readable; we re-derive from the configuration +
    // cached sets the same way evaluateSupportContextKeys does.
    const cfg = vscode.workspace.getConfiguration("dabblerSessionSets");
    const uatPref = cfg.get<string>("uatSupport.enabled", "auto");
    const e2ePref = cfg.get<string>("e2eSupport.enabled", "auto");
    const all = this.cache ?? readAllSessionSets();
    const anyUat = all.some((s) => s.config?.requiresUAT);
    const anyE2e = all.some((s) => s.config?.requiresE2E);
    return {
      uat: uatPref === "always" || (uatPref === "auto" && anyUat),
      e2e: e2ePref === "always" || (e2ePref === "auto" && anyE2e),
    };
  }

  private findSetBySlug(slug: string): SessionSet | undefined {
    const all = this.cache ?? readAllSessionSets();
    return all.find((s) => s.name === slug);
  }

  // ----- Suppression state -----

  private getSuppression(): SuppressionState {
    return this.context.workspaceState.get<SuppressionState>(SUPPRESSION_KEY, {});
  }

  private async setSuppression(next: SuppressionState): Promise<void> {
    await this.context.workspaceState.update(SUPPRESSION_KEY, next);
  }

  private handleToggle(slug: string, expanded: boolean, markerUpdatedAt: string | null): void {
    const current = this.getSuppression();
    if (expanded) {
      // Operator manually expanded — clear suppression for this slug.
      const next = clearSuppression(current, slug);
      if (next !== current) {
        void this.setSuppression(next);
        this.postSuppressionEcho();
      }
    } else if (markerUpdatedAt) {
      // Operator manually collapsed — suppress for this occurrence only.
      const next = suppress(current, slug, markerUpdatedAt);
      void this.setSuppression(next);
      this.postSuppressionEcho();
    }
  }

  // ----- Render scheduling + snapshot fire -----

  private scheduleRender(): void {
    if (this.renderTimer) clearTimeout(this.renderTimer);
    this.renderTimer = setTimeout(() => this.postSnapshot(), RENDER_DEBOUNCE_MS);
  }

  private postSnapshot(): void {
    if (!this.view) return;
    this.version++;
    if (!this.cache) {
      this.cache = readAllSessionSets();
    }
    const all = this.cache;

    // Prune suppression for slugs that no longer exist.
    const visibleSlugs = new Set(all.map((s) => s.name));
    const current = this.getSuppression();
    const pruned = prune(current, visibleSlugs);
    if (pruned !== current) {
      void this.setSuppression(pruned);
    }

    const snap: MarkerSnapshot = this.marker.snapshot();
    const inputs: RowResolutionInputs = {
      resolution: snap.resolution,
      state: snap.state,
    };

    const payload: SnapshotPayload = {
      buckets: this.buildBuckets(all, inputs),
      hasAnySets: all.length > 0,
      welcomeHtml: this.welcomeHtml,
      ambiguityBanner: {
        visible:
          snap.resolution.kind === "unresolved" &&
          snap.resolution.reason === "multiple-in-progress-sets",
        candidates:
          snap.resolution.kind === "unresolved" &&
          snap.resolution.reason === "multiple-in-progress-sets"
            ? snap.resolution.candidates ?? []
            : [],
      },
    };

    const msg: HostToWebview = {
      type: "rowsSnapshot",
      version: this.version,
      scanState: this.toProtocolScanState(),
      payload,
    };
    this.view.webview.postMessage(msg);
  }

  private postScanState(): void {
    if (!this.view) return;
    this.version++;
    const msg: HostToWebview = {
      type: "scanStateChanged",
      version: this.version,
      state: this.toProtocolScanState(),
    };
    this.view.webview.postMessage(msg);
    // A scan-state flip to "ready" also warrants a fresh row snapshot.
    if (this.scanState.phase === "ready") {
      this.scheduleRender();
    }
  }

  private postSuppressionEcho(): void {
    if (!this.view) return;
    this.version++;
    const msg: HostToWebview = {
      type: "suppressionEcho",
      version: this.version,
      suppressed: this.getSuppression(),
    };
    this.view.webview.postMessage(msg);
  }

  private toProtocolScanState(): ProtocolScanState {
    return this.scanState.phase === "loading" ? "loading" : "ready";
  }

  private buildBuckets(all: SessionSet[], inputs: RowResolutionInputs): BucketPayload[] {
    const buckets = bucketSets(all);
    const groups: BucketPayload[] = [
      this.buildBucket("in-progress", "In Progress", buckets.inProgress, inputs),
      this.buildBucket("not-started", "Not Started", buckets.notStarted, inputs),
      this.buildBucket("complete", "Complete", buckets.complete, inputs),
    ];
    if (buckets.cancelled.length > 0) {
      groups.push(this.buildBucket("cancelled", "Cancelled", buckets.cancelled, inputs));
    }
    return groups;
  }

  private buildBucket(
    key: BucketPayload["key"],
    label: string,
    subset: SessionSet[],
    inputs: RowResolutionInputs,
  ): BucketPayload {
    const sorted = sortBucket(subset, key);
    const rows = sorted.map((set) => this.buildRow(set, inputs));
    return { key, label, count: subset.length, rows };
  }

  private buildRow(set: SessionSet, inputs: RowResolutionInputs): RowPayload {
    const resolvedSlug =
      inputs.resolution.kind === "resolved" ? inputs.resolution.resolved.slug : null;
    const isResolvedSet = set.name === resolvedSlug;
    // Only render the accordion-body HTML for the resolved set; per
    // S4 Q3 = a, non-in-progress rows do not get an accordion at all,
    // and non-resolved in-progress rows don't get one either (rare —
    // only fires under multi-in-progress ambiguity, where the banner
    // surfaces the issue).
    const accordionHtml = isResolvedSet ? renderAccordionBody(inputs.state) : null;
    return {
      slug: set.name,
      name: set.name,
      state: set.state,
      description: descriptionFor(set),
      contextValue: contextValueFor(set),
      iconSlug: ICON_FILES[set.state] ?? "",
      needsMigration: set.needsMigration,
      isResolvedSet,
      accordionHtml,
    };
  }

  // ----- Welcome HTML extraction -----

  // Parse package.json `viewsWelcome` contribution for our view id
  // and convert the contents markdown to an HTML fragment the
  // webview can render. Keeps the package.json declaration as the
  // single source of truth (per S4 Q3 = a, GPT M4 cleanliness).
  private loadWelcomeHtmlFromPackageJson(): string {
    try {
      const pkgPath = vscode.Uri.joinPath(this.context.extensionUri, "package.json").fsPath;
      const fs = require("fs") as typeof import("fs");
      const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
      const entries: Array<{ view?: string; contents?: string }> = pkg?.contributes?.viewsWelcome ?? [];
      const ours = entries.find((e) => e.view === CustomSessionSetsView.viewType);
      if (!ours?.contents) return this.escHtml("No welcome content available.");
      return this.renderWelcomeMarkdown(ours.contents);
    } catch {
      return this.escHtml("No welcome content available.");
    }
  }

  // Minimal markdown → HTML for the viewsWelcome contents. Supports
  // paragraphs (separated by \n) and the two link forms the actual
  // entry uses: `[label](command:foo)` and `[label](https://...)`.
  // Stays narrow on purpose — we control the source string in
  // package.json, so we don't need a full markdown parser.
  private renderWelcomeMarkdown(src: string): string {
    const linkRe = /\[([^\]]+)\]\(([^)]+)\)/g;
    const paragraphs = src.split(/\n+/);
    const out = paragraphs.map((p) => {
      const escapedTextWithPlaceholders = this.escHtml(p);
      // Re-find link patterns in the ESCAPED text since escHtml
      // doesn't touch `[`, `]`, `(`, `)`.
      const withLinks = escapedTextWithPlaceholders.replace(linkRe, (_m, label, href) => {
        const safeHref = this.escAttr(href);
        const safeLabel = this.escHtml(label);
        return `<a href="${safeHref}">${safeLabel}</a>`;
      });
      return `<p>${withLinks}</p>`;
    });
    return out.join("\n");
  }

  // ----- Webview shell HTML -----

  // The host-side webview HTML only sets up the document chrome +
  // CSP + the empty <main> the client.js mounts into. Snapshot
  // messages drive all subsequent rendering — keeps the protocol
  // single-source-of-truth and avoids host/webview state divergence.
  private renderShell(): string {
    if (!this.view) return "";
    const webview = this.view.webview;
    const cssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "session-sets-tree", "tree.css"),
    );
    const jsUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "session-sets-tree", "client.js"),
    );
    const nonce = String(Math.floor(Math.random() * 1e16));
    // The accordion includes inline SVG generated by
    // OrchestratorAccordion.ts; per the existing indicator CSP, the
    // SVG fragments are part of innerHTML (not separate script), so
    // they're covered by style-src + the webview's own document.
    const csp =
      `default-src 'none'; ` +
      `style-src ${webview.cspSource} 'unsafe-inline'; ` +
      `script-src 'nonce-${nonce}';`;
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="${csp}">
  <link rel="stylesheet" href="${cssUri}">
  <title>Session Sets</title>
</head>
<body>
  <main id="root" role="presentation"></main>
  <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
  }

  // ----- Local escape helpers (welcome path; renderShell only) -----

  private escHtml(s: string): string {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  private escAttr(s: string): string {
    return this.escHtml(s).replace(/"/g, "&quot;");
  }
}

// Silence the unused-import warning for `isCurrentSessionInFlight`
// without removing it — kept as a re-export for any test that
// imports the predicate via this module path.
export { isCurrentSessionInFlight };
