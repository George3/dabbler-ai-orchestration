# Set 029 Session 4 verification — Round B (integration: view + client)

## Context

Round A (separate file) verified the provider-layer extracts +
typed-protocol modules. Verdict: **SUGGEST (1)** — minor suggestion
on `describeMarker` purity (calls `Date.now()` for the secondary
effort-age suffix). All other items VERIFIED.

**Round B scope** (this round): the integration surface where M1
(DOM structure), M6 (command-dispatch / Layer-2 coverage), M8
(indicator-action parity), and R10/R11/R12 (focus/a11y, QuickPick
UX, invalid interactive nesting) live.

Splitting per memory `feedback_split_large_verification_bundles`
to stay under the bundle ceiling.

## Files in this bundle (3 + extension.ts diff context, ~1100 LOC)

1. `src/providers/CustomSessionSetsView.ts` (498 LOC) — the
   `WebviewViewProvider`. Consumes `SessionSetsModel` +
   `MarkerWatchService` + `OrchestratorAccordion` + `ActionRegistry` +
   `suppressionState`. Owns lifecycle, message dispatch, snapshot
   serialization, QuickPick context menu, command allowlist.
2. `media/session-sets-tree/client.js` (290 LOC) — webview-side
   rendering, ARIA tree (roving tabindex), kbd nav (↑/↓/Home/End/
   ←/→/Enter/Space/Shift+F10/ContextMenu), contextmenu event
   capture, postMessage protocol with monotonic-version drop, defense-
   in-depth HTML escaping.
3. `media/session-sets-tree/tree.css` (~280 LOC) — tree shell
   (bucket headers, rows, focus/selection, ambiguity banner,
   welcome panel, loading sentinel) + lifted v0.15.0 gauge CSS.

## What you're being asked to verify in Round B

Answer Q1–Q8 in order with **VERIFIED / MUST-FIX / SUGGEST** verdicts
plus 1–3 sentences of reasoning each. After Q1–Q8, emit a final
verdict line per the format at the bottom.

### Q1. DOM structure: no invalid interactive nesting (M1 / R12)

Per audit GPT-5.4 M1: do NOT use `<button role="treeitem">` wrapping
the accordion body. The treeitem container must be a focusable
non-button element (e.g., `<div role="treeitem" tabindex="-1">`) so
the accordion body's interactive children (install-hook /
set-orchestrator / writer-log buttons) are NOT nested inside an
interactive button.

Verify in `client.js`'s `renderRow()`:
- The treeitem is a `<div role="treeitem" tabindex="-1">`, NOT a
  `<button>`.
- The row-header (`<div class="row-header" role="presentation">`)
  inside is a non-interactive presentational wrapper.
- The accordion-body (`<div class="accordion-body" role="region">`)
  with the install-hook / set-orchestrator / writer-log buttons is
  rendered as a sibling region inside the treeitem container, not
  nested inside any interactive button.

### Q2. ARIA tree semantics (WAI-ARIA 1.2 single-select tree)

Verify the rendered structure follows the WAI-ARIA single-select
tree pattern:
- Container has `role="tree"` and `aria-label`.
- Each bucket has `role="group"` with `aria-labelledby` pointing at
  a header element.
- Each row has `role="treeitem"`, `aria-level`, `aria-selected`,
  and `aria-expanded` (only when expandable per Q3 of the audit —
  non-expandable rows should NOT carry `aria-expanded`, per GPT M3
  "no inert chevron").
- Roving tabindex: at any time, exactly one treeitem has
  `tabindex="0"`, all others `tabindex="-1"`. `initRovingFocus()`
  initializes; `focusItem()` rotates.
- Keyboard handler covers: ↑/↓ sibling, Home/End first/last,
  ←/→ collapse/expand, Enter/Space activate, Shift+F10 +
  ContextMenu key for the QuickPick.

### Q3. Monotonic version drop client-side (M3 carry-forward)

Per audit GPT-5.4 M3: webview client drops messages with
`version < currentVersion`. Verify in `client.js`:
- The `message` event listener checks `if (typeof msg.version ===
  "number" && msg.version < currentVersion) return;` BEFORE acting
  on the message.
- `currentVersion` is bumped to the message's version on accept.
- `rowsSnapshot`, `scanStateChanged`, `suppressionEcho` all carry
  versions and respect the drop logic.

### Q4. Command-dispatch allowlist (defense-in-depth)

`CustomSessionSetsView.ts` includes a `COMMAND_ALLOWLIST` set
containing the 14 row-action command ids + the 3 indicator-action
buttons (install-hook / set-orchestrator / writer-log). The
`dispatchCommand(commandId, args)` method rejects any commandId not
in the allowlist before calling `vscode.commands.executeCommand`.

Verify:
- All 17 expected commands are in the allowlist (14 actions + 3
  indicator buttons).
- No commandId from a webview message can fire executeCommand
  without passing the allowlist check.
- Rejected commands log a warning (not silent).

### Q5. Indicator-action parity (M8 — ship blocker for retirement)

Per audit GPT-5.4 M8: the `dabblerOrchestratorIndicator` view must
NOT retire until the accordion body preserves install-hook +
set-orchestrator + open-writer-log buttons. The retirement happened
in this session — verify the parity exists.

Verify in `OrchestratorAccordion.ts` (Round A bundle — re-check):
- `renderAccordionEmpty()` renders all three buttons (install-hook
  CTA + set-orchestrator + writer-log).
- `renderAccordionLoaded()` renders set-orchestrator + writer-log
  (the install-hook button is unnecessary when a marker exists, but
  the set-orchestrator + writer-log buttons must persist).
- Buttons carry `data-command="dabbler.installOrchestratorHook.claudeCode"`,
  `data-command="dabbler.setOrchestrator"`, and
  `data-command="dabbler.openOrchestratorWriterLog"` respectively.
- The webview client.js wires these via the `[data-command]` event
  listener (the buttons inside the accordion body are not wrapped
  in a treeitem interactive element — see Q1).

### Q6. Suppression handshake (host ↔ webview)

The suppression state lives in `workspaceState` (per Q2 = a). The
host echoes the state to the webview via `SuppressionEchoMsg`. The
webview tracks the same state via the `suppressed` local + a
`manualToggles` overlay for current-session clicks.

Verify in `CustomSessionSetsView.ts`:
- `handleToggle(slug, expanded, markerUpdatedAt)` calls `suppress()`
  on manual collapse and `clearSuppression()` on manual expand, then
  fires `postSuppressionEcho()`.
- The reducer prunes via the round-up snapshot (`postSnapshot()`
  calls `prune(current, visibleSlugs)`).
- `getSuppression()` / `setSuppression()` read/write
  `context.workspaceState` under the key
  `"dabbler.sessionSets.suppressedExpand"`.

### Q7. Ambiguity banner (Q8 = a+c)

When the resolver returns `multiple-in-progress-sets`, a banner
appears above the In Progress bucket with a link to open the writer
log. S3's silent fail-close behavior is preserved for
`no-in-progress-set` / `no-docs-session-sets` (no banner, no
accordion, no orphan marker).

Verify:
- `CustomSessionSetsView.postSnapshot()` populates
  `payload.ambiguityBanner = { visible, candidates }` with
  `visible = true` only when `reason === "multiple-in-progress-sets"`.
- `client.js render()` checks `lastSnapshot.ambiguityBanner.visible`
  and emits a `.ambiguity-banner` div with an
  `[data-command="dabbler.openOrchestratorWriterLog"]` button.
- No code path writes an orphan marker on failed resolution
  (carry-forward from S3 fail-closed posture).

### Q8. CSP + nonce hygiene

The webview HTML shell (`CustomSessionSetsView.renderShell()`)
must declare a strict Content-Security-Policy with:
- `default-src 'none'` (deny everything by default).
- `style-src ${webview.cspSource} 'unsafe-inline'` (CSS file +
  inline SVG `<style>`-free; SVG fragments contain only attributes,
  not embedded `<script>`).
- `script-src 'nonce-${nonce}'` with a freshly-generated nonce that
  matches the `<script nonce="${nonce}">` in the shell.

Verify:
- Nonce is freshly generated per `renderShell()` call (not stable
  across renders).
- CSP allows the webview's own resource origin for CSS via
  `webview.cspSource`.
- No `script-src 'unsafe-inline'` or `'unsafe-eval'`.
- No external network origin in `script-src` or `style-src`.

---

## Final verdict (Round B)

Emit one summary line at the end:

`VERDICT: VERIFIED` if Q1–Q8 all pass without must-fix items
`VERDICT: MUST-FIX (<count>)` if any Q has a must-fix
`VERDICT: SUGGEST (<count>)` if no must-fix but ≥1 suggest items

Followed by a 2–3-sentence overall summary.
