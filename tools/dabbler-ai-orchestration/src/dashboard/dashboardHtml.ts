// Set 052 S2 — pure HTML builders for the cost-dashboard webview.
//
// Extracted from CostDashboard.ts so the honest-copy invariants (D5: no
// fictional `config.py METRICS_ENABLED` flag; name the real
// `metrics.enabled` knob; the staleness banner) are unit-testable
// without standing up a webview panel. No `vscode` import — callers pass
// the nonce + cspSource the panel hands them.

import { StalenessResult } from "../utils/routerConfig";

/**
 * Locate the line to reveal when opening `router-config.yaml` (D6). For
 * the `metadata` anchor we prefer the `pricing_reviewed:` line (what the
 * operator edits to clear a staleness warning), falling back to the
 * `metadata:` block header. For `metrics` we target `metrics.enabled`.
 * Returns -1 when no anchor is found (caller opens at the top). Pure
 * string logic — kept here (vscode-free) so it is unit-testable.
 */
export function findConfigAnchorLine(text: string, anchor: "metadata" | "metrics"): number {
  const lines = text.split(/\r?\n/);
  const find = (re: RegExp): number => lines.findIndex((l) => re.test(l));
  if (anchor === "metadata") {
    const reviewed = find(/^\s*pricing_reviewed\s*:/);
    if (reviewed >= 0) return reviewed;
    return find(/^metadata\s*:/);
  }
  // metrics: find the block header, then the nested `enabled:` key.
  const metricsHeader = find(/^metrics\s*:/);
  if (metricsHeader >= 0) {
    for (let i = metricsHeader + 1; i < lines.length; i++) {
      if (/^\S/.test(lines[i])) break; // left the metrics block
      if (/^\s*enabled\s*:/.test(lines[i])) return i;
    }
    return metricsHeader;
  }
  return -1;
}

/** HTML-escape for interpolating filesystem paths / config values into
 *  the webview. */
export function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Shared <head> CSP + base styles for the non-data state pages. Allows
 *  the nonce'd script that wires the action buttons (CSP-safe: event
 *  delegation, no inline handlers). */
function head(nonce: string, cspSource: string): string {
  return `<meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src ${cspSource} 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
  <style nonce="${nonce}">
    body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 20px 28px; max-width: 760px; margin: 0 auto; }
    h2 { font-size: 1.1em; font-weight: 600; }
    code { background: var(--vscode-textCodeBlock-background); padding: 1px 4px; border-radius: 3px; }
    p { line-height: 1.5; }
    .muted { color: var(--vscode-descriptionForeground); font-size: 0.9em; }
    .btn { display: inline-block; padding: 5px 12px; margin: 8px 6px 0 0; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 3px; font-size: inherit; cursor: pointer; }
    .btn:hover { background: var(--vscode-button-hoverBackground); }
    .banner { border: 1px solid var(--vscode-inputValidation-warningBorder, var(--vscode-charts-yellow)); background: var(--vscode-inputValidation-warningBackground, rgba(255,200,0,0.08)); border-radius: 4px; padding: 10px 14px; margin: 0 0 16px; }
    .banner-title { font-weight: 600; }
  </style>`;
}

/** CSP-safe action wiring: a single delegated click listener reads
 *  `data-cmd` and posts it to the extension. Avoids inline `onclick`,
 *  which a nonce-only `script-src` does not cover. */
export function actionScript(nonce: string): string {
  return `<script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.addEventListener('click', (e) => {
      const el = e.target && e.target.closest ? e.target.closest('[data-cmd]') : null;
      if (el) vscode.postMessage({ command: el.getAttribute('data-cmd') });
    });
  </script>`;
}

/**
 * Non-blocking staleness banner (D4). Returns "" when the estimates are
 * fresh so the renderer can unconditionally inject it. The "Update cost
 * estimates" button posts `updateRates`, which opens `router-config.yaml`
 * at the `metadata` block (D6).
 */
export function stalenessBannerHtml(staleness: StalenessResult): string {
  if (!staleness.stale) return "";
  const age =
    staleness.ageDays === null
      ? "Cost estimates have no recorded review date"
      : `Cost estimates were last reviewed ${staleness.ageDays} day${staleness.ageDays === 1 ? "" : "s"} ago (threshold ${staleness.reviewFrequencyDays})`;
  return `<div class="banner">
    <div class="banner-title">⚠ Cost estimates may be stale</div>
    <p class="muted">${esc(age)}. The per-provider rates behind these numbers are operator-maintained — refresh them so the costs stay accurate.</p>
    <button class="btn" data-cmd="updateRates">Update cost estimates</button>
  </div>`;
}

/** Shown when no workspace folder is open. */
export function noWorkspaceHtml(nonce: string, cspSource: string): string {
  return `<!DOCTYPE html><html><head>${head(nonce, cspSource)}</head><body>
  <h2>Cost Dashboard</h2>
  <p>Open a workspace folder to view routing costs.</p>
  </body></html>`;
}

/**
 * Defensive: the command is gated on `dabblerSessionSets.routesCost`, so
 * a routing-incapable workspace should never reach the panel — but if it
 * does, say so honestly rather than implying a flag will fix it.
 */
export function noRouterHtml(nonce: string, cspSource: string): string {
  return `<!DOCTYPE html><html><head>${head(nonce, cspSource)}</head><body>
  <h2>Cost Dashboard</h2>
  <p>This workspace does not route through the AI router, so there is no
  cost data to show. The cost dashboard is available in repositories that
  carry an <code>ai_router/router-config.yaml</code> (Full tier).</p>
  </body></html>`;
}

/**
 * State 1 of 3 (D5): metrics logging is OFF. Names the REAL knob
 * (`metrics.enabled` in `router-config.yaml`) — never the fictional
 * `config.py METRICS_ENABLED` the dead-icon placeholder invented.
 */
export function disabledStateHtml(
  nonce: string,
  cspSource: string,
  configPath: string,
): string {
  return `<!DOCTYPE html><html><head>${head(nonce, cspSource)}</head><body>
  <h2>Cost Dashboard</h2>
  <p>Metrics logging is currently <strong>off</strong>, so no routing
  costs are being recorded.</p>
  <p>To start collecting cost data, set <code>metrics.enabled: true</code>
  in <code>${esc(configPath)}</code>.</p>
  <button class="btn" data-cmd="openConfig">Open router-config.yaml</button>
  ${actionScript(nonce)}
  </body></html>`;
}

/**
 * State 2 of 3 (D5): metrics are ON but nothing has been logged yet —
 * distinct from "disabled". Names the file the router writes so the
 * operator can confirm the path, and surfaces the staleness banner.
 */
export function emptyStateHtml(
  nonce: string,
  cspSource: string,
  metricsPath: string,
  bannerHtml: string,
): string {
  return `<!DOCTYPE html><html><head>${head(nonce, cspSource)}</head><body>
  <h2>Cost Dashboard</h2>
  ${bannerHtml}
  <p>Metrics are enabled, but no routed calls have been recorded yet.
  Costs will appear here after the AI router runs.</p>
  <p class="muted">Reading from <code>${esc(metricsPath)}</code>.</p>
  ${actionScript(nonce)}
  </body></html>`;
}
