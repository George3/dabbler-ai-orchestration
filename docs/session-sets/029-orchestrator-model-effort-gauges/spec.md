# Orchestrator Model & Effort Indicator Gauges

> **Purpose:** Add an always-on, ≤100px-tall webview pinned above the
> Session Set Explorer that shows the current orchestrator's **model**
> and **effort level** as two side-by-side CSS gauges (semi-circle
> style per the dev.to gauge reference), so the operator never
> accidentally runs a fresh session on a lower-tier model after
> temporarily switching down for a cheap task. v1 supports four
> orchestrator surfaces: Claude Code, Gemini Code Assist Agent,
> Codex, and GitHub Copilot.
>
> **Session Set:** `docs/session-sets/029-orchestrator-model-effort-gauges/`
> **Created:** 2026-05-17
> **Workflow:** Full
> **Prerequisite:** None — operator-initiated UX feature.

---

## Session Set Configuration

```yaml
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
totalSessions: 6
```

> **Rationale on `effort: high`:** the hard part isn't the gauge; it's
> the cross-provider detection (Claude has hooks, others don't), and
> verifying the design holds up across four orchestrator surfaces
> before committing the implementation. The audit session (S1) plus
> the multi-provider detection session (S5, renumbered from S3 in the
> 2026-05-18 custom-tree pivot) are both Opus-class work.
>
> **Rationale on `requiresE2E: true`:** the visual gauge is a Layer 3
> Playwright Electron concern (rendered-text invariant: needle position
> + provider/model label + effort tier). The existing Playwright
> scaffolding at `tools/dabbler-ai-orchestration/tests/playwright/` is
> the right place to add the smoke. No new UAT (no operator-driven
> acceptance checklist needed for a status indicator).

---

## Problem statement

The operator routinely flips the orchestrator model down for cheap
tasks (e.g., Claude Haiku 4.5 for a quick file rename) and forgets
to flip it back to Opus 4.7 before starting substantive work. The
failure mode is silent: a new session opens on Haiku, the operator
doesn't notice until 15 minutes in when the output quality is wrong,
and the session has to be aborted or salvaged.

The cost of the failure is two-sided:

1. **Quality loss** — substantive work on a lower-tier model produces
   weaker output that often needs to be redone.
2. **Cost waste** — even a "cheap" model burns budget on work it
   can't complete well, plus the redo cost.

The fix is a passive, always-visible signal. The operator should be
able to glance at the activity bar and see, at a glance, "I'm on
Opus 4.7, effort=high, thinking=on" or "I'm on Haiku 4.5, effort=low,
thinking=off" — without having to ask the orchestrator, check the
model picker, or run a command.

## Goal state

When this set ships, the **Dabbler AI Orchestration** view container
has a new webview view, pinned above `dabblerSessionSets`, named
"Orchestrator". The view:

- Is ≤100px tall (operator's hard constraint)
- Renders two side-by-side semi-circle CSS gauges:
  - **Left gauge: Model.** Needle position encodes tier-within-provider:
    bottom-left zone = low-tier (Haiku / Flash / 4o-mini), middle zone =
    mid-tier (Sonnet / Flash 2.5 / 4o), top-right zone = flagship
    (Opus / Pro / o1 / Claude 5.x). Color polarity: red (low) → yellow
    (mid) → green (flagship). Sublabel under the gauge shows
    `<Provider> <Model>` text (e.g., "Claude Opus 4.7").
  - **Right gauge: Effort.** Five normalized levels (Low / Medium / High
    / Extra-High / Max) plus a binary "Thinking" indicator (LED dot
    next to the gauge). Color polarity: identical to the model gauge
    (red=low, green=max).
- Updates within ≤500ms of an orchestrator model/effort change
  (via filesystem watch on a marker file written by per-surface
  hooks, config-watcher shims, and the manual-override quickpick —
  only Claude actually installs a hook per audit-locked D8)
- Shows a graceful **"No signal — install hook"** CTA when the marker
  file is **missing** (per audit-locked Q6).
- Shows a **distinct stale state** when the marker exists but
  `updatedAt` is older than `stalenessMaxSec` (**default 8h** per
  audit-locked Q6 — was 1h pre-audit): diagonal-stripe overlay at
  50% opacity over the underlying signalKind treatment, plus
  "last updated Xh ago" annotation. **No install-hook CTA on
  stale** — only on missing.
- Exposes per-orchestrator-surface installer commands (per
  audit-locked D8):
  - **Claude Code:** `SessionStart` hook in `~/.claude/settings.json`
    (NOT `Stop` — Stop has no `model` field per audit S1).
  - **Codex:** auto-detected via `~/.codex/config.toml` filesystem
    watcher; no user-facing installer (signal is `configured-default`).
  - **Gemini Code Assist + GitHub Copilot:** "installer" command
    opens the manual-override quickpick with provider pre-selected
    (manual-only in v1 — no documented persisted state).
  - **Universal manual-override quickpick** (`Dabbler: Set Orchestrator
    Model & Effort`) as the always-available fallback.

---

## Decisions locked from operator dialogue (do not re-litigate)

| # | Decision | Locked value |
|---|---|---|
| D1 | Provider scope | **All four orchestrator surfaces**: Claude Code, Gemini Code Assist Agent, Codex, GitHub Copilot. v1 ships best-effort detection for each plus manual override as universal fallback. |
| D2 | Layout | **Two side-by-side semi-circle gauges** plus a binary "Thinking" LED beside the effort gauge. Three-gauge variants rejected; binary thinking-on/off doesn't warrant a third gauge. |
| D3 | Height budget | **≤150px total visible content** (revised 2026-05-18 during Set 029 Session 2 mid-S2 after on-device legibility feedback — was ≤100px in the original audit-locked text; the operator IS the one who set the original constraint AND the one who relaxed it). VS Code's standard view header (~22px) sits above this. Semi-circle gauges at ~100×54 fit comfortably; full-circle gauges do not. See CHANGELOG [0.14.2] §"Mid-S2 sizing + responsive-wrap revision" for the full revision detail. |
| D4 | Location | **New webview view (`dabblerOrchestratorIndicator`) pinned above `dabblerSessionSets` in the existing `dabblerSessionSetsContainer`.** Not a status-bar item (operator's framing was "panel at the top of Session Set Explorer"). |
| D5 | Color polarity | **SUPERSEDED 2026-05-18 round 2.** Original audit-locked value: "Red = low-tier / low-effort (warning state), green = flagship / max-effort (preferred state)." Revised after on-device operator review: gauge color is now **valence-neutral, drawn from the IBM 5-color colorblind-safe categorical palette** (`#648FFF` blue, `#785EF0` purple, `#DC267F` magenta, `#FE6100` orange, `#FFB000` yellow). Encoding is categorical (which level) not semantic (good/bad) — because Haiku is the right pick for cheap tasks, not a failure state. The "current orchestrator doesn't match recommendation" semantic moved from gauge color to a separate `≠ recommended` badge driven by ai-assignment.md. See CHANGELOG [0.14.2] §"Post-S2 polish — operator-feedback round 2". |
| D6 | Effort scale | **Five normalized levels** (Low / Medium / High / Extra-High / Max), mapping from provider-native scales as follows. Thinking on/off is a separate binary LED. |
| D7 | Marker file | **`~/.dabbler/current-orchestrator.json`** (global, user-home, single canonical file). Multi-writer: each provider's hook/shim writes the same file. Schema in Session 1 audit deliverable. |
| D8 | Hook installer | **Per-provider commands, but only Claude installs an actual hook** (per audit Q2/Q4/Q5): Claude = `SessionStart` hook in `~/.claude/settings.json` (NOT `Stop` — Stop has no `model` field per audit S1). Codex = `~/.codex/config.toml` watcher (no user-facing install; auto-activates). Gemini/Copilot = "installer" command opens the manual-override quickpick with provider preset (manual-only in v1). Universal manual-override (`Dabbler: Set Orchestrator Model & Effort`) supports MRU ordering + hotkey-bindable command args per audit E4. |
| D9 | Set structure | **Single set, audit-then-implement.** 6 sessions (REVISED 2026-05-18 via custom-tree-pivot audit): S1 design audit, S2 core webview + Claude path, **S3 per-session-set identity** (new), **S4 custom-tree pivot** (new, gated by its own pre-session audit), S5 non-Claude detection (renumbered from old S3), S6 polish + release (renumbered from old S4). See [`docs/proposals/2026-05-18-custom-tree-pivot/`](../../proposals/2026-05-18-custom-tree-pivot/) for the audit and packaging decisions that drove the renumbering. |
| D10 | Backwards compatibility | **No legacy behavior to preserve.** This is a net-new view. Empty/missing marker file = "No signal" empty state with install CTA. |

### Effort-level normalization table (locked)

| Normalized | Claude Code | Gemini Code Assist | Codex | GitHub Copilot |
|---|---|---|---|---|
| Low (0-25) | (no native control)\* | Low | Low (Intelligence) | Low (Thinking Effort) |
| Medium (26-50) | **default** | Medium | Medium | Medium |
| High (51-75) | `/think` (last-observed only) | High | High | High |
| Extra-High (76-90) | `/megathink` (last-observed only) | Extra-High | Extra-High | Extra-High |
| Max (91-100) | `/ultrathink` (last-observed only) | Max | (not exposed) | (not exposed) |

\* **REVISED per audit Q1/S2 (2026-05-17, refined 2026-05-18):**
Claude Code has no per-message effort slider; treating the most
recent `/think*` invocation as "current effort" would recreate the
false-confidence failure mode this feature is designed to prevent.
GPT-5.4 was explicit on this; Gemini Pro supported the broader
anti-lagging-signal concern. Locked design: effort gauge shows
**Medium (default)** for Claude sessions. If a `/think*` invocation
is observed during the session, the gauge displays the corresponding
tier with `signalKind: "last-observed"`, a time-elapsed sublabel
("(last /think Xm ago)"), a small clock-icon overlay on the gauge,
and hollow-rim + filled-needle visual treatment — three independent
"this is not live" cues, because hollow-rim alone proved too easy
to misread at small gauge sizes (per post-audit verifier finding
2026-05-18). Resets to Medium on `SessionStart` ONLY when both
conditions are verified in Session 2: (a) `/clear` fires
`SessionStart`, AND (b) `/clear` resets effort to Medium
semantically. Otherwise `last-observed` is preserved across
`/clear`; see **R7**.

### Thinking on/off (binary LED beside effort gauge)

| Provider | Source |
|---|---|
| Claude Code | "On" whenever any `/think*` was used in current session; else "Off". |
| Gemini Code Assist | "Thinking" toggle in the IDE panel. Direct read. |
| Codex | (no native concept) — LED hidden, only the Intelligence gauge shows. |
| GitHub Copilot | (no native concept) — LED hidden, only the Thinking Effort gauge shows. |

---

## Resolved design questions (from cross-provider audit 2026-05-17)

Cross-provider audit conducted 2026-05-17 with GPT-5.4 and Gemini Pro.
Full audit at
`docs/proposals/2026-05-17-model-effort-gauges-design-audit/audit-summary.md`.
Question numbering aligns with the audit proposal — the original spec
Q1 ("marker file schema") was rolled into D7's marker-schema
deliverable and is now captured in the audit-summary's "Marker file
schema (REVISED — locked)" section.

- **Q1 — Claude Code effort representation.** Locked: Medium default;
  recent `/think*` invocations shown as `signalKind: "last-observed"`
  with "(last /think Xm ago)" sublabel + clock-icon overlay (per
  refined 2026-05-18 visual treatment). Reset to Medium on
  `SessionStart` only when both `/clear`-fires-SessionStart and
  `/clear`-resets-effort are true (Session 2 verification step).
  → `audit-summary.md` §Q1.
- **Q2 — Gemini Code Assist detection.** Locked: manual-only for v1.
  No documented persisted state. → `audit-summary.md` §Q2.
- **Q3 — Codex detection.** Locked: read `~/.codex/config.toml` on
  activation + filesystem watcher. `signalKind: "configured-default"`.
  NOT a live signal. → `audit-summary.md` §Q3.
- **Q4 — GitHub Copilot detection.** Locked: manual-only for v1. Old
  settings keys deprecated, no current public key. →
  `audit-summary.md` §Q4.
- **Q5 — Claude Code hook protocol.** Locked: use `SessionStart`
  (NOT `Stop` — Stop has no `model` field). Mid-session `/model`
  changes NOT auto-detected in v1; manual override is the recovery
  path. → `audit-summary.md` §Q5.
- **Q6 — Stale-signal recovery UX.** Locked: 8h default
  (`stalenessMaxSec: 28800`); visually distinct stripe pattern for
  stale; always show "last updated" timestamp. →
  `audit-summary.md` §Q6.

### Showstoppers identified and mitigated

The audit surfaced five showstoppers, all resolved with concrete
mitigations now folded into the locked design:

- **S1**: Claude Stop hook has no `model` field → switched to
  `SessionStart` (Q5).
- **S2**: `/think*`-as-current-effort recreates the failure mode →
  Medium default + last-observed treatment (Q1).
- **S3**: `initialSize` is not a real VS Code contributes.views
  property → dropped; ordering/sizing best-effort + Playwright
  screenshot assertions in Session 2.
- **S4**: Stop hook timing makes gauge lagging → same fix as S1.
- **S5**: Windows atomic-write contention with file watcher →
  retry loop (**REVISED 2026-05-18**: 5 attempts = initial + 4
  retries at 50/200/600/1200ms backoff between attempts, ~2050ms
  total ceiling) in all marker writers (Session 2 / Session 5
  implementation; Session 5 renumbered from S3 in the 2026-05-18
  custom-tree pivot). Shared helper also implements multi-writer
  precedence read-check-rewrite (see audit-summary §"Multi-writer
  precedence").

### Marker schema bumped to v2

The audit introduced two new schema fields (`signalKind` and
`confidence`) with breaking semantics; canonical schema lives in
`audit-summary.md` "Marker file schema (REVISED — locked)" section.

---

## Sessions

### Session 1 of 6: Cross-provider design audit

**Goal:** Lock the six open design questions (Q1–Q6) via a
cross-provider verification call against the design proposal. Produce
an `audit-summary.md` whose verdicts feed Session 2's implementation.

**Steps:**

1. Author the design proposal as a single markdown doc at
   `docs/proposals/2026-05-17-model-effort-gauges-design-audit/proposal.md`,
   incorporating all 10 locked decisions and the 6 open questions.
   Include ASCII wireframes of the gauge layout (mirroring the spec's
   "Goal state" section).
2. **WAIVED 2026-05-18 (operator-confirmed):** the originally-planned
   `route_audit.py` helper was waived in favor of manual paste-and-
   collect against GPT-5.4 + Gemini Pro (per memory
   `feedback_ai_router_usage` — router is reserved for end-of-session
   verification). The raw reviewer responses are preserved at
   `gpt-5-4-result.json` and `gemini-pro-result.json`. There is no
   `route_audit.py` file; future maintainers should not expect one.
3. Capture each verifier's verdict as `gpt-5-4-result.json` and
   `gemini-pro-result.json`.
4. Synthesize verdicts into `audit-summary.md`, locking each of Q1–Q6
   with a concrete answer. Where the two verifiers disagree, flag
   the disagreement and pick a tiebreaker; document the tiebreaker
   rationale.
5. Update this spec.md's "Open design questions" section to mark each
   Q resolved with a one-line summary pointing at `audit-summary.md`.
   The full resolution lives in the summary doc — don't duplicate.
6. Verify Session 1 itself via a `task_type='session-verification'`
   call (gpt-5-4) before close-out. **REVISED 2026-05-18:** the
   verifier returned a punch list of must-fix items spanning
   doc-accuracy drift (Bucket 1) and design refinements (Bucket 2).
   Bucket 2 was routed through a cross-engine consensus call
   (`route_consensus.py`, gpt-5-4 + gemini-pro) per the new memory
   `feedback_prefer_ai_consensus_over_human_prompt`; both engines
   accepted the proposed direction with gpt-5-4 adding five
   tightening modifications. Fixes applied to `audit-summary.md`
   and this spec; **Round B verification** confirms the fixes before
   close-out.

**Creates:**
- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/proposal.md`
- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/gpt-5-4-result.json`
- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/gemini-pro-result.json`
- `docs/proposals/2026-05-17-model-effort-gauges-design-audit/audit-summary.md`
- `docs/session-sets/029-orchestrator-model-effort-gauges/session-reviews/session-001/`
  (prompt.md + prompt.rendered.md + route_verify.py + verify-result.json
  + route_consensus.py + consensus-gpt-5-4.json + consensus-gemini-pro.json
  + route_verify_round_b.py + verify-result-round-b.json
  + session-001-review.md)

**Touches:**
- `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
  (mark Q1–Q6 resolved, point at `audit-summary.md`)

**Ends with:** All six open design questions resolved, audit-summary
checked in, spec.md updated, session verification VERIFIED.

**Progress keys:** `session-001/proposal-drafted`, `session-001/audit-routed`,
`session-001/audit-summary-locked`, `session-001/spec-updated`,
`session-001/session-verified`

**Estimated cost:** $0.30–$0.80 (two audit calls + one verification
call; range based on `project_verification_cost_empirical` p50=$0.13,
p95=$1.82).

---

### Session 2 of 6: Core webview + Claude detection + hook installer

**Goal:** Ship the gauge UI end-to-end for the Claude Code surface.
The webview renders, the marker-file watcher fires, the Claude Code
`SessionStart` hook can be installed in one click, and the gauges
update on session start (and on `/think*` invocations if hook payload
exposes message text). Other surfaces show "No signal — install hook"
placeholder.

**Steps (REVISED per audit 2026-05-17):**

1. **Webview view registration.** Add `dabblerOrchestratorIndicator`
   to `package.json` `contributes.views.dabblerSessionSetsContainer`
   with `type: "webview"`. Order it **first** in the array. **Do NOT
   use `initialSize`** (per audit S3 — not a real VS Code contributes.views
   property). Ordering and sizing are best-effort; Playwright screenshot
   assertions in step 7 below catch regressions.
2. **Webview provider.** Implement
   `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
   as a `WebviewViewProvider`. HTML+CSS based on the dev.to gauge
   reference (https://dev.to/madsstoumann/how-to-create-gauges-in-css-3581)
   adapted to semi-circle form factor. Two gauges + thinking LED +
   provider/model label. Visual-treatment matrix for the four
   `signalKind` values (per audit-summary §"Visual treatment by
   signalKind" REVISED 2026-05-18 — stripes are stale-only):
   - `current`: solid fill, solid rim, no badge
   - `configured-default`: solid fill at ~85% opacity, **dashed
     rim**, **"DEFAULT" pill badge** below model name
   - `last-observed`: hollow rim + filled needle + **clock-icon
     overlay** (top-right ~12×12px) + "(last /think Xm ago)" suffix
   - `manual`: solid fill + small operator-icon overlay
   Tooltip copy embeds confidence explicitly per the matrix
   ("live signal (high confidence)", "configured default (medium
   confidence — does not track runtime changes)", etc.).
   Last-updated timestamp always visible (small text below sublabel).
3. **Marker-file reader and watcher.** Use `vscode.workspace.createFileSystemWatcher`
   with absolute path `~/.dabbler/current-orchestrator.json`. Marker
   schema v2 (with `signalKind` + `confidence` per audit). Stale state
   (>`stalenessMaxSec`, default 28800s = 8h): **diagonal-stripe
   overlay at ~50% opacity** over whatever the underlying signalKind
   treatment is (signal-agnostic) + "last updated Xh ago"
   annotation, no install-hook CTA. Stripes are stale-only —
   `configured-default` no longer uses stripes (it uses a dashed
   rim + DEFAULT pill instead) so the two states are now
   distinguishable at small gauge sizes.
4. **Empty state.** When marker file is missing, render solid grey
   gauges + "No signal — install hook" CTA. CTA fires the
   `Dabbler: Install Orchestrator Hook (Claude Code)` command.
5. **Claude Code SessionStart hook installer.** New command
   `dabbler.installOrchestratorHook.claudeCode`. Reads
   `~/.claude/settings.json` (or creates if missing), idempotently
   appends a `SessionStart` hook entry (**NOT `Stop`** — per audit S1
   Stop has no `model` field) that pipes the hook payload to a helper
   script which extracts `.model` and writes
   `~/.dabbler/current-orchestrator.json` with `signalKind: "current"`,
   `confidence: "high"`, `effort.normalized: "medium"`, `effort.signalKind: "current"`.
   **Confidence-low producer rule (REVISED 2026-05-18):** if the hook
   payload's `.model` is missing/null/unparseable, the helper writes
   `confidence: "low"` + `model: "unknown"` + `modelDisplayName:
   "Claude (model unknown)"`. The tooltip reflects this: "live signal
   (low confidence — hook payload missing model)".
   Helper script ships at
   `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`.
   **Marker writer implements retry loop** (REVISED 2026-05-18:
   **5 attempts = initial + 4 retries at 50/200/600/1200ms** backoff
   between attempts, ~2050ms total ceiling) per audit S5 REVISED to
   handle Windows file-lock contention with the VS Code file watcher.
   **Marker writer also implements multi-writer precedence** (per
   audit-summary §"Multi-writer precedence"): read existing target →
   compare `signalKind` precedence (`current` > `manual` >
   `last-observed` > `configured-default`) → re-read immediately
   before atomic rename → skip write if proposed signal is weaker
   than fresh existing signal; log skipped writes to
   `~/.dabbler/orchestrator-writer.log`. ~30 LOC shared helper;
   reused by Session 5 writers (renumbered from S3 in the 2026-05-18 custom-tree pivot).
   **Pre-implementation verification (NEW 2026-05-18):** verify
   whether Claude `/clear` (a) fires the `SessionStart` hook AND
   (b) resets effort to Medium semantically. The `SessionStart` hook
   only clobbers a fresh `last-observed` effort signal when BOTH
   are true. If either is false, preserve `last-observed` across
   `/clear`; document the asymmetry in CHANGELOG and as **R7**.
6. **Effort tracking (best-effort).** Also install a `UserPromptSubmit`
   hook that detects `/think*` invocations in user messages and updates
   the marker's `effort.normalized` with `effort.signalKind: "last-observed"`,
   `effort.native: "/think"` (or megathink/ultrathink), and
   `effort.observedAt: <ISO timestamp>` (used by the webview to
   render the time-elapsed suffix "(last /think Xm ago)"). **If
   `UserPromptSubmit` does not expose message text in its payload,
   fall back to Medium-only effort for Claude** and document the
   limitation in CHANGELOG. Verify field availability as the first
   step of implementation.
7. **Layer 3 Playwright smoke + screenshot assertions** (clean
   profile — container-height cannot be guaranteed against
   user-resized profiles per audit-summary §S3). Scenarios at
   `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`:
   - seed marker with Claude Opus + `signalKind: "current"`, assert
     solid-fill gauge needle in flagship zone
   - rewrite with Haiku + `signalKind: "current"`, assert needle moves
     to low zone
   - rewrite with `signalKind: "current"` + `confidence: "low"` +
     `model: "unknown"`, assert tooltip shows "live signal (low
     confidence — hook payload missing model)"
   - rewrite with `effort.signalKind: "last-observed"`, assert
     hollow-rim + clock-icon overlay + time-elapsed suffix on
     effort gauge
   - rewrite with `signalKind: "configured-default"`, assert dashed
     rim + DEFAULT pill badge (NOT stripes — stripes are stale-only)
   - rewrite `updatedAt` to 9h ago, assert stale state (diagonal-
     stripe overlay at 50% opacity over the underlying treatment +
     "last updated 9h ago" annotation)
   - **Screenshot assertion** verifies the view container ordering
     (orchestrator indicator above session sets tree) in a clean
     profile.
   - Multi-writer precedence smoke: write `configured-default`
     marker, then write `current` (should replace), then write
     `configured-default` again (should be skipped — log
     line written to `orchestrator-writer.log`).
8. **Version bump:** `package.json` 0.13.17 → 0.13.18.
9. **CHANGELOG:** new entry under 0.13.18 noting Claude-only v1
   preview with explicit limitations:
   - starting model only (no runtime `/model` detection in v1)
   - effort best-effort (Medium default plus last-observed `/think*`
     if `UserPromptSubmit` hook supports message text)
   - manual-override quickpick available for any state the hook
     misses
   - **container height cannot be guaranteed** (per audit-summary §S3):
     content is sized to fit within 100px, but VS Code persists
     user-resized view heights; if the operator has previously
     dragged the divider, that height is restored. To reset, drag
     the divider back. Content remains scrollable if compressed.
   - **/clear-vs-SessionStart asymmetry** (if applicable per the
     pre-implementation verification): if `/clear` does not fire
     SessionStart or does not reset effort, `last-observed`
     `/think*` signals persist across `/clear`.
   Mark non-Claude paths as "coming in 0.14.0".

**Creates:**
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
- `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`
- `tools/dabbler-ai-orchestration/media/orchestrator-indicator/` (CSS, optional fonts/icons)

**Touches:**
- `tools/dabbler-ai-orchestration/package.json` (view registration, command, version)
- `tools/dabbler-ai-orchestration/src/extension.ts` (register provider + command)
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md` (brief note under "VS Code extension" pointing at the new view)

**Ends with:** Claude Code path live; Playwright smoke passing locally;
0.13.18 packaged but not yet published (publish in S6, renumbered from S4 in the 2026-05-18 custom-tree pivot).

**Progress keys:** `session-002/webview-registered`, `session-002/provider-implemented`,
`session-002/marker-watcher-wired`, `session-002/claude-hook-installer-shipped`,
`session-002/playwright-smoke-green`, `session-002/version-bumped`

**Estimated cost:** $0.10–$0.30 (single end-of-session verification;
implementation work is all local Claude tokens).

---

### Session 3 of 6: Per-session-set identity (NEW, REVISED 2026-05-18 via custom-tree-pivot audit)

**Goal:** Move orchestrator-marker identity from per-workspace
(`~/.dabbler/current-orchestrator.json`) to per-session-set
(`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`).
Bump marker schema to v3 with `sessionSetSlug` as an integrity
field. Extract a `SessionSetsModel` data layer from the existing
`SessionSetsProvider` so the future custom tree (S4) and the
current native tree share the same scan/bucket/sort logic.

This session ships a **correctness fix**: the cross-window
contamination bug (per memory `project_consumer_repos` — three
parallel windows on three repos clobbering one global marker) is
eliminated. No user-facing UI change beyond per-set marker
resolution; the existing `WebviewView` orchestrator indicator
continues to render. The renderer reads the per-set marker for
the in-progress set in the current workspace; falls back to its
empty-state CTA when no marker is resolvable.

**Operator decisions encoded** (per
[`docs/proposals/2026-05-18-custom-tree-pivot/synthesis.md`](../../proposals/2026-05-18-custom-tree-pivot/synthesis.md)):

- **D1 (packaging):** Split per GPT-5.4 — identity-only S3,
  custom-tree work to S4.
- **D2 (ambiguity):** Fail closed per GPT-5.4 — skip the write
  when multiple in-progress sets are resolvable; log to
  `orchestrator-writer.log`. No Quick Pick / workspaceState
  persistence in S3.
- **D3 (orphan):** Implicit fail-closed for S3 — skip write when
  no in-progress set is resolvable. No workspace-level orphan
  marker created. Richer orphan UI defers to S4.

**Steps:**

1. **Marker schema v3.** Add top-level `sessionSetSlug` to the
   marker JSON; bump `schemaVersion` to `3`. Reader validates
   `sessionSetSlug` matches the host row's slug before rendering;
   logs and falls back to empty state on mismatch. Document the v3
   shape (either at `docs/orchestrator-marker-schema.md` as a new
   file, or appended to `docs/session-state-schema.md` — pick
   whichever fits the existing schema-doc convention).
2. **Per-set marker path.** New writer path:
   `<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`.
   Add `docs/session-sets/*/.dabbler/` to the canonical
   `.gitignore` template shipped by `scripts/init-workflow.py` (or
   equivalent). **Auto-patch existing repos non-interactively on
   next workspace init** (Gemini Pro must-fix). Idempotent;
   harmless if already present.
3. **Hook-to-set walk-up resolver.** In
   `scripts/write-orchestrator-marker.js`, replace the hard-coded
   global path with a walk-up that locates the workspace root,
   reads `docs/session-sets/<slug>/session-state.json` for each
   set, and returns the single set whose status is
   `"in-progress"`. **Fail closed** (return null + log) when
   zero or multiple in-progress sets are found, or when the
   walk-up doesn't reach a `docs/session-sets/` directory at all.
4. **Fail-closed posture.** On null resolution, the writer logs
   the reason to `~/.dabbler/orchestrator-writer.log` and **does
   not write a marker.** The renderer surfaces its existing
   empty-state CTA. No workspace-level orphan marker is created
   (keeps workspace identity out of the canonical model per D3 /
   GPT-5.4 must-fix).
5. **Reader path resolution.** The
   `orchestratorIndicatorProvider` reader resolves the marker
   path the same way the writer does. The provider's file-system
   watcher binds to the resolved per-set path and re-binds when
   the in-progress set changes (e.g., on close-out). Slug
   validation gates render.
6. **Multi-writer precedence — unchanged.** The existing
   precedence policy (`current` > `manual` > `last-observed` >
   `configured-default`) and the Windows-aware retry loop
   (5 attempts at 50/200/600/1200ms) continue to apply, now
   scoped to the per-set marker. Contention surface shrinks
   substantially since each set has at most one Claude session
   in flight at a time.
7. **`SessionSetsModel` data-layer extraction** (mandatory per
   both reviewers). Extract
   `src/providers/SessionSetsModel.ts` from
   `SessionSetsProvider.ts`: scan, bucket, sort, `progressText`,
   `isCurrentSessionInFlight`, `iconUriFor`, `needsMigrationBadge`.
   `SessionSetsProvider` becomes a thin shim that consumes
   `SessionSetsModel`. Both the current native tree (S3 ship)
   and the future custom tree (S4) consume the same model.
   **Layer-2 tests** at
   `src/test/suite/sessionSetsProvider.test.ts` repointed to
   `SessionSetsModel` and continue to gate bucketing/sort
   invariants.
8. **Backward compatibility.** Pre-existing
   `~/.dabbler/current-orchestrator.json` is silently ignored by
   the new reader. Operators with the v0.14.2 Claude Code hook
   installed must re-run `Dabbler: Install Orchestrator Hook
   (Claude Code)` to pick up the new resolver logic (installer
   is idempotent; helper-script path unchanged). Acceptable
   because v0.14.2 has not shipped to Marketplace — no external
   consumer is affected.
9. **Playwright smoke updates.** Add scenarios:
   - Two in-progress sets in one workspace → writer skips,
     `orchestrator-writer.log` carries the ambiguity entry,
     indicator shows empty-state CTA.
   - Single in-progress set → writer writes to
     `<set>/.dabbler/orchestrator.json`, indicator renders the
     gauges.
   - Schema-v3 marker with mismatched `sessionSetSlug` → reader
     falls back to empty state and logs.
   - `cwd` outside any `docs/session-sets/` directory → writer
     skips, no orphan marker written.
10. **Version bump:** 0.14.2 → **0.15.0** (minor — identity-model
    change per Gemini + GPT-5.4 consensus on Q9).

**Creates:**
- `tools/dabbler-ai-orchestration/src/providers/SessionSetsModel.ts`
  (data-layer extraction)
- `docs/orchestrator-marker-schema.md` _(or appended section in
  the session-state-schema doc)_ — documents the v3 marker
  shape, the per-set path, the fail-closed posture, and the
  walk-up resolver

**Touches:**
- `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
  (walk-up resolver; per-set path; schema-v3 write; fail-closed
  log line)
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  (per-set path resolution; re-bind watcher on in-progress-set
  change; `sessionSetSlug` validation; existing empty-state CTA
  surfaces on null resolution)
- `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`
  (collapse to thin shim over `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/src/test/suite/sessionSetsProvider.test.ts`
  (repoint to `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts`
  (new fail-closed + slug-validation scenarios)
- `tools/dabbler-ai-orchestration/package.json` (version → 0.15.0)
- `tools/dabbler-ai-orchestration/CHANGELOG.md` (new
  `[0.15.0]` section)
- `scripts/init-workflow.py` _(or wherever the canonical
  `.gitignore` template lives)_ — add
  `docs/session-sets/*/.dabbler/` to the ignore pattern; apply
  to existing repos on next `init`

**Ends with:** Per-set markers are the canonical identity model.
Three parallel windows on three repos render their own correct
orchestrator state (cross-window contamination bug eliminated).
The current native `TreeView` and `WebviewView` indicator continue
to render — no UI rewrite yet. `SessionSetsModel` exists and is
ready for the S4 custom tree to consume. 0.15.0 packaged, not
yet published.

**Progress keys:** `session-003/schema-v3-shipped`,
`session-003/per-set-marker-path`, `session-003/walk-up-resolver`,
`session-003/fail-closed-posture`, `session-003/sessionsetsmodel-extracted`,
`session-003/layer2-tests-repointed`,
`session-003/playwright-fail-closed-scenarios`,
`session-003/gitignore-autopatch`, `session-003/version-bumped`

**Estimated cost:** $0.10–$0.30 (single end-of-session
verification; implementation is local Claude tokens).

---

### Session 4 of 6: Custom-tree pivot (REVISED 2026-05-18 via custom-tree-implementation audit)

**Goal:** Replace the native `dabblerSessionSets` `TreeView` with a
webview-rendered custom tree (same view id, same view container).
Lift the v0.14.2 orchestrator gauges into per-row accordions on
in-progress rows so the orchestrator UI is contextually anchored
to the work it describes. Retire the dedicated
`dabblerOrchestratorIndicator` view in the same session. The S3
per-set markers + walk-up resolver + `SessionSetsModel` data layer
carry forward unchanged.

**Operator decisions encoded** (per
[`docs/proposals/2026-05-18-custom-tree-implementation/synthesis.md`](../../proposals/2026-05-18-custom-tree-implementation/synthesis.md),
three-way agreement: operator + Gemini Pro + GPT-5.4):

- **Q1–Q11 all locked at proposed defaults** — see synthesis.md table
  for the full grid; no reviewer divergences on the answer set.
- **M1–M10 tightening items** (mostly from GPT-5.4) — absorbed into
  the step list below.
- **Five new risks added to spec (R10–R14)**: focus/a11y (top-tier),
  QuickPick UX divergence (mid-tier), invalid interactive nesting,
  XSS via marker payload, message-ordering race. See Risks section.
- **Cost forecast bumped** from $0.10–$0.30 to **$0.20–$0.60** with
  Round-B verification pre-planned per memory
  `feedback_split_large_verification_bundles`.

**Steps:**

1. **Re-register `dabblerSessionSets` as `WebviewViewProvider`.**
   Same view id, same view container, same name "Session Sets".
   Flip `type` in `package.json` from native tree (default) to
   `"webview"`. Container icon, ordering, `contextualTitle`,
   `viewsWelcome` declaration all preserved. Delete the
   `dabblerOrchestratorIndicator` view entry in the same
   package.json edit (per M8: gated on accordion-body preserving
   install-hook + set-orchestrator + open-writer-log buttons).

2. **DOM structure (per M1 — invalid-nesting fix).** Do NOT use
   `<button role="treeitem">` wrapping the accordion body. Use
   focusable container with separate header control:
   ```html
   <div role="tree" aria-label="Session Sets">
     <div role="group" aria-label="In Progress (1)">
       <div role="treeitem" tabindex="-1" aria-level="1" aria-expanded="true"
            aria-selected="false" data-slug="029-...">
         <div class="row-header" role="presentation">
           <span class="icon">…</span>
           <span class="name">029-…</span>
           <span class="description">3/6 · session 4 in flight · 2026-05-18</span>
         </div>
         <div class="accordion-body" role="region" aria-label="Orchestrator">
           <!-- lifted gauge HTML; may contain buttons safely -->
         </div>
       </div>
     </div>
   </div>
   ```
   Roving `tabindex` (or `aria-activedescendant`) tracks the focused
   row. Accordion-body buttons (install-hook, set-orchestrator,
   open-writer-log) are NOT nested inside an interactive treeitem
   button — they're inside a `role="region"`, which is valid.

3. **ARIA tree semantics (WAI-ARIA 1.2 single-select tree pattern).**
   Required for v1:
   - `role="tree"` on container; `role="group"` on bucket;
     `role="treeitem"` on each row; `role="region"` on accordion body.
   - `aria-level`, `aria-expanded` (only on expandable rows —
     non-in-progress rows omit it per M3's "no inert chevron"),
     `aria-selected` on focused row.
   - Roving `tabindex` (single tabstop into the tree; arrow keys
     move focus within).
   - Keyboard: ↑/↓ sibling, ←/→ collapse/expand (or parent/first-
     child), Enter/Space activate (= `openSpec` for v1 per M3's
     primary-activation rule), Home/End first/last, `Shift+F10` +
     Context Menu key open the action QuickPick on the focused row.
   - Tab from inside expanded accordion exits cleanly to next
     focusable element outside the tree (no focus traps).
   - `// TODO: type-ahead search (deferred to v1.1)` comment in the
     kbd handler per Gemini M10.

4. **Three-file extraction (per Q1 + M4).**
   - `src/providers/OrchestratorAccordion.ts` (~400 LOC, new): pure
     render functions lifted from `orchestratorIndicatorProvider.ts`
     — `renderGaugeSvg`, `describeMarker`, `describeRecommendation`,
     `tierRank`, `effortRank`, `fmtAgeStandalone`,
     `providerHasExtraCapacity`, mismatch helpers, `escHtml`, the
     visual-treatment matrix. **No `vscode.*` lifecycle calls; no
     filesystem watchers.** Just deterministic string-in → HTML-out.
   - `src/providers/MarkerWatchService.ts` (~150 LOC, new): the
     marker reader, the `session-state.json` watcher, the
     workspace-folder listener, the polling backstop. **Emits typed
     events / state**, not HTML or webview commands. Disposable;
     injected into the view provider as a dependency. Unit-testable
     in isolation (which today's mixed provider is not).
   - `src/providers/CustomSessionSetsView.ts` (~500 LOC, new): the
     `WebviewViewProvider`. Owns lifecycle (resolveWebviewView,
     dispose), consumes `SessionSetsModel` + `MarkerWatchService` +
     `OrchestratorAccordion`, serializes render snapshots, posts
     messages to the webview, receives webview messages and
     dispatches via `ActionRegistry` + `vscode.commands.executeCommand`.
   - **Delete** `src/providers/SessionSetsProvider.ts` (no re-export
     shell — per M4). Test files that imported helpers from it
     repoint to `SessionSetsModel`.
   - **Delete** `src/providers/orchestratorIndicatorProvider.ts`
     (no re-export shell — per M4). Its render helpers are now in
     `OrchestratorAccordion.ts`; its lifecycle is now in
     `MarkerWatchService.ts` + `CustomSessionSetsView.ts`.

5. **`ActionRegistry` (per M2).** New
   `src/providers/ActionRegistry.ts` (~150 LOC). One typed module
   with the 14 row-actions, each as `{ id, label, when: (set:
   SessionSet, supports: { uat, e2e }) => boolean }`. The same
   predicates drive (a) the right-click QuickPick, (b) `Shift+F10`
   / Context Menu key, (c) any future inline overflow button.
   Replaces the lost `view/item/context` declarative rules in
   `package.json` — those entries are **deleted** from package.json
   in this session.

6. **Webview client script (per M6 — separate from view provider).**
   New `media/session-sets-tree/client.js` (~200 LOC). Owns kbd
   navigation, selection-state bookkeeping, contextmenu event
   capture, postMessage to the host. Keeping this OUT of
   `CustomSessionSetsView.ts` (which runs in the extension host) is
   a hard rule — host file stays focused on lifecycle + message
   protocol; client.js stays focused on user interaction.
   Cross-script type safety via the shared protocol module (step 7).

7. **Typed message protocol with monotonic version (per M3).** New
   `src/types/sessionSetsWebviewProtocol.ts` (~100 LOC).
   Discriminated unions for `HostToWebview` and `WebviewToHost`
   messages; every render message carries a monotonic
   `version: number` field. Webview client.js drops any render
   message with `version < currentVersion`. Snapshot-style payloads
   for row list; narrow event messages for UI-only state (focus
   moved, accordion toggled). Eliminates the message-ordering race
   when watcher events + polling backstop + manual refresh race.

8. **Suppression-state persistence (per Q2 + M7).** `workspaceState`
   key shape: `dabbler.sessionSets.suppressedExpand`, value =
   `Record<string, string>` mapping `slug` → `marker.updatedAt` of
   the suppressed occurrence. A row is suppressed iff
   `state[slug] === currentMarker.updatedAt`. Manual re-expand
   (click chevron) clears `state[slug]`. Prune: on every persist,
   drop entries whose slug is no longer in any bucket's set list.
   Reducer logic in `src/providers/suppressionState.ts` (small file,
   ~50 LOC, fully unit-tested per M6).

9. **HTML escaping (per M5).** Every dynamic string interpolation
   into webview HTML goes through `escHtml()` (lifted from
   `orchestratorIndicatorProvider.ts` into `OrchestratorAccordion.ts`).
   Includes: set names, descriptions, recommendation text, marker
   `model` / `modelDisplayName` / `effort.native`, ai-assignment
   recommendation, "updated Xs ago" formatted strings. Layer-2 test:
   set name with `<script>` content renders escaped, not executed.

10. **`viewsWelcome` empty state.** Preserve the `viewsWelcome`
    declaration in `package.json` (operator-discoverable). Extension
    host parses the contents string at activation, passes to webview
    as initial render state; webview renders as HTML with `command:`
    links intact (webview supports `command:` href natively when
    `enableCommandUris: true`).

11. **Loading-state UX.** When `scanState == loading`, webview
    renders centered `<div>` "Setting up your project…" with subtext
    "scanning session sets…". Identical text to today's loading
    sentinel. Host posts `{ type: "scanStateChanged", state:
    "loading"|"ready", version }` on every transition.

12. **Orphan handling (per Q8 = a+c).** S3's silent fail-close
    behavior preserved: when the resolver returns
    `{ reason: "no-in-progress-set" | "no-docs-session-sets" }`, no
    marker is written, no accordion is rendered. Add: when
    `{ reason: "multiple-in-progress-sets" }`, render a banner above
    the In Progress bucket: `"Multiple in-progress sets —
    orchestrator info hidden. [Open writer log]"`. Banner is
    visually distinct from ordinary empty-state copy (lighter
    background, info-icon prefix).

13. **Indicator-action parity (per M8 — ship blocker for
    retirement).** Before `dabblerOrchestratorIndicator` view entry
    is deleted, the accordion body MUST preserve:
    - **Install hook button** (CTA when no marker): fires
      `dabbler.installOrchestratorHook.claudeCode`.
    - **Set orchestrator button** (CTA when fresh marker /
      always-available action): fires `dabbler.setOrchestrator`.
    - **Open writer log button** (footer link): fires
      `dabbler.openOrchestratorWriterLog`.
    All three buttons fire via the same `postMessage` →
    `vscode.commands.executeCommand` plumbing as the context-menu
    actions.

14. **Title-bar actions preserved.** `view/title` entries in
    `package.json` (refresh, showCostDashboard, getStarted) work
    identically for webview and tree views. No code change.

15. **Layer-2 unit coverage (per M6).** New unit-test files:
    - `src/test/suite/actionRegistry.test.ts` (~100 LOC): every
      action × every state combination × uat/e2e gating.
    - `src/test/suite/suppressionState.test.ts` (~50 LOC): tuple-key
      reducer, manual-reexpand clearing, pruning.
    - `src/test/suite/markerWatchService.test.ts` (~100 LOC):
      state-transition emission (scan / marker-changed /
      workspace-folder-changed); subscription lifecycle.

16. **Layer-3 Playwright rewrite.** New
    `src/test/playwright/session-sets-tree.spec.ts` (~500 LOC).
    Scenarios:
    - Bucket grouping + sort order (port from `treeView.spec.ts`).
    - Accordion auto-expand on SessionStart marker write;
      auto-collapse on session close.
    - Manual collapse suppresses auto-expand for current occurrence
      only (write fresh marker → suppression released).
    - Right-click on row opens QuickPick with applicable actions
      only (assert against `ActionRegistry` expectations).
    - `Shift+F10` and Context Menu key open same QuickPick.
    - Kbd nav: ↑/↓/Home/End/Enter/Space behavior; focus stays on
      row when accordion collapsed; Tab exits tree cleanly.
    - Multiple-in-progress-sets banner renders with link to writer log.
    - `viewsWelcome` empty state renders with command links functional.
    - Loading-state sentinel → ready transition swaps cleanly.
    - All gauge scenarios from `orchestrator-indicator.spec.ts`:
      signalKind matrix (current/configured-default/last-observed/
      manual), confidence-low rendering, mismatch badge, stale state,
      schema-v3 slug mismatch fallback.
    - HTML escape: set name with `<script>` renders as text.
    - Indicator-action parity: install-hook + set-orchestrator +
      open-writer-log buttons fire correct commands.
    - Theme parity: light + dark theme screenshots of an in-progress
      row with expanded accordion.

17. **Selector updates on other Playwright specs.**
    `src/test/playwright/loading-state.spec.ts` and
    `src/test/playwright/migration-cta.spec.ts` selectors change
    from native-tree `[role=treeitem]` / `[aria-label]` patterns to
    webview-side `[data-slug]` / `[role=treeitem]` patterns
    (overlap intentional — ARIA role survives). Logic unchanged;
    assertion strings updated.

18. **Delete superseded files.**
    - `src/providers/SessionSetsProvider.ts` (deleted; tests
      repointed to `SessionSetsModel`).
    - `src/providers/orchestratorIndicatorProvider.ts` (deleted;
      helpers moved to `OrchestratorAccordion.ts`, lifecycle moved
      to `MarkerWatchService.ts`).
    - `src/test/playwright/orchestrator-indicator.spec.ts` (deleted;
      logic ported to `session-sets-tree.spec.ts`).
    - `src/test/playwright/treeView.spec.ts` (deleted; logic ported
      to `session-sets-tree.spec.ts`).
    - Package.json `view/item/context` entries (all 14 — actions now
      fired by `ActionRegistry` via QuickPick).
    - Package.json `dabblerOrchestratorIndicator` view entry.

19. **Version bump:** 0.15.0 → **0.16.0** (minor — architectural
    change: TreeView → WebviewView).

20. **CHANGELOG.** New `[0.16.0]` entry describing the pivot.
    Cross-link to `proposal.md` + `synthesis.md`. Notes:
    indicator-view retired in same release (no parallel surfaces);
    QuickPick replaces native context menu (UX divergence,
    theme-aware); `view/item/context` removed from package.json
    (`ActionRegistry` is the new authority).

**Creates:**

- `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
- `tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
- `tools/dabbler-ai-orchestration/src/providers/MarkerWatchService.ts`
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`
- `tools/dabbler-ai-orchestration/src/providers/suppressionState.ts`
- `tools/dabbler-ai-orchestration/src/types/sessionSetsWebviewProtocol.ts`
- `tools/dabbler-ai-orchestration/media/session-sets-tree/client.js`
- `tools/dabbler-ai-orchestration/media/session-sets-tree/tree.css`
- `tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/suppressionState.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/markerWatchService.test.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/session-sets-tree.spec.ts`

**Touches:**

- `tools/dabbler-ai-orchestration/package.json` (flip view type to
  webview; delete indicator view entry; delete 14 `view/item/context`
  entries; preserve `view/title`, `viewsWelcome`, commands,
  configuration; version bump)
- `tools/dabbler-ai-orchestration/src/extension.ts` (register
  `CustomSessionSetsView`; remove `SessionSetsProvider` +
  `OrchestratorIndicatorProvider` registrations)
- `tools/dabbler-ai-orchestration/src/test/playwright/loading-state.spec.ts`
  (selector updates)
- `tools/dabbler-ai-orchestration/src/test/playwright/migration-cta.spec.ts`
  (selector updates)
- `tools/dabbler-ai-orchestration/src/test/suite/sessionSetsProvider.test.ts`
  (repoint imports from deleted `SessionSetsProvider` to `SessionSetsModel`)
- `tools/dabbler-ai-orchestration/CHANGELOG.md` ([0.16.0] entry)

**Deletes:**

- `tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts`
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/orchestrator-indicator.spec.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/treeView.spec.ts`

**Ends with:** Custom tree shipped in v0.16.0. Single unified
webview surface; `dabblerOrchestratorIndicator` retired same
release. Gauges anchored in-row for in-progress sets. 14
row-actions fired via `ActionRegistry` + QuickPick. WAI-ARIA 1.2
single-select tree pattern with roving tabindex. Versioned
monotonic message protocol prevents stale-render races. All
dynamic text HTML-escaped. Layer-2 unit coverage for
`ActionRegistry`, suppression-state reducer, `MarkerWatchService`.
Layer-3 Playwright rewrite covers kbd nav, context menu, ARIA,
indicator-action parity, theme parity, schema-v3 slug validation.
0.16.0 packaged, not yet published (publish in S6).

**Progress keys:** `session-004/view-pivot-shipped`,
`session-004/dom-structure-correct`, `session-004/aria-tree-compliant`,
`session-004/three-file-extraction-done`, `session-004/action-registry-shipped`,
`session-004/client-script-extracted`, `session-004/versioned-protocol-shipped`,
`session-004/suppression-reducer-tested`, `session-004/html-escape-everywhere`,
`session-004/viewswelcome-parity`, `session-004/loading-state-parity`,
`session-004/orphan-banner-shipped`, `session-004/indicator-action-parity`,
`session-004/layer2-unit-coverage`, `session-004/playwright-rewrite-green`,
`session-004/selector-updates-applied`, `session-004/superseded-files-deleted`,
`session-004/version-bumped`

**Estimated cost (REVISED per audit synthesis):** **$0.20–$0.60**
with Round-B pre-planned per memory
`feedback_split_large_verification_bundles`. Round-A verifies the
implementation bundle (~1500 LOC pre-split into sub-bundles per the
same memory if >700 LOC per slice); Round-B verifies fixes applied.

---

### Session 5 of 6: Non-Claude provider detection + manual override

**Goal:** Add detection paths per the Session 1 audit's locked
resolutions: Codex auto-detect via `~/.codex/config.toml` watcher
(configured-default signal); Gemini Code Assist and GitHub Copilot
manual-only in v1 (no documented persisted state). Universal
manual-override quickpick with MRU + hotkey-bindable args.

**Steps (REVISED per audit 2026-05-17):**

1. **Codex detection (auto).** Read `~/.codex/config.toml` on extension
   activation and via filesystem watcher. Parse `model` and
   `model_reasoning_effort` fields. Write marker with
   `signalKind: "configured-default"`, `confidence: "medium"`,
   `effort.signalKind: "configured-default"`. **Document honestly**
   in the hover tooltip: "configured default (medium confidence —
   does not track runtime changes from `~/.codex/config.toml`)".
   Marker writer reuses the retry-loop helper from Session 2
   (5 attempts, 50/200/600/1200ms backoff) AND the multi-writer
   precedence read-check-rewrite helper — a `configured-default`
   write will be skipped if a fresh `current`/`manual`/`last-observed`
   signal exists, preventing the failure mode where a Codex
   config-watcher fire stomps a live Claude session signal.
2. **Gemini Code Assist: manual-only.** Per audit Q2 — no documented
   persisted state. The `Dabbler: Install Orchestrator Hook (Gemini Code Assist)`
   command opens the manual-override quickpick with `provider: "google"`
   pre-selected. No actual hook is installed.
3. **GitHub Copilot: manual-only.** Per audit Q4 — old settings keys
   deprecated, no current public key. The `… (GitHub Copilot)` command
   opens the manual-override quickpick with `provider: "github"`
   pre-selected. No actual hook installed.
4. **Manual-override quickpick** (`dabbler.setOrchestrator`)
   (REVISED 2026-05-18 — single-picker-with-MRU-plus-multi-step-
   fallback shape, aligned with audit-summary §"Manual-override
   quickpick UX"):
   - **Top section: MRU tuples**, one row per recent
     `<provider> + <model> + <effort> + <thinking>` combination
     ("Anthropic Opus 4.7 — High effort, Thinking on"), sorted
     most-recent first. Selecting a tuple applies it directly.
     Stored in `~/.dabbler/orchestrator-mru.json`.
   - **Bottom row: "(set new combination…)"** — enters a multi-step
     flow (provider → model → effort → thinking on/off) for novel
     combinations.
   - Both paths write the marker with `signalKind: "manual"`,
     `confidence: "high"` via the shared helper (retry loop +
     multi-writer precedence). **Force-override semantics:** if the
     helper detects a fresher `current`-precedence signal from
     another writer, the quickpick shows a "Override existing live
     signal from <writer>?" confirmation before proceeding.
   - **Accepts command palette args** for hotkey-bindable presets per
     audit E4. Example: operator binds `Ctrl+Shift+Alt+O` to
     `dabbler.setOrchestrator` with args `{"provider":"anthropic","model":"claude-opus-4-7","effort":"high","thinking":true}`
     for one-keystroke "back to Opus full power". Hotkey-bindable
     calls also pass through the force-override confirmation when
     applicable.
   - "(create new hotkey binding)" item below the multi-step entry:
     copies the `keybindings.json` snippet to clipboard pre-filled
     with the current selection.
5. **Smart empty-state CTA.** Webview detects which orchestrator
   extensions/CLIs are installed (presence of Claude Code, Gemini Code
   Assist extension, Codex CLI on PATH, GitHub Copilot extension) and
   surfaces the *right* installer/preset command in the "No signal"
   CTA — not a generic "install hook" link. If multiple are detected,
   show the most-recently-used per MRU.
6. **Playwright smoke expansion.** Add scenarios:
   - `signalKind: "configured-default"` for Codex — verify dashed
     rim + DEFAULT pill badge visual treatment on both gauges (NOT
     stripes — REVISED 2026-05-18)
   - `signalKind: "manual"` for Gemini and Copilot — verify
     operator-icon overlay visual treatment
   - MRU quickpick reordering (write 3 manual overrides, reopen
     quickpick, assert MRU order)
   - Force-override prompt: seed `current` Claude marker, invoke
     manual-override, assert the "Override existing live signal
     from <writer>?" confirmation appears.
   - Multi-writer precedence skip: write `current` then write
     `configured-default`, assert the `configured-default` write
     is skipped and a line is appended to `orchestrator-writer.log`.
7. **Version bump:** 0.13.18 → 0.14.0 (minor — multi-provider
   feature-complete).

**Creates:**
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
  (opens manual-override quickpick with `provider: "google"`
  pre-selected — no actual hook installed)
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
  (opens manual-override quickpick with `provider: "github"`
  pre-selected — no actual hook installed)
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts`
  (universal manual-override quickpick)
- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts`
  (REVISED 2026-05-18 per audit Q3 / D8 / Round-C verifier finding:
  Codex auto-detect is a config-watcher shim, NOT an installer
  command. Activated automatically on extension start; no
  user-facing installer command file)
- (possibly) provider-specific shim scripts under
  `tools/dabbler-ai-orchestration/scripts/`

**Touches:**
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  (smarter empty-state CTA)
- `tools/dabbler-ai-orchestration/package.json` (**3 new commands**
  — installer-Gemini, installer-Copilot, setOrchestratorManual;
  Codex auto-detection has no command, just a watcher activated
  at extension start; REVISED 2026-05-18)
- `tools/dabbler-ai-orchestration/src/extension.ts`
- `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`
- `tools/dabbler-ai-orchestration/CHANGELOG.md`

**Ends with:** All four orchestrator surfaces are supported (auto
where viable, manual override where not). Layer 3 smoke green for
all four. 0.14.0 packaged but not published.

**Progress keys:** `session-005/gemini-detection`, `session-005/codex-detection`,
`session-005/copilot-detection`, `session-005/manual-override-shipped`,
`session-005/smart-empty-state`, `session-005/playwright-smoke-all-four`

**Estimated cost:** $0.10–$0.30.

---

### Session 6 of 6: Polish, README, marketplace publish

**Goal:** Final polish, README update with screenshot, version bump to
0.17.x if anything moves, publish to Marketplace. **Includes an
explicit HTML-preview iteration cycle for the Session Set Explorer
styling** (operator request 2026-05-19 mid-S5, mirroring the
v0.14.2 gauge-styling iteration that ran for ~11 rounds).

**Steps:**

0. **HTML-preview iteration cycle for the Session Set Explorer.**
   Build a standalone HTML preview at
   `docs/proposals/<date>-explorer-styling/preview.html` that
   renders representative explorer states (in-progress with marker
   loaded, in-progress with empty/no-marker decorated by the
   Session 5 smart CTA, multi-bucket layout with grouping, mismatch
   suggested-section visible, stale annotation, force-override
   prompt aftermath, etc.) using the same CSS/SVG fragments the
   webview emits. Iterate on operator on-device screenshots. Land
   styling changes back into `OrchestratorAccordion.ts` +
   `media/session-sets-tree/client.css` after each round. Do NOT
   ship 0.17.x/0.18.x to Marketplace until the iteration converges.
1. **README screenshot + section.** Add a "Orchestrator Indicator"
   section to the extension README (and the repo-root README if it
   has a screenshot reel). PNG screenshot at
   `tools/dabbler-ai-orchestration/media/screenshots/orchestrator-indicator.png`.
2. **CHANGELOG consolidation.** Merge 0.13.18 + 0.14.0 + 0.14.1
   entries into a coherent feature note. Cross-link to the audit
   doc.
3. **CLAUDE.md update.** Expand the brief note from S2 into a proper
   subsection under "VS Code extension" naming the view, the marker
   file, the hook installers, and the manual override.
4. **Marketplace publish.** `cd tools/dabbler-ai-orchestration &&
   npx vsce publish --pat $env:AZURE_VSCODE_MARKETPLACE_TOKEN`
   (per memory `reference_vsce_pat`). Operator-confirms before
   publishing.
5. **Cross-repo notification.** Drop a brief note in each consumer
   repo's CLAUDE.md or equivalent pointing at the new view (only
   where it materially changes the workflow — likely just a
   one-liner in each).

**Creates:**
- `tools/dabbler-ai-orchestration/media/screenshots/orchestrator-indicator.png`

**Touches:**
- `tools/dabbler-ai-orchestration/README.md`
- `README.md` (repo root, if it has a feature reel)
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md`
- `tools/dabbler-ai-orchestration/package.json` (version, if 0.14.1 needed)
- Consumer-repo CLAUDE.md files (one-liner pointers)

**Ends with:** Marketplace 0.14.0 (or 0.14.1) live; README and CLAUDE.md
reflect the new feature; consumer repos pointed at it.

**Progress keys:** `session-006/readme-updated`, `session-006/changelog-merged`,
`session-006/claudemd-expanded`, `session-006/marketplace-published`,
`session-006/consumer-repos-notified`

**Estimated cost:** $0.05–$0.15.

---

## Risks

- **R1 — Detection viability.** The audit may discover that
  Gemini/Codex/Copilot expose no programmatic way to read current
  effort/model. Mitigation: manual-override command is the universal
  fallback; v1 ships honestly with "manual only" for any surface
  that can't be auto-detected.
- **R2 — Hook payload format drift.** Claude Code's `SessionStart` /
  `UserPromptSubmit` hook payload schemas may change between
  extension versions (REVISED 2026-05-18: was previously worded
  against `Stop` hook, which the audit rejected — see audit-summary
  §Q5). Mitigation: the helper script (`write-orchestrator-marker.js`)
  parses defensively and emits `signalKind: "current"` +
  `confidence: "low"` + `model: "unknown"` on schema miss (per
  Session 2 step 5 confidence-low producer rule). No crash; the
  tooltip surfaces the low-confidence reason explicitly.
- **R3 — 100px is tight.** If audit reviewers prefer larger gauges
  for legibility, we may need to compromise: ≤100px content area
  (excluding VS Code's view header). Audit reviews this explicitly.
- **R4 — Marker-file race conditions** (NARROWED SCOPE 2026-05-18
  post-pivot — see S3). Multiple orchestrator surfaces writing the
  same marker file could race. Mitigation: atomic writes (write +
  rename) plus **multi-writer precedence** (REVISED 2026-05-18 per
  audit-summary §"Multi-writer precedence"): every writer reads the
  existing target, compares `signalKind` precedence (`current` >
  `manual` > `last-observed` > `configured-default`), re-reads
  immediately before the atomic rename to close the TOCTOU race
  window, and skips the write if the proposed signal is weaker than
  a fresh existing signal. Skipped writes are logged to
  `~/.dabbler/orchestrator-writer.log`. **Post-pivot:** contention
  surface shrinks substantially since each set has at most one
  Claude session in flight at a time; the global-marker
  cross-window race is eliminated by the identity model change in
  S3, not by this mitigation.
- **R5 — Windows atomic-write contention** (added per audit S5;
  REVISED 2026-05-18). Atomic write-and-rename on Windows 11
  intermittently throws `PermissionError` when the VS Code file
  watcher is active on the target. Mitigation: all marker writers
  (Claude SessionStart hook script, Codex config.toml watcher,
  manual-override quickpick) implement retry loop with exponential
  backoff: **5 attempts = initial + 4 retries, 50/200/600/1200ms
  backoff between attempts, ~2050ms total ceiling**. (Was 3
  attempts at 50/150/400ms = 600ms before the 2026-05-18 verifier
  finding flagged the ceiling as too short for typical Windows
  AV-plus-file-watcher contention.) Helper shared across all four
  writer paths.
- **R6 — `UserPromptSubmit` hook may not expose message text**
  (added per audit). Required to detect `/think*` invocations for
  Claude effort tracking. Mitigation: Session 2 step 6 verifies field
  availability first; if not available, falls back to Medium-only
  effort for Claude (already the audit-locked default) and documents
  the limitation in CHANGELOG. No code crash either way.
- **R7 — `/clear`-vs-`SessionStart` asymmetry** (added 2026-05-18
  per post-audit verifier finding Q7 #3). The Q1 design says effort
  resets to Medium on `SessionStart`. If Claude `/clear` does not
  fire `SessionStart`, or fires it but does not reset effort
  semantically, a stale `last-observed` `/think*` signal will
  persist across `/clear` and the gauge may display effort from
  before the clear. Mitigation: Session 2 step 5
  pre-implementation verification checks both conditions; clobber
  on `/clear` is gated on BOTH being true. If either is false,
  `last-observed` is preserved across `/clear` and the asymmetry
  is documented in CHANGELOG. Operator has manual-override
  quickpick as universal reset.
- **R8 — Wrong-set attachment** (added 2026-05-18 per custom-tree
  pivot synthesis). If the S3 walk-up resolver picks the wrong
  in-progress set (e.g., stale `session-state.json` lingers as
  in-progress after a forgotten close-out), the operator sees
  correct-looking orchestrator data attached to the wrong work.
  Mitigation: the indicator's hover tooltip surfaces the resolved
  set slug; the operator can spot the mismatch. The fail-closed
  posture (skip write on ambiguous resolution) limits the
  exposure window to the single-in-progress-but-stale case. S4
  may add a small "attached to: <slug>" badge in the gauge frame
  for at-a-glance verification.
- **R9 — `.gitignore` auto-patch missed** (added 2026-05-18 per
  custom-tree pivot synthesis). If a workspace's `.gitignore` is
  not auto-patched (e.g., operator never re-runs `init`), per-set
  markers under `docs/session-sets/*/.dabbler/` could be staged
  for commit by mistake. Mitigation: the marker file's content is
  bounded and harmless if committed; the auto-patch is
  idempotent on subsequent inits; a one-line note in CHANGELOG
  [0.15.0] flags it; S3 step 2 explicitly requires the
  non-interactive auto-patch as a must-fix.
- **R10 — Webview focus / tab-order regression** (added 2026-05-18
  per S4 custom-tree implementation audit; GPT-5.4 flagged as
  top-tier: "the easiest way for a custom tree to feel broken").
  Native `TreeView` handles focus/blur, tab order, and ARIA
  selection automatically. The S4 webview must reproduce all of
  this manually. A regression — focus lost on collapse, Tab
  trapping inside an expanded accordion, focused row losing
  visual highlight — is highly visible to any operator using
  keyboard nav. Mitigation: WAI-ARIA 1.2 single-select tree
  pattern with roving `tabindex` per S4 step 3; Layer-3 Playwright
  kbd-nav coverage explicit (↑/↓/Home/End/Enter/Space/Tab
  in-and-out scenarios); ship-blocker per M8 — `dabblerOrchestratorIndicator`
  view does not retire until kbd/focus parity verified.
- **R11 — QuickPick context-menu UX divergence** (added 2026-05-18
  per S4 custom-tree implementation audit; GPT-5.4 sized as
  mid-tier: "acceptable v1 fidelity loss"). VS Code's native
  right-click context menu has different chrome from a QuickPick
  fired from the host (cmd-palette styling vs. native menu
  styling). Operator-visible change for the 14 row-actions.
  Mitigation: QuickPick is theme-aware and keyboard-navigable;
  same predicates from `ActionRegistry` drive right-click +
  `Shift+F10` + Context Menu key, so all three entrypoints feel
  consistent; v1.1 fallback is a custom HTML menu if feedback
  flags the divergence as material.
- **R12 — Invalid interactive nesting / focus trap** (added
  2026-05-18 per S4 audit GPT-5.4 M1). The naive DOM (a
  `<button role="treeitem">` wrapping a `<div role="region">`
  containing more buttons) is invalid HTML and bad a11y —
  interactive content inside an interactive button. Mitigation:
  M1 fixes the DOM per S4 step 2 (focusable `<div
  role="treeitem">` container with separate header control;
  accordion body sits outside the treeitem tabstop in
  `role="region"`); Layer-3 Playwright kbd nav covers focus
  traversal in/out of expanded accordion.
- **R13 — Webview XSS via marker payload** (added 2026-05-18 per
  S4 audit GPT-5.4 M5). Set names, descriptions, recommendation
  text, marker `model` / `effort.native` / `modelDisplayName`,
  and ai-assignment text all flow from JSON files into webview
  HTML. Without escaping, a `<` in a set name (or, in the worst
  case, an attacker-controlled marker payload) corrupts the
  rendered tree or executes script. Mitigation: M5 mandates
  `escHtml()` on every dynamic interpolation per S4 step 9;
  Layer-2 + Layer-3 tests cover injection-attempt payloads.
- **R14 — Message-ordering race** (added 2026-05-18 per S4 audit
  GPT-5.4 M3). Watcher events / polling backstop ticks / scan
  refreshes / manual refresh can race in the host; stale
  messages can repaint over fresh state in the webview. Without
  monotonic snapshots, the operator can see (e.g.) a freshly-
  closed session's gauge reappear because a delayed polling tick
  delivered a stale render after the close-out paint.
  Mitigation: M3 (monotonic `version` field on every render
  message; webview client.js drops out-of-order) per S4 step 7;
  Layer-2 tests on the reducer verify stale-version drop
  behavior.

## Routing notes (REVISED 2026-05-18)

- **Audit calls (S1): WAIVED.** The originally-planned
  `route_audit.py` call was waived per memory `feedback_ai_router_usage`
  (router reserved for end-of-session verification). The audit was
  conducted by manual paste-and-collect against GPT-5.4 + Gemini
  Pro; raw responses preserved at
  `docs/proposals/2026-05-17-model-effort-gauges-design-audit/{gpt-5-4,gemini-pro}-result.json`.
  Cost: **$0.00**.
- **Session-end verification (S1, S2, S3, S4, S5, S6):**
  `task_type='session-verification'`, single verifier (gpt-5-4)
  via `ai_router.query(...)`. S1 actually used three routed calls
  (Round A verification + cross-engine consensus on must-fix items +
  Round B confirmation), per the new memory
  `feedback_prefer_ai_consensus_over_human_prompt` carve-out.
- **In-session consensus calls (NEW class, 2026-05-18):** when a
  verifier returns a punch list of design refinements, the
  must-fix items are routed through GPT-5.4 + Gemini Pro for
  consensus before applying. This supersedes
  `feedback_ai_router_usage` for design-question consensus only;
  implementation work in S2/S3/S4/S5 still uses pure Claude tokens.
- **Pre-session audit (S4 only, planned):** the custom-tree
  session's pre-session audit (per
  `feedback_audit_then_spec_for_substantial_features`) routes
  through Gemini Pro via the router; GPT-5.4 via manual paste in
  GitHub Copilot per
  `feedback_split_large_verification_bundles`. Estimated
  $0.05–$0.20 for the routed Gemini call.
- **Implementation work (S2, S3, S4, S5):** pure Claude tokens, no
  router invocation.

## Total estimated cost (REVISED 2026-05-18 S4 custom-tree implementation audit, actuals through S3 + both mid-set audits)

- **Session 1 actual: ~$0.85** — Round A verification $0.264 +
  cross-engine consensus (gpt-5-4 + gemini-pro) $0.085 + Round B
  $0.138 + Round C $0.358. Round C cost was higher than typical
  ($0.36 vs. p50 $0.13) because gpt-5-4 emitted 22k output tokens
  on a tight prompt. Three routed verification rounds were needed
  because each successive bundle exposed previously-uninspected
  sections of spec.md with pre-audit drift. All converged cleanly
  — no verifier spiral per memory
  `feedback_verifier_spiral_recruit_codex`.
- **Session 2 actual: ~$0.58** — verification Rounds A + B + C
  across the Claude-only orchestrator-indicator ship.
- **Custom-tree pivot audit (mid-set, 2026-05-18): $0.022** —
  Gemini Pro consensus call only (GPT-5.4 via manual paste in
  GitHub Copilot = $0.00 per
  `feedback_split_large_verification_bundles`). Authored
  proposal + synthesis + S3 spec delta; replaced the obsolete
  per-workspace-markers path.
- **Session 3 actual: ~$0.085** — Gemini Pro × 3 rounds for
  verification; GPT-5.4 via manual paste = $0.00. Implementation
  was pure Claude tokens.
- **Custom-tree implementation audit (mid-set, 2026-05-18): $0.025**
  — Gemini Pro consensus call only (GPT-5.4 via manual paste =
  $0.00). Authored proposal + synthesis + S4 spec delta; locked
  Q1–Q11 at proposed defaults with no operator divergences; M1–M10
  tightening absorbed into spec. **Total mid-set audit spend: $0.047**.
- **Session 4 forecast: $0.20–$0.60** (REVISED 2026-05-18 per S4
  audit GPT cost note + Gemini M9). Round-A verifies the
  implementation bundle (~1500 LOC, pre-split into sub-bundles per
  `feedback_split_large_verification_bundles` if any slice >700 LOC);
  Round-B verifies fixes applied. Pre-planning Round-B explicitly
  rather than pretending the first pass will certainly be the last.
- **Session 5 forecast: $0.10–$0.30** (unchanged).
- **Session 6 forecast: $0.05–$0.15** (unchanged).
- **Total Set 029 forecast remainder (post-S3): $0.375 – $1.075**
  (was $0.30–$1.00 pre-S4-audit).
- **Cumulative end of Set 029: $1.95 – $2.65** against the
  operator's **$5.00 NTE ceiling** (confirmed 2026-05-18 at S1
  resume time). Comfortable headroom for Round-B verifications.
