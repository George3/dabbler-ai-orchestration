// Pure HTML builders for the Set 060 Getting Started surfaces
// (no-folder CTA + the three-step setup form). Extracted from
// client.js in Session 3 so the rendering — including the D6
// provider-key warning and the D7 worktree note — is unit-testable
// from mocha without a webview (the Set 052 dashboardHtml.ts "pure
// builders" pattern, in plain JS because the webview loads this file
// raw, not through the esbuild bundle).
//
// UMD-lite: in the webview this attaches `DabblerGettingStartedHtml`
// to the global scope (client.js consumes it; CustomSessionSetsView
// loads it as a second nonce'd <script> BEFORE client.js); under Node
// (mocha) it exports via module.exports.
//
// Everything here is a pure string function of (gs payload, control
// state) — no DOM, no postMessage, no vscode API. client.js owns the
// wiring (event listeners + show/hide toggling on control changes).
(function (factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    // eslint-disable-next-line no-undef
    (typeof self !== "undefined" ? self : this).DabblerGettingStartedHtml = factory();
  }
})(function () {
  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // D6 (Set 060 S3): the Full-tier provider-key warning, rendered
  // under the Build button. Shown only when the tier radio is on
  // "full" AND the host reported no provider key in its environment;
  // client.js toggles `hidden` on radio changes without a host
  // round-trip. The copy carries the two load-bearing instructions:
  // set at least one key, then RELOAD THE WINDOW (the extension host
  // captures the merged Windows System + User environment at launch,
  // so a key set afterwards is invisible until reload).
  var ENV_WARNING_TEXT =
    "The Full tier routes work through provider APIs, but no provider " +
    "API key was found. Set at least one of ANTHROPIC_API_KEY, " +
    "OPENAI_API_KEY, or GEMINI_API_KEY in your environment variables, " +
    "then reload the VS Code window (keys set after launch are not " +
    "visible until you reload). The Lightweight tier needs no keys.";

  // D7 (Set 060 S3, carries verifier issue S060-S2-V1-001): the
  // parallel-worktree info note under the checkbox. Shown only while
  // the box is checked; client.js toggles `hidden` on checkbox
  // changes.
  var WORKTREE_NOTE_TEXT =
    "Parallel session sets use git worktrees: each parallel set works " +
    "in its own worktree and is merged back to the main branch when " +
    "the sets complete.";

  /**
   * The D6 warning element. `visible` = (tier === "full" &&
   * !gs.providerKeyPresent); rendered hidden (not omitted) so the
   * client can flip visibility on radio changes without re-rendering.
   */
  function envWarningHtml(visible) {
    return (
      '<div class="gs-warning" data-gs-warning="env" role="alert"' +
      (visible ? "" : " hidden") +
      ">" +
      escHtml(ENV_WARNING_TEXT) +
      "</div>"
    );
  }

  /** The D7 worktree note element. `visible` = the checkbox is checked. */
  function worktreeNoteHtml(visible) {
    return (
      '<div class="gs-note" data-gs-note="worktree" role="note"' +
      (visible ? "" : " hidden") +
      ">" +
      escHtml(WORKTREE_NOTE_TEXT) +
      "</div>"
    );
  }

  // No workspace folder open (D5). A single CTA to open / create a
  // project folder (showOpenDialog -> vscode.openFolder host-side).
  function renderNoFolder() {
    return (
      '<div class="getting-started">' +
        '<div class="gs-header">' +
          '<div class="gs-title">Getting Started</div>' +
          '<div class="gs-subtitle">Open or create a project folder to begin.</div>' +
        '</div>' +
        '<div class="gs-step">' +
          '<div class="gs-step-body">' +
            '<button class="gs-button" type="button" data-gs-action="open-folder">' +
              'Open or create a project folder…' +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  // Folder open, no session sets yet (D1). The three-step setup form.
  // Each step greys out + shows a green check when its D3 completion
  // flag is set. Live state lives ONLY here (D2).
  function gsStep(num, title, complete, bodyHtml) {
    var cls = complete ? "gs-step gs-step-complete" : "gs-step";
    var check = complete ? "✓" : "";
    return (
      '<div class="' + cls + '">' +
        '<div class="gs-step-head">' +
          '<span class="gs-check" aria-hidden="true">' + check + '</span>' +
          '<span class="gs-step-title">' + escHtml(num + ". " + title) + '</span>' +
        '</div>' +
        '<div class="gs-step-body">' + bodyHtml + '</div>' +
      '</div>'
    );
  }

  /**
   * The full Getting Started form. `gs` is the host's
   * GettingStartedPayload (three D3 completion flags +
   * providerKeyPresent); `controls` is the webview-local control
   * state `{ tier: "full"|"lightweight", parallel: boolean }` so
   * re-renders keep the operator's picks (Set 060 S2).
   */
  function renderGettingStarted(gs, controls) {
    var fullChecked = controls.tier === "lightweight" ? "" : " checked";
    var lightChecked = controls.tier === "lightweight" ? " checked" : "";
    var parallelChecked = controls.parallel ? " checked" : "";
    var envWarningVisible =
      controls.tier !== "lightweight" && gs.providerKeyPresent === false;
    var step1 = gsStep(
      1,
      "Build project structure",
      gs.structureBuilt,
      '<div class="gs-radio-group" role="radiogroup" aria-label="Project tier">' +
        '<label class="gs-radio"><input type="radio" name="gs-tier" value="full"' + fullChecked + '> Full</label>' +
        '<label class="gs-radio"><input type="radio" name="gs-tier" value="lightweight"' + lightChecked + '> Lightweight</label>' +
      '</div>' +
      '<button class="gs-button" type="button" data-gs-action="build-structure">' +
        'Build project structure' +
      '</button>' +
      envWarningHtml(envWarningVisible),
    );
    var step2 = gsStep(
      2,
      "Create or import a project plan",
      gs.planPresent,
      '<button class="gs-button" type="button" data-gs-action="import-plan">' +
        'Import project-plan.md…' +
      '</button>' +
      '<button class="gs-button gs-button-secondary" type="button" data-gs-action="copy-plan-prompt">' +
        'Copy prompt for planning' +
      '</button>',
    );
    var step3 = gsStep(
      3,
      "Build session sets",
      gs.sessionSetsPresent,
      '<button class="gs-button" type="button" data-gs-action="build-session-sets">' +
        'Copy prompt to build session sets' +
      '</button>' +
      '<label class="gs-checkbox">' +
        '<input type="checkbox" name="gs-parallel"' + parallelChecked + '> Create parallel session sets where possible' +
      '</label>' +
      worktreeNoteHtml(!!controls.parallel),
    );
    return (
      '<div class="getting-started">' +
        '<div class="gs-header">' +
          '<div class="gs-title">Getting Started</div>' +
          '<div class="gs-subtitle">Complete each step to set up your project, then start your first session.</div>' +
        '</div>' +
        step1 + step2 + step3 +
      '</div>'
    );
  }

  return {
    renderNoFolder: renderNoFolder,
    renderGettingStarted: renderGettingStarted,
    gsStep: gsStep,
    envWarningHtml: envWarningHtml,
    worktreeNoteHtml: worktreeNoteHtml,
    ENV_WARNING_TEXT: ENV_WARNING_TEXT,
    WORKTREE_NOTE_TEXT: WORKTREE_NOTE_TEXT,
  };
});
