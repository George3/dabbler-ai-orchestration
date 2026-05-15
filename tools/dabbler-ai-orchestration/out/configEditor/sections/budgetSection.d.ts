import { SectionState, SectionRenderResult } from "./types";
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
export declare function render(state: SectionState): SectionRenderResult;
