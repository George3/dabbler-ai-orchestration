# Set 029 Session 4 verification — Round A (provider-layer + types)

## Context

Set 029 Session 4 ships the **custom-tree pivot** in v0.16.0: replaces
the native `dabblerSessionSets` `TreeView` with a webview-rendered
custom tree, lifts the v0.15.0 gauges into per-row accordions on the
resolved in-progress set, and retires the dedicated
`dabblerOrchestratorIndicator` view in the same release.

Pre-S4 audit (2026-05-18) routed through Gemini Pro + GPT-5.4
landed at three-way agreement on Q1-Q11 + 10 must-fix tightening
items (M1-M10). Audit artifacts at
`docs/proposals/2026-05-18-custom-tree-implementation/`. Spec at
`docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
§"Session 4 of 6".

**Round A scope** (this round): the provider-layer extracts +
typed-protocol module + small abstraction modules. These are the
files where M2/M3/M4/M5/M7 + R13/R14 are most at risk. Round B
will cover `CustomSessionSetsView.ts` + `client.js` (the
integration surface where M1/M6/M8 + R10/R11/R12 live).

Splitting per memory `feedback_split_large_verification_bundles`
to stay under the bundle ceiling that gpt-5-4 timeouts at and to
keep each round's punch list focused.

## Files in this bundle (4 + 1 schema, ~700 LOC)

1. `src/providers/OrchestratorAccordion.ts` (431 LOC) — pure render
   helpers extracted from the retired
   `orchestratorIndicatorProvider.ts` (998 LOC). Per S4 M4: NO
   `vscode.*` lifecycle calls, NO filesystem watchers, NO
   message-protocol coupling.
2. `src/providers/MarkerWatchService.ts` (395 LOC) — marker reader
   + per-set marker watcher + state-watcher + workspace-folder
   listener + polling backstop. Per S4 M4: presentation-agnostic
   (emits typed events, not HTML).
3. `src/providers/ActionRegistry.ts` (79 LOC) — typed
   action-applicability predicates for the 14 row-context actions.
   Per S4 M2: single source of truth replacing the lost
   `package.json` `view/item/context` rules.
4. `src/providers/suppressionState.ts` (61 LOC) — pure reducer for
   manual-collapse-suppresses-auto-expand state, keyed on
   (slug, marker.updatedAt) tuple. Per S4 M7.
5. `src/types/sessionSetsWebviewProtocol.ts` (130 LOC) — typed
   discriminated unions for host↔webview messages with monotonic
   `version` field on render messages. Per S4 M3.

## What you're being asked to verify in Round A

Answer Q1–Q7 in order with **VERIFIED / MUST-FIX / SUGGEST** verdicts
plus 1–3 sentences of reasoning each. After Q1–Q7, emit a final
verdict line per the format at the bottom.

### Q1. OrchestratorAccordion extraction cleanliness (M4)

`OrchestratorAccordion.ts` should be pure render — no `vscode.*`
calls, no filesystem watchers, no lifecycle. Caller (in Round B)
takes a `RenderState` value and asks for HTML.

Verify:
- No `import * as vscode from "vscode"` or `import {} from "vscode"`.
- No `fs.readFileSync` or `fs.createReadStream` calls.
- Functions are deterministic state-in → string-out: `renderGaugeSvg`,
  `renderAccordionEmpty`, `renderAccordionLoaded`, `renderAccordionBody`,
  `describeMarker`, `describeRecommendation`, `modelTooltip`,
  `effortTooltip`, `tierToNeedleAngle`, `effortToNeedleAngle`,
  `effortColorBucket`, `fmtAge`, `escHtml`, `escAttr`,
  `computeMismatch`.

### Q2. HTML escape coverage (M5 / R13)

Per audit GPT-5.4 M5: every dynamic string interpolation into
webview HTML must go through `escHtml()` (or `escAttr()` for
attribute contexts).

Verify in `OrchestratorAccordion.ts`:
- `escHtml(marker.providerDisplayName)`, `escHtml(marker.modelDisplayName)`,
  `escHtml(describeMarker(marker))`, `escHtml(describeRecommendation(...))`,
  `escHtml(effortDisplayName(...))` all escape before interpolation.
- `escAttr(modelTip)`, `escAttr(effortTip)`, `escAttr(mismatch.reason)`,
  `escAttr(tier)`, `escAttr(signalKind)` all escape attribute values.
- Any string that flows directly into the rendered HTML without a
  call to `escHtml`/`escAttr` is a MUST-FIX.

### Q3. ActionRegistry (M2) — predicate correctness

`ActionRegistry.ts` exposes 14 actions (matching the 14
`view/item/context` entries deleted from `package.json` in this
session). The `when` predicates must reproduce the original
declarative gating exactly:

- 7 "open" actions (openSpec / openActivityLog / openChangeLog /
  openAiAssignment / openSessionState / openFolder / copySlug):
  always available.
- `openUatChecklist`: gated on `supports.uat && set.config.requiresUAT`.
- `revealPlaywrightTests`: gated on `supports.e2e && set.config.requiresE2E`.
- `copyStartCommand.default` + `copyStartCommand.parallel`: gated on
  `state === "in-progress" || state === "not-started"`.
- `cancel`: gated on `state ∈ {in-progress, not-started, complete}`.
- `restore`: gated on `state === "cancelled"`.
- `migrate`: gated on `set.needsMigration`.

Verify each predicate matches the spec. `applicableActions(set, supports)`
returns pre-sorted by `group` so menu order is deterministic.

### Q4. suppressionState (M7) — tuple-key semantics

Per audit Q2(a) + M7: suppression keyed by the
`(slug, marker.updatedAt)` tuple. Manual collapse suppresses for
that occurrence ONLY; the next SessionStart writes a fresh marker
with a new `updatedAt`, so the suppression naturally lifts without
explicit aging.

Verify:
- `isSuppressed(state, slug, updatedAt)` returns true iff
  `state[slug] === updatedAt`.
- `suppress(state, slug, updatedAt)` returns a NEW object (immutable).
- `clearSuppression(state, slug)` returns the SAME instance when the
  slug isn't present (no-allocation optimization).
- `prune(state, visibleSlugs)` drops entries whose slug is no longer
  visible; returns the SAME instance when no change.

### Q5. Versioned message protocol (M3)

Per audit GPT-5.4 M3: every render message carries a monotonic
`version: number`. Webview client drops messages with
`version < currentVersion` to prevent stale watcher/polling repaints.

Verify in `sessionSetsWebviewProtocol.ts`:
- `RowsSnapshotMsg`, `ScanStateChangedMsg`, `SuppressionEchoMsg` all
  have `version: number`.
- `ReadyMsg`, `ExecuteCommandMsg`, `ShowRowContextMenuMsg`,
  `ToggleRowMsg`, `ActivateRowMsg` (webview → host messages) do NOT
  carry a version (they're one-shot commands, not snapshots).
- `RowPayload` has the shape needed to drive the webview rendering:
  slug, name, state, description, contextValue, iconSlug,
  needsMigration, isResolvedSet, accordionHtml (pre-rendered or null).

### Q6. MarkerWatchService presentation-agnostic boundary (M4)

`MarkerWatchService.ts` should NOT generate HTML or webview commands.
It owns: marker reader, watchers, state computation. Emits typed
state changes via `vscode.EventEmitter<MarkerSnapshot>`.

Verify:
- No `escHtml`, no template strings building `<div>` / `<svg>`.
- `snapshot()` returns `{ resolution: SetResolution, state: RenderState }`
  — typed shapes, not strings.
- `computeState(resolution)` reads the marker file via `fs.readFileSync`,
  parses JSON, validates `sessionSetSlug` against `resolution.slug`,
  computes mismatch via `findActiveRecommendation()` → `computeMismatch()`.
- The slug-mismatch fallback logs to `vscode.OutputChannel` named
  "Dabbler Orchestrator Indicator" and returns `{ kind: "empty" }`
  (R8 wrong-set-attachment guard preserved from S3).

### Q7. Walk-up resolver fail-closed posture (R8 carry-forward)

`resolveActiveSet()` in `MarkerWatchService.ts` mirrors the writer-
side `walkUpResolveSet()` in `scripts/write-orchestrator-marker.js`
(S3-shipped). Both must fail closed identically:

- 0 in-progress sets → `{ kind: "unresolved", reason: "no-in-progress-set" }`
- >1 in-progress sets → `{ kind: "unresolved", reason: "multiple-in-progress-sets", candidates: [...] }`
- No `docs/session-sets/` directory anywhere in the walk → `{ kind: "unresolved", reason: "no-docs-session-sets" }`
- No workspace folder → `{ kind: "unresolved", reason: "no-workspace" }`

Verify the resolver semantics match the S3 writer's resolver
(symmetry is load-bearing: a writer that wrote to set X but a
reader that resolved set Y would silently mismatch).

---

## Final verdict (Round A)

Emit one summary line at the end:

`VERDICT: VERIFIED` if Q1–Q7 all pass without must-fix items
`VERDICT: MUST-FIX (<count>)` if any Q has a must-fix
`VERDICT: SUGGEST (<count>)` if no must-fix but ≥1 suggest items

Followed by a 2–3-sentence overall summary.


---

## File 1: src/providers/OrchestratorAccordion.ts

```typescript
// Pure render helpers for the orchestrator accordion body in the Set
// 029 Session 4 custom-tree view. Extracted from the retired
// orchestratorIndicatorProvider.ts per S4 audit Q1 (a) +
// GPT-5.4 M4 — no filesystem watchers, no vscode.* lifecycle calls,
// no message-protocol coupling. Just deterministic state-in → HTML-out.
//
// Visual treatment, gauge geometry, mismatch semantics, escaping —
// all unchanged from v0.15.0. Callers (CustomSessionSetsView)
// resolve the RenderState elsewhere and ask this module to render
// the body fragment.

// ----- Schema types -----

export interface OrchestratorMarker {
  schemaVersion: number;
  sessionSetSlug?: string;
  updatedAt: string;
  writer: string;
  signalKind: "current" | "configured-default" | "last-observed" | "manual";
  confidence: "high" | "medium" | "low";
  provider: string;
  providerDisplayName: string;
  model: string;
  modelDisplayName: string;
  tier: "low" | "mid" | "flagship" | "unknown";
  effort: {
    normalized: "low" | "medium" | "high" | "extra-high" | "max";
    native: string;
    thinking: boolean;
    signalKind: "current" | "configured-default" | "last-observed" | "manual";
    confidence: "high" | "medium" | "low";
    observedAt?: string;
  };
  stalenessMaxSec: number;
}

export interface Recommendation {
  rawText: string;
  providerName: string;
  modelName: string;
  effort: string;
  sessionLabel: string;
  setName: string;
}

export interface Mismatch {
  recommendation: Recommendation;
  reason: string;
}

export type RenderState =
  | { kind: "empty" }
  | { kind: "loaded"; marker: OrchestratorMarker; stale: boolean; ageSec: number; mismatch: Mismatch | null };

export const DEFAULT_STALENESS_MAX_SEC = 28800; // 8h

// ----- Tier / effort rank helpers (mismatch logic) -----

export function tierRank(tier: string | undefined): number {
  switch ((tier || "").toLowerCase()) {
    case "low":      return 0;
    case "mid":      return 1;
    case "flagship": return 2;
    default:         return -1;
  }
}

export function effortRank(effort: string | undefined): number {
  switch ((effort || "").toLowerCase()) {
    case "low":        return 0;
    case "medium":     return 1;
    case "high":       return 2;
    case "extra-high": return 3;
    case "max":        return 4;
    default:           return -1;
  }
}

export function classifyRecommendationTier(providerName: string, modelName: string): string {
  const p = (providerName || "").toLowerCase();
  const m = (modelName || "").toLowerCase();
  if (p.includes("claude") || m.includes("claude")) {
    if (m.includes("opus")) return "flagship";
    if (m.includes("sonnet")) return "mid";
    if (m.includes("haiku")) return "low";
  }
  if (p.includes("gemini") || m.includes("gemini")) {
    if (m.includes("pro")) return "flagship";
    if (m.includes("flash 2") || m.includes("2.5")) return "mid";
    if (m.includes("flash")) return "low";
  }
  if (p.includes("codex") || p.includes("openai") || m.startsWith("gpt-") || m.includes("codex") || m.startsWith("o1") || m.startsWith("o3")) {
    if (m.includes("mini")) return "low";
    if (m.startsWith("o1") || m.startsWith("o3") || m.includes("5") || (m.includes("4o") && !m.includes("mini"))) return "flagship";
    return "mid";
  }
  if (p.includes("copilot") || m.includes("copilot")) return "mid";
  return "unknown";
}

// ----- Formatting helpers -----

export function fmtAge(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return "?";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

export function providerHasExtraCapacity(provider: string): boolean {
  const p = (provider || "").toLowerCase();
  return p === "anthropic" || p === "google" || p.includes("claude") || p.includes("gemini");
}

export function effortDisplayName(effort: string): string {
  switch (effort) {
    case "low":        return "Low";
    case "medium":     return "Medium";
    case "high":       return "High";
    case "extra-high": return "Extra-High";
    case "max":        return "Max";
    default:           return "Unknown";
  }
}

// Compose the full "Actual Model" description from a marker. Canonical
// textual description shown in the model table. Future-proof — new
// capacity parameters become extra clauses appended here.
export function describeMarker(marker: OrchestratorMarker): string {
  const provider = marker.providerDisplayName || "";
  const modelIsUnknown = !marker.model || marker.model === "unknown";
  const modelText = modelIsUnknown ? "(model unknown)" : (marker.modelDisplayName || "");
  const effortText = effortDisplayName(marker.effort.normalized).toLowerCase();
  const modelClause = marker.signalKind === "configured-default"
    ? `${provider} ${modelText} (configured default)`
    : `${provider} ${modelText}`;
  let desc = `${modelClause}, ${effortText} effort`;
  if (providerHasExtraCapacity(marker.provider)) {
    const thinkingOn = marker.effort.thinking === true;
    if (thinkingOn && marker.effort.signalKind === "last-observed" && marker.effort.observedAt) {
      const ageSec = (Date.now() - Date.parse(marker.effort.observedAt)) / 1000;
      const native = marker.effort.native || "/think";
      desc += `, thinking on (last ${native} ${fmtAge(ageSec)} ago)`;
    } else if (thinkingOn) {
      desc += `, thinking on`;
    } else {
      desc += `, thinking off`;
    }
  }
  return desc.trim().replace(/\s+/g, " ");
}

export function describeRecommendation(rec: Recommendation): string {
  return `${rec.providerName} ${rec.modelName}, ${rec.effort.toLowerCase()} effort`.replace(/\s+/g, " ");
}

// ----- Mismatch computation -----

export function computeMismatch(marker: OrchestratorMarker, rec: Recommendation): Mismatch | null {
  const norm = (s: string) => String(s ?? "").replace(/\s+/g, " ").trim().toLowerCase();

  const providerOk = norm(marker.providerDisplayName).includes(norm(rec.providerName)) ||
                     norm(rec.providerName).includes(norm(marker.providerDisplayName));
  const modelOk = norm(marker.modelDisplayName).includes(norm(rec.modelName)) ||
                  norm(rec.modelName).includes(norm(marker.modelDisplayName));
  const effortOk = norm(marker.effort.normalized) === norm(rec.effort);

  if (providerOk && modelOk && effortOk) return null;

  const diffs: string[] = [];
  if (!providerOk || !modelOk) {
    diffs.push(
      `model: actual "${marker.providerDisplayName} ${marker.modelDisplayName}", recommended "${rec.providerName} ${rec.modelName}"`,
    );
  }
  if (!effortOk) {
    diffs.push(`effort: actual "${marker.effort.normalized}", recommended "${rec.effort}"`);
  }
  if (!providerOk && diffs.length === 0) {
    diffs.push(`provider: actual "${marker.providerDisplayName}", recommended "${rec.providerName}"`);
  }

  return {
    recommendation: rec,
    reason:
      `Current orchestrator differs from ${rec.setName} ${rec.sessionLabel} recommendation. ` +
      diffs.join("; ") +
      ". This may be intentional (e.g., extra credits, task harder or simpler than anticipated) — " +
      `the Suggested row surfaces the recommendation; you decide. ` +
      `Switch via "Dabbler: Set Orchestrator Model & Effort".`,
  };
}

// ----- HTML escaping (S4 R13 mitigation per GPT M5) -----

export function escHtml(s: string): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function escAttr(s: string): string {
  return escHtml(s).replace(/"/g, "&quot;");
}

// ----- Gauge geometry -----

export function tierToNeedleAngle(tier: string): number {
  switch (tier) {
    case "low":      return -150;
    case "mid":      return -90;
    case "flagship": return -30;
    case "unknown":  return -90;
    default:         return -90;
  }
}

export function effortToNeedleAngle(effort: string): number {
  switch (effort) {
    case "low":        return -150;
    case "medium":     return -90;
    case "high":       return -60;
    case "extra-high": return -35;
    case "max":        return -15;
    default:           return -90;
  }
}

export function effortColorBucket(effort: string): string {
  switch (effort) {
    case "low":        return "low";
    case "medium":     return "mid";
    case "high":       return "mid";
    case "extra-high": return "flagship";
    case "max":        return "flagship";
    default:           return "unknown";
  }
}

export function renderGaugeSvg(tier: string, signalKind: string, needleAngleDeg: number): string {
  const cx = 35;
  const cy = 35;
  const radius = 28;
  const arcBg = `M${cx - radius},${cy} A${radius},${radius} 0 0 1 ${cx + radius},${cy}`;

  const fillAngleDeg = Math.max(-180, Math.min(0, needleAngleDeg));
  const fillAngleRad = (fillAngleDeg * Math.PI) / 180;
  const fillEndX = cx + radius * Math.cos(fillAngleRad);
  const fillEndY = cy + radius * Math.sin(fillAngleRad);
  const arcFill = `M${cx - radius},${cy} A${radius},${radius} 0 0 1 ${fillEndX.toFixed(2)},${fillEndY.toFixed(2)}`;

  const needleAngleRad = (needleAngleDeg * Math.PI) / 180;
  const needleLength = radius - 4;
  const needleTipX = cx + needleLength * Math.cos(needleAngleRad);
  const needleTipY = cy + needleLength * Math.sin(needleAngleRad);

  return `<svg class="gauge-svg" viewBox="0 0 70 38" data-tier="${escAttr(tier)}" data-signal="${escAttr(signalKind)}">
  <path class="gauge-arc-bg" d="${arcBg}" />
  <path class="gauge-arc-fill" d="${arcFill}" />
  <path class="gauge-rim" d="${arcBg}" />
  <line class="gauge-needle" x1="${cx}" y1="${cy}" x2="${needleTipX.toFixed(2)}" y2="${needleTipY.toFixed(2)}" />
  <circle class="gauge-needle-pivot" cx="${cx}" cy="${cy}" r="1.6" />
</svg>`;
}

// ----- Tooltips -----

export function modelTooltip(marker: OrchestratorMarker): string {
  const conf = marker.confidence;
  switch (marker.signalKind) {
    case "current":
      return conf === "low"
        ? "live signal (low confidence — hook payload missing model)"
        : `live signal (${conf} confidence)`;
    case "configured-default":
      return "configured default (medium confidence — does not track runtime changes)";
    case "last-observed":
      return "last observed via /think (high confidence in detection, but may not reflect current message)";
    case "manual":
      return "set manually (high confidence)";
    default:
      return "";
  }
}

export function effortTooltip(marker: OrchestratorMarker): string {
  const eSig = marker.effort.signalKind;
  if (eSig === "last-observed" && marker.effort.observedAt) {
    const age = fmtAge((Date.now() - Date.parse(marker.effort.observedAt)) / 1000);
    return `last observed ${age} ago via ${marker.effort.native || "/think"} (high confidence in detection, but may not reflect current message)`;
  }
  if (eSig === "configured-default") {
    return "configured default effort (medium confidence — does not track runtime changes)";
  }
  if (eSig === "manual") {
    return "set manually (high confidence)";
  }
  return `effort: ${effortDisplayName(marker.effort.normalized)} (${marker.effort.confidence} confidence)`;
}

// ----- Accordion body rendering -----

// Empty state for the accordion: marker not present for the resolved
// in-progress set. Renders grey gauges + the three indicator-action
// buttons (install hook / set orchestrator / writer log). Per S4 M8,
// these three affordances MUST be in the accordion body before the
// dabblerOrchestratorIndicator view retires.
//
// Buttons fire via `data-command` attributes; the webview client.js
// captures clicks and posts `{ type: "executeCommand", commandId }` to
// the host. The host dispatches via vscode.commands.executeCommand.
export function renderAccordionEmpty(): string {
  return `<div class="acc-empty">
  <div class="grey-gauges">
    <div class="gauge-svg-wrap">${renderGaugeSvg("unknown", "current", 0)}</div>
    <div class="gauge-svg-wrap">${renderGaugeSvg("unknown", "current", 0)}</div>
  </div>
  <div class="acc-empty-cta">
    <span>No signal — </span>
    <button class="acc-link" type="button" data-command="dabbler.installOrchestratorHook.claudeCode">install hook</button>
  </div>
  <div class="acc-actions">
    <button class="acc-action" type="button" data-command="dabbler.setOrchestrator">Set Orchestrator…</button>
    <button class="acc-action" type="button" data-command="dabbler.openOrchestratorWriterLog">Writer Log</button>
  </div>
</div>`;
}

// Loaded state: marker present. Lifts the v0.14.2 gauge treatment
// wholesale — same SVG, same sublabels, same model-section vertical
// stack with optional Suggested row, same stale annotation, same
// "updated Xs ago" footer.
export function renderAccordionLoaded(
  marker: OrchestratorMarker,
  stale: boolean,
  ageSec: number,
  mismatch: Mismatch | null,
): string {
  const modelClasses = [
    "gauge-cell",
    `tier-${marker.tier || "unknown"}`,
    `signal-${marker.signalKind}`,
  ].join(" ");
  const effortClasses = [
    "gauge-cell",
    `effort-${marker.effort.normalized || "unknown"}`,
    `signal-${marker.effort.signalKind || "current"}`,
  ].join(" ");

  const modelNeedle = tierToNeedleAngle(marker.tier);
  const effortNeedle = effortToNeedleAngle(marker.effort.normalized);

  const modelIsUnknown = !marker.model || marker.model === "unknown";
  const modelSublabelText = modelIsUnknown
    ? escHtml(marker.providerDisplayName)
    : `${escHtml(marker.providerDisplayName)} ${escHtml(marker.modelDisplayName)}`;

  const modelOverlay = marker.signalKind === "last-observed"
    ? `<span class="clock-overlay" title="last observed signal">⏱</span>`
    : "";
  const effortOverlay = marker.effort.signalKind === "last-observed"
    ? `<span class="clock-overlay" title="last observed signal">⏱</span>`
    : "";

  const modelTip = modelTooltip(marker);
  const effortTip = effortTooltip(marker);

  const staleClass = stale ? "stale" : "";
  const staleAnnotation = stale
    ? `<div class="last-updated">last updated ${fmtAge(ageSec)} ago — stale</div>`
    : `<div class="last-updated">updated ${fmtAge(ageSec)} ago</div>`;

  const actualDescription = describeMarker(marker);
  const actualSection = mismatch
    ? `<div class="model-section">
    <div class="model-section-header">Actual Model</div>
    <div class="model-section-text">${escHtml(actualDescription)}</div>
  </div>`
    : `<div class="model-section">
    <div class="model-section-text">${escHtml(actualDescription)}</div>
  </div>`;
  const suggestedSection = mismatch
    ? `<div class="model-section model-section-suggested" title="${escAttr(mismatch.reason)}">
    <div class="model-section-header">Suggested</div>
    <div class="model-section-text">${escHtml(describeRecommendation(mismatch.recommendation))}</div>
  </div>`
    : "";
  const modelSections = `<div class="model-sections">${actualSection}${suggestedSection}</div>`;

  // Per S4 M8 (indicator-action parity): the Set Orchestrator and
  // Writer Log buttons stay available even when a marker is loaded.
  // They live below the model-sections so the gauges remain the
  // visual focus.
  const actionsRow = `<div class="acc-actions">
    <button class="acc-action" type="button" data-command="dabbler.setOrchestrator">Set Orchestrator…</button>
    <button class="acc-action" type="button" data-command="dabbler.openOrchestratorWriterLog">Writer Log</button>
  </div>`;

  return `<div class="gauges ${staleClass}">
  <div class="${modelClasses}" title="${escAttr(modelTip)}">
    <div class="gauge-svg-wrap">
      ${renderGaugeSvg(marker.tier, marker.signalKind, modelNeedle)}
      ${modelOverlay}
    </div>
    <div class="gauge-sublabel">${modelSublabelText}</div>
  </div>
  <div class="${effortClasses}" title="${escAttr(effortTip)}">
    <div class="gauge-svg-wrap">
      ${renderGaugeSvg(effortColorBucket(marker.effort.normalized), marker.effort.signalKind, effortNeedle)}
      ${effortOverlay}
    </div>
    <div class="gauge-sublabel">${escHtml(effortDisplayName(marker.effort.normalized))}</div>
  </div>
</div>
${staleAnnotation}
${modelSections}
${actionsRow}`;
}

// Top-level dispatcher: state-in, HTML-out. Caller decides whether
// to render the accordion at all (per Q3 = a, non-in-progress rows
// don't get one); this function handles the in-progress case where
// the row IS expanded and the body needs HTML.
export function renderAccordionBody(state: RenderState): string {
  if (state.kind === "empty") {
    return renderAccordionEmpty();
  }
  return renderAccordionLoaded(state.marker, state.stale, state.ageSec, state.mismatch);
}

```


---

## File 2: src/providers/MarkerWatchService.ts

```typescript
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

```


---

## File 3: src/providers/ActionRegistry.ts

```typescript
// Typed action registry for the Set 029 Session 4 custom-tree view.
// Replaces the lost `package.json` `view/item/context` declarative
// rules per S4 audit GPT-5.4 M2: one source of truth for
// command-applicability that drives right-click QuickPick,
// `Shift+F10` / Context Menu key, and any future inline overflow
// button. Same predicates everywhere — no scatter, no drift.
//
// Each action has:
//   id      — the VS Code command id (registered elsewhere; this
//             module never calls executeCommand directly)
//   label   — operator-facing menu label
//   group   — numeric sort key (matches the @1/@2 numerals from the
//             retired package.json `view/item/context` groups so the
//             menu order survives the pivot)
//   when    — pure predicate: (set, supports) → bool
//
// The 14 actions are the same 14 that S3 had in package.json's
// `view/item/context`. The single difference is mechanism:
// declarative → typed code.

import { SessionSet } from "../types";

export interface ActionSupports {
  uat: boolean;
  e2e: boolean;
}

export interface RowAction {
  id: string;
  label: string;
  group: number;
  when: (set: SessionSet, supports: ActionSupports) => boolean;
}

const inFlightLike = (s: SessionSet): boolean =>
  s.state === "in-progress" || s.state === "not-started";

const cancellable = (s: SessionSet): boolean =>
  s.state === "in-progress" || s.state === "not-started" || s.state === "complete";

const isCancelled = (s: SessionSet): boolean => s.state === "cancelled";

const needsMigration = (s: SessionSet): boolean => s.needsMigration;

// Ordered list — `group` controls QuickPick / context-menu sort.
// Anything in group 1xx is "open", 2xx is "navigate", 3xx is "copy
// command", 4xx is "copy meta", 8xx is "migrate", 9xx is "lifecycle".
export const ROW_ACTIONS: RowAction[] = [
  { id: "dabblerSessionSets.openSpec",          label: "Open Spec",                          group: 101, when: () => true },
  { id: "dabblerSessionSets.openActivityLog",   label: "Open Activity Log",                  group: 102, when: () => true },
  { id: "dabblerSessionSets.openChangeLog",     label: "Open Change Log",                    group: 103, when: () => true },
  { id: "dabblerSessionSets.openAiAssignment",  label: "Open AI Assignment",                 group: 104, when: () => true },
  { id: "dabblerSessionSets.openUatChecklist",  label: "Open UAT Checklist",                 group: 105,
    when: (s, sup) => sup.uat && s.config?.requiresUAT === true },
  { id: "dabblerSessionSets.revealPlaywrightTests", label: "Reveal Playwright Tests for This Set", group: 106,
    when: (s, sup) => sup.e2e && s.config?.requiresE2E === true },
  { id: "dabblerSessionSets.openSessionState",  label: "Open Session State",                 group: 107, when: () => true },
  { id: "dabblerSessionSets.openFolder",        label: "Reveal Folder",                      group: 201, when: () => true },
  { id: "dabblerSessionSets.copyStartCommand.default",  label: "Copy: Start next session",          group: 301,
    when: (s) => inFlightLike(s) },
  { id: "dabblerSessionSets.copyStartCommand.parallel", label: "Copy: Start next parallel session", group: 302,
    when: (s) => inFlightLike(s) },
  { id: "dabblerSessionSets.copySlug",          label: "Copy: Slug only",                    group: 401, when: () => true },
  { id: "dabblerSessionSets.migrate",           label: "Migrate to v3 schema",               group: 801, when: needsMigration },
  { id: "dabblerSessionSets.cancel",            label: "Cancel Session Set",                 group: 901,
    when: (s) => cancellable(s) },
  { id: "dabblerSessionSets.restore",           label: "Restore Session Set",                group: 902,
    when: (s) => isCancelled(s) },
];

// Resolve the applicable subset for a given set + support flags,
// pre-sorted by `group` so the QuickPick / context-menu order is
// deterministic.
export function applicableActions(set: SessionSet, supports: ActionSupports): RowAction[] {
  return ROW_ACTIONS
    .filter((a) => a.when(set, supports))
    .slice()
    .sort((a, b) => a.group - b.group);
}

```


---

## File 4: src/providers/suppressionState.ts

```typescript
// Manual-collapse suppression state for the Set 029 Session 4 custom
// tree. Per S4 audit Q2(a) + GPT-5.4 M7: the suppression key is the
// (slug, marker.updatedAt) tuple — naturally aging because the key
// changes on every new SessionStart. Pure reducer functions; the
// caller persists the resulting state via vscode workspaceState.
//
// The state object is `Record<slug, marker.updatedAt>`. A row is
// suppressed iff `state[slug] === currentMarker.updatedAt` for that
// row's marker. Manual re-expand clears state[slug]. Pruning drops
// entries whose slug is no longer in the visible set list.

export type SuppressionState = Record<string, string>;

// Is the row for this (slug, updatedAt) currently suppressed?
export function isSuppressed(
  state: SuppressionState,
  slug: string,
  markerUpdatedAt: string | null,
): boolean {
  if (!markerUpdatedAt) return false;
  return state[slug] === markerUpdatedAt;
}

// Operator manually collapsed the accordion. Suppress auto-expand
// for THIS occurrence (same updatedAt). The next SessionStart writes
// a fresh marker with a new updatedAt — that automatically un-
// suppresses because the key tuple no longer matches.
export function suppress(
  state: SuppressionState,
  slug: string,
  markerUpdatedAt: string,
): SuppressionState {
  return { ...state, [slug]: markerUpdatedAt };
}

// Operator manually expanded the row again (clicked the collapsed
// header). Clear suppression for the slug entirely — the next
// auto-expand signal will fire normally even within the current
// occurrence.
export function clearSuppression(state: SuppressionState, slug: string): SuppressionState {
  if (!(slug in state)) return state;
  const next: SuppressionState = { ...state };
  delete next[slug];
  return next;
}

// Prune entries whose slug is no longer in the visible-set list.
// Prevents workspaceState from accumulating stale keys after sets
// are renamed, deleted, or moved.
export function prune(state: SuppressionState, visibleSlugs: ReadonlySet<string>): SuppressionState {
  let changed = false;
  const next: SuppressionState = {};
  for (const slug of Object.keys(state)) {
    if (visibleSlugs.has(slug)) {
      next[slug] = state[slug];
    } else {
      changed = true;
    }
  }
  return changed ? next : state;
}

```


---

## File 5: src/types/sessionSetsWebviewProtocol.ts

```typescript
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
export interface RowPayload {
  slug: string;
  name: string;
  state: "in-progress" | "not-started" | "complete" | "cancelled";
  description: string;             // already-formatted: "3/6 · session 4 in flight · 2026-05-18"
  contextValue: string;            // for ActionRegistry membership tests (e.g., "sessionSet:in-progress:uat")
  iconSlug: string;                // "in-progress.svg" / "done.svg" / etc.
  needsMigration: boolean;
  isResolvedSet: boolean;          // true iff this is the row the orchestrator marker resolves to
  accordionHtml: string | null;    // pre-rendered (for resolved set) or null (for everything else)
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
  // Banner above In Progress bucket when resolver returned
  // "multiple-in-progress-sets" (per S4 Q8 = a+c).
  ambiguityBanner: { visible: boolean; candidates: string[] };
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
  suppressed: Record<string, string>;  // slug → marker.updatedAt
}

export type HostToWebview = RowsSnapshotMsg | ScanStateChangedMsg | SuppressionEchoMsg;

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
export interface ToggleRowMsg {
  type: "toggleRow";
  slug: string;
  expanded: boolean;
  markerUpdatedAt: string | null;
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

```
