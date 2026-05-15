import { SectionState, SectionRenderResult } from "./types";
/**
 * §4 Significance flagging.
 *
 * Mostly read-only documentation. The actual commands ship in Session 6:
 * - dabbler.flagDecisionForReview
 * - dabbler.scanAnnotationsForActiveSet
 *
 * Session 5 surfaces a "Run command now..." button that posts a message
 * the host turns into a `vscode.commands.executeCommand` call — with a
 * graceful fallback notification when the command is not yet registered.
 *
 * Appendix B: decision_review.honor_annotations → local-overrides.yaml.
 */
export declare function render(state: SectionState): SectionRenderResult;
