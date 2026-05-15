import { SectionState, SectionRenderResult } from "./types";
import { fieldSource, getByPath, indicatorHtml } from "./helpers";

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
export function render(state: SectionState): SectionRenderResult {
  const honor = getByPath(state.localOverrides, "decision_review.honor_annotations");
  // Default: true (per wireframes §4)
  const honorOn = typeof honor === "boolean" ? honor : true;
  const honorSource = fieldSource(state, "localOnly", "", "decision_review.honor_annotations", true);

  const html = `
<div class="section-block">
  <h3>Two ways to flag a decision for cross-provider review</h3>

  <ol class="numbered-list">
    <li>
      <strong>Run the command</strong>
      <div class="command-box">
        <code>Dabbler: Flag Decision for Cross-Provider Review</code>
      </div>
      <p class="section-help">You'll be prompted for a one-line reason. The flag is queued in the active session-set's decision-review queue.</p>
      <button type="button" id="s4-run-flag-command" class="secondary">Run command now&hellip;</button>
    </li>
    <li>
      <strong>Add an annotation in source code</strong>
      <pre class="code-sample"># @dabbler:outsource-review("reason text here")</pre>
      <p class="section-help">The orchestrator scans open files at session start; any new annotations are queued automatically.</p>
    </li>
  </ol>
</div>

<div class="section-block">
  <h3>Honor annotations</h3>
  <div class="field-row">
    <label><input type="checkbox" id="s4-honor-annotations" data-field="honorAnnotations"${honorOn ? " checked" : ""} /> Honor <code>@dabbler:outsource-review</code> annotations in this project</label>
    ${indicatorHtml(honorSource, "honorAnnotations")}
  </div>
  <p class="section-info">Defaults to ON; this setting lives in <code>local-overrides.yaml</code> at <code>decision_review.honor_annotations</code>.</p>
</div>

<div class="section-block">
  <h3>Queue file</h3>
  <p class="section-info">
    Flagged decisions are appended to:
    <br/>
    <code>docs/session-sets/&lt;active-slug&gt;/decision-review-queue.jsonl</code>
    <br/>
    They surface in the orchestrator's initial planning checklist at the next session start.
  </p>
</div>
`;
  return { html };
}
