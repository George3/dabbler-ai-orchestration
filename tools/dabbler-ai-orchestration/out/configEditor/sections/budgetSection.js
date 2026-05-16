"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.render = render;
const helpers_1 = require("./helpers");
/**
 * §2 Budget.
 *
 * Threshold + scope + warn-at-percent slider. Cost-messaging copy follows
 * the operator's feedback_user_facing_cost_messaging memory:
 * explicit dollar ranges, multi-week scale, open-source caveat,
 * dashboard pointer.
 *
 * Appendix B:
 * - threshold_usd → budget.yaml (locally overridable per-operator cap)
 * - scope → budget.yaml (NOT locally overridable)
 * - warn_at_percent → budget.yaml (locally overridable)
 */
function render(state) {
    const sharedThreshold = (0, helpers_1.asNumber)((0, helpers_1.getByPath)(state.budget, "threshold_usd"));
    const localThreshold = (0, helpers_1.asNumber)((0, helpers_1.getByPath)(state.localOverrides, "threshold_usd"));
    const effectiveThreshold = Number.isFinite(localThreshold)
        ? localThreshold
        : Number.isFinite(sharedThreshold)
            ? sharedThreshold
            : 10;
    const sharedScope = (0, helpers_1.getByPath)(state.budget, "scope");
    const effectiveScope = typeof sharedScope === "string" ? sharedScope : "per-session-set";
    const sharedWarn = (0, helpers_1.asNumber)((0, helpers_1.getByPath)(state.budget, "warn_at_percent"));
    const localWarn = (0, helpers_1.asNumber)((0, helpers_1.getByPath)(state.localOverrides, "warn_at_percent"));
    const effectiveWarn = Number.isFinite(localWarn)
        ? localWarn
        : Number.isFinite(sharedWarn)
            ? sharedWarn
            : 80;
    const thresholdSource = (0, helpers_1.fieldSource)(state, "budget", "threshold_usd", "threshold_usd", true);
    const scopeSource = (0, helpers_1.fieldSource)(state, "budget", "scope", "", false);
    const warnSource = (0, helpers_1.fieldSource)(state, "budget", "warn_at_percent", "warn_at_percent", true);
    const warnAmount = (effectiveThreshold * effectiveWarn) / 100;
    const fmt = (n) => `$${n.toFixed(2)}`;
    const html = `
<div class="section-block">
  <h3>Budget threshold</h3>
  <p class="section-help">
    Operating cost is governed by an open-source AI orchestration framework — actual provider costs vary
    <strong>$0–~$50/week</strong>, which works out to <strong>~$0–$200/month</strong> or
    <strong>~$5–$50 for a typical 2–3 week session set</strong>, depending on routing mode and session frequency.
    See the cost dashboard (Dabbler: Show Cost Dashboard) for live cumulative spend.
    The framework is open-source; you are not billed by Dabbler — you are billed by
    Anthropic, Google, and/or OpenAI directly per their pricing.
  </p>
  <div class="field-row">
    <label for="s2-threshold-usd">Threshold (USD)</label>
    <input type="number" id="s2-threshold-usd" data-field="thresholdUsd" min="0" step="0.01" value="${(0, helpers_1.escapeHtml)(effectiveThreshold.toFixed(2))}" />
    ${(0, helpers_1.indicatorHtml)(thresholdSource, "thresholdUsd")}
  </div>
  <div class="field-row">
    <label for="s2-scope">Scope</label>
    <select id="s2-scope" data-field="scope">
      <option value="per-session-set"${effectiveScope === "per-session-set" ? " selected" : ""}>Per session-set (recommended)</option>
      <option value="per-project"${effectiveScope === "per-project" ? " selected" : ""}>Per project</option>
      ${effectiveScope === "per-session" ? `<option value="per-session" selected>Per session (hand-edit only)</option>` : ""}
    </select>
    ${(0, helpers_1.indicatorHtml)(scopeSource, "scope")}
  </div>
  <div class="field-row">
    <label for="s2-warn-at-percent">Warn at</label>
    <input type="range" id="s2-warn-at-percent" data-field="warnAtPercent" min="0" max="100" step="5" value="${effectiveWarn}" />
    <span id="s2-warn-at-percent-value" class="slider-value">${effectiveWarn}%</span>
    ${(0, helpers_1.indicatorHtml)(warnSource, "warnAtPercent")}
  </div>
</div>

<div class="section-block">
  <h3>Prompt UX preview</h3>
  <p class="section-help">How the orchestrator will react at each cumulative-spend band, based on the threshold and warn percentage above.</p>
  <div class="preview-block" id="s2-preview">
    <p><strong>Below ${effectiveWarn}% of ${fmt(effectiveThreshold)} (${fmt(warnAmount)}):</strong>
       <span class="preview-detail">Silent — no prompt, just log to cost dashboard.</span></p>
    <p><strong>Between ${effectiveWarn}% and 100% (${fmt(warnAmount)}–${fmt(effectiveThreshold)}):</strong>
       <span class="preview-detail">Heads-up — non-blocking notification, one per band.</span></p>
    <p><strong>At or above ${fmt(effectiveThreshold)}:</strong>
       <span class="preview-detail">Confirm-or-abort — modal dialog before the call proceeds.</span></p>
  </div>
</div>
`;
    return { html };
}
//# sourceMappingURL=budgetSection.js.map