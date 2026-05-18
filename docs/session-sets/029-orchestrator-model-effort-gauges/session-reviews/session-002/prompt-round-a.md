# Session 2 verification — Round A (marker writer + CSS visual matrix)

## Context

Set 029 ships a VS Code webview view pinned above the Dabbler Session
Set Explorer showing the current orchestrator's **model** and **effort
level** as two side-by-side semi-circle CSS gauges. Operator-facing
failure mode being eliminated: a session silently starts on a lower-
tier model after the operator dialed down for a cheap task.

Session 1 (the cross-provider design audit) locked the design — Q1–Q6,
five showstoppers S1–S5, the marker schema v2 with `signalKind` +
`confidence`, the visual-treatment matrix REVISED 2026-05-18, the
multi-writer precedence policy, the Windows-aware retry loop (5
attempts at 50/200/600/1200ms backoff), the confidence-low producer
rule, and R7 (the `/clear`-vs-`SessionStart` dual-condition check).
Pre-implementation verification 2026-05-18 confirmed via the official
Claude Code hooks docs that `/clear` fires `SessionStart` with
`source: "clear"` AND `/think*` are per-message escalations (not
session settings) — both R7 conditions TRUE, so the SessionStart hook
clobbers `effort` to Medium on every source.

Session 2 ships the Claude path end-to-end. This is **Round A of two**
— focused on the data layer (the marker writer helper) and the visual
matrix (the CSS). Round B covers the provider rendering + the hook
installer. Splitting per memory `feedback_split_large_verification_bundles`
to stay under the 700 LOC bundle ceiling.

## What you're being asked to verify in Round A

1. **`scripts/write-orchestrator-marker.js`** (~390 LOC) — the shared
   marker writer reused by Session 3. All four modes: `session-start`,
   `user-prompt-submit`, `manual`, `configured-default`. Multi-writer
   precedence, retry loop, confidence-low producer, atomic write,
   effort-merge for `/think*`.

2. **`media/orchestrator-indicator/indicator.css`** (~215 LOC) — the
   CSS encoding the visual-treatment matrix per signalKind. Includes
   the operator-revised 2026-05-18 sizing (gauges 100×54, fonts ~40-
   50% bigger than original, container 150px) and the responsive
   wrap (panels <260px wrap second gauge below first).

The locked design lives in `audit-summary.md` (referenced; not
inlined). Spec deltas are in spec.md Session 2 step list. The
operator-feedback-driven mid-S2 sizing revision is documented in
CHANGELOG and in memory `gauges-sizing-followup`.

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Marker writer faithfulness — precedence policy.**
   `attemptWriteWithPrecedence` reads existing marker, checks if it's
   stale, then compares signalKind precedence:
   - `PRECEDENCE = ["current", "manual", "last-observed", "configured-default"]` — lower index = stronger
   - Skip condition: `proposedRank > existingRank` (proposed is weaker)
   - On skip, append to `~/.dabbler/orchestrator-writer.log`
   - Stale signals (>`stalenessMaxSec`) never block fresh writes
   Verify the inequality direction and the precedence ordering. Is
   `current > manual > last-observed > configured-default` correctly
   implemented?

**Q2. Marker writer faithfulness — TOCTOU race window.**
   The audit prescribed "re-read immediately before atomic rename"
   to close the time-of-check/time-of-use race. The current
   implementation reads existing marker inside
   `attemptWriteWithPrecedence` ONCE and then writes — there's no
   second read between "decide to proceed" and "rename". Is the race
   window left open? If so, is the loss of safety material in
   practice given the retry loop?

**Q3. Marker writer faithfulness — retry loop math.**
   `RETRY_BACKOFFS_MS = [50, 200, 600, 1200]` (4 entries), and
   `runWithRetries` iterates `attempt = 0` to
   `RETRY_BACKOFFS_MS.length` inclusive (= 5 iterations: 0,1,2,3,4).
   The sleep happens AFTER attempts 0,1,2,3 (4 sleeps before the
   final attempt 4 runs). Total ceiling = 50+200+600+1200 = 2050ms.
   Verify: this matches the locked design "5 attempts = initial +
   4 retries, 50/200/600/1200ms backoff between attempts, ~2050ms
   total".

**Q4. Marker writer faithfulness — confidence-low producer rule.**
   In `buildMarker`, when `args.mode === "session-start"` and
   `modelMissing` is truthy:
   ```js
   const modelMissing = !model || typeof model !== "string" ||
                        model.trim() === "" || /^unknown$/i.test(model);
   if (args.mode === "session-start" && modelMissing) {
     confidence = "low";
     model = "unknown";
   }
   ```
   Does this match the locked rule "if the SessionStart hook
   payload's `.model` is missing, null, or unparseable, emit
   `confidence: low` + `model: unknown` + `modelDisplayName: Claude
   (model unknown)`"? The display name is derived via
   `deriveModelDisplayName("anthropic", "unknown")` which falls
   through to the `if (!model || model === "unknown")` branch
   returning "Claude (model unknown)". Cross-check the conditional
   ordering — does the modelMissing check trigger BEFORE `model =
   "unknown"`, so the regex `/^unknown$/i.test(model)` evaluates the
   ORIGINAL payload model? (Yes, per the code structure — but verify.)

**Q5. Marker writer faithfulness — effort reset on SessionStart.**
   Per R7 verification PASSED 2026-05-18 (both conditions TRUE), the
   SessionStart hook should clobber `effort` to Medium on every
   source value. The implementation hard-codes for
   `mode === "session-start"`:
   ```js
   effort = {
     normalized: "medium",
     native: "default",
     thinking: false,
     signalKind: "current",
     confidence: confidence,  // mirrors the model confidence
   };
   ```
   Faithful? Note: this discards any payload-provided `effort`
   sub-object on SessionStart. Is this the right behavior, or should
   the SessionStart hook permit operators to inject effort via the
   payload?

**Q6. Marker writer faithfulness — user-prompt-submit merge-effort path.**
   When mode is `user-prompt-submit`:
   - Detects `/think` / `/megathink` / `/ultrathink` prefix in
     `payload.prompt`; on no match, exits cleanly with no write
     (correct — non-`/think*` prompts shouldn't churn the marker)
   - When marker exists, calls `mergeEffort` which preserves the
     top-level signal and updates ONLY `effort.*`
   - When marker doesn't exist, BOOTSTRAPS a Medium-default Claude
     marker via `buildMarker({...args, mode: "session-start"}, ...)`
     then OVERWRITES the bootstrap's effort with the just-detected
     `/think*` values
   - The merge path writes via `atomicWrite` directly (bypassing
     precedence check) on the rationale that effort.signalKind is
     a separate axis from top-level signalKind
   Is the bootstrap behavior correct? Scenarios to consider:
   (a) Operator installs the hook AFTER Claude has been running for
   hours — first `/think` invocation creates a low-confidence
   `model: "unknown"` Claude marker with the observed effort. Is
   this the right "honest default" or should it wait for the next
   SessionStart?
   (b) Concurrent: SessionStart fires while UserPromptSubmit is
   merging — the merge writes by-passing precedence. Could this
   stomp a fresher SessionStart's `confidence: "high"` marker with
   a `confidence: "low"` bootstrap? (The atomic rename should make
   either-write-wins safe, but: does it preserve invariants?)

**Q7. Marker writer faithfulness — atomic write semantics.**
   `atomicWrite` writes to `<target>.tmp.<pid>.<rand>` and renames
   onto target; cleanup of the tmp file on rename failure. Sleep
   helper uses `Atomics.wait(view, 0, 0, ms)` for synchronous sleep
   between retries (sub-second). Any concern with:
   - Cleanup race if two processes happen to pick the same random
     suffix (extremely unlikely but check)?
   - Atomic-write semantics on Windows where the target file is
     held open by VS Code's file watcher (the retry loop handles
     this, but does the helper close any file handles it might
     leak)?
   - The Atomics.wait pattern as a sync-sleep — Node's docs note
     this is the canonical sync-sleep pattern; any gotcha?

**Q8. CSS visual matrix correctness.**
   `indicator.css` encodes the visual-treatment matrix per signalKind.
   Inline assertions to verify against `audit-summary.md`:
   - `.signal-current` → solid fill (`stroke-opacity: 1`), solid rim
   - `.signal-configured-default` → ~85% opacity fill, dashed rim
     (`stroke-dasharray: 2 2`), + a `.default-pill` badge in HTML
   - `.signal-last-observed` → hollow rim + filled needle (the CSS
     has `.signal-last-observed .gauge-arc-fill { stroke-opacity: 0 }`
     so the fill arc disappears, and `.gauge-rim { stroke-opacity: 1;
     stroke-width: 1.5 }` so the rim is visibly thicker)
   - `.signal-manual` → solid fill + operator-icon overlay
   - `.stale` (signal-agnostic) → diagonal-stripe overlay at ~18%
     white opacity (NOT the audit's "50% opacity"). Is "18% opacity
     overlay over the underlying gauge fill" close enough to the
     audit's "50% opacity over the underlying signalKind treatment"
     for the practical visual outcome? The 18% figure is the opacity
     of the stripe color over transparency — the effective contrast
     is higher because the gauge under it has its own color.
   - **Stripes are stale-only** (REVISED 2026-05-18): the CSS has
     no `.signal-configured-default` rule that applies stripes.
     Verify by inspection.

**Q9. CSS sizing + responsive-wrap correctness.**
   The mid-S2 operator-feedback sizing revision:
   - Container `max-height: 150px` (was 100)
   - Gauge SVG `width: 100px; height: 54px` (was 70×38)
   - Stroke widths bumped 6→7 to match scaled gauges
   - Fonts: gauge-cell 10→14px, gauge-suffix 9→12px, last-updated
     9→12px, empty-state 11→14px, default-pill 8→10px, overlays
     11→14px, thinking LED 7→10px
   - Responsive wrap: `@media (max-width: 260px) { .gauges {
     grid-template-columns: 1fr; } }`
   Any issues? Specifically:
   - 260px threshold — at default font/scale, are two 100px gauges +
     gap actually fitting at 260px+, or is the threshold too low?
   - The `gauge-arc-bg` stroke-width 7 with a 28-radius arc on a
     70-unit viewBox — is the stroke proportionally OK after CSS
     scales the viewBox up to 100×54? (The viewBox is 0 0 70 38;
     stroke-width is in user-space units, so scaling the CSS width
     should NOT change the perceived stroke thickness — verify.)
   - Audit D3 said "≤100px hard constraint"; this ships at 150px.
     The CHANGELOG and memory `gauges-sizing-followup` document the
     drift explicitly. The audit-summary.md and spec.md still say
     "≤100px"; should those be updated, or is the CHANGELOG note
     sufficient?

**Q10. Overall Round A verdict.**
   Are the marker writer and CSS implementations ready to close out
   from a data/visual-correctness standpoint? Smallest concrete
   must-fix items, if any?

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.
