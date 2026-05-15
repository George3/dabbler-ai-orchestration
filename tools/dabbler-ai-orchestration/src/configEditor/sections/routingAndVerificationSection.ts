import { SectionState, SectionRenderResult } from "./types";
import { escapeHtml, fieldSource, getByPath, indicatorHtml } from "./helpers";

/**
 * §1 Routing & Verification.
 *
 * Two decoupled dropdowns. Per Set 025 wireframes §1:
 * - When outsourcing = "disabled", "Automatic via API" verification is
 *   greyed out and only "Manual" / "None" are selectable.
 * - Manual-template block appears conditionally when verification = manual.
 *
 * YAML targets (Appendix B):
 * - routing.outsourcing_mode → router-config.yaml (or local-overrides.yaml)
 * - verification_method → budget.yaml (NOT locally overridable)
 */
export function render(state: SectionState): SectionRenderResult {
  // Effective routing.outsourcing_mode (local > shared > default)
  const localRouting = getByPath(state.localOverrides, "routing.outsourcing_mode");
  const sharedRouting = getByPath(state.routerConfig, "routing.outsourcing_mode");
  const effectiveRouting =
    (typeof localRouting === "string" ? localRouting : null) ??
    (typeof sharedRouting === "string" ? sharedRouting : null) ??
    "whenever-helpful";

  const routingSource = fieldSource(
    state,
    "routerConfig",
    "routing.outsourcing_mode",
    "routing.outsourcing_mode",
    true
  );

  const verification = getByPath(state.budget, "verification_method");
  const effectiveVerification =
    typeof verification === "string" ? verification : "api";

  const verificationSource = fieldSource(state, "budget", "verification_method", "", false);

  const outsourcingDisabled = effectiveRouting === "disabled";

  const html = `
<div class="section-block">
  <h3>Mid-session outsourcing</h3>
  <p class="section-help">When should the orchestrator route reasoning tasks to external AI providers during the session itself (not at session end)?</p>
  <div class="field-row">
    <label for="s1-outsourcing-mode">Mode</label>
    <select id="s1-outsourcing-mode" data-field="outsourcingMode">
      <option value="whenever-helpful"${effectiveRouting === "whenever-helpful" ? " selected" : ""}>Whenever helpful (let AI decide)</option>
      <option value="verification-only"${effectiveRouting === "verification-only" ? " selected" : ""}>Verification only</option>
      <option value="disabled"${effectiveRouting === "disabled" ? " selected" : ""}>Disabled</option>
    </select>
    ${indicatorHtml(routingSource, "outsourcingMode")}
  </div>
</div>

<div class="section-block">
  <h3>Cross-provider verification</h3>
  <p class="section-help">How should end-of-session cross-provider verification run? (Rule 2 of the workflow doc: every session ends with verification unless this is explicitly set to None.)</p>
  <div class="field-row">
    <label for="s1-verification-method">Method</label>
    <select id="s1-verification-method" data-field="verificationMethod" data-disable-api="${outsourcingDisabled ? "1" : "0"}">
      <option value="api"${effectiveVerification === "api" ? " selected" : ""}${outsourcingDisabled ? " disabled" : ""}>Automatic via API (recommended)</option>
      <option value="manual-via-other-engine"${effectiveVerification === "manual-via-other-engine" ? " selected" : ""}>Manual via portable markdown</option>
      <option value="skipped"${effectiveVerification === "skipped" ? " selected" : ""}>None</option>
    </select>
    ${indicatorHtml(verificationSource, "verificationMethod")}
  </div>
  <p class="section-info" id="s1-api-constraint" style="${outsourcingDisabled ? "" : "display:none;"}">
    &#9432; "Automatic via API" requires outsourcing to be enabled. When outsourcing is Disabled, only "Manual" and "None" are available here.
  </p>
  <div id="s1-manual-template" style="${effectiveVerification === "manual-via-other-engine" ? "" : "display:none;"}">
    <p class="section-info">
      Manual verification template URL:
      <a href="https://raw.githubusercontent.com/darndestdabbler/dabbler-ai-orchestration/master/ai_router/prompt-templates/verification.md" target="_blank" rel="noopener">
        ai_router/prompt-templates/verification.md
      </a>
    </p>
  </div>
</div>
`;
  return { html };
}
