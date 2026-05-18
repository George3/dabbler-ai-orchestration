// Per-set marker watcher + state computation. Extracted from
// orchestratorIndicatorProvider.ts in Set 029 Session 4 per audit
// Q1(a) + GPT-5.4 M4. Owns: marker reader, per-set marker watcher,
// workspace state-watcher, workspace-folder listener, polling
// backstop, slug validation. Presentation-agnostic — emits typed
// state, never HTML.
//
// The active in-progress set is resolved via a walk through the
// workspace folders (mirroring scripts/write-orchestrator-marker.js's
// walk-up resolver). Fail-closed: multiple in-progress sets returns
// `unresolved` with `multiple-in-progress-sets` reason (caller
// surfaces the operator-actionable banner per S4 Q8 = a+c).

import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { readAllSessionSets } from "../utils/fileSystem";
import {
  DEFAULT_STALENESS_MAX_SEC,
  OrchestratorMarker,
  Recommendation,
  RenderState,
  computeMismatch,
} from "./OrchestratorAccordion";

const POLL_BACKSTOP_MS = 60_000;
const RENDER_DEBOUNCE_MS = 50;
const SESSION_STATE_GLOB = "docs/session-sets/*/session-state.json";

export interface ResolvedSet {
  workspaceRoot: string;
  slug: string;
  setDir: string;
  markerPath: string;
}

export type SetResolution =
  | { kind: "resolved"; resolved: ResolvedSet }
  | {
      kind: "unresolved";
      reason:
        | "no-workspace"
        | "no-docs-session-sets"
        | "no-in-progress-set"
        | "multiple-in-progress-sets";
      candidates?: string[];
    };

export function resolveActiveSet(): SetResolution {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    return { kind: "unresolved", reason: "no-workspace" };
  }
  for (const folder of folders) {
    const root = folder.uri.fsPath;
    const candidate = path.join(root, "docs", "session-sets");
    let candidateIsDir = false;
    try {
      candidateIsDir = fs.statSync(candidate).isDirectory();
    } catch {
      candidateIsDir = false;
    }
    if (!candidateIsDir) continue;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(candidate, { withFileTypes: true });
    } catch {
      continue;
    }
    const inProgress: string[] = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const statePath = path.join(candidate, entry.name, "session-state.json");
      let state: { status?: unknown } | null = null;
      try {
        state = JSON.parse(fs.readFileSync(statePath, "utf8"));
      } catch {
        continue;
      }
      if (state && (state as { status?: unknown }).status === "in-progress") {
        inProgress.push(entry.name);
      }
    }
    if (inProgress.length === 1) {
      const slug = inProgress[0];
      const setDir = path.join(candidate, slug);
      return {
        kind: "resolved",
        resolved: {
          workspaceRoot: root,
          slug,
          setDir,
          markerPath: path.join(setDir, ".dabbler", "orchestrator.json"),
        },
      };
    }
    if (inProgress.length === 0) {
      return { kind: "unresolved", reason: "no-in-progress-set" };
    }
    return {
      kind: "unresolved",
      reason: "multiple-in-progress-sets",
      candidates: inProgress,
    };
  }
  return { kind: "unresolved", reason: "no-docs-session-sets" };
}

// Emitted whenever resolution or marker content may have changed.
// Subscribers re-pull resolution + state via the public accessors.
export interface MarkerSnapshot {
  resolution: SetResolution;
  state: RenderState;
}

export class MarkerWatchService implements vscode.Disposable {
  private _onDidChange = new vscode.EventEmitter<MarkerSnapshot>();
  readonly onDidChange: vscode.Event<MarkerSnapshot> = this._onDidChange.event;

  private markerWatcherDisposable: vscode.Disposable | undefined;
  private stateWatcherDisposable: vscode.Disposable | undefined;
  private workspaceFoldersListener: vscode.Disposable | undefined;
  private currentMarkerPath: string | null = null;
  private pollHandle: NodeJS.Timeout | undefined;
  private fireTimer: NodeJS.Timeout | undefined;
  private outputChannel: vscode.OutputChannel | undefined;

  constructor() {}

  // Start watching. Idempotent — calling start() twice is safe.
  public start(): void {
    if (this.workspaceFoldersListener) return;
    this.workspaceFoldersListener = vscode.workspace.onDidChangeWorkspaceFolders(() => {
      this.stateWatcherDisposable?.dispose();
      this.stateWatcherDisposable = undefined;
      this.setUpStateWatcher();
      this.rebindMarkerWatcher();
      this.scheduleFire();
    });
    this.setUpStateWatcher();
    this.rebindMarkerWatcher();
    // Initial snapshot fires synchronously via the schedule below.
    this.scheduleFire();
  }

  public dispose(): void {
    this.markerWatcherDisposable?.dispose();
    this.markerWatcherDisposable = undefined;
    this.stateWatcherDisposable?.dispose();
    this.stateWatcherDisposable = undefined;
    this.workspaceFoldersListener?.dispose();
    this.workspaceFoldersListener = undefined;
    this.currentMarkerPath = null;
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
      this.pollHandle = undefined;
    }
    if (this.fireTimer) {
      clearTimeout(this.fireTimer);
      this.fireTimer = undefined;
    }
    this._onDidChange.dispose();
  }

  // Snapshot accessor for synchronous callers (e.g., initial render
  // before any change events have fired).
  public snapshot(): MarkerSnapshot {
    const resolution = resolveActiveSet();
    const state = this.computeState(resolution);
    return { resolution, state };
  }

  private setUpStateWatcher(): void {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return;
    const pattern = new vscode.RelativePattern(folders[0], SESSION_STATE_GLOB);
    const watcher = vscode.workspace.createFileSystemWatcher(pattern);
    const trigger = () => {
      this.rebindMarkerWatcher();
      this.scheduleFire();
    };
    watcher.onDidCreate(trigger);
    watcher.onDidChange(trigger);
    watcher.onDidDelete(trigger);
    this.stateWatcherDisposable = watcher;
  }

  private rebindMarkerWatcher(): void {
    const res = resolveActiveSet();
    const nextPath = res.kind === "resolved" ? res.resolved.markerPath : null;
    if (nextPath === this.currentMarkerPath && this.markerWatcherDisposable) {
      return;
    }
    this.markerWatcherDisposable?.dispose();
    this.markerWatcherDisposable = undefined;
    this.currentMarkerPath = nextPath;
    if (!nextPath) {
      this.ensurePollBackstop();
      return;
    }
    const markerDir = path.dirname(nextPath);
    const pattern = new vscode.RelativePattern(
      vscode.Uri.file(markerDir),
      "orchestrator.json",
    );
    const watcher = vscode.workspace.createFileSystemWatcher(pattern);
    const trigger = () => this.scheduleFire();
    watcher.onDidCreate(trigger);
    watcher.onDidChange(trigger);
    watcher.onDidDelete(trigger);
    this.markerWatcherDisposable = watcher;
    this.ensurePollBackstop();
  }

  private ensurePollBackstop(): void {
    if (this.pollHandle) return;
    this.pollHandle = setInterval(() => {
      this.rebindMarkerWatcher();
      this.scheduleFire();
    }, POLL_BACKSTOP_MS);
  }

  // Debounce coalesces watcher bursts (e.g., Windows atomic write
  // emits create+delete+create in quick succession).
  private scheduleFire(): void {
    if (this.fireTimer) clearTimeout(this.fireTimer);
    this.fireTimer = setTimeout(() => {
      this._onDidChange.fire(this.snapshot());
    }, RENDER_DEBOUNCE_MS);
  }

  private getOutputChannel(): vscode.OutputChannel {
    if (!this.outputChannel) {
      this.outputChannel = vscode.window.createOutputChannel("Dabbler Orchestrator Indicator");
    }
    return this.outputChannel;
  }

  public computeState(resolution: SetResolution): RenderState {
    if (resolution.kind === "unresolved") {
      return { kind: "empty" };
    }
    let raw: string;
    try {
      raw = fs.readFileSync(resolution.resolved.markerPath, "utf8");
    } catch {
      return { kind: "empty" };
    }
    let marker: OrchestratorMarker;
    try {
      marker = JSON.parse(raw) as OrchestratorMarker;
    } catch {
      return { kind: "empty" };
    }
    if (!marker || typeof marker !== "object" || !marker.signalKind) {
      return { kind: "empty" };
    }
    // Slug-integrity check (S3 schema-v3 + S4 R13 guard). Marker with
    // sessionSetSlug !== resolved.slug is treated as orphaned/stale —
    // log + fall back to empty.
    if (marker.sessionSetSlug !== undefined && marker.sessionSetSlug !== resolution.resolved.slug) {
      this.getOutputChannel().appendLine(
        `[${new Date().toISOString()}] Slug mismatch at ${resolution.resolved.markerPath}: ` +
        `marker has '${String(marker.sessionSetSlug)}', resolved set is '${resolution.resolved.slug}'. ` +
        `Falling back to empty state.`,
      );
      return { kind: "empty" };
    }
    const ageSec = (Date.now() - Date.parse(marker.updatedAt)) / 1000;
    const stalenessMaxSec =
      typeof marker.stalenessMaxSec === "number"
        ? marker.stalenessMaxSec
        : DEFAULT_STALENESS_MAX_SEC;
    const stale = ageSec > stalenessMaxSec;

    let mismatch = null;
    try {
      const rec = this.findActiveRecommendation();
      if (rec) {
        mismatch = computeMismatch(marker, rec);
      }
    } catch {
      mismatch = null;
    }
    return { kind: "loaded", marker, stale, ageSec, mismatch };
  }

  // Find the recommendation from the active session set's
  // ai-assignment.md for the targeted session (currentSession or
  // next-to-start). Best-effort; defensive on every parse step.
  private findActiveRecommendation(): Recommendation | null {
    let sets;
    try {
      sets = readAllSessionSets();
    } catch {
      return null;
    }
    const inProgress = sets.filter((s) => s.state === "in-progress");
    if (inProgress.length === 0) return null;
    inProgress.sort((a, b) => (b.lastTouched ?? "").localeCompare(a.lastTouched ?? ""));
    const set = inProgress[0];

    const live = set.liveSession;
    let targetSession: number | null = null;
    if (live && typeof live.currentSession === "number") {
      targetSession = live.currentSession;
    } else if (
      live &&
      Array.isArray(live.completedSessions) &&
      typeof set.totalSessions === "number" &&
      live.completedSessions.length < set.totalSessions
    ) {
      const maxCompleted = live.completedSessions.length === 0
        ? 0
        : Math.max(...live.completedSessions);
      targetSession = maxCompleted + 1;
    }
    if (targetSession === null) return null;

    let text: string;
    try {
      text = fs.readFileSync(set.aiAssignmentPath, "utf8");
    } catch {
      return null;
    }
    return extractRecommendation(text, targetSession, set.name);
  }
}

// Free function — kept extracted for unit-testability without
// instantiating the service. Parses ai-assignment.md for the
// recommendation block of a specific session.
export function extractRecommendation(
  text: string,
  sessionNumber: number,
  setName: string,
): Recommendation | null {
  const lines = text.split(/\r?\n/);
  const headingRe = new RegExp(
    `^##\\s+Session\\s+${sessionNumber}(?:\\s+of\\s+\\d+)?\\s*:\\s*(.*)$`,
    "i",
  );
  let sessionStartIdx = -1;
  let sessionTitle = "";
  for (let i = 0; i < lines.length; i++) {
    const m = headingRe.exec(lines[i]);
    if (m) {
      sessionStartIdx = i;
      sessionTitle = m[1].trim();
      break;
    }
  }
  if (sessionStartIdx === -1) return null;

  let recHeadingIdx = -1;
  for (let i = sessionStartIdx + 1; i < lines.length; i++) {
    if (/^##\s+/.test(lines[i])) break;
    if (/^###\s+Recommended\s+orchestrator/i.test(lines[i])) {
      recHeadingIdx = i;
      break;
    }
  }
  if (recHeadingIdx === -1) return null;

  let paragraphStart = -1;
  for (let i = recHeadingIdx + 1; i < lines.length; i++) {
    if (/^###\s+/.test(lines[i]) || /^##\s+/.test(lines[i])) break;
    if (lines[i].trim().length > 0) {
      paragraphStart = i;
      break;
    }
  }
  if (paragraphStart === -1) return null;

  const paragraphLines: string[] = [];
  for (let i = paragraphStart; i < lines.length; i++) {
    if (lines[i].trim().length === 0) break;
    if (/^###\s+/.test(lines[i]) || /^##\s+/.test(lines[i])) break;
    paragraphLines.push(lines[i]);
  }
  const paragraph = paragraphLines.join(" ").trim();

  const recRe = /^([A-Z][A-Za-z]+)\s+([^@]+?)\s*@\s*effort\s*=\s*([a-z-]+)/i;
  const m = recRe.exec(paragraph);
  if (!m) return null;

  return {
    rawText: paragraph,
    providerName: m[1].trim(),
    modelName: m[2].trim().replace(/[.,;]+$/, ""),
    effort: m[3].trim().toLowerCase(),
    sessionLabel: `Session ${sessionNumber}: ${sessionTitle}`,
    setName,
  };
}
