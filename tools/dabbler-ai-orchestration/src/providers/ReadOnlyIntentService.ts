// Set 036 Session 4 (Q3 — "Open in Read-Only Mode"): in-memory map of
// session-set paths the operator has flagged for read-only observation.
//
// The flag is *transient*: it lives only for the extension host's
// lifetime. Restarting the window clears it. The audit (proposal-
// addendum §Q3) and Q6 REJECTED both call for no persistent off-switch
// for takeover enforcement, so persisting this intent across sessions
// would re-introduce the same risk surface Q6 rejected.
//
// What "read-only intent" does:
//   1. Extension-dispatched commands that write orchestrator state for
//      the flagged set (currently `dabbler.checkOutOrchestrator`)
//      prompt the operator to clear the intent before proceeding.
//   2. Other (non-state-writing) extension features (the accordion
//      render, the tree-view sort, etc.) are not affected.
//
// What it does NOT do:
//   - Stop external CLI invocations of `python -m ai_router.start_session`.
//     Those run outside the extension's reach; the read-only contract
//     for the AI agent is observed by the agent itself, not the
//     extension.
//
// The single-instance assumption is acceptable because the modal
// helper that sets the flag is itself singleton-scoped (one
// CheckoutPollService per extension host).

import * as vscode from "vscode";

export class ReadOnlyIntentService implements vscode.Disposable {
  private readonly intents = new Set<string>();
  private readonly emitter = new vscode.EventEmitter<string>();

  // Fires with the affected session-set path whenever an intent is
  // added or cleared. CustomSessionSetsView subscribes so the rendered
  // accordion can show a read-only badge alongside the orchestrator
  // gauges (display-only — wiring left to Session 6's UI sweep).
  readonly onDidChange: vscode.Event<string> = this.emitter.event;

  setReadOnly(sessionSetPath: string): void {
    if (!sessionSetPath) return;
    if (this.intents.has(sessionSetPath)) return;
    this.intents.add(sessionSetPath);
    this.emitter.fire(sessionSetPath);
  }

  clearReadOnly(sessionSetPath: string): void {
    if (!sessionSetPath) return;
    if (!this.intents.delete(sessionSetPath)) return;
    this.emitter.fire(sessionSetPath);
  }

  isReadOnly(sessionSetPath: string): boolean {
    return this.intents.has(sessionSetPath);
  }

  // Test introspection only — production code should never iterate
  // the full set; check membership via isReadOnly().
  get intentCount(): number {
    return this.intents.size;
  }

  dispose(): void {
    this.intents.clear();
    this.emitter.dispose();
  }
}

// Module-level singleton so commands and the CheckoutPollService share
// the same map without threading the instance through every signature.
// Constructed lazily on first access so unit tests that don't activate
// the extension can still import the type without triggering the
// EventEmitter (which is harmless but adds noise in vscode-stub
// environments).
let _singleton: ReadOnlyIntentService | null = null;

export function getReadOnlyIntentService(): ReadOnlyIntentService {
  if (_singleton === null) _singleton = new ReadOnlyIntentService();
  return _singleton;
}

// Test seam: reset the singleton between test cases so leaked intents
// from one suite don't bleed into another. Not used by production code.
export function resetReadOnlyIntentServiceForTests(): void {
  if (_singleton !== null) {
    _singleton.dispose();
    _singleton = null;
  }
}
