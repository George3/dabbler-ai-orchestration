import { SectionState, SectionRenderResult } from "./types";
/**
 * §4 Significance flagging.
 *
 * Mostly read-only documentation. Two commands back the operator-invoked
 * surfaces (both shipped in Set 026 Session 6):
 *
 * - `dabbler.flagDecisionForReview` — input box → JSONL append.
 * - `dabbler.scanAnnotationsForActiveSet` — workspace walk for
 *   `# @dabbler:outsource-review("...")` annotations → dedup + JSONL
 *   append.
 *
 * The "Run command now..." button posts a message the host turns into a
 * `vscode.commands.executeCommand("dabbler.flagDecisionForReview")` call.
 *
 * Appendix B: decision_review.honor_annotations → local-overrides.yaml.
 */
export declare function render(state: SectionState): SectionRenderResult;
