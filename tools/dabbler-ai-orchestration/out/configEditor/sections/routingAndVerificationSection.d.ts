import { SectionState, SectionRenderResult } from "./types";
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
export declare function render(state: SectionState): SectionRenderResult;
