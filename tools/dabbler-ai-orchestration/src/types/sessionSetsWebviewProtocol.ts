// Typed message protocol between the extension host
// (CustomSessionSetsView in the extension process) and the webview
// client.js running inside the Session Sets webview. Per S4 audit
// GPT-5.4 M3: every render message carries a monotonic `version`
// field; the webview drops out-of-order messages so stale watcher
// ticks or polling backstops cannot repaint over fresh state.
//
// Layering:
//   - HostToWebview = host → webview (render + ui-only state changes)
//   - WebviewToHost = webview → host (activation + command requests)
//
// Snapshot messages (RowsSnapshot, ScanStateChanged) carry a
// monotonic version that the host increments on every fire. Narrow
// event messages (FocusMoved) do NOT carry a version — they're
// UI-only and never overwrite snapshot data.

// ----- Common -----

export type ScanState = "loading" | "ready";

// Row payload — what the webview needs to render one tree row.
// Derived from SessionSet + the SessionSetsModel helpers; the host
// runs the model functions once per snapshot and ships only the
// strings + flags the webview needs.
//
// Set 049 S4 (rip-out): Set 045's `harvestSignals` + `conflicts`
// fields are retired. The orchestrator-rendering surface in the
// Session Set Explorer reverts to its pre-Set-045 shape — no
// harvest-record badges (W / N / M / B), no coordination-conflict
// pills. Per Non-goal 2, the Python-side log-harvest infrastructure
// (joiner CLI + parsers) and the writer-bypass detector (D3) survive
// independently; only the Explorer rendering of those signals is
// removed here.
export interface RowPayload {
  slug: string;
  name: string;
  state: "in-progress" | "not-started" | "complete" | "cancelled";
  // Set 034: progress fraction moved out of `description` into its own
  // right-aligned bold colored list-icon column on the left side of
  // the row. Always non-empty when totalSessions > 0; may be "" only
  // when the set has no totalSessions on disk yet.
  fraction: string;                // e.g. "3/6", "0/4", "3/3"
  description: string;             // remaining description after fraction extraction (e.g. "session 4 in flight  ·  2026-05-18")
  contextValue: string;            // for ActionRegistry membership tests (e.g., "sessionSet:in-progress:uat")
  iconSlug: string;                // "in-progress.svg" / "done.svg" / etc.
  needsMigration: boolean;
  // Set 050 S4 (Explorer UX revision): the unobtrusive asterisk that
  // replaces the old "(needs migration)" description label. `marker` is
  // "*" on sub-current sets (else ""); `tooltip` is the hover text
  // ("Ran under schema v<N>"). The webview renders the marker next to
  // the row name with the tooltip as its `title` attribute.
  migrationMarker: string;
  migrationTooltip: string;
  // Set 034: the per-row orchestrator-tracking accordion is retired.
  // These fields remain on the protocol so older host/webview pairings
  // stay structurally compatible, but the host always emits null and
  // the webview never renders an accordion body.
  accordionHtml: string | null;
  accordionUpdatedAt: string | null;
}

export interface BucketPayload {
  key: "in-progress" | "not-started" | "complete" | "cancelled";
  label: string;                   // "In Progress"
  count: number;
  rows: RowPayload[];
}

export interface SnapshotPayload {
  buckets: BucketPayload[];
  // Empty when no sets at all; webview falls back to viewsWelcome HTML.
  hasAnySets: boolean;
  // Welcome HTML (rendered host-side from package.json `viewsWelcome`
  // contents — preserves declarative source per Q3 = a).
  welcomeHtml: string;
}

// ----- Host → Webview -----

export interface RowsSnapshotMsg {
  type: "rowsSnapshot";
  version: number;                 // monotonic; webview drops older versions
  scanState: ScanState;
  payload: SnapshotPayload;
}

export interface ScanStateChangedMsg {
  type: "scanStateChanged";
  version: number;
  state: ScanState;
}

// Suppression-state echo: host tells webview which rows are currently
// suppressed (from workspaceState) so the initial paint matches.
export interface SuppressionEchoMsg {
  type: "suppressionEcho";
  version: number;
  suppressed: Record<string, string>;  // slug → accordion.updatedAt
}

// Set 048 S3 (spec §3.3, Bias 3 flip): the Set 034 cursor-anchored
// HTML popup is retired. The right-click context menu is rebuilt on
// `vscode.window.showQuickPick` (two-step submenu pattern); the
// `RenderContextMenuMsg` host→webview message and the
// `ExecuteRowCommandMsg` webview→host message were removed because
// the QuickPick lives entirely in the extension host.

export type HostToWebview =
  | RowsSnapshotMsg
  | ScanStateChangedMsg
  | SuppressionEchoMsg;

// ----- Webview → Host -----

// Generic command dispatch — webview asks host to run a registered
// vscode command. Used for all 14 row-context actions and the three
// indicator-action buttons (install-hook / set-orchestrator /
// open-writer-log). Host validates the commandId against an allowlist
// before calling executeCommand (defense-in-depth against a malicious
// webview).
export interface ExecuteCommandMsg {
  type: "executeCommand";
  commandId: string;
  args?: unknown[];
}

// Right-click / Shift+F10 / Context Menu key on a row → open
// QuickPick. Host computes applicable actions from ActionRegistry
// and shows the picker.
export interface ShowRowContextMenuMsg {
  type: "showRowContextMenu";
  slug: string;
}

// Operator manually collapsed / expanded a row. Host updates
// workspaceState (suppress / clear) and may re-fire a SuppressionEcho.
// `accordionUpdatedAt` carries the suppression-key value from the
// row's accordion (orchestrator.lastActivityAt) so suppression
// ages naturally when the orchestrator block changes.
export interface ToggleRowMsg {
  type: "toggleRow";
  slug: string;
  expanded: boolean;
  accordionUpdatedAt: string | null;
}

// Operator activated a row (Enter / Space / double-click). Defaults
// to openSpec per S4 step 3 (M3 primary-activation rule). Host can
// extend later (e.g., open accordion + spec in split view).
export interface ActivateRowMsg {
  type: "activateRow";
  slug: string;
}

// Webview is ready and wants the initial snapshot.
export interface ReadyMsg {
  type: "ready";
}

export type WebviewToHost =
  | ExecuteCommandMsg
  | ShowRowContextMenuMsg
  | ToggleRowMsg
  | ActivateRowMsg
  | ReadyMsg;
