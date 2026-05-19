# Set 029: Orchestrator Model & Effort Indicator Gauges

**Status:** In progress (5 of 6 sessions complete; mid-set pivot 2026-05-18 reshaped 4 → 6 sessions)
**Created:** 2026-05-17
**Cost so far:** $1.686 (S1 $0.845 + S2 $0.578 + mid-set custom-tree-pivot audit $0.022 Gemini Pro + S3 $0.085 Gemini Pro × 3 rounds + mid-set S4 implementation audit $0.025 Gemini Pro + S4 verification $0.053 Gemini Pro × 2 rounds + S5 verification $0.035 Gemini Pro × 2 rounds; GPT-5.4 via manual paste = $0.00).
**Forecast remaining:** $0.05–$0.20 across S6 verification.
**NTE ceiling:** $5.00 (operator-confirmed 2026-05-18 at S1 resume); ~$3.31 headroom remains.

---

## Context

The operator routinely switches the orchestrator model down for cheap
tasks (Claude Haiku for a quick rename) and sometimes forgets to
switch back up to Opus before starting substantive work. The failure
mode is silent: a new session opens on a lower-tier model, output
quality is wrong, and the session has to be aborted or salvaged.

Set 029 adds an always-on visual signal — two semi-circle CSS gauges
pinned above the Session Set Explorer — that makes the current
orchestrator model and effort level glance-readable at all times.

v1 supports all four of the operator's orchestrator surfaces (Claude
Code, Gemini Code Assist Agent, Codex, GitHub Copilot) with
auto-detection where viable and a manual-override quickpick command
as the universal fallback.

---

## Session 1: cross-provider design audit (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after three verification rounds + one cross-
engine consensus call. All 12 Round-A must-fix items addressed in
Round B; incidental drift surfaced in Rounds B and C closed
mechanically against locked D1–D10 / Q1–Q6 decisions.

**Deliverables:**

- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/audit-summary.md`
  (post-Round-C, all locked-design decisions captured)
- `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
  (post-Round-C, drift-free, Goal state aligned with D1–D10 + Q1–Q6)
- `session-reviews/session-001/` (Rounds A/B/C + consensus call
  scripts, prompts, raw responses, and session-001-review.md)

**Locked design decisions Session 2 implements verbatim:**

1. Marker schema v2 at `~/.dabbler/current-orchestrator.json`
   with `signalKind` (`current` | `configured-default` |
   `last-observed` | `manual`), `confidence`, `effort.signalKind`,
   `effort.confidence`, `effort.observedAt`, `stalenessMaxSec`
   (default 28800s = 8h).
2. Claude `SessionStart` hook (NOT Stop) writes the marker on
   session start; `UserPromptSubmit` hook (field-availability
   gated) writes effort updates on `/think*`.
3. Multi-writer precedence policy (`current` > `manual` >
   `last-observed` > `configured-default`) with read → re-read
   immediately before atomic rename → skip-if-weaker semantics.
   Manual-override quickpick has a force-override escape hatch.
4. Windows retry loop: 5 attempts at 50/200/600/1200ms backoff
   (~2050ms total ceiling).
5. Confidence-low producer rule: helper emits `confidence: "low"`
   + `model: "unknown"` on missing/null/unparseable payload.
6. Pre-implementation `/clear` dual-condition verification: only
   clobber `last-observed` on `/clear` if `/clear` both fires
   SessionStart AND resets effort.
7. Visual-treatment matrix: stripes are stale-only;
   `configured-default` = dashed rim + DEFAULT pill;
   `last-observed` = hollow rim + clock-icon overlay + time-elapsed
   sublabel; `manual` = solid + operator-icon overlay.
8. No `initialSize`; container height cannot be guaranteed
   (documented in CHANGELOG); Playwright screenshot assertions in
   clean profile only.

**Process notes worth surfacing:**

- The router-call waiver from S1 step 2 (no `route_audit.py`) is
  durably noted in spec.md so future maintainers don't expect that
  file.
- A new in-session-consensus class of router call was introduced
  this session per memory `feedback_prefer_ai_consensus_over_human_prompt`:
  design refinements get routed through GPT-5.4 + Gemini Pro before
  AskUserQuestion. Successfully rehearsed here; the formal
  `delegation.decision_consensus` config knob remains a candidate
  follow-on session set (see `docs/planning/delegation-consensus-config.md`).
- Round-A bundles should include the entire spec.md in future
  audit-then-spec sessions; Rounds B and C exposed pre-audit drift
  in regions not bundled in Round A. Cost-wise this is fine —
  session-verification at the gpt-5-4 rate handles full spec.md
  bundles for under $0.50.
- Round C cost $0.36 vs. typical p50 $0.13 due to gpt-5-4 emitting
  22k output tokens. Note for memory `feedback_split_large_verification_bundles`
  scope — output-token blowup can drive cost as much as input-token
  size.

**Cost breakdown:**

| Round | Tokens (in/out) | Cost | Verdict |
|---|---|---|---|
| Round A verification | 14,923 / 15,144 | $0.264 | REJECTED, 12 must-fix |
| Bucket-2 consensus (gpt-5-4 + gemini-pro) | 2,606+2,794 / 4,915+83 | $0.085 | Both engines accept direction |
| Round B verification | 17,043 / 6,333 | $0.138 | 12 ADDRESSED + 1 new |
| Round C verification | 10,660 / 22,077 | $0.358 | 1 ADDRESSED + 2 new mechanical |
| **Session 1 total** | — | **$0.845** | VERIFIED |

## Session 2: core webview + Claude detection + hook installer (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after three verification rounds (Round A + Round B + Round C confirmation). 5 must-fix items surfaced across A/B; all addressed; Round C confirmed 4/5 fully resolved and surfaced one residual race-window in the user-prompt-submit merge branch (re-read happened before tmp write rather than immediately before rename); tightened mechanically. Round-by-round finding count was 3→2→1 — convergence, not spiral per memory `feedback_verifier_spiral_recruit_codex`. No Round D.

**Deliverables (Claude-only v1 preview):**

- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts` (~395 LOC) — `WebviewViewProvider` for `dabblerOrchestratorIndicator`. Marker reader + FileSystemWatcher + 60s poll backstop + 50ms render debounce. Renders SVG semi-circle gauges with the audit-locked visual-treatment matrix (current/configured-default/last-observed/manual). Tooltip copy embeds confidence explicitly.
- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js` (~410 LOC after R-A/R-C tightenings) — shared marker writer. Four modes (session-start, user-prompt-submit, manual, configured-default). Multi-writer precedence with re-read-immediately-before-rename closing the TOCTOU window. 5-attempt retry loop at 50/200/600/1200ms backoff for Windows file-watcher contention. Confidence-low producer rule when SessionStart payload `.model` is missing/null/unparseable. Reused by Session 3 writers.
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts` (~170 LOC) — idempotent installer for SessionStart × 4 source matchers (startup/resume/clear/compact) + UserPromptSubmit hook in `~/.claude/settings.json`. Atomic write. Preserves foreign hooks verbatim.
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManualStub.ts` (~25 LOC) — stub for `dabbler.setOrchestrator`; surfaces a "coming in 0.14.3" dialog with one-click jump to the Claude installer until Session 3 lands the full quickpick.
- `tools/dabbler-ai-orchestration/src/commands/openOrchestratorWriterLog.ts` (~25 LOC) — opens `~/.dabbler/orchestrator-writer.log` for diagnosing skipped marker writes.
- `tools/dabbler-ai-orchestration/media/orchestrator-indicator/indicator.css` (~250 LOC after sizing+overlay revisions) — visual-treatment matrix CSS + responsive-wrap at <260px panel widths + stale-overlay pseudo-element painting at z-index 2 above the gauge artwork.
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts` — 8 Playwright scenarios (current Opus, Haiku, low-confidence, last-observed effort, configured-default, stale, empty-state, and helper-precedence non-Electron). All green.

**Pre-implementation verification (R7 dual-condition check):**

WebFetch against the official Claude Code hooks docs confirmed all three preconditions: `/clear` fires `SessionStart` with `source: "clear"` (matcher table); `/think*` are per-message escalations not session settings (so `/clear` is a fresh-session boundary semantically — R7 BOTH conditions TRUE); `UserPromptSubmit` payload includes the `prompt` field with full user-submitted text (so `/think*` prefix detection ships at full functionality without the Medium-only fallback). Design decision: SessionStart hook clobbers effort to Medium on ALL source values (startup/resume/clear/compact) — simpler than per-source branching and lagging-signal-resistant.

**Mid-S2 operator feedback (live, after first Playwright run):**

After seeing the rendered gauges, the operator flagged: (a) the Medium effort gauge's color arc was visually too low compared to the Model gauge — was at -120° (1/3 fill) while the Model gauge for Opus rendered at -30° (5/6 fill); (b) fonts + gauges needed to be ~40-50% bigger for legibility; (c) the layout needed to wrap responsively when the panel is narrow. Applied in-session: Medium effort needle re-centered to -90° (gauge midpoint, half-fill) with other levels redistributed; gauge SVG 70×38 → 100×54 (~43% bigger); font sizes bumped ~40-50%; container max-height 100 → 150px; responsive wrap at <260px. The audit-locked "≤100px hard constraint" in D3 is now superseded; documented with a superseding note in audit-summary.md and spec.md. Memory `gauges-sizing-followup` updated to reflect this is now SHIPPED, not pending. New CHANGELOG section "Mid-S2 sizing + responsive-wrap revision" added.

**Significant verifier findings + fixes:**

| Round | Finding | Fix |
|---|---|---|
| Round A Q2 | TOCTOU race in `attemptWriteWithPrecedence` — read-once-decide-write left a race window | Added re-read immediately before `renameSync`; skip with `weaker-than-existing-on-reread` reason if a stronger fresh marker raced ahead |
| Round A Q6 | UserPromptSubmit merge/bootstrap could clobber fresher SessionStart markers | Rewrote the merge branch to read latest snapshot inside the try block, immediately before `writeFileSync` + `renameSync` |
| Round A Q8 | Stale stripes used `background-image` on `.gauge-svg` which paints BEHIND the SVG content, not as a true overlay; also alpha was 18% vs. the audit's 50% target | Replaced with `.stale .gauge-cell::before` absolute-positioned at z-index 2 with `pointer-events: none` and 45% alpha |
| Round B Q1 | `renderLoaded` effort suffix branches (`(default)` / `(manual)`) keyed off `marker.signalKind` (top-level model signal) instead of `marker.effort.signalKind` | All three effort suffix branches now check `marker.effort.signalKind`; effort and model are independent axes per schema v2 |
| Round B Q4 | Gauge angle math used a `180 + needleAngleDeg` offset that inverted the y-axis, sending -90° DOWN instead of UP — all needle/fill endpoints were BELOW the visible viewBox | Removed the `180 +` offset; use angle directly. SVG's y-down axis naturally inverts sin behavior: `cy + radius * sin(-90°) = cy - radius` correctly places the endpoint at top-center. Also simplified `largeArc = 0` always (upper-semicircle arcs are always ≤180°) |
| Round C residual | The Round A Q6 fix re-read happened BEFORE the tmp-file write, not immediately before rename — partial fix | Tightened: `readExistingMarker()` now happens inside the try block immediately before `writeFileSync` + `renameSync`. Residual window matches `attemptWriteWithPrecedence`. |

**Process notes:**

- The Playwright iframe selector was broken in the initial spec — `iframe[title*="Orchestrator"]` doesn't match because VS Code wraps webview views in `iframe.webview` (no title) and the actual content lives in a PROGRAMMATIC child iframe added by the outer iframe's service-worker bootstrap (no `<iframe>` element in the outer DOM, so Playwright's `frameLocator` chains can't see it). Fix used the lower-level Frame API: `page.locator('iframe.webview').elementHandle()` → `contentFrame()` → `childFrames()`. Documented in the helper's comments + the activity log.
- Pre-existing `treeView.spec.ts` failures (2 of them) reproduce on clean master without S2 changes — unrelated.
- Pre-existing `notificationsSection.test.ts` + `configEditor-foundation.test.ts` failures in `npm run test:unit` also reproduce on master — unrelated Set-026/Set-030-era test issues, not regressions from S2.
- Spec drift correction: spec.md S2 step 8 said "0.13.17 → 0.13.18" (authored 2026-05-17, before Set 030 shipped its 0.14.x line); corrected to 0.14.1 → 0.14.2.
- The `tests/playwright/` path in spec.md S2 step 7 should be `src/test/playwright/` — aligned to the actual `playwright.config.ts` `testDir`. Spec is durably stale on the path; CHANGELOG documents the correction.

**Cost breakdown:**

| Round | Tokens (in/out) | Cost | Verdict |
|---|---|---|---|
| Round A verification (marker writer + CSS) | 9,255 / 8,607 | $0.152 | 3 must-fix |
| Round B verification (provider + installer) | 9,590 / 12,159 | $0.206 | 2 must-fix |
| Round C confirmation pass | 13,361 / 12,407 | $0.220 | 4/5 fully fixed, 1 residual; tightened |
| **Session 2 total** | — | **$0.578** | VERIFIED |

Bundle splitting per memory `feedback_split_large_verification_bundles`: full set of code was ~1170 LOC, split into A (~605 LOC) and B (~565 LOC) to stay under the 700-LOC ceiling. Round C re-bundled the full post-fix versions of all three high-leverage files.

## Mid-set pivot (2026-05-18) — custom-tree audit

Post-S2 polish surfaced a structural issue: the v0.14.2
`~/.dabbler/current-orchestrator.json` is a single global file. The
operator's three-parallel-window workflow (per memory
`project_consumer_repos`) means every window's SessionStart hook
clobbers the same marker — the most-recently-started session wins,
the others' gauges silently show wrong data.

An initial fix path (per-workspace markers hashed by workspace
folder path) was drafted at
[`docs/proposals/2026-05-18-per-workspace-orchestrator-markers/`](../../proposals/2026-05-18-per-workspace-orchestrator-markers/)
and reviewed by Gemini Pro + GPT-5.4 (manual paste). Mid-review
the operator and I concluded the underlying issue is the **identity
model**, not just the marker path. A second pivot proposal at
[`docs/proposals/2026-05-18-custom-tree-pivot/`](../../proposals/2026-05-18-custom-tree-pivot/)
re-routed the design through both reviewers.

**Reviewer verdicts converged on 7 of 10 questions; diverged on
3.** Operator decisions resolved the divergences (split S3 from
custom-tree work; fail-closed on ambiguous resolution; no
workspace orphan marker). Set 029 reshapes:

| New session | Goal | Status |
|---|---|---|
| S3 | Per-session-set identity (marker schema v3, walk-up resolver, `SessionSetsModel` extraction) | pending |
| S4 | Custom-tree pivot (webview-based Session Sets tree with embedded gauges) | pending, gated by own pre-session audit |
| S5 | Non-Claude detection + manual override (renumbered from old S3, content unchanged) | pending |
| S6 | Polish + README + Marketplace publish (renumbered from old S4, content unchanged) | pending |

The pivot itself shipped no code; spec.md was updated to reflect
the new structure. v0.14.2 stays the released-but-unpublished
state of the extension until S3 ships 0.15.0.

**Cost:** $0.022 (Gemini Pro consensus call; GPT-5.4 manual = $0.00).

## Session 3: per-session-set identity (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after three verification rounds (Round A
writer + schema doc VERIFIED clean; Round B reader + model + tests
3 MUST-FIX; Round C confirmation pass VERIFIED). All three Round-B
issues addressed and confirmed. No spiral per memory
`feedback_verifier_spiral_recruit_codex`.

**Verifier:** Gemini Pro for all three rounds — gpt-5-4 returned
429 on the OpenAI Responses endpoint twice (initial bundle attempt
at 101k chars + Round-A re-try at 37k chars), so the round-A
script was pinned to `model="gemini-pro"` to dodge the sticky rate
limit. Cross-provider verification satisfied: Claude orchestrator
+ Gemini Pro verifier.

**Deliverables (v0.15.0, breaking-within-v0.14.2-preview):**

- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
  (~613 LOC, rewritten) — marker schema v3 with top-level
  `sessionSetSlug` integrity field; walk-up resolver
  (`walkUpResolveSet(startCwd)`) replaces the hardcoded
  `~/.dabbler/current-orchestrator.json` path. Fail-closed posture:
  on zero / multiple in-progress sets or no reachable
  `docs/session-sets/`, skip the write and append a JSON entry
  (`reason`, `candidates`, `cwd`) to
  `~/.dabbler/orchestrator-writer.log`. Writer log stays global so
  one log captures every writer attempt across every set. The
  per-set `.dabbler/` directory gets a self-protecting `.gitignore`
  (`*\n!.gitignore\n`) dropped automatically on first create —
  consumer repos inherit untracked-marker behavior without any
  operator intervention. `mergeEffort()` re-stamps `sessionSetSlug`
  + `schemaVersion: 3` so a marker that survives a cross-set
  boundary converges on the right slug.
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  (~946 LOC, modified) — new `resolveActiveSet()` runs the same
  walk-up algorithm rooted at `workspaceFolders[0]`. Two watchers:
  state watcher on `docs/session-sets/*/session-state.json` for
  re-resolution on transition; per-set marker watcher rebound on
  resolution change. Slug-integrity check: marker whose
  `sessionSetSlug` doesn't match the resolved slug falls back to
  the empty-state CTA and logs to the
  "Dabbler Orchestrator Indicator" output channel.
- `tools/dabbler-ai-orchestration/src/providers/SessionSetsModel.ts`
  (~131 LOC, new) — data-layer extraction. Pulled `progressText`,
  `isCurrentSessionInFlight`, `iconUriFor`, `needsMigrationBadge`,
  `forceClosedBadge`, `modeBadge`, `touchedDate`, `uatBadge`,
  `bucketSets`, `sortBucket`, `ICON_FILES` out of
  `SessionSetsProvider.ts`. Both the current native tree (S3 ship)
  and the future custom webview tree (S4) consume the same model.
- `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`
  (~246 LOC, refactored) — collapsed to a thin VS Code adapter
  consuming `SessionSetsModel`. Re-exports the helper subset that
  callers (`cancelTreeView.test.ts`, `forceClosedBadge.test.ts`)
  still import from this module, so no upstream import surface
  broke. The Layer-2 test
  `src/test/suite/sessionSetsProvider.test.ts` was repointed to
  import directly from `SessionSetsModel` to track the canonical
  home.
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts`
  (~751 LOC, rewritten) — 12 scenarios total (A–L). All existing
  A–H scenarios updated to seed markers at the per-set path +
  call `startSession(seed, 1)` so the resolver finds an
  in-progress set. New: I (mismatched slug → empty state),
  J (helper ambiguous → write skipped + log), K (helper happy
  path verifies schema-v3 + slug + `.gitignore` self-protect),
  L (helper outside `docs/session-sets/` → skip).
- `docs/orchestrator-marker-schema.md` (new) — authoritative
  reference for the v3 marker shape, the walk-up resolver, the
  fail-closed posture, the self-protecting `.gitignore`, and the
  multi-writer precedence/retry policy.
- `.gitignore` — workspace-root patch adding
  `docs/session-sets/*/.dabbler/` as belt-and-suspenders.

**Significant verifier findings + fixes:**

| Round | Finding | Fix |
|---|---|---|
| Round A | All four Qs VERIFIED clean | — |
| Round B Q5 | Slug-validation truthiness bug: `marker.sessionSetSlug && ...` would let `null` / `""` through as "absent" rather than "mismatch" | Tightened to `marker.sessionSetSlug !== undefined && ...`. An empty-string slug now correctly fails the mismatch check and routes to empty state |
| Round B Q6 | `setUpStateWatcher()` is only called once at view resolution; if `workspaceFolders` is empty then, the watcher never binds and the 60s poll is the only signal for set transitions | Added `vscode.workspace.onDidChangeWorkspaceFolders` listener; on fire, disposes the stale state watcher and re-runs `setUpStateWatcher()` + `rebindMarkerWatcher()` + `scheduleRender()`. Listener is itself disposed by `tearDownWatchers()` |
| Round B Q8 | Spec says reader "logs" on slug mismatch, but the implementation fell silent | Added lazy `getOutputChannel()` creating "Dabbler Orchestrator Indicator" on first append; slug-mismatch branch in `computeState()` now logs timestamped line with both slugs + the resolved marker path |

**Deferred suggest item (Round B Q8):** end-to-end ambiguous
scenario launching VS Code with two in-progress sets. The
helper-side scenario J already exercises the writer's fail-closed
behavior; the reader's empty-state-on-unresolved is exercised by
G + I. An end-to-end ambiguous launch would add coverage but no
new failure-mode visibility; deferred to S4 alongside the custom
tree's empty-state rework.

**Process notes:**

- The 101k-char single-bundle verification round hit gpt-5-4 429
  immediately; even the 37k-char Round A pinned-to-gpt-5-4 was
  sticky on the same rate limit. Switching to Gemini Pro on Round A
  cleared in one attempt and stayed clean for B + C. Memory
  `feedback_split_large_verification_bundles` already documents the
  bundle-size threshold; the new observation is that the
  sticky-rate-limit window can outlast the failed call by minutes.
  Cross-provider escape (Gemini) was the right move.
- The Gemini Pro verifier surfaced concrete, code-grade fixes
  (specific lines + replacement code blocks) rather than the
  meta-commentary failure mode flagged in earlier memories. The
  three MUST-FIX items were all narrowly-scoped and converged
  cleanly on a single confirmation pass.
- The self-protecting `.gitignore` (`*\n!.gitignore\n`) inside each
  `.dabbler/` directory is a clean alternative to the
  "auto-patch the workspace-root `.gitignore`" path the spec
  originally called for. No `scripts/init-workflow.py` exists in
  this repo, so the writer-side drop became the canonical
  mechanism. Idempotent; harmless if already present; consumer
  repos inherit the protection on first marker write.

**Cost breakdown:**

| Round | Tokens (in/out) | Cost | Verdict |
|---|---|---|---|
| Round A verification (writer + schema doc) | 10,889 / 428 | $0.018 | VERIFIED clean |
| Round B verification (reader + model + provider + tests + CHANGELOG) | 27,264 / 1,296 | $0.047 | MUST-FIX (3) |
| Round C confirmation (post-fix reader only) | 13,129 / 333 | $0.020 | VERIFIED |
| **Session 3 total** | — | **$0.085** | VERIFIED |

Bundle splitting per memory `feedback_split_large_verification_bundles`:
the initial single-round 101k-char bundle hit gpt-5-4 429; split into
Round A (writer + doc, ~38k chars), Round B (reader + model +
provider + tests + CHANGELOG, ~95k chars), and Round C (post-fix
reader only, ~46k chars). Verifier pinned to `gemini-pro` after the
two gpt-5-4 429s. Cost came in well under the $0.10–$0.30 forecast.

## Session 4: custom-tree pivot (COMPLETE 2026-05-18)

**Verdict:** VERIFIED after two routed verification rounds (Gemini
Pro). Round A returned SUGGEST (1) on a minor `describeMarker`
purity item (calls `Date.now()` for the secondary effort-age
suffix); triaged as optional follow-up since the function is
otherwise pure and the integration round (B) was clean. Round B
returned VERIFIED on all 8 questions covering DOM structure / ARIA
semantics / monotonic version drop / command-dispatch allowlist /
indicator-action parity / suppression handshake / ambiguity banner
/ CSP & nonce hygiene.

**Deliverables (v0.16.0 packaged, not yet published):**

- `dabblerSessionSets` re-registered as a `WebviewViewProvider`.
  Native `TreeDataProvider` retired. Same view id, same view
  container, same `viewsWelcome` declaration.
- `dabblerOrchestratorIndicator` view retired in the same release.
  Gauges anchored in per-row accordions on the resolved in-progress
  set (per S4 Q11 = a; M8 indicator-action parity gate satisfied).
- ARIA-compliant tree: `role="tree"` / `role="group"` /
  `role="treeitem"` / `aria-level` / `aria-expanded` / `aria-selected`
  with roving tabindex and full WAI-ARIA 1.2 single-select tree
  kbd nav (↑/↓/Home/End/←/→/Enter/Space/Shift+F10/ContextMenu).
- Typed `ActionRegistry` replaces the 14 deleted
  `view/item/context` declarative rules from package.json (per S4 M2).
  Right-click + Shift+F10 + Context Menu key all open the same
  QuickPick from `ActionRegistry.applicableActions(set, supports)`.
- Per-set marker handling unchanged from S3 (walk-up resolver,
  fail-closed posture, multi-writer precedence, schema-v3 slug
  integrity check). On `multiple-in-progress-sets`, an ambiguity
  banner surfaces above the In Progress bucket with a link to the
  writer log (per S4 Q8 = a+c).
- Suppression state persisted in `workspaceState` under
  `dabbler.sessionSets.suppressedExpand`, keyed on
  `(slug, marker.updatedAt)` tuple per S4 M7 — manual collapse
  suppresses for the current occurrence only; the next SessionStart
  writes a fresh marker with a new updatedAt that naturally lifts
  the suppression.
- Versioned monotonic message protocol per S4 M3 — the webview
  client drops any render message with `version < currentVersion`
  to prevent stale watcher/polling repaints over fresh state.
- Defense-in-depth HTML escaping on every dynamic webview
  interpolation per S4 M5 — `escHtml()` host-side in
  `OrchestratorAccordion.ts`, repeated webview-side in
  `client.js` for the row name + description + welcome content.

**File changes:**

- **Created** (12 files):
  - `src/providers/CustomSessionSetsView.ts` (498 LOC)
  - `src/providers/OrchestratorAccordion.ts` (431 LOC, lifted from
    the retired indicator provider's render helpers)
  - `src/providers/MarkerWatchService.ts` (395 LOC, lifted from
    the retired indicator provider's lifecycle / watchers)
  - `src/providers/ActionRegistry.ts` (79 LOC)
  - `src/providers/suppressionState.ts` (61 LOC)
  - `src/types/sessionSetsWebviewProtocol.ts` (130 LOC)
  - `media/session-sets-tree/client.js` (~290 LOC)
  - `media/session-sets-tree/tree.css` (~280 LOC)
  - `src/test/suite/actionRegistry.test.ts` (~135 LOC)
  - `src/test/suite/suppressionState.test.ts` (~95 LOC)
  - `src/test/suite/markerWatchService.test.ts` (~95 LOC)
  - `src/test/playwright/session-sets-tree.spec.ts` (~165 LOC)
- **Modified** (6 files):
  - `src/extension.ts` (register `CustomSessionSetsView`; remove
    `SessionSetsProvider` + `OrchestratorIndicatorProvider`)
  - `package.json` (view type → webview; delete indicator view
    entry + 14 `view/item/context` entries; version 0.15.0 →
    0.16.0)
  - `src/test/suite/forceClosedBadge.test.ts` (repoint import to
    `SessionSetsModel`)
  - `src/test/playwright/loading-state.spec.ts` (webview iframe
    selector)
  - `src/test/playwright/migration-cta.spec.ts` (FrameLocator type
    + webview iframe path)
  - `src/test/playwright/electronLaunch.ts`
    (`openSessionSetsView` returns a FrameLocator into the
    two-level webview iframe stack)
  - `tools/dabbler-ai-orchestration/CHANGELOG.md` (`[0.16.0]` entry)
- **Deleted** (4 source files + entire `src/test/suite/e2e/`
  directory):
  - `src/providers/SessionSetsProvider.ts` (246 LOC)
  - `src/providers/orchestratorIndicatorProvider.ts` (998 LOC)
  - `src/test/playwright/orchestrator-indicator.spec.ts` (751 LOC)
  - `src/test/playwright/treeView.spec.ts` (265 LOC)
  - `src/test/suite/cancelTreeView.test.ts` + `src/test/suite/e2e/`
    (TreeView-specific @vscode/test-electron tests — mechanism
    obsolete with pivot; bucketing/sort invariants covered by
    `sessionSetsProvider.test.ts` already repointed to
    `SessionSetsModel` in S3).

**Net code:** ~+2654 LOC new code, ~-2260 LOC deleted, leaving the
extension surface ~+400 LOC overall with substantially better
separation of concerns (3 focused provider files where 1 998-LOC
file existed, plus the dedicated ActionRegistry + suppressionState +
typed protocol modules that didn't exist before).

**Layer-2 unit-test results:**

`npm run test:unit` — **369 passing, 2 pre-existing failures**
(`configEditor-foundation` ViewColumn stub gap,
`notificationsSection` HTML assertion — both predate S4). S4's 26
new tests all green.

**TypeScript compile:**

`npx tsc --noEmit` — clean. No errors, no warnings.

**Cost:**

- Pre-session audit (mid-set, captured earlier): $0.025 Gemini Pro
- Round A verification: $0.027 Gemini Pro
- Round B verification: $0.026 Gemini Pro
- **Session 4 total: $0.078** — well under the $0.20–$0.60 spec
  forecast. Two rounds converged cleanly without must-fix items
  triggering a Round C.

**Open follow-ups (not S4 ship blockers):**

1. `describeMarker` `Date.now()` purity (Round A SUGGEST) — pass
   `effortAgeSec` into the function instead of computing inline.
   ~10 LOC; suggested for hygiene PR or S5/S6 fold-in.
2. Type-ahead search in the tree (Gemini M10 from S4 audit) —
   deferred to v1.1; `// TODO:` marker in `client.js` already
   placed.
3. Inline overflow button for row actions (GPT-5.4 Q6 rec) —
   optional v1.1 if right-click-only discovery cost materializes.
4. Visual freshness cue beyond "updated Xs ago" — defer until
   cross-window confusion surfaces in real use.

## Session 5: Non-Claude provider detection + manual override (v0.17.0)

**Goal:** Add detection paths for non-Claude orchestrators per the
locked S1 audit resolutions. Codex auto-detect via config-watcher;
Gemini Code Assist + GitHub Copilot manual-only (no documented
persisted state); universal manual-override quickpick with MRU,
multi-step flow, hotkey args, force-override confirmation; smart
empty-state CTA that picks the install/preset link based on what's
actually installed locally.

**Creates:**

- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts` (213 LOC)
  — Codex `~/.codex/config.toml` watcher. Parses top-level `model` and
  `model_reasoning_effort`, dispatches a `configured-default`
  (medium-confidence) marker write via the shared helper. Debounces
  filesystem events to one dispatch per 500 ms quiet window.
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts`
  (533 LOC) — universal manual-override quickpick implementation.
  Replaces the S2 stub. MRU at `~/.dabbler/orchestrator-mru.json`
  (cap 8); multi-step provider→model→effort→thinking flow;
  hotkey-bindable `{provider, model, effort, thinking}` args;
  force-override modal confirmation when an existing `current`-
  precedence marker is fresh; delegates marker writes to the shared
  helper via `--mode manual`.
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
  (27 LOC) — opens the manual-override quickpick with
  `prefillProvider: "google"`. No actual hook installed.
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
  (24 LOC) — same shape with `prefillProvider: "github"`.
- `tools/dabbler-ai-orchestration/src/providers/detectOrchestrators.ts`
  (136 LOC) — smart empty-state CTA helper. Detects installed
  orchestrators (Claude Code via `~/.claude/`, Codex via
  `~/.codex/`, Gemini Code Assist + GitHub Copilot via
  `vscode.extensions.getExtension`). Picks the surfaced CTA by MRU
  bias when available, else priority order.
- `src/test/suite/codexConfigParser.test.ts` (10 tests) — TOML
  extractor.
- `src/test/suite/setOrchestratorManual.test.ts` (8 tests) — MRU
  read/write/dedupe/cap + formatTupleLabel.
- `src/test/suite/detectOrchestrators.test.ts` (8 tests) —
  detection priority + MRU-bias + CTA selection.

**Touches:**

- `tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
  — `RenderState.empty` variant carries optional `cta: EmptyCta`.
  `renderAccordionEmpty(cta?)` substitutes the passed CTA's command
  ID + label into the "No signal — <label>" link. Falls back to the
  Claude installer when no CTA passed (preserves v0.16.0 behavior).
- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
  — Allowlist expanded with `dabbler.installOrchestratorHook.gemini`
  and `.copilot`. `scheduleRender()` computes the CTA via
  `pickEmptyStateCta()` when the resolved set's marker is empty and
  passes it into the render state.
- `tools/dabbler-ai-orchestration/src/extension.ts` — registers
  three new commands (Gemini installer-shim, Copilot installer-shim,
  real manual-override) and activates the Codex config-watcher at
  extension start. Retires the S2 stub registration.
- `tools/dabbler-ai-orchestration/media/session-sets-tree/client.js`
  — `[data-command]` click handler reads optional
  `data-command-args` attribute, JSON-parses to an array, forwards
  as the `executeCommand` postMessage `args` field. JSON parse
  errors fall back to `args: undefined`.
- `tools/dabbler-ai-orchestration/src/test/vscode-stub.js` —
  Added `vscode.extensions.getExtension` with a mutable
  `__installedExtensions` set so detection unit tests can simulate
  presence/absence. Also added `vscode.env.clipboard.writeText`.
- `tools/dabbler-ai-orchestration/src/test/playwright/electronLaunch.ts`
  — `seedOrchestratorMarker(handle, overrides)` helper writes a
  per-set marker JSON for visual-state Playwright tests.
- `tools/dabbler-ai-orchestration/src/test/playwright/session-sets-tree.spec.ts`
  — 3 new scenarios: configured-default Codex visual
  (`signal-configured-default` class), manual Gemini visual
  (`signal-manual` class), empty-state CTA fallback ("No signal —"
  + `acc-link` button).
- `tools/dabbler-ai-orchestration/package.json` — 2 new command
  contributes (Gemini installer-shim, Copilot installer-shim);
  version 0.16.0 → 0.17.0.
- `tools/dabbler-ai-orchestration/CHANGELOG.md` — full 0.17.0 entry.
- `CLAUDE.md` — Extension versioning section rewritten to reflect
  the v0.14.2 → v0.17.0 walk through Set 029.

**Retired:**

- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManualStub.ts`
  (32 LOC) — S2 placeholder superseded by the real implementation.

**Net code:** ~+1,290 LOC additions, ~-44 LOC deletions.

**Layer-2 unit-test results:**

`npm run test:unit` — **397 passing, 2 pre-existing failures**
(`configEditor-foundation` ViewColumn stub gap,
`notificationsSection` HTML assertion — both predate S4). S5's 21
new tests all green.

**TypeScript compile:**

`npx tsc --noEmit` — clean. No errors, no warnings.

**Cost:**

- Round A verification: $0.019 Gemini Pro
- Round B verification: $0.016 Gemini Pro
- **Session 5 total: $0.035** — well under the $0.10–$0.30 spec
  forecast. Both rounds converged cleanly without must-fix items.

**Open follow-ups (not S5 ship blockers):**

1. MRU file race condition (Round B SUGGEST) — `pushMru` is a
   read-modify-write without serialization. Realistic UI-bound
   concurrency window is essentially zero. Revisit if programmatic
   callers are ever wired.
2. Sync fs in `readCurrentMarkerForWorkspace` (Round B SUGGEST) —
   refactor to `fs/promises` if/when the helper grows a callable
   API. Not a hot path.
3. **S6 scope addition (operator request 2026-05-19 mid-S5):**
   HTML-preview iteration cycle for Session Set Explorer styling.
   Mirrors the v0.14.2 gauge-styling iteration that ran for ~11
   rounds. Captured as Step 0 in spec.md S6; memory
   `project_029_s6_html_preview_iteration` records the rationale.
4. New visual treatments the S5 spec mentioned (DEFAULT pill badge
   for configured-default, operator-icon overlay for manual) — the
   marker emits the right `signalKind` and the existing dashed-rim
   treatment is in place, but the pill/operator-icon polish belongs
   in the S6 HTML-preview iteration.

## Session 6: UI affordance polish + Set 030 audit-input scaffolding (v0.17.1)

**Goal:** finalize Session 5's multi-provider work for Marketplace
publish via polish + README + CHANGELOG + CLAUDE.md updates. The
session expanded mid-flight to include a cross-provider consensus
call on the orchestrator-tracking architecture, which deferred the
architecture migration to a follow-on session set
(`030-orchestrator-checkout-checkin`) and reduced this session's
ship scope to UI affordance polish only.

### What shipped (source changes)

**Relegate `dabbler.setOrchestrator` + `dabbler.openOrchestratorWriterLog`
from accordion-body buttons to right-click context menu +
Command Palette.** Per the cross-provider consensus call run
mid-session (GPT-5.4 round 2 Q4 must-fix: "do not leave a
prominently visible button with a label that implies stronger
behavior than it actually has"). The accordion body is no longer
cluttered with two buttons that don't directly affect the
surrounding gauges. Both commands remain available via Command
Palette under the "Dabbler" category. `ActionRegistry` now has 16
row actions (was 14): `dabbler.setOrchestrator` at group 501
surfaces only on in-progress rows; `dabbler.openOrchestratorWriterLog`
at group 502 is always available as a diagnostic. Source files
touched: `src/providers/ActionRegistry.ts`,
`src/providers/OrchestratorAccordion.ts` (removed `acc-actions` HTML
from both `renderAccordionEmpty` and `renderAccordionLoaded`),
`media/session-sets-tree/tree.css` (removed dead `.acc-actions` +
`.acc-action` rules), `src/test/suite/actionRegistry.test.ts`
(updated 14→16 + new applicability test).

**`readCurrentMarkerForWorkspace` async refactor** per S5 Round-B
Gemini SUGGEST #2. Converted from sync `fs.statSync` /
`fs.readdirSync` / `fs.readFileSync` to `fs.promises.*` + `await`.
Caller (`maybeConfirmForceOverride`) was already async; the await
chain is well-contained. Function is non-exported so no public
surface change. Source: `src/commands/setOrchestratorManual.ts`.

**Documentation rolls forward.** `CHANGELOG.md` v0.17.1 entry,
`package.json` + `package-lock.json` version bump 0.17.0 → 0.17.1,
`CLAUDE.md` extension-versioning subsection extended with the
v0.17.1 walk + Set 030 pointer, extension `README.md` Other-features
bullet added describing the orchestrator indicator + the right-click
affordance.

### What did NOT ship (deferred)

**Check-out / check-in architecture migration.** Mid-session
consensus call (Gemini Pro round 1 + GPT-5.4 rounds 1 & 2 via
manual paste after OpenAI 429 ×2) endorsed the direction but
surfaced three High items + two open questions that warrant a full
audit-then-spec cycle. Pre-audit artifacts preserved at
`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`:
`proposal.md`, `proposal-addendum.md`, `consensus-gemini-pro.{txt,
json}`, `consensus-gpt-5-4.txt` (round 1), `consensus-gpt-5-4-round-2.txt`,
plus a `README.md` capturing the decision trail + must-resolve items
for the follow-on set's audit cycle.

**Multi-set rendering** and **ambiguity-banner removal** are coupled
to the resolver refactor required by the architecture migration —
they ship together in the follow-on set, not piecemeal.

**HTML-preview styling iteration** (spec Step 0). Operator decision
mid-session: defer to post-Set-030 when multi-set rendering is real
and the iteration can include actual two-in-progress scenarios.
Round 1 + 2 of the preview are preserved at
`docs/proposals/2026-05-19-explorer-styling/preview.html` as
historical reference.

**`pushMru` MRU file race fix** from S5 Round-B SUGGEST #1. Analysis
found the proposed promise-chain mutex would target a race that
doesn't exist in the current sync code (the in-process race claim
was for the *async* version of the function; cross-process races on
the file need file-level locking, which the proposed fix doesn't
provide). Folded into the Set 030 module rewrite where the surface
changes anyway.

**Cross-repo notification one-liners** (spec Step 5). v0.17.1
doesn't materially change consumer-repo workflows — the buttons
moved but remain accessible. The cross-repo notifications wait for
the Set 030 architecture migration which DOES materially change
workflow (check-in becomes mandatory on close, multi-orchestrator
queueing surfaces).

**README screenshot.** Operator decision: defer the screenshot to
post-Set-030 so the screenshot can capture multi-in-progress
rendering. Bullet added without screenshot for v0.17.1.

### Round A verification

`session-reviews/session-006/verify-result-round-a.{txt,json}`.
Verifier: gemini-pro (S3/S4/S5 pin). Coverage:

- Q1 ActionRegistry correctness — **VERIFIED** (when predicates
  correct, group-5xx ordering deterministic, test updates match)
- Q2 OrchestratorAccordion HTML cleanup — **VERIFIED** (acc-actions
  cleanly removed from both states; surrounding HTML still valid;
  acc-link + model-sections preserved)
- Q3 Dead-CSS removal in tree.css — **VERIFIED** (acc-actions +
  acc-action removed cleanly; adjacent acc-link rule preserved)
- Q4 readCurrentMarkerForWorkspace async correctness — **VERIFIED**
  (sync→async conversion correct; control flow preserved; caller
  awaits)
- Q5 Test correctness — **VERIFIED** (16-action assertion correct;
  new applicability test covers the state matrix)
- Q6 Anything else risky — **SUGGEST** (`.gitattributes` for LF/CRLF
  consistency; environment-wide change deferred to operator
  decision, not a ship blocker)

No must-fix items; no Round B needed.

### Layer-2 unit-test results

`npm run test:unit` — **398 passing, 2 pre-existing failures**
(`configEditor-foundation` ViewColumn stub gap,
`notificationsSection` HTML assertion — both predate S6). The new
ActionRegistry test passes. Compile is clean.

### Cost

- Architecture-decision consensus call: $0.015 (Gemini Pro round 1)
  + $0.000 (GPT-5.4 rounds 1 & 2 via manual paste after 429 ×2)
- Round A verification: $0.012 (Gemini Pro)
- **Session 6 total: $0.027** — well within the $0.05–$0.15 spec
  forecast (S6 was the cheapest session in Set 029).

### Open follow-ups (queued, not blockers)

1. **Set 030 audit cycle** opens against the artifacts at
   `docs/proposals/2026-05-19-orchestrator-tracking-architecture/`.
   Three Highs + two open questions captured in that directory's
   README.md as must-resolve items.
2. **`.gitattributes`** with `* text=auto eol=lf` for LF/CRLF
   consistency (gemini-pro Round-A SUGGEST). Environment-wide change;
   operator decides separately.
3. **README + repo-root screenshot** refresh post-Set-030 when
   multi-set rendering ships.

---

## Final cost summary

| Session | Forecast | Actual | Notes |
|---|---|---|---|
| S1 (design audit) | $0.30–$0.80 | ~$0.85 | 3 verification rounds — successive bundles surfaced pre-audit drift, all converged |
| Custom-tree pivot mid-set audit | — | $0.022 | Gemini Pro consensus; GPT manual paste $0.00 |
| S2 (Claude-only ship) | $0.20–$0.60 | ~$0.58 | Rounds A+B+C |
| Custom-tree impl mid-set audit | — | $0.025 | Gemini Pro consensus; GPT manual paste $0.00 |
| S3 (per-set identity) | $0.05–$0.20 | $0.085 | Gemini-only ×3 rounds |
| S4 (custom-tree pivot) | $0.20–$0.60 | $0.078 | Two rounds, no Round C needed |
| S5 (multi-provider) | $0.10–$0.30 | $0.035 | Two rounds, no must-fix |
| S6 (UI polish) | $0.05–$0.15 | $0.027 | Architecture-consensus + verification |
| **Set 029 total** | **$1.15–$1.75** (revised at S1 resume) | **~$1.70** | At the top of the revised range; architecture-consensus mid-session pushed S6 up but stayed under cap |

The architecture-consensus call ($0.015 routed + $0.000 manual paste)
was a one-time mid-session spend that produced the audit-input
artifacts for Set 030, avoiding a separate audit-only session set
with its own router spend. Net positive on cost discipline.

---

## Final cost summary

(populated after Session 6 close-out)
