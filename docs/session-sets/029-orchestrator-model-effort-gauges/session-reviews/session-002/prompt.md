# Session 2 verification prompt — Set 029 (orchestrator model & effort indicator gauges, Claude path)

## Context

Set 029 ships a small VS Code webview view pinned above the Dabbler
Session Set Explorer that shows the current orchestrator's **model**
and **effort level** as two side-by-side semi-circle CSS gauges. The
operator-facing failure mode being eliminated: a session silently starts
on a lower-tier model after the operator dialed down for a cheap task
and forgot to dial back up.

Session 1 (the cross-provider design audit) locked the design — Q1–Q6,
five showstoppers S1–S5, the marker schema v2 with `signalKind` +
`confidence`, the visual-treatment matrix REVISED 2026-05-18, the
multi-writer precedence policy, the Windows-aware retry loop (5 attempts
at 50/200/600/1200ms backoff), the confidence-low producer rule for the
Claude SessionStart hook, and R7 (the `/clear`-vs-`SessionStart` dual-
condition asymmetry to verify in S2). All ratified by three verification
rounds against gpt-5-4 plus one Bucket-2 consensus call against gpt-5-4
+ gemini-pro. Total S1 routed spend: $0.845 against the operator's
$5.00 NTE for the set.

Session 2 ships the **Claude path end-to-end**: the webview view + the
provider with marker reader/watcher + the empty-state CTA + the Claude
Code `SessionStart` + `UserPromptSubmit` hook installer + the shared
`scripts/write-orchestrator-marker.js` helper + the Layer 3 Playwright
smoke. Non-Claude surfaces and the universal manual-override quickpick
ship in Session 3.

Pre-implementation verification (per spec.md S2 step 5/6 + R7):
WebFetch against the official Claude Code hooks docs
(https://code.claude.com/docs/en/hooks) confirmed all three open
preconditions:

- `/clear` fires `SessionStart` with `source: "clear"` (the matcher
  table lists `startup` / `resume` / `clear` / `compact` as the four
  source values; `model` is one of the documented input fields on
  SessionStart).
- `/think*` are per-message thinking-budget escalations, NOT a
  persistent session setting — `/clear` is by definition a fresh-
  session boundary semantically.
- `UserPromptSubmit` payload exposes a `prompt` field with the full
  user-submitted text — `/think*` prefix detection ships at full
  functionality without the Medium-only fallback.

Both R7 conditions are TRUE, so the SessionStart hook clobbers `effort`
to Medium on every source value (startup/resume/clear/compact).

## What you're being asked to verify

Session 2 ships **code**, not docs. Your verification is therefore an
**implementation review**: does the code shipped in S2 faithfully
implement the locked design from S1's audit?

The bundle below is split across four sections:

1. **`scripts/write-orchestrator-marker.js`** — the shared marker
   writer (~390 LOC). All four modes (session-start /
   user-prompt-submit / manual / configured-default), multi-writer
   precedence, retry loop, atomic write, confidence-low producer,
   effort-merge for `/think*`. Reused by Session 3.

2. **`src/providers/orchestratorIndicatorProvider.ts`** — the
   webview provider (~380 LOC). Marker reader + watcher + render
   pipeline + visual-treatment matrix + tooltips + stale state.

3. **`src/commands/installOrchestratorHookClaudeCode.ts`** — the
   Claude hook installer (~170 LOC). Idempotent edit of
   `~/.claude/settings.json`. Installs SessionStart × 4 source
   matchers + one UserPromptSubmit hook.

4. **`media/orchestrator-indicator/indicator.css`** — the CSS
   (~190 LOC). Encodes the visual-treatment matrix per signalKind.

The locked design lives in `audit-summary.md` (already in context from
S1). Spec deltas are in spec.md (Session 2 step list).

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Marker writer faithfulness to the locked design.**
   `scripts/write-orchestrator-marker.js` is the cornerstone of the
   set — Session 3's three writers (Codex config watcher, manual
   quickpick, future Gemini/Copilot) all reuse it. Verify:
   - **Precedence policy** (audit §"Multi-writer precedence"):
     `attemptWriteWithPrecedence` reads existing marker, checks if
     it's stale, then compares signalKind precedence. Is the order
     correct? Specifically, is the precedence comparison consistent
     with "current > manual > last-observed > configured-default"?
     The implementation uses `precedenceIndex()` returning lower
     index = stronger; the skip condition is `proposedRank >
     existingRank` (proposed is weaker). Is the inequality direction
     right?
   - **TOCTOU race window**: the audit prescribed "re-read
     immediately before atomic rename". The current implementation
     reads inside `attemptWriteWithPrecedence` once, then writes.
     Is the re-read pattern faithful, OR has the race window
     been left open? If the latter, is the loss of safety material
     in practice (concurrent writers landing within the same
     `attempt` window)?
   - **Retry loop**: `runWithRetries` does 5 attempts with the
     locked 50/200/600/1200ms backoffs. Verify the loop boundary
     math — the audit says "initial + 4 retries", which means 5
     total attempts; the implementation iterates `attempt = 0` to
     `RETRY_BACKOFFS_MS.length`, i.e., 5 iterations (0,1,2,3,4) with
     the backoff sleep happening after attempts 0,1,2,3 (4 sleeps,
     ~2050ms total). Correct?
   - **Confidence-low producer rule**: in `buildMarker`, when
     `args.mode === "session-start"` and `modelMissing`, force
     `confidence = "low"` + `model = "unknown"`. Does this match
     the audit's "if the SessionStart hook payload's `.model` is
     missing, null, or unparseable" exactly?
   - **Effort reset on SessionStart**: per the R7 verification, every
     SessionStart write should reset `effort` to Medium regardless of
     `source`. The implementation hard-codes the effort sub-object
     for `mode === "session-start"` to `{normalized: "medium",
     native: "default", thinking: false, signalKind: "current",
     confidence: <model confidence>}`. Faithful?
   - **`user-prompt-submit` merge-effort path**: when an existing
     marker exists, it preserves top-level signal and updates only
     effort. When no marker exists, it bootstraps a Medium-default
     Claude marker first, then overwrites effort with the just-
     detected `/think*`. Is the bootstrap behavior reasonable for an
     operator who installed the hook AFTER Claude was already
     running? Should it perhaps skip the write instead and wait for
     the next SessionStart?
   - **Atomic write**: write to `<target>.tmp.<pid>.<rand>` then
     rename, cleanup tmp on failure. Faithful to typical atomic
     write-and-rename semantics?

**Q2. Provider implementation faithfulness to the visual-treatment matrix.**
   `orchestratorIndicatorProvider.ts` renders the gauges. Verify
   against the REVISED 2026-05-18 visual-treatment matrix in
   audit-summary.md:
   - The four `signalKind` values get the prescribed treatments:
     - `current`: solid fill + solid rim + no badge ✓
     - `configured-default`: ~85% opacity + dashed rim + DEFAULT pill ✓
     - `last-observed`: hollow rim + filled needle + clock-icon overlay
       + time-elapsed suffix ✓
     - `manual`: solid fill + operator-icon overlay ✓
     Are the CSS class hooks the provider emits actually wired to
     those visual treatments in `indicator.css`?
   - **Stripes are stale-only** (REVISED 2026-05-18): the audit
     specifically separated stripes from `configured-default` so the
     two states are distinguishable at small gauge sizes. The
     provider emits `.stale` on `.gauges` when ageSec >
     stalenessMaxSec; the CSS renders the diagonal-stripe overlay on
     `.stale .gauge-svg`. Is `configured-default` free of stripe
     usage (verify CSS doesn't have a `.signal-configured-default`
     rule that applies stripes)?
   - **Last-updated annotation always visible**: the provider's
     `renderLoaded` emits a "updated Xs ago" / "last updated Xh ago
     — stale" annotation. Is the timestamp visible regardless of
     state, per audit Q6?
   - **Tooltip copy embeds confidence explicitly**: the provider's
     `modelTooltip` and `effortTooltip` produce phrases like "live
     signal (low confidence — hook payload missing model)",
     "configured default (medium confidence — does not track runtime
     changes)", "last observed Xm ago via /think...". Does this
     match the audit's tooltip prescriptions?
   - **Watcher + poll backstop**: provider uses
     `vscode.workspace.createFileSystemWatcher` with a
     `RelativePattern(MARKER_DIR, "current-orchestrator.json")` plus
     a 60s poll backstop + 50ms render debounce. The 50ms debounce
     coalesces Windows atomic-write bursts. Is the 60s backstop
     adequate for the operator's stated workflow (multi-day session
     sets with breaks), or could the gauge display a >60s-stale
     signal in some edge case if the watcher misses?
   - **Empty state**: renders solid grey gauges + "No signal —
     install hook" CTA when the marker file is missing. CTA
     dispatches `dabbler.installOrchestratorHook.claudeCode`.
     Faithful to D8?

**Q3. Hook installer correctness.**
   `installOrchestratorHookClaudeCode.ts` writes
   `~/.claude/settings.json`. Verify:
   - **Idempotence**: the installer looks up existing entries by
     matcher AND a command-string-substring check for
     "write-orchestrator-marker.js", then upgrades in place. Re-
     running shouldn't duplicate entries. Trace through the
     `ensureMatcherEntry` logic for both first-install and re-
     install — any case where a duplicate is emitted?
   - **Source matcher coverage**: installer adds SessionStart hooks
     for all four source matchers (startup/resume/clear/compact). Is
     this correct per the docs, or should some sources be excluded?
     (E.g., is `compact` a session boundary in the conceptual sense
     this feature uses, or is it a mid-conversation event that
     should preserve `last-observed` effort?)
   - **UserPromptSubmit matcher**: installer adds ONE UserPromptSubmit
     entry without a matcher (fires on every prompt). Correct?
   - **Helper-path quoting**: the installer constructs `node
     "${helperAbsPath}" --mode ${mode}`. Path quoting handles spaces
     (`C:\Users\Some Name\...`). Any platforms / shells where this
     breaks? (Claude Code hook commands are invoked via the OS
     shell — Bash on POSIX, cmd / PowerShell on Windows.)
   - **Foreign-hook preservation**: the installer iterates only the
     `hooks.SessionStart` / `hooks.UserPromptSubmit` arrays and only
     touches entries whose command contains
     "write-orchestrator-marker.js". Other operator-installed hooks
     stay verbatim. Is the substring check too loose (could it match
     an unrelated user script with that filename) or too tight
     (could it miss an upgraded dabbler hook that has been renamed)?
   - **Atomic settings.json write**: write to
     `<settings.json>.tmp.<pid>.<rand>` + rename. Same atomic pattern
     as the marker writer. Adequate?

**Q4. CSS visual matrix correctness.**
   `media/orchestrator-indicator/indicator.css` encodes the visual
   treatments. Spot-check:
   - `.signal-last-observed .gauge-arc-fill` has `stroke-opacity: 0`
     (hollow rim — no fill arc), and `.signal-last-observed
     .gauge-rim` has `stroke-opacity: 1` (visible rim). Faithful to
     "hollow rim + filled needle"? (The needle is `.gauge-needle`
     and renders unconditionally — that's the "filled needle" part.)
   - `.signal-configured-default .gauge-rim` has `stroke-dasharray:
     2 2` (dashed). Faithful?
   - `.stale .gauge-svg` applies a `repeating-linear-gradient`
     diagonal-stripe background at ~18% white opacity. Is "~18%"
     close enough to the audit's "50% opacity" prescription? (The
     opacity is the overlay's opacity over the underlying gauge
     fill, not the gauge's overall opacity.)
   - Are the color hex values (red `#e06c75`, yellow `#e5c07b`,
     green `#98c379`) recognizable in both light and dark themes?
     Note: the provider doesn't toggle themes — VS Code's theme
     affects `--vscode-foreground` and `--vscode-editorWidget-border`
     but the gauge fills are hard-coded. Acceptable?

**Q5. Layer 3 Playwright smoke coverage.**
   `src/test/playwright/orchestrator-indicator.spec.ts` ships 8
   scenarios (A–H). Verify the coverage against spec.md S2 step 7:
   - Scenario A (current Opus → flagship classes + label) ✓
   - Scenario B (Haiku → low-tier classes + label) ✓
   - Scenario C (confidence-low tooltip text) ✓
   - Scenario D (last-observed effort with clock overlay + elapsed
     suffix) ✓
   - Scenario E (configured-default → DEFAULT pill + NO stripes) ✓
   - Scenario F (stale 9h → stripe class + annotation) ✓
   - Scenario G (no marker → empty-state CTA) — spec didn't
     explicitly list this but it's the empty-state path from D8 ✓
   - Scenario H (helper-script multi-writer precedence, non-Electron)
     — Scenario H tests the helper directly via `child_process.spawn`.
     Is testing the helper at the non-Electron layer adequate for
     the multi-writer precedence policy, or does the policy need
     in-Electron coverage too (e.g., to confirm the webview re-renders
     when the marker file is overwritten by the helper)?
   - **Coverage gap check**: spec.md S2 step 7 also called for a
     "screenshot assertion" of the view container ordering
     (orchestrator above session sets). The Playwright spec doesn't
     include a screenshot assertion — instead the comment notes
     ordering is asserted "via a DOM index check on side-bar
     viewlets", but the spec file doesn't actually contain such an
     assertion in any scenario. Is this a material gap, or is the
     view-registration test implicit (if the registration is wrong,
     Scenario A wouldn't be able to find the iframe at all)?

**Q6. Spec/CHANGELOG/CLAUDE.md consistency.**
   - **Version drift correction**: spec.md S2 step 8 said "0.13.17
     → 0.13.18"; current is 0.14.1 (Set 030 shipped 0.14.x first).
     This release bumps to 0.14.2. CHANGELOG documents the spec-
     drift correction. Acceptable, or should the spec.md itself be
     updated to reflect the actual progression?
   - **CHANGELOG completeness**: the [0.14.2] entry documents
     additions, known limitations, and implementation notes. Any
     material thing shipped in S2 that's not in the CHANGELOG?
   - **CLAUDE.md note**: the "Extension versioning" section
     mentions the new view + the helper + the SessionStart +
     UserPromptSubmit hooks + the multi-writer precedence + Windows
     retry. Adequate as the brief note S2 was supposed to produce
     (S4 expands it into a proper subsection)?

**Q7. Open architectural questions for S3.**
   Session 3 adds three more writers (Codex config watcher, manual
   quickpick, and the Gemini/Copilot "installer" stub that opens
   the quickpick). Looking only at what S2 shipped, can S3 reuse the
   helper as-is, or are there gaps in the helper's API that S3 will
   bump into? Specifically:
   - The helper's `manual` mode expects payload to carry
     `provider` + `model` + `effort.{normalized,native,thinking}`.
     The S3 quickpick will compose these from user picks. Is the
     payload contract obvious enough that the quickpick TypeScript
     code can construct it without surprises?
   - The helper's `--force-override` flag bypasses the precedence
     check. S3's manual-override is supposed to show a "Override
     existing live signal from <writer>?" confirmation before
     proceeding. The helper writes the writer name into
     `~/.dabbler/current-orchestrator.json` (`writer` field), so the
     quickpick can read it to populate the confirmation dialog.
     Is that the right architecture, or should the helper itself
     produce the confirmation prompt? (Probably the former — UI
     belongs in the extension, not the helper.)
   - The helper's `configured-default` mode is what Codex's watcher
     will call. Does the helper handle a Codex payload shape
     (`{provider: "openai", model: "gpt-5-codex", effort:
     {normalized: "high", native: "high"}}`) correctly today, or
     will S3 need to extend the helper?

**Q8. Overall.**
   Is Set 029 Session 2 ready to close out? If not, the smallest
   concrete change to get it there. Specifically:
   - Any must-fix items in the marker writer that would silently
     corrupt the marker file or skip writes incorrectly?
   - Any must-fix items in the provider that would render the wrong
     visual treatment for a signalKind?
   - Any must-fix items in the installer that would break the
     `~/.claude/settings.json` on re-run?

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.
