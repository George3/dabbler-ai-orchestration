import { SectionState, SectionRenderResult } from "./types";
/**
 * §5 Notifications.
 *
 * Pushover toggle + two env-var-name inputs with ✓/(unset) badges.
 * The "Send a test notification now" button is rendered in Session 5
 * but disabled with a "(wired in Session 7)" label — implementation
 * happens in the final session of Set 026.
 *
 * Appendix B: all three fields live in local-overrides.yaml only.
 */
export declare function render(state: SectionState): SectionRenderResult;
