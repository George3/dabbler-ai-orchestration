# Set 029 Session 4 verification — Round B (integration: view + client)

## Context

Round A (separate file) verified the provider-layer extracts +
typed-protocol modules. Verdict: **SUGGEST (1)** — minor suggestion
on `describeMarker` purity (calls `Date.now()` for the secondary
effort-age suffix). All other items VERIFIED.

**Round B scope** (this round): the integration surface where M1
(DOM structure), M6 (command-dispatch / Layer-2 coverage), M8
(indicator-action parity), and R10/R11/R12 (focus/a11y, QuickPick
UX, invalid interactive nesting) live.

Splitting per memory `feedback_split_large_verification_bundles`
to stay under the bundle ceiling.

## Files in this bundle (3 + extension.ts diff context, ~1100 LOC)

1. `src/providers/CustomSessionSetsView.ts` (498 LOC) — the
   `WebviewViewProvider`. Consumes `SessionSetsModel` +
   `MarkerWatchService` + `OrchestratorAccordion` + `ActionRegistry` +
   `suppressionState`. Owns lifecycle, message dispatch, snapshot
   serialization, QuickPick context menu, command allowlist.
2. `media/session-sets-tree/client.js` (290 LOC) — webview-side
   rendering, ARIA tree (roving tabindex), kbd nav (↑/↓/Home/End/
   ←/→/Enter/Space/Shift+F10/ContextMenu), contextmenu event
   capture, postMessage protocol with monotonic-version drop, defense-
   in-depth HTML escaping.
3. `media/session-sets-tree/tree.css` (~280 LOC) — tree shell
   (bucket headers, rows, focus/selection, ambiguity banner,
   welcome panel, loading sentinel) + lifted v0.15.0 gauge CSS.

## What you're being asked to verify in Round B

Answer Q1–Q8 in order with **VERIFIED / MUST-FIX / SUGGEST** verdicts
plus 1–3 sentences of reasoning each. After Q1–Q8, emit a final
verdict line per the format at the bottom.

### Q1. DOM structure: no invalid interactive nesting (M1 / R12)

Per audit GPT-5.4 M1: do NOT use `<button role="treeitem">` wrapping
the accordion body. The treeitem container must be a focusable
non-button element (e.g., `<div role="treeitem" tabindex="-1">`) so
the accordion body's interactive children (install-hook /
set-orchestrator / writer-log buttons) are NOT nested inside an
interactive button.

Verify in `client.js`'s `renderRow()`:
- The treeitem is a `<div role="treeitem" tabindex="-1">`, NOT a
  `<button>`.
- The row-header (`<div class="row-header" role="presentation">`)
  inside is a non-interactive presentational wrapper.
- The accordion-body (`<div class="accordion-body" role="region">`)
  with the install-hook / set-orchestrator / writer-log buttons is
  rendered as a sibling region inside the treeitem container, not
  nested inside any interactive button.

### Q2. ARIA tree semantics (WAI-ARIA 1.2 single-select tree)

Verify the rendered structure follows the WAI-ARIA single-select
tree pattern:
- Container has `role="tree"` and `aria-label`.
- Each bucket has `role="group"` with `aria-labelledby` pointing at
  a header element.
- Each row has `role="treeitem"`, `aria-level`, `aria-selected`,
  and `aria-expanded` (only when expandable per Q3 of the audit —
  non-expandable rows should NOT carry `aria-expanded`, per GPT M3
  "no inert chevron").
- Roving tabindex: at any time, exactly one treeitem has
  `tabindex="0"`, all others `tabindex="-1"`. `initRovingFocus()`
  initializes; `focusItem()` rotates.
- Keyboard handler covers: ↑/↓ sibling, Home/End first/last,
  ←/→ collapse/expand, Enter/Space activate, Shift+F10 +
  ContextMenu key for the QuickPick.

### Q3. Monotonic version drop client-side (M3 carry-forward)

Per audit GPT-5.4 M3: webview client drops messages with
`version < currentVersion`. Verify in `client.js`:
- The `message` event listener checks `if (typeof msg.version ===
  "number" && msg.version < currentVersion) return;` BEFORE acting
  on the message.
- `currentVersion` is bumped to the message's version on accept.
- `rowsSnapshot`, `scanStateChanged`, `suppressionEcho` all carry
  versions and respect the drop logic.

### Q4. Command-dispatch allowlist (defense-in-depth)

`CustomSessionSetsView.ts` includes a `COMMAND_ALLOWLIST` set
containing the 14 row-action command ids + the 3 indicator-action
buttons (install-hook / set-orchestrator / writer-log). The
`dispatchCommand(commandId, args)` method rejects any commandId not
in the allowlist before calling `vscode.commands.executeCommand`.

Verify:
- All 17 expected commands are in the allowlist (14 actions + 3
  indicator buttons).
- No commandId from a webview message can fire executeCommand
  without passing the allowlist check.
- Rejected commands log a warning (not silent).

### Q5. Indicator-action parity (M8 — ship blocker for retirement)

Per audit GPT-5.4 M8: the `dabblerOrchestratorIndicator` view must
NOT retire until the accordion body preserves install-hook +
set-orchestrator + open-writer-log buttons. The retirement happened
in this session — verify the parity exists.

Verify in `OrchestratorAccordion.ts` (Round A bundle — re-check):
- `renderAccordionEmpty()` renders all three buttons (install-hook
  CTA + set-orchestrator + writer-log).
- `renderAccordionLoaded()` renders set-orchestrator + writer-log
  (the install-hook button is unnecessary when a marker exists, but
  the set-orchestrator + writer-log buttons must persist).
- Buttons carry `data-command="dabbler.installOrchestratorHook.claudeCode"`,
  `data-command="dabbler.setOrchestrator"`, and
  `data-command="dabbler.openOrchestratorWriterLog"` respectively.
- The webview client.js wires these via the `[data-command]` event
  listener (the buttons inside the accordion body are not wrapped
  in a treeitem interactive element — see Q1).

### Q6. Suppression handshake (host ↔ webview)

The suppression state lives in `workspaceState` (per Q2 = a). The
host echoes the state to the webview via `SuppressionEchoMsg`. The
webview tracks the same state via the `suppressed` local + a
`manualToggles` overlay for current-session clicks.

Verify in `CustomSessionSetsView.ts`:
- `handleToggle(slug, expanded, markerUpdatedAt)` calls `suppress()`
  on manual collapse and `clearSuppression()` on manual expand, then
  fires `postSuppressionEcho()`.
- The reducer prunes via the round-up snapshot (`postSnapshot()`
  calls `prune(current, visibleSlugs)`).
- `getSuppression()` / `setSuppression()` read/write
  `context.workspaceState` under the key
  `"dabbler.sessionSets.suppressedExpand"`.

### Q7. Ambiguity banner (Q8 = a+c)

When the resolver returns `multiple-in-progress-sets`, a banner
appears above the In Progress bucket with a link to open the writer
log. S3's silent fail-close behavior is preserved for
`no-in-progress-set` / `no-docs-session-sets` (no banner, no
accordion, no orphan marker).

Verify:
- `CustomSessionSetsView.postSnapshot()` populates
  `payload.ambiguityBanner = { visible, candidates }` with
  `visible = true` only when `reason === "multiple-in-progress-sets"`.
- `client.js render()` checks `lastSnapshot.ambiguityBanner.visible`
  and emits a `.ambiguity-banner` div with an
  `[data-command="dabbler.openOrchestratorWriterLog"]` button.
- No code path writes an orphan marker on failed resolution
  (carry-forward from S3 fail-closed posture).

### Q8. CSP + nonce hygiene

The webview HTML shell (`CustomSessionSetsView.renderShell()`)
must declare a strict Content-Security-Policy with:
- `default-src 'none'` (deny everything by default).
- `style-src ${webview.cspSource} 'unsafe-inline'` (CSS file +
  inline SVG `<style>`-free; SVG fragments contain only attributes,
  not embedded `<script>`).
- `script-src 'nonce-${nonce}'` with a freshly-generated nonce that
  matches the `<script nonce="${nonce}">` in the shell.

Verify:
- Nonce is freshly generated per `renderShell()` call (not stable
  across renders).
- CSP allows the webview's own resource origin for CSS via
  `webview.cspSource`.
- No `script-src 'unsafe-inline'` or `'unsafe-eval'`.
- No external network origin in `script-src` or `style-src`.

---

## Final verdict (Round B)

Emit one summary line at the end:

`VERDICT: VERIFIED` if Q1–Q8 all pass without must-fix items
`VERDICT: MUST-FIX (<count>)` if any Q has a must-fix
`VERDICT: SUGGEST (<count>)` if no must-fix but ≥1 suggest items

Followed by a 2–3-sentence overall summary.


---

## File 1: src/providers/CustomSessionSetsView.ts

```typescript
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

```


---

## File 2: media/session-sets-tree/client.js

```javascript
// Webview-side client for the Set 029 Session 4 custom Session Sets
// view. Owns: ARIA tree rendering (roving tabindex), keyboard nav,
// contextmenu / Shift+F10 / Context Menu key dispatch, manual expand/
// collapse, postMessage protocol with monotonic-version drop per
// S4 audit GPT-5.4 M3.
//
// All dynamic text from the host snapshot is HTML-escaped here on the
// webview side too (defense-in-depth) before any innerHTML
// assignment, per S4 R13 mitigation / GPT-5.4 M5.
//
// TODO: type-ahead search (WAI-ARIA tree pattern). Deferred to v1.1
// per S4 audit Gemini M10 — today's set counts are small enough that
// arrow nav is fine; the affordance ships when set counts grow.

(function () {
  const vscode = acquireVsCodeApi();
  const root = document.getElementById("root");
  let currentVersion = -1;
  let scanState = "loading";
  let lastSnapshot = null;
  let suppressed = {}; // slug -> marker.updatedAt
  // Manually toggled slugs in the current session (added on every
  // user click). Persists across re-renders so a fresh snapshot
  // doesn't snap-back an operator's manual collapse / expand.
  const manualToggles = {};

  // ----- Escape helpers (defense-in-depth) -----
  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escAttr(s) {
    return escHtml(s).replace(/"/g, "&quot;");
  }

  // ----- Message receive (host → webview) -----
  window.addEventListener("message", function (event) {
    const msg = event.data;
    if (!msg || typeof msg !== "object") return;
    if (typeof msg.version === "number" && msg.version < currentVersion) {
      // Stale snapshot — drop. Monotonic version protects against
      // out-of-order watcher / polling races.
      return;
    }
    if (typeof msg.version === "number") {
      currentVersion = msg.version;
    }
    switch (msg.type) {
      case "rowsSnapshot":
        scanState = msg.scanState || "ready";
        lastSnapshot = msg.payload;
        render();
        return;
      case "scanStateChanged":
        scanState = msg.state;
        render();
        return;
      case "suppressionEcho":
        suppressed = msg.suppressed || {};
        render();
        return;
    }
  });

  // ----- Render -----
  function render() {
    if (!root) return;
    if (scanState === "loading") {
      root.innerHTML =
        '<div class="loading-sentinel" role="status" aria-live="polite">' +
          '<div class="loading-title">Setting up your project…</div>' +
          '<div class="loading-subtitle">scanning session sets…</div>' +
        '</div>';
      return;
    }
    if (!lastSnapshot) {
      // Ready but no snapshot yet. Render nothing; host will ship one
      // momentarily.
      root.innerHTML = "";
      return;
    }
    if (!lastSnapshot.hasAnySets) {
      // viewsWelcome equivalent — render the welcome HTML provided
      // by the host (it parses package.json viewsWelcome contents).
      // welcomeHtml is host-escaped via the renderWelcomeMarkdown
      // pipeline, safe to insert.
      root.innerHTML = '<div class="welcome">' + lastSnapshot.welcomeHtml + '</div>';
      return;
    }

    const parts = [];
    if (lastSnapshot.ambiguityBanner.visible) {
      const cands = lastSnapshot.ambiguityBanner.candidates
        .map(function (s) { return escHtml(s); })
        .join(", ");
      parts.push(
        '<div class="ambiguity-banner" role="status">' +
          '<span class="ambiguity-icon" aria-hidden="true">ℹ</span>' +
          'Multiple in-progress sets — orchestrator info hidden.' +
          ' <button type="button" class="ambiguity-link" data-command="dabbler.openOrchestratorWriterLog">' +
          'Open writer log</button>' +
          (cands ? ' <span class="ambiguity-candidates">(' + cands + ')</span>' : '') +
        '</div>'
      );
    }

    parts.push('<div role="tree" aria-label="Session Sets" class="tree">');
    for (const bucket of lastSnapshot.buckets) {
      parts.push(renderBucket(bucket));
    }
    parts.push('</div>');
    root.innerHTML = parts.join("");

    wireInteraction();
    initRovingFocus();
  }

  function renderBucket(bucket) {
    const labelText = bucket.label + "  (" + bucket.count + ")";
    const groupId = "group-" + bucket.key;
    if (bucket.count === 0) {
      return (
        '<div role="group" aria-labelledby="' + groupId + '" class="bucket bucket-empty">' +
          '<div id="' + groupId + '" class="bucket-header">' + escHtml(labelText) + '</div>' +
        '</div>'
      );
    }
    const rows = bucket.rows.map(function (row) { return renderRow(row); }).join("");
    return (
      '<div role="group" aria-labelledby="' + groupId + '" class="bucket">' +
        '<div id="' + groupId + '" class="bucket-header">' + escHtml(labelText) + '</div>' +
        rows +
      '</div>'
    );
  }

  function renderRow(row) {
    const isExpandable = row.isResolvedSet && row.accordionHtml !== null;
    // Default expansion: in-progress + resolved + not currently
    // suppressed for this occurrence. Manual override (current
    // session click) takes precedence.
    let expanded;
    if (Object.prototype.hasOwnProperty.call(manualToggles, row.slug)) {
      expanded = manualToggles[row.slug];
    } else {
      expanded = isExpandable && !isSuppressedForRow(row);
    }
    const ariaExpanded = isExpandable ? ' aria-expanded="' + (expanded ? "true" : "false") + '"' : "";
    const chevron = isExpandable
      ? '<span class="chevron" aria-hidden="true">' + (expanded ? "▾" : "▸") + '</span>'
      : '<span class="chevron-spacer" aria-hidden="true"></span>';
    const accordionAttrs = isExpandable
      ? (' data-expandable="1" data-marker-updated-at="' +
          (row._markerUpdatedAt ? escAttr(row._markerUpdatedAt) : "") + '"')
      : "";

    const bodyHtml = isExpandable && expanded
      ? '<div class="accordion-body" role="region" aria-label="Orchestrator">' +
          // accordionHtml is host-escaped (OrchestratorAccordion.escHtml
          // / escAttr) — safe to inject.
          row.accordionHtml +
        '</div>'
      : "";

    return (
      '<div role="treeitem" tabindex="-1" aria-level="2"' + ariaExpanded +
      ' aria-selected="false" data-slug="' + escAttr(row.slug) + '"' +
      ' data-state="' + escAttr(row.state) + '"' +
      ' data-context-value="' + escAttr(row.contextValue) + '"' +
      accordionAttrs +
      ' class="row row-' + escAttr(row.state) + '">' +
        '<div class="row-header" role="presentation">' +
          chevron +
          '<span class="row-icon" aria-hidden="true" data-icon="' + escAttr(row.iconSlug) + '"></span>' +
          '<span class="row-name">' + escHtml(row.name) + '</span>' +
          '<span class="row-description">' + escHtml(row.description) + '</span>' +
        '</div>' +
        bodyHtml +
      '</div>'
    );
  }

  function isSuppressedForRow(row) {
    // We don't currently transport per-row marker.updatedAt on the
    // RowPayload — the resolved set's accordion-body is generated
    // by the host from MarkerWatchService.snapshot(), and the
    // suppression echo carries slug → updatedAt mapping. If the
    // host's suppression record exists for this slug, treat as
    // suppressed (the snapshot was generated with the same marker
    // state that the suppression is keyed against).
    return Object.prototype.hasOwnProperty.call(suppressed, row.slug);
  }

  // ----- Roving tabindex + kbd nav -----
  function initRovingFocus() {
    const items = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (items.length === 0) return;
    // The first row owns the single tabstop into the tree.
    items.forEach(function (el, idx) {
      el.setAttribute("tabindex", idx === 0 ? "0" : "-1");
    });
  }

  function focusItem(item) {
    if (!item) return;
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    all.forEach(function (el) {
      el.setAttribute("tabindex", "-1");
      el.setAttribute("aria-selected", "false");
    });
    item.setAttribute("tabindex", "0");
    item.setAttribute("aria-selected", "true");
    item.focus();
  }

  function moveFocus(current, delta) {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    const i = all.indexOf(current);
    if (i === -1) return;
    const next = all[Math.min(all.length - 1, Math.max(0, i + delta))];
    focusItem(next);
  }

  function focusFirst() {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (all.length) focusItem(all[0]);
  }
  function focusLast() {
    const all = Array.from(root.querySelectorAll('[role="treeitem"]'));
    if (all.length) focusItem(all[all.length - 1]);
  }

  function toggleRow(item, expand) {
    const slug = item.getAttribute("data-slug");
    const isExpandable = item.getAttribute("data-expandable") === "1";
    if (!slug || !isExpandable) return;
    const desired =
      typeof expand === "boolean"
        ? expand
        : item.getAttribute("aria-expanded") !== "true";
    manualToggles[slug] = desired;
    const markerUpdatedAt = item.getAttribute("data-marker-updated-at") || null;
    vscode.postMessage({
      type: "toggleRow",
      slug: slug,
      expanded: desired,
      markerUpdatedAt: markerUpdatedAt,
    });
    render();
    // Re-focus the same row after re-render.
    const refreshed = root.querySelector('[data-slug="' + cssEscape(slug) + '"]');
    if (refreshed) focusItem(refreshed);
  }

  // ----- Interaction wiring (after each render) -----
  function wireInteraction() {
    // Click on row header → activate (default = openSpec).
    Array.from(root.querySelectorAll('.row-header')).forEach(function (header) {
      header.addEventListener("click", function (ev) {
        const item = ev.currentTarget.closest('[role="treeitem"]');
        if (!item) return;
        // Click on the chevron toggles expand/collapse; click
        // elsewhere on the header activates.
        if (ev.target && ev.target.classList && ev.target.classList.contains("chevron")) {
          toggleRow(item);
          ev.stopPropagation();
          return;
        }
        focusItem(item);
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "activateRow", slug: slug });
        }
      });
    });

    // Right-click → context menu.
    Array.from(root.querySelectorAll('[role="treeitem"]')).forEach(function (item) {
      item.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        focusItem(item);
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "showRowContextMenu", slug: slug });
        }
      });
    });

    // Buttons inside accordion / banner with data-command.
    Array.from(root.querySelectorAll('[data-command]')).forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const commandId = btn.getAttribute("data-command");
        if (!commandId) return;
        vscode.postMessage({ type: "executeCommand", commandId: commandId });
      });
    });
  }

  // Root-level keydown — captures keys regardless of which row has
  // focus. Implements WAI-ARIA single-select tree pattern.
  document.addEventListener("keydown", function (ev) {
    const item = ev.target.closest && ev.target.closest('[role="treeitem"]');
    if (!item) return;
    switch (ev.key) {
      case "ArrowDown":
        ev.preventDefault();
        moveFocus(item, 1);
        return;
      case "ArrowUp":
        ev.preventDefault();
        moveFocus(item, -1);
        return;
      case "Home":
        ev.preventDefault();
        focusFirst();
        return;
      case "End":
        ev.preventDefault();
        focusLast();
        return;
      case "ArrowRight":
        ev.preventDefault();
        if (item.getAttribute("data-expandable") === "1") {
          if (item.getAttribute("aria-expanded") !== "true") {
            toggleRow(item, true);
          }
        }
        return;
      case "ArrowLeft":
        ev.preventDefault();
        if (item.getAttribute("data-expandable") === "1" && item.getAttribute("aria-expanded") === "true") {
          toggleRow(item, false);
        }
        return;
      case "Enter":
      case " ":
        ev.preventDefault();
        const slug = item.getAttribute("data-slug");
        if (slug) {
          vscode.postMessage({ type: "activateRow", slug: slug });
        }
        return;
      case "F10":
        if (ev.shiftKey) {
          ev.preventDefault();
          const s = item.getAttribute("data-slug");
          if (s) vscode.postMessage({ type: "showRowContextMenu", slug: s });
        }
        return;
      case "ContextMenu":
        ev.preventDefault();
        const slugCm = item.getAttribute("data-slug");
        if (slugCm) vscode.postMessage({ type: "showRowContextMenu", slug: slugCm });
        return;
    }
  });

  // Minimal CSS.escape polyfill for attribute-selector use.
  function cssEscape(s) {
    if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, function (c) {
      return "\\" + c.charCodeAt(0).toString(16) + " ";
    });
  }

  // Handshake: tell host we're ready for the first snapshot.
  vscode.postMessage({ type: "ready" });
})();

```


---

## File 3: media/session-sets-tree/tree.css

```css
/*
 * Custom Session Sets tree — Set 029 Session 4.
 *
 * Two layers:
 *   1. Tree shell: bucket groups, rows, chevron, focus / selection,
 *      loading sentinel, welcome panel, ambiguity banner.
 *   2. Accordion body: lifted wholesale from v0.15.0's
 *      orchestrator-indicator/indicator.css so the gauge HTML
 *      generated by OrchestratorAccordion.ts renders identically to
 *      the retired dedicated indicator view.
 *
 * Theme-aware throughout: every color is either a VS Code CSS variable
 * or a chosen-for-both-themes IBM palette tone (gauge colors).
 */

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  font-family: var(--vscode-font-family);
  font-size: var(--vscode-font-size);
  color: var(--vscode-foreground);
  background: transparent;
}

/* ---- Theme-derived custom properties (mirrors indicator.css) ---- */
:root {
  --indicator-stripe-color: rgba(255, 255, 255, 0.30);
  --indicator-band-bg: var(--vscode-foreground);
  --indicator-band-fg: var(--vscode-editor-background, #1e1e1e);
}
body.vscode-light, body.vscode-high-contrast-light {
  --indicator-stripe-color: rgba(0, 0, 0, 0.22);
  --indicator-band-bg: #3C3C3C;
  --indicator-band-fg: #ffffff;
}

/* ---- Loading sentinel ---- */
.loading-sentinel {
  padding: 14px 12px;
  text-align: center;
  opacity: 0.75;
}
.loading-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.loading-subtitle { font-size: 12px; opacity: 0.7; }

/* ---- Welcome panel (rendered from package.json viewsWelcome) ---- */
.welcome {
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.55;
}
.welcome p { margin: 0 0 8px 0; }
.welcome a {
  color: var(--vscode-textLink-foreground);
  text-decoration: none;
}
.welcome a:hover { color: var(--vscode-textLink-activeForeground); text-decoration: underline; }

/* ---- Ambiguity banner (multi-in-progress fail-closed signal) ---- */
.ambiguity-banner {
  padding: 8px 10px;
  margin: 0 0 8px 0;
  background: var(--vscode-inputValidation-infoBackground, rgba(100, 143, 255, 0.12));
  border-left: 3px solid var(--vscode-inputValidation-infoBorder, #648FFF);
  color: var(--vscode-foreground);
  font-size: 12px;
  line-height: 1.4;
}
.ambiguity-icon { margin-right: 6px; }
.ambiguity-link {
  background: none;
  border: none;
  padding: 0;
  margin: 0 4px;
  color: var(--vscode-textLink-foreground);
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
}
.ambiguity-link:hover { color: var(--vscode-textLink-activeForeground); }
.ambiguity-candidates { opacity: 0.7; }

/* ---- Tree shell ---- */
.tree {
  display: flex;
  flex-direction: column;
  padding: 2px 0;
}

.bucket {
  margin-bottom: 4px;
}
.bucket-header {
  padding: 4px 12px 2px 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.72;
  user-select: none;
}
.bucket-empty .bucket-header {
  opacity: 0.45;
}

/* ---- Row ---- */
.row {
  display: block;
  padding: 0;
  margin: 0;
  outline: none;
  border-left: 2px solid transparent;
  cursor: default;
}
.row:focus,
.row[aria-selected="true"] {
  background: var(--vscode-list-focusBackground, rgba(127, 127, 127, 0.10));
  border-left-color: var(--vscode-focusBorder, #007fd4);
}
.row:focus-visible {
  outline: 1px solid var(--vscode-focusBorder, #007fd4);
  outline-offset: -1px;
}

.row-header {
  display: flex;
  align-items: center;
  padding: 3px 10px 3px 8px;
  gap: 4px;
  font-size: 13px;
  line-height: 1.4;
  user-select: none;
}
.row-header:hover {
  background: var(--vscode-list-hoverBackground, rgba(127, 127, 127, 0.10));
}
.chevron, .chevron-spacer {
  display: inline-block;
  width: 14px;
  flex-shrink: 0;
  text-align: center;
  opacity: 0.7;
  cursor: pointer;
}
.row-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-right: 2px;
  /* Icons resolved at runtime via data-icon attribute; the host
   * could swap to actual sprite URIs, but for v1 a textual badge
   * via the bucket header + row-state class is enough visual
   * signal. */
}
.row-icon[data-icon="done.svg"]::before        { content: "✓"; opacity: 0.7; }
.row-icon[data-icon="in-progress.svg"]::before { content: "▶"; opacity: 0.85; }
.row-icon[data-icon="not-started.svg"]::before { content: "○"; opacity: 0.55; }
.row-icon[data-icon="cancelled.svg"]::before   { content: "✕"; opacity: 0.55; }

.row-name {
  flex: 0 0 auto;
  max-width: 60%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}
.row-description {
  flex: 1 1 auto;
  margin-left: 8px;
  font-size: 12px;
  opacity: 0.7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- Accordion body ---- */
.accordion-body {
  padding: 4px 10px 8px 24px;
  container-type: inline-size;
}

/* Action buttons inside the accordion (install-hook / set-orchestrator
 * / writer-log per S4 M8 indicator-action parity). */
.acc-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.acc-action {
  background: var(--vscode-button-secondaryBackground, transparent);
  color: var(--vscode-button-secondaryForeground, var(--vscode-foreground));
  border: 1px solid var(--vscode-button-border, var(--vscode-contrastBorder, transparent));
  border-radius: 2px;
  padding: 3px 10px;
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
}
.acc-action:hover {
  background: var(--vscode-button-secondaryHoverBackground, var(--vscode-list-hoverBackground));
}
.acc-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--vscode-textLink-foreground);
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
}
.acc-link:hover { color: var(--vscode-textLink-activeForeground); }

.acc-empty {
  padding: 4px 0 0 0;
  font-size: 12px;
  line-height: 1.4;
}
.acc-empty .grey-gauges {
  display: flex;
  justify-content: flex-start;
  gap: 14px;
  opacity: 0.45;
  margin-bottom: 4px;
}
.acc-empty-cta { margin-bottom: 4px; }

/* ===== LIFTED FROM indicator.css (gauge body) ===== */

.gauges {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: start;
}
@container (max-width: 260px) {
  .gauges { grid-template-columns: 1fr; }
}

.gauge-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  font-size: 14px;
  line-height: 1.2;
}

.gauge-svg-wrap {
  position: relative;
  display: inline-block;
  width: 100px;
  height: 54px;
}
.gauge-svg {
  width: 100px;
  height: 54px;
  display: block;
}

.gauge-arc-bg {
  fill: none;
  stroke: var(--vscode-editorWidget-border, #444);
  stroke-width: 7;
  stroke-linecap: butt;
}
.gauge-arc-fill {
  fill: none;
  stroke-width: 7;
  stroke-linecap: butt;
}
.gauge-rim {
  fill: none;
  stroke: var(--vscode-foreground);
  stroke-width: 1;
  stroke-opacity: 0.6;
}
.gauge-needle {
  stroke: var(--vscode-foreground);
  stroke-width: 1.4;
  stroke-linecap: round;
}
.gauge-needle-pivot {
  fill: var(--vscode-foreground);
}
.gauge-sublabel {
  margin-top: 2px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* IBM palette tier/effort colors (valence-neutral, colorblind-safe). */
.tier-low      .gauge-arc-fill { stroke: #648FFF; }
.tier-mid      .gauge-arc-fill { stroke: #785EF0; }
.tier-flagship .gauge-arc-fill { stroke: #DC267F; }
.tier-unknown  .gauge-arc-fill { stroke: var(--vscode-disabledForeground, #888); }

.effort-low        .gauge-arc-fill { stroke: #648FFF; }
.effort-medium     .gauge-arc-fill { stroke: #785EF0; }
.effort-high       .gauge-arc-fill { stroke: #DC267F; }
.effort-extra-high .gauge-arc-fill { stroke: #FE6100; }
.effort-max        .gauge-arc-fill { stroke: #FFB000; }
.effort-unknown    .gauge-arc-fill { stroke: var(--vscode-disabledForeground, #888); }

.signal-current            .gauge-arc-fill { stroke-opacity: 1; }
.signal-manual             .gauge-arc-fill { stroke-opacity: 1; }
.signal-last-observed      .gauge-arc-fill { stroke-opacity: 1; }
.signal-configured-default .gauge-arc-fill { stroke-opacity: 0.85; }
.signal-configured-default .gauge-rim {
  stroke-dasharray: 2 2;
  stroke-opacity: 1;
}

.clock-overlay {
  position: absolute;
  top: -2px;
  left: -2px;
  font-size: 14px;
  opacity: 0.85;
  line-height: 1;
  z-index: 1;
}

/* Stale-state diagonal stripes (signal-agnostic overlay). */
.stale .gauge-svg-wrap::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
  background-image: repeating-linear-gradient(
    -45deg,
    var(--indicator-stripe-color) 0px,
    var(--indicator-stripe-color) 4px,
    transparent 4px,
    transparent 10px
  );
}

.last-updated {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 2px;
  text-align: center;
}

/* Model description sections (Actual / Suggested vertical stack). */
.model-sections { margin-top: 6px; }
.model-section + .model-section { margin-top: 8px; }
.model-section-header {
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  font-variant: small-caps;
  letter-spacing: 0.08em;
  line-height: 1.5;
  padding: 2px 6px;
  background: var(--indicator-band-bg);
  color: var(--indicator-band-fg);
  margin: 0 -10px 4px -10px;
}
.model-section-text {
  text-align: left;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.model-section-suggested .model-section-text {
  font-style: italic;
}

```
