# Session 1 verification prompt — Set 029 (orchestrator model & effort indicator gauges)

## Context

Set 029 ships a small VS Code webview view that pins above the
Dabbler Session Set Explorer and shows the current orchestrator's
**model** and **effort level** as two side-by-side semi-circle CSS
gauges. The operator-facing failure mode being eliminated: a session
silently starts on a lower-tier model after the operator dialed down
for a cheap task and forgot to dial back up.

Set 029 is structured as **audit-then-implement**, four sessions:

- **Session 1** (this one): cross-provider design audit. Lock six
  open design questions (Q1–Q6) and any showstoppers reviewers
  raise. Produce `audit-summary.md`. Update `spec.md`.
- **Session 2**: core webview + Claude detection + hook installer.
- **Session 3**: non-Claude detection (Codex auto, Gemini/Copilot
  manual-only) + manual-override quickpick.
- **Session 4**: polish + Marketplace publish.

Session 1's audit was conducted by manual paste-and-collect against
GPT-5.4 and Gemini Pro — not via `ai_router.route()` — per memory
`feedback_ai_router_usage` (router reserved for end-of-session
verification only). The two reviewer responses live at
`docs/proposals/2026-05-17-model-effort-gauges-design-audit/`
(`gpt-5-4-result.json`, `gemini-pro-result.json`). The orchestrator
(Claude Opus 4.7) synthesized them into `audit-summary.md`, then
updated `spec.md` to mark Q1–Q6 RESOLVED and to incorporate the
five resolved showstoppers (S1–S5).

## What you're being asked to verify

Set 029 Session 1 produces **only docs** — no executable code (one
helper script was scoped but waived). Your verification is therefore
a **doc-only synthesis review**.

The artifacts inlined below are:

1. **`audit-summary.md`** — the synthesis under review. Locks
   Q1–Q6, resolves S1–S5, defines the marker schema v2 with
   `signalKind` + `confidence`, defines the visual-treatment matrix
   per `signalKind`, and prescribes the manual-override quickpick UX.
2. **`gpt-5-4-result.json`** — GPT-5.4's raw audit response (the
   input to the synthesis).
3. **`gemini-pro-result.json`** — Gemini Pro's raw audit response
   (also input).
4. **Spec excerpts** — the `spec.md` sections that changed as a
   result of the audit (D6 effort table, D7 marker path, D8 hook
   installer matrix, Q1–Q6 RESOLVED stubs, Sessions 2 & 3 rewritten
   steps, R5/R6 risks).

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Faithful synthesis of reviewer verdicts.** For each of
Q1–Q6, does `audit-summary.md`'s locked verdict accurately reflect
what GPT-5.4 and Gemini Pro actually said in their raw responses?
Flag any cases where the summary claims a reviewer "agreed" with
something the reviewer didn't actually opine on, or where a
reviewer's stated concern was lost in synthesis. Note: the summary
acknowledges Gemini was silent on Q2/Q3/Q4/Q6 — verify that
GPT-5.4's verdict alone on those questions is defensible from the
GPT raw response.

**Q2. Showstopper mitigations.** Five showstoppers (S1–S5) are
listed with mitigations. For each, is the mitigation an actual fix
(addresses the root cause) or does it merely defer the problem?
Specifically:
- **S1 / S4** (Claude Stop hook lacks `model` field / Stop timing
  is lagging) → switch to `SessionStart`. Is `SessionStart` actually
  documented to carry a `model` field (per GPT-5.4's primary-doc
  citation in its raw response)? Does it fire at the right time?
- **S2** (`/think*`-as-effort recreates the failure mode) → Medium
  default + `signalKind: "last-observed"` for observed `/think*`.
  Does the `"last-observed"` visual treatment (hollow rim + filled
  needle, sublabel suffix "(last)") *really* prevent the operator
  from misreading it as a live signal, or does it still look
  similar enough at a glance to recreate the failure?
- **S3** (`initialSize` is not a real VS Code contributes.views
  property) → drop it; rely on Playwright screenshot assertions.
  Is screenshot assertion an adequate substitute for guaranteed
  initial sizing, given the operator's hard ≤100px constraint?
  What happens if the user has previously dragged the view to a
  different height?
- **S5** (Windows atomic-write contention with file watcher) →
  retry loop with 3 attempts at 50/150/400ms backoff. Is this
  bounded-retry shape likely to succeed against Windows
  PermissionError behavior, or does the upper bound need to be
  longer? Is there a risk the retry loop itself triggers the
  watcher repeatedly and amplifies the contention?

**Q3. Marker schema v2 sanity.** The v2 schema (lines 167–190 of
`audit-summary.md`) introduces `signalKind`, `confidence`, and
nested `effort.signalKind` / `effort.confidence`. Verify:
- The four `signalKind` values (`current`, `configured-default`,
  `last-observed`, `manual`) cover all four provider × signal
  combinations Sessions 2 and 3 will produce. Any gap?
- The visual-treatment matrix (lines 207–213) maps each
  `signalKind` to a distinct visual treatment. Are all four
  visually distinguishable at gauge sizes that fit in a ≤100px
  webview, given typical VS Code rendering at 1×/1.5×/2× DPI?
  (Specifically: solid vs. striped fill at small sizes.)
- Is `confidence` actually used anywhere in the design? If it
  only appears in a tooltip, is the field worth its weight in the
  schema?

**Q4. Spec-vs-summary consistency.** Read the spec excerpts
inlined below against `audit-summary.md`. Any drift between the
two — e.g., a decision worded one way in the summary and a different
way in the spec, or a step in Session 2/3 that contradicts a locked
audit verdict? Pay particular attention to:
- D8 (hook installer matrix) — does it match the locked
  Claude=SessionStart / Codex=config-toml-watcher / Gemini-Copilot=
  manual-only pattern from the audit?
- Effort table D6 — does the Claude column match the Medium-default
  + last-observed-`/think*` resolution from Q1?
- Sessions 2 step 6 (effort tracking via `UserPromptSubmit` hook)
  — the audit notes uncertainty about whether `UserPromptSubmit`
  exposes message text; does the spec adequately gate the
  implementation on that uncertainty (i.e., verify field
  availability first; fall back to Medium-only if not)?
- R5 + R6 in the spec's Risks section — present and consistent
  with their audit-summary sources?

**Q5. Step-2 waiver implications.** Session 1 spec step 2
prescribed authoring `route_audit.py` and invoking
`ai_router.route(task_type='cross-provider-audit')` for both
reviewers. The audit was instead conducted by manual paste-and-
collect at $0.00 cost, per memory `feedback_ai_router_usage`. Does
this waiver introduce any traceability or reproducibility gap that
would bite Session 2 or a future maintainer reading the audit trail?
Specifically:
- Are the raw reviewer responses (`gpt-5-4-result.json`,
  `gemini-pro-result.json`) sufficient on their own to re-derive
  the synthesis if the audit-summary were lost?
- Is the prompt that was actually sent to each reviewer recoverable
  from the current artifacts (the proposal.md is preserved, but is
  it clear that's what was pasted)?
- Should the step-2 waiver be documented somewhere durable beyond
  the activity log so that Session 2/3/4 don't expect a
  `route_audit.py` to exist?

**Q6. Session 2 buildability.** Reading only `audit-summary.md`
and the `spec.md` excerpts (not this prompt), could a fresh
orchestrator pick up Session 2 cold and ship the Claude path?
Identify the smallest concrete gap that would force them to circle
back to a design decision.

**Q7. Open architectural questions.** Specifically:
- The marker file is at `~/.dabbler/current-orchestrator.json`
  (global, single canonical file). Multiple orchestrator surfaces
  write the same file. The audit prescribes write-and-rename with
  retry loop — but does the design address what happens when two
  surfaces are *simultaneously* active (e.g., the operator has
  Claude Code AND Cursor's Codex pane open)? Whose write wins, and
  is that the right behavior?
- The stale threshold (`stalenessMaxSec`, default 8h) — is 8h the
  right default for the operator's stated workflow (multi-day
  session sets with breaks)? Should it be a per-set or per-
  workspace override rather than a global setting?
- The `signalKind: "last-observed"` for Claude effort resets to
  Medium on `SessionStart`. Does "SessionStart" in Claude Code
  fire on every `/clear` or only on truly new sessions? If `/clear`
  fires SessionStart, the gauge could clobber a recently-set
  `/megathink` indicator unexpectedly. Audit consider this?

**Q8. Overall.** Is Set 029 Session 1 ready to close out? If not,
the smallest concrete change to get it there.

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.


---

## Doc 1: audit-summary.md

# Audit summary: orchestrator model & effort indicator gauges

**Date:** 2026-05-17
**Reviewers consulted:** GPT-5.4, Gemini Pro
**Status:** Audit complete; all six open questions resolved with locked
verdicts. Five showstoppers identified and resolved with concrete
mitigations. Spec and implementation plan updated accordingly.

> **Process note.** The audit was conducted by manual paste-and-collect
> rather than via `ai_router.route()`, per operator preference and
> memory `feedback_ai_router_usage` (router reserved for end-of-session
> verification). GPT-5.4 returned a comprehensive prose review with
> primary-doc citations; Gemini Pro returned freeform commentary
> covering Q5 and two showstopper escalations but did not produce
> structured answers for Q2/Q3/Q4/Q6. Where Gemini was silent on a
> question, GPT-5.4's answer carries it.

---

## Convergence & divergence

The two reviewers converged on the most consequential finding (Q5)
and on the dominant v1 implementation shape (heavy manual-override
reliance for non-Claude surfaces).

| Topic | GPT-5.4 | Gemini Pro | Outcome |
|---|---|---|---|
| Q5 — Claude Stop hook | Wrong on field-availability (Stop has no `model`) | Wrong on timing (Stop is lagging) | **Strong agreement**: reject Stop, use SessionStart |
| Q1 — Claude effort | Label "last think," not current effort | Implied via "what you just did" framing | **Agreement** |
| Q2/Q3/Q4 — non-Claude detection | Manual-only for Gemini and Copilot; Codex config.toml as configured-default | Did not address directly, but accepts fallback dominance | **No divergence** |
| Q6 — staleness | 8h default; distinct from no-signal | Did not address | **Carried by GPT** |
| Windows atomic-write contention | Not raised | Raised as showstopper (retry loop + backoff required) | **Unique to Gemini, accepted** |
| Schema additions (signalKind, confidence) | Strongly raised | Not raised | **Unique to GPT, accepted** |
| Manual override UX (MRU + hotkeys) | Not raised | Raised as escalation | **Unique to Gemini, accepted** |

There were no substantive contradictions between the reviewers. Where
one was silent and the other spoke, the speaker's verdict stands.

---

## Locked resolutions for Q1–Q6

### Q1 — Claude Code effort representation
**LOCKED: option (b)+(c) hybrid.**

For Claude Code sessions, the effort gauge shows **Medium (default)**
unless a `/think*` invocation has been observed within the current
session, in which case the gauge displays the corresponding tier
with `signalKind: "last-observed"` and a "last" qualifier in the
sublabel (e.g., "High (last /think)"). On `SessionStart`, the
effort tier resets to Medium.

**Reasoning:** Both reviewers warned against treating per-message
`/think*` invocations as current state. The hybrid honors the
operator's intent (they DID just dial up to /megathink) without
falsely promising that subsequent messages will continue at that
tier.

---

### Q2 — Gemini Code Assist Agent detection
**LOCKED: manual-only for v1.**

No documented persisted Effort/Thinking state was found in the
Gemini Code Assist Agent. v1 ships with manual-override only for
Gemini. The empty-state CTA in the webview detects an active
Gemini Code Assist extension and surfaces the manual-override
quickpick command.

**Future:** if Gemini exposes settings or a config file in a later
release, add detection in a follow-on set.

---

### Q3 — Codex detection
**LOCKED: read `~/.codex/config.toml` as `signalKind: "configured-default"`.**

The extension reads Codex's config.toml on activation and on file
change (filesystem watcher). The `model` and `model_reasoning_effort`
fields populate the marker with `signalKind: "configured-default"`
and `confidence: "medium"`. The gauge UI visually distinguishes this
from a `current` signal (see "Visual treatment by signalKind" below).

**Reasoning:** GPT-5.4 confirmed config.toml has these fields and
that their machine has `model_reasoning_effort = "high"` configured.
This is a *useful* signal (it tells us the operator's chosen default)
but it is NOT a live signal — runtime `/model` changes in Codex
won't update the file. The signalKind field communicates that
honestly.

---

### Q4 — GitHub Copilot detection
**LOCKED: manual-only for v1.**

GPT-5.4 confirmed the old settings keys
(`github.copilot.chat.anthropic.thinking.effort`,
`github.copilot.chat.responsesApiReasoningEffort`) are deprecated,
and no current public key exposes live Thinking Effort. Per-model
persistence in the model picker is internal to Copilot.

**Future:** if Copilot adds a public settings key, add detection
in a follow-on set.

---

### Q5 — Claude Code hook protocol (REWRITTEN from original proposal)
**LOCKED: use `SessionStart` hook, not `Stop`. Mid-session `/model`
changes are NOT auto-detected in v1; document the limitation and
provide manual override.**

Documented Claude Code hook payload contents (per GPT-5.4's
primary-doc verification):

- **`SessionStart`** receives a `model` field. **This is the hook
  to use.**
- **`Stop`** receives `session_id`, `transcript_path`, `cwd`,
  `stop_hook_active`, `last_assistant_message` — **but NO `model`
  field.** Original proposal was wrong on this.

Implementation plan:

1. Install a `SessionStart` hook in `~/.claude/settings.json` that
   writes the marker file with the starting model + Medium default
   effort.
2. Install a `UserPromptSubmit` (or similar pre-turn) hook that
   detects `/think*` invocations in the user's message and updates
   the marker's `effort` field with `signalKind: "last-observed"`.
   Verify field availability in Session 2 — if `UserPromptSubmit`
   does not expose the message text, fall back to no effort
   tracking for Claude (Medium default only).
3. **Do not** attempt to detect runtime `/model` changes via hooks
   in v1. The empty-state CTA surfaces the manual-override
   quickpick prominently so the operator has a quick recovery
   path when they switch mid-session.

---

### Q6 — Stale-signal recovery UX
**LOCKED: 8h staleness default; distinct visual treatment from "no signal";
always show "last updated" timestamp.**

- `stalenessMaxSec` default: **28800** (8h), configurable.
- Visual states:
  - **Current:** solid color fill on gauges, full opacity.
  - **Stale:** striped (diagonal hatch) fill, ~60% opacity, "last
    updated Xh ago" annotation below the gauges. No install-hook
    CTA.
  - **No signal:** solid grey, "No signal — install hook" CTA below.
- The "last updated" timestamp is always visible (small text, below
  sublabel) regardless of state. Helps the operator calibrate trust.

---

## Resolved showstoppers (5 total) and mitigations

| # | Showstopper | Source | Mitigation |
|---|---|---|---|
| S1 | Claude Stop hook has no `model` field | GPT-5.4 | Switch to `SessionStart` hook (see Q5) |
| S2 | `/think*`-as-effort recreates false-confidence failure | GPT-5.4 | Effort gauge shows Medium default; `/think*` appears with `signalKind: "last-observed"` (see Q1) |
| S3 | `initialSize` is not in VS Code's contributes.views spec | GPT-5.4 | Drop `initialSize` from the proposal. Treat ordering/sizing as best-effort. Add Playwright screenshot assertions in Session 2 to catch visual regressions. |
| S4 | Stop hook timing makes gauge lagging | Gemini | Same fix as S1 (SessionStart fires before turn starts) |
| S5 | Windows atomic-write contention with file watcher → PermissionError | Gemini | Shim script implements retry loop with exponential backoff (3 retries: 50ms, 150ms, 400ms). Document the pattern; reuse for all four provider writers. |

---

## Marker file schema (REVISED — locked)

```json
{
  "schemaVersion": 2,
  "updatedAt": "2026-05-17T14:32:00-04:00",
  "writer": "claude-code-session-start-hook",
  "signalKind": "current",
  "confidence": "high",
  "provider": "anthropic",
  "providerDisplayName": "Claude",
  "model": "claude-opus-4-7",
  "modelDisplayName": "Opus 4.7",
  "tier": "flagship",
  "effort": {
    "normalized": "medium",
    "native": "default",
    "thinking": false,
    "signalKind": "current",
    "confidence": "high"
  },
  "stalenessMaxSec": 28800
}
```

### Changes from the original proposal

- **`schemaVersion`**: bumped to 2 (was 1) — breaking change to
  introduce `signalKind` and `confidence`.
- **`signalKind`** (new, top-level): `"current"` | `"configured-default"` |
  `"last-observed"` | `"manual"`. Drives visual treatment of the gauges.
- **`confidence`** (new, top-level): `"high"` | `"medium"` | `"low"`.
  Surfaced subtly in tooltip; doesn't drive gauge color directly.
- **`effort.signalKind`** + **`effort.confidence`** (new, nested):
  effort can have a *different* signalKind from the model — e.g., Claude
  with `model.signalKind="current"` (just session-started) but
  `effort.signalKind="last-observed"` (a `/think*` was issued mid-session).
- **`stalenessMaxSec`**: default raised from 3600 (1h) to 28800 (8h).

### Visual treatment by signalKind

| signalKind | Gauge fill | Sublabel suffix | Tooltip |
|---|---|---|---|
| `current` | Solid color | (none) | "live signal" |
| `configured-default` | Diagonal stripes | "(default)" | "configured default from ~/.codex/config.toml" |
| `last-observed` | Hollow rim + filled needle | "(last)" | "last observed Xm ago via /think" |
| `manual` | Solid + small operator-icon overlay | "(manual)" | "set manually at HH:MM" |

---

## Manual-override quickpick UX (NEW REQUIREMENT — locked)

Per Gemini's E4 escalation, the manual-override command must:

1. Open a single quickpick with **MRU ordering**: the most recently
   used `<provider> + <model> + <effort> + <thinking>` combinations
   surface first. Store MRU in `~/.dabbler/orchestrator-mru.json`.
2. Support **command palette arguments** so the operator can bind
   common states to hotkeys via VS Code's keybinding system. Example
   binding the operator could add to `keybindings.json`:
   ```jsonc
   {
     "key": "ctrl+shift+alt+o",
     "command": "dabbler.setOrchestrator",
     "args": {
       "provider": "anthropic",
       "model": "claude-opus-4-7",
       "effort": "high",
       "thinking": true
     }
   }
   ```
3. The quickpick has a "**(create new hotkey binding)**" item at the
   bottom that copies the necessary `keybindings.json` snippet to
   the clipboard pre-filled with the current pick.

---

## Action items for Session 2 and beyond

### Session 2 (core webview + Claude path)

- [ ] Use `SessionStart` hook, not `Stop` (per Q5 locked).
- [ ] Implement marker schema v2 with `signalKind` + `confidence`.
- [ ] Helper script uses write-and-rename with retry loop (3 attempts,
      50/150/400ms backoff) per S5.
- [ ] Effort gauge: Medium default for Claude; `last-observed` styling
      if a `/think*` is detected via `UserPromptSubmit` hook (verify
      field availability — fall back to Medium-only if not).
- [ ] Webview HTML/CSS implements visual treatment matrix for the
      four `signalKind` values.
- [ ] Drop `initialSize` from package.json view contribution. Document
      ordering as best-effort.
- [ ] Playwright smoke includes signalKind=current AND signalKind=last-observed
      scenarios.
- [ ] Last-updated timestamp visible in all states.

### Session 3 (non-Claude providers)

- [ ] Gemini: ship manual-only (no hook installer needed; the
      installer command surfaces the manual-override with a Gemini
      preset).
- [ ] Codex: read `~/.codex/config.toml` on extension activation and
      via filesystem watcher. Write marker with `signalKind="configured-default"`.
- [ ] Copilot: ship manual-only (same shape as Gemini).
- [ ] Manual-override quickpick implements MRU + hotkey-friendly args
      per Gemini's E4.
- [ ] Smart empty-state detection: identifies which orchestrator is
      most likely active (by checking installed extensions) and surfaces
      the *right* installer/preset command in the CTA.

### Session 4 (polish + publish)

- [ ] Playwright screenshot assertions for layout (compensates for S3's
      lack of `initialSize` guarantee).
- [ ] Tooltip text per visual-treatment matrix.
- [ ] README screenshot showing all four signalKind visual treatments
      side-by-side (educates the operator on what each fill style means).

### Out-of-set follow-ups (not Session 029 scope)

- [ ] Investigate the `route(task_type="architecture")` 2-min timeout
      GPT-5.4 mentioned (escalation E3). Likely a router-config or
      upstream-provider issue; track separately.

---

## Spec deltas to apply

The following items in `docs/session-sets/029-orchestrator-model-effort-gauges/spec.md`
need updating to reflect the audit:

1. **D2** (layout) — no change.
2. **D3** (height budget) — no change (still ≤100px).
3. **D6** (effort scale) — update Claude column in normalization table:
   "(no native control), Medium default; recent /think* shown as
   last-observed".
4. **D7** (marker file path) — no change; schema version bumped to 2.
5. **D8** (hook installers) — re-scope:
   - Claude: SessionStart hook installer (was Stop).
   - Gemini/Copilot: "installer" is shorthand for "open manual-override
     with provider pre-selected". No actual hook installed.
   - Codex: config.toml watcher (no user-facing installation; happens
     on extension activation).
6. **Q1–Q6 sections**: mark RESOLVED with one-liner pointing here.
7. **Session 2 steps**: rewrite per action items above.
8. **Session 3 steps**: rewrite per action items above.
9. **Risks section**: add R5 (Windows atomic-write contention) and
   R6 (UserPromptSubmit hook may not expose message text).

---

## Cost summary

- Audit calls: **$0.00** (manual paste-and-collect — no router invocation
  per operator's chosen workflow for this audit).
- Total Session 1 cost so far: **$0.00**.
- Forecast for remaining set (S2-S4): unchanged from spec, $0.25-$0.75
  range (lower bound since S2-S4 verification cost trends low for
  implementation-driven sessions per memory
  `project_verification_cost_empirical`).


---

## Doc 2: gpt-5-4-result.json (raw audit input)

```json
{
  "reviewer": "gpt-5.4",
  "reviewedAt": "2026-05-17T00:00:00-04:00",
  "verdict": "good-shape-needs-fixes-before-implementation",
  "format_note": "Reviewer's response was prose, not strict JSON. The structure below interpolates their points into the requested format. Verbatim text preserved in the rationale fields where possible.",
  "showstoppers": [
    {
      "id": "S1-claude-stop-hook-no-model-field",
      "concern": "Claude Stop hook does NOT receive a 'model' field. Current Claude Code hook docs show Stop receives stop_hook_active and last_assistant_message; only SessionStart receives a model field. The proposal's Q5 premise is wrong — Stop has session_id, transcript_path, cwd, etc., not model. This is a blocker for Session 2 as currently scoped.",
      "severity": "blocker",
      "source": "Claude Code hooks documentation"
    },
    {
      "id": "S2-claude-effort-as-think-recreates-failure-mode",
      "concern": "Showing the most-recent /think* invocation as live 'effort' can recreate the exact false-confidence failure this feature is meant to prevent. /think* is per-message, not persistent. Should be labeled 'last think' or hidden, not shown as 'current effort'.",
      "severity": "major"
    },
    {
      "id": "S3-initialSize-not-in-vscode-api",
      "concern": "The proposal's reference to `initialSize` on a webview view contribution is suspect. Official VS Code contributes.views docs show no initialSize property. Treat sizing/order as best-effort. Add screenshot-based acceptance tests to catch regressions.",
      "severity": "major",
      "source": "VS Code contributes.views documentation"
    }
  ],
  "answers": {
    "Q1": {
      "answer": "Label as 'last think,' not current effort. Combine with the new signalKind field (see escalations) to make this honest. Specifically: for Claude sessions, effort gauge shows Medium by default (since that is the implicit default); a recent /think* invocation can be reflected with signalKind='last-observed' and a 'last' qualifier in the sublabel, but should NOT be rendered as the current operating effort.",
      "rationale": "/think* is not a persistent setting. Treating most-recent-wins as 'current effort' recreates the false-confidence failure the feature is meant to prevent.",
      "confidence": "high"
    },
    "Q2": {
      "answer": "Ship as manual-only for Gemini Code Assist in v1.",
      "rationale": "Official Gemini Code Assist agent-mode docs mention ~/.gemini/settings.json for tools/MCP and VS Code settings for yolo mode, but no documented persisted 'Effort' or 'Thinking' state was found. v1 should not pretend to auto-detect what isn't exposed.",
      "confidence": "medium",
      "source": "Gemini Code Assist agent mode documentation"
    },
    "Q3": {
      "answer": "Detection IS viable but NOT as 'current' — read ~/.codex/config.toml as a CONFIGURED-DEFAULT signal. Codex supports model and model_reasoning_effort fields in that config (reviewer confirms model_reasoning_effort='high' on their machine). This is a configured default, NOT the live thread value after a runtime /model change.",
      "rationale": "Codex's config.toml gives us something useful (the operator's chosen default), but conflating it with 'current state' would be misleading. Label as signalKind='configured-default' and don't pretend it tracks runtime changes.",
      "confidence": "high",
      "source": "Codex config reference"
    },
    "Q4": {
      "answer": "Ship as manual-only for Copilot in v1 unless a public key can be proven.",
      "rationale": "VS Code docs say Thinking Effort is configured via the model picker and persists per model. The old settings keys (github.copilot.chat.anthropic.thinking.effort, github.copilot.chat.responsesApiReasoningEffort) are deprecated. No current public settings key was found that would let an extension read live Thinking Effort.",
      "confidence": "medium",
      "source": "VS Code language models documentation"
    },
    "Q5": {
      "answer": "REJECT current Stop-hook-based plan. For Claude Code: use SessionStart for the starting model, transcript_path scraping for mid-session changes (or accept that runtime /model changes need manual override). Do NOT claim Stop has model.",
      "rationale": "Documented: Stop receives session_id, transcript_path, cwd, stop_hook_active, last_assistant_message. SessionStart receives a model field. Building on Stop for model state is wrong on field-availability grounds.",
      "confidence": "high",
      "source": "Claude Code hooks documentation"
    },
    "Q6": {
      "answer": "Make stale visually distinct from no-signal. Default stalenessMaxSec longer than 1h — recommend 8h or 'same day' equivalent. Always show 'last updated' timestamp regardless of state. No install-hook CTA in stale state.",
      "rationale": "1h is too aggressive for Claude Code sessions where the operator may be reading. Long sessions can exceed it. Stale and no-signal currently look too similar; the operator might conflate them.",
      "confidence": "medium"
    }
  },
  "escalations": [
    {
      "id": "E1-add-signal-kind-to-schema",
      "concern": "Marker schema should carry a signalKind field: 'current' | 'configured-default' | 'last-observed' | 'manual'. The UI can then communicate honestly what kind of signal it's showing (and visually distinguish them, e.g., via striping for non-current signals)."
    },
    {
      "id": "E2-add-confidence-to-schema",
      "concern": "Add confidence: 'high' | 'medium' | 'low' to the marker, displayed subtly (hover/tooltip). Helps the operator calibrate trust in the gauge."
    },
    {
      "id": "E3-route-architecture-call-timed-out",
      "concern": "Reviewer attempted to route an independent architecture review via route(task_type='architecture') per repo discipline, but the call timed out after 2 minutes. Feedback above is direct review + primary-doc verification. Operator may want to investigate the timeout separately — not blocking for this set."
    }
  ],
  "summary": "Feature shape is good; gauge UI idea is sound; but detection claims must be tightened before implementation. Highest-priority fix: Claude Stop hook does not carry a model field (use SessionStart). Second-highest: do not show /think* as current effort. Gemini and Copilot should be manual-only in v1. Codex can read its config.toml as a configured-default, not a live signal. Schema needs signalKind + confidence fields; UI must distinguish current vs configured-default vs last-observed vs manual."
}

```

---

## Doc 3: gemini-pro-result.json (raw audit input)

```json
{
  "reviewer": "gemini-pro",
  "reviewedAt": "2026-05-17T00:00:00-04:00",
  "verdict": "partial-review-freeform-commentary-only",
  "format_note": "Reviewer provided freeform commentary only; structured Q1-Q6 answers were not produced. The commentary touches on Q1, Q5, and showstopper escalations; the remaining open questions (Q2, Q3, Q4, Q6) are not directly addressed and must rely on the other reviewer's answers.",
  "showstoppers": [
    {
      "id": "S4-stop-hook-timing-undercuts-feature",
      "concern": "If the gauge updates only after a turn finishes (Stop hook), it conveys 'what you just did' rather than 'what you are about to do'. If the operator switches to Opus but doesn't send a prompt, the gauge won't update until they do — severely undercutting the feature's utility. Use SessionStart or a TurnStart-equivalent if available.",
      "severity": "major",
      "convergesWith": "gpt-5.4: S1-claude-stop-hook-no-model-field"
    },
    {
      "id": "S5-windows-atomic-write-vs-file-watcher-contention",
      "concern": "On Windows 11 (the operator's platform), atomic file renaming intermittently throws PermissionError when a file-watcher is active on the target. Even with os.replace (Python) or fs.renameSync (Node), strict file locks during watcher scan cycles cause failures. The shim script writing the marker MUST implement a short retry loop with exponential backoff to handle this gracefully.",
      "severity": "major"
    }
  ],
  "answers": {
    "Q1": {
      "answer": "Not directly addressed, but implied: 'last did' vs 'about to do' framing argues against using lagging signals as live state for the effort gauge. Converges with gpt-5.4's Q1 answer (label as 'last think,' not current effort).",
      "rationale": "Implied from the Hook Timing Problem commentary.",
      "confidence": "low",
      "source": "interpolated from freeform commentary"
    },
    "Q2": { "answer": "NOT ADDRESSED", "rationale": "Gemini commentary mentions Q2 only as part of 'Given my assessments for Q2, Q3, and Q4', implying agreement with manual-only outcome but without primary-doc citation.", "confidence": "low" },
    "Q3": { "answer": "NOT ADDRESSED", "rationale": "Same as Q2 — Gemini groups Q2/Q3/Q4 under 'fallback reliance' but does not provide a concrete answer.", "confidence": "low" },
    "Q4": { "answer": "NOT ADDRESSED", "rationale": "Same as Q2.", "confidence": "low" },
    "Q5": {
      "answer": "Use SessionStart or TurnStart hook (whichever Claude Code supports) instead of Stop. Reasoning: timing, not just field availability — Stop fires AFTER the response, making the gauge a lagging indicator.",
      "rationale": "Even if Stop carried a model field, its timing is wrong for a 'current state' indicator. Operators need to see model BEFORE they send the prompt, not after.",
      "confidence": "high"
    },
    "Q6": { "answer": "NOT ADDRESSED", "rationale": "No commentary on staleness UX.", "confidence": "low" }
  },
  "escalations": [
    {
      "id": "E4-manual-override-mru-and-hotkeys",
      "concern": "Given Q2/Q3/Q4 will likely all be manual-only in v1, the manual-override quickpick will be the dominant path. Reduce friction with (a) MRU cycling — most recently used model+effort combinations surface first; (b) command palette argument support — bind common states to hotkeys ('Set Orchestrator to Opus + High + Thinking on' as a single command instance)."
    }
  ],
  "summary": "Two concrete additions to GPT-5.4's review: (1) Stop hook is wrong on TIMING grounds, not just field-availability — use SessionStart/TurnStart. (2) Windows atomic write contention with file watchers is a real, common failure mode that must be handled with retry-loop + exponential backoff in the shim script. Heavy v1 reliance on manual-override means the override UX needs MRU + hotkey support to not become its own pain point."
}

```

---

## Doc 4: spec.md excerpts (audit-driven changes)

=== FILE: docs/session-sets/029-orchestrator-model-effort-gauges/spec.md (337 LOC across 5 slice(s)) ===
--- docs/session-sets/029-orchestrator-model-effort-gauges/spec.md lines 96-145 ---
   96  ## Decisions locked from operator dialogue (do not re-litigate)
   97  
   98  | # | Decision | Locked value |
   99  |---|---|---|
  100  | D1 | Provider scope | **All four orchestrator surfaces**: Claude Code, Gemini Code Assist Agent, Codex, GitHub Copilot. v1 ships best-effort detection for each plus manual override as universal fallback. |
  101  | D2 | Layout | **Two side-by-side semi-circle gauges** plus a binary "Thinking" LED beside the effort gauge. Three-gauge variants rejected; binary thinking-on/off doesn't warrant a third gauge. |
  102  | D3 | Height budget | **≤100px total visible content** (operator's hard constraint). VS Code's standard view header (~22px) sits above this. Semi-circle gauges at ~70-80px tall fit comfortably; full-circle gauges do not. |
  103  | D4 | Location | **New webview view (`dabblerOrchestratorIndicator`) pinned above `dabblerSessionSets` in the existing `dabblerSessionSetsContainer`.** Not a status-bar item (operator's framing was "panel at the top of Session Set Explorer"). |
  104  | D5 | Color polarity | **Red = low-tier / low-effort (warning state), green = flagship / max-effort (preferred state).** Inverts the conventional "red = expensive" mapping because the operator's stated failure mode is *forgetting to switch back up*, not *spending too much*. |
  105  | D6 | Effort scale | **Five normalized levels** (Low / Medium / High / Extra-High / Max), mapping from provider-native scales as follows. Thinking on/off is a separate binary LED. |
  106  | D7 | Marker file | **`~/.dabbler/current-orchestrator.json`** (global, user-home, single canonical file). Multi-writer: each provider's hook/shim writes the same file. Schema in Session 1 audit deliverable. |
  107  | D8 | Hook installer | **Per-provider commands, but only Claude installs an actual hook** (per audit Q2/Q4/Q5): Claude = `SessionStart` hook in `~/.claude/settings.json` (NOT `Stop` — Stop has no `model` field per audit S1). Codex = `~/.codex/config.toml` watcher (no user-facing install; auto-activates). Gemini/Copilot = "installer" command opens the manual-override quickpick with provider preset (manual-only in v1). Universal manual-override (`Dabbler: Set Orchestrator Model & Effort`) supports MRU ordering + hotkey-bindable command args per audit E4. |
  108  | D9 | Set structure | **Single set, audit-then-implement.** 4 sessions: S1 design audit, S2 core webview + Claude path, S3 non-Claude detection, S4 polish + release. |
  109  | D10 | Backwards compatibility | **No legacy behavior to preserve.** This is a net-new view. Empty/missing marker file = "No signal" empty state with install CTA. |
  110  
  111  ### Effort-level normalization table (locked)
  112  
  113  | Normalized | Claude Code | Gemini Code Assist | Codex | GitHub Copilot |
  114  |---|---|---|---|---|
  115  | Low (0-25) | (no native control)\* | Low | Low (Intelligence) | Low (Thinking Effort) |
  116  | Medium (26-50) | **default** | Medium | Medium | Medium |
  117  | High (51-75) | `/think` (last-observed only) | High | High | High |
  118  | Extra-High (76-90) | `/megathink` (last-observed only) | Extra-High | Extra-High | Extra-High |
  119  | Max (91-100) | `/ultrathink` (last-observed only) | Max | (not exposed) | (not exposed) |
  120  
  121  \* **REVISED per audit Q1/S2 (2026-05-17):** Claude Code has no
  122  per-message effort slider; treating the most recent `/think*`
  123  invocation as "current effort" would recreate the false-confidence
  124  failure mode this feature is designed to prevent (both reviewers
  125  agreed). Locked design: effort gauge shows **Medium (default)** for
  126  Claude sessions. If a `/think*` invocation is observed during the
  127  session, the gauge displays the corresponding tier with
  128  `signalKind: "last-observed"` and an "(last /think)" sublabel
  129  qualifier, rendered with hollow-rim visual treatment to distinguish
  130  from a live signal. Resets to Medium on `SessionStart`.
  131  
  132  ### Thinking on/off (binary LED beside effort gauge)
  133  
  134  | Provider | Source |
  135  |---|---|
  136  | Claude Code | "On" whenever any `/think*` was used in current session; else "Off". |
  137  | Gemini Code Assist | "Thinking" toggle in the IDE panel. Direct read. |
  138  | Codex | (no native concept) — LED hidden, only the Intelligence gauge shows. |
  139  | GitHub Copilot | (no native concept) — LED hidden, only the Thinking Effort gauge shows. |
  140  
  141  ---
  142  
  143  ## Resolved design questions (from cross-provider audit 2026-05-17)
  144  
  145  Cross-provider audit conducted 2026-05-17 with GPT-5.4 and Gemini Pro.

--- docs/session-sets/029-orchestrator-model-effort-gauges/spec.md lines 146-200 ---
  146  Full audit at
  147  `docs/proposals/2026-05-17-model-effort-gauges-design-audit/audit-summary.md`.
  148  Question numbering aligns with the audit proposal — the original spec
  149  Q1 ("marker file schema") was rolled into D7's marker-schema
  150  deliverable and is now captured in the audit-summary's "Marker file
  151  schema (REVISED — locked)" section.
  152  
  153  - **Q1 — Claude Code effort representation.** Locked: Medium default;
  154    recent `/think*` invocations shown as `signalKind: "last-observed"`
  155    with "(last /think)" sublabel suffix. Reset to Medium on
  156    `SessionStart`. → `audit-summary.md` §Q1.
  157  - **Q2 — Gemini Code Assist detection.** Locked: manual-only for v1.
  158    No documented persisted state. → `audit-summary.md` §Q2.
  159  - **Q3 — Codex detection.** Locked: read `~/.codex/config.toml` on
  160    activation + filesystem watcher. `signalKind: "configured-default"`.
  161    NOT a live signal. → `audit-summary.md` §Q3.
  162  - **Q4 — GitHub Copilot detection.** Locked: manual-only for v1. Old
  163    settings keys deprecated, no current public key. →
  164    `audit-summary.md` §Q4.
  165  - **Q5 — Claude Code hook protocol.** Locked: use `SessionStart`
  166    (NOT `Stop` — Stop has no `model` field). Mid-session `/model`
  167    changes NOT auto-detected in v1; manual override is the recovery
  168    path. → `audit-summary.md` §Q5.
  169  - **Q6 — Stale-signal recovery UX.** Locked: 8h default
  170    (`stalenessMaxSec: 28800`); visually distinct stripe pattern for
  171    stale; always show "last updated" timestamp. →
  172    `audit-summary.md` §Q6.
  173  
  174  ### Showstoppers identified and mitigated
  175  
  176  The audit surfaced five showstoppers, all resolved with concrete
  177  mitigations now folded into the locked design:
  178  
  179  - **S1**: Claude Stop hook has no `model` field → switched to
  180    `SessionStart` (Q5).
  181  - **S2**: `/think*`-as-current-effort recreates the failure mode →
  182    Medium default + last-observed treatment (Q1).
  183  - **S3**: `initialSize` is not a real VS Code contributes.views
  184    property → dropped; ordering/sizing best-effort + Playwright
  185    screenshot assertions in Session 2.
  186  - **S4**: Stop hook timing makes gauge lagging → same fix as S1.
  187  - **S5**: Windows atomic-write contention with file watcher →
  188    retry loop (3 attempts, 50/150/400ms backoff) in all marker
  189    writers (Session 2 / Session 3 implementation).
  190  
  191  ### Marker schema bumped to v2
  192  
  193  The audit introduced two new schema fields (`signalKind` and
  194  `confidence`) with breaking semantics; canonical schema lives in
  195  `audit-summary.md` "Marker file schema (REVISED — locked)" section.
  196  
  197  ---
  198  
  199  ## Sessions
  200  

--- docs/session-sets/029-orchestrator-model-effort-gauges/spec.md lines 255-360 ---
  255  ---
  256  
  257  ### Session 2 of 4: Core webview + Claude detection + hook installer
  258  
  259  **Goal:** Ship the gauge UI end-to-end for the Claude Code surface.
  260  The webview renders, the marker-file watcher fires, the Claude Code
  261  `SessionStart` hook can be installed in one click, and the gauges
  262  update on session start (and on `/think*` invocations if hook payload
  263  exposes message text). Other surfaces show "No signal — install hook"
  264  placeholder.
  265  
  266  **Steps (REVISED per audit 2026-05-17):**
  267  
  268  1. **Webview view registration.** Add `dabblerOrchestratorIndicator`
  269     to `package.json` `contributes.views.dabblerSessionSetsContainer`
  270     with `type: "webview"`. Order it **first** in the array. **Do NOT
  271     use `initialSize`** (per audit S3 — not a real VS Code contributes.views
  272     property). Ordering and sizing are best-effort; Playwright screenshot
  273     assertions in step 7 below catch regressions.
  274  2. **Webview provider.** Implement
  275     `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  276     as a `WebviewViewProvider`. HTML+CSS based on the dev.to gauge
  277     reference (https://dev.to/madsstoumann/how-to-create-gauges-in-css-3581)
  278     adapted to semi-circle form factor. Two gauges + thinking LED +
  279     provider/model label. Visual-treatment matrix for the four
  280     `signalKind` values (per audit-summary §"Visual treatment by signalKind"):
  281     - `current`: solid fill, full opacity
  282     - `configured-default`: diagonal stripes fill
  283     - `last-observed`: hollow rim + filled needle
  284     - `manual`: solid + small operator-icon overlay
  285     Last-updated timestamp always visible (small text below sublabel).
  286  3. **Marker-file reader and watcher.** Use `vscode.workspace.createFileSystemWatcher`
  287     with absolute path `~/.dabbler/current-orchestrator.json`. Marker
  288     schema v2 (with `signalKind` + `confidence` per audit). Stale state
  289     (>`stalenessMaxSec`, default 28800s = 8h): striped fill at ~60%
  290     opacity + "last updated Xh ago" annotation, no install-hook CTA.
  291  4. **Empty state.** When marker file is missing, render solid grey
  292     gauges + "No signal — install hook" CTA. CTA fires the
  293     `Dabbler: Install Orchestrator Hook (Claude Code)` command.
  294  5. **Claude Code SessionStart hook installer.** New command
  295     `dabbler.installOrchestratorHook.claudeCode`. Reads
  296     `~/.claude/settings.json` (or creates if missing), idempotently
  297     appends a `SessionStart` hook entry (**NOT `Stop`** — per audit S1
  298     Stop has no `model` field) that pipes the hook payload to a helper
  299     script which extracts `.model` and writes
  300     `~/.dabbler/current-orchestrator.json` with `signalKind: "current"`,
  301     `confidence: "high"`, `effort.normalized: "medium"`, `effort.signalKind: "current"`.
  302     Helper script ships at
  303     `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`.
  304     **Marker writer implements retry loop** (3 attempts: 50ms / 150ms / 400ms
  305     backoff) per audit S5 to handle Windows file-lock contention with
  306     the VS Code file watcher.
  307  6. **Effort tracking (best-effort).** Also install a `UserPromptSubmit`
  308     hook that detects `/think*` invocations in user messages and updates
  309     the marker's `effort.normalized` with `effort.signalKind: "last-observed"`
  310     and `effort.native: "/think"` (or megathink/ultrathink). **If
  311     `UserPromptSubmit` does not expose message text in its payload,
  312     fall back to Medium-only effort for Claude** and document the
  313     limitation in CHANGELOG. Verify field availability as the first
  314     step of implementation.
  315  7. **Layer 3 Playwright smoke + screenshot assertions.** Scenarios at
  316     `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`:
  317     - seed marker with Claude Opus + `signalKind: "current"`, assert
  318       solid-fill gauge needle in flagship zone
  319     - rewrite with Haiku + `signalKind: "current"`, assert needle moves
  320       to low zone
  321     - rewrite with `effort.signalKind: "last-observed"`, assert
  322       hollow-rim visual treatment on effort gauge
  323     - rewrite `updatedAt` to 9h ago, assert stale state (stripes + "last
  324       updated 9h ago" annotation)
  325     - **Screenshot assertion** verifies the view container ordering
  326       (orchestrator indicator above session sets tree).
  327  8. **Version bump:** `package.json` 0.13.17 → 0.13.18.
  328  9. **CHANGELOG:** new entry under 0.13.18 noting Claude-only v1
  329     preview with explicit limitations: starting model only (no runtime
  330     `/model` detection in v1); effort best-effort (Medium default plus
  331     last-observed `/think*` if `UserPromptSubmit` hook supports message
  332     text); manual-override quickpick available for any state the hook
  333     misses. Mark non-Claude paths as "coming in 0.14.0".
  334  
  335  **Creates:**
  336  - `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  337  - `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
  338  - `tools/dabbler-ai-orchestration/scripts/write-orchestrator-marker.js`
  339  - `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`
  340  - `tools/dabbler-ai-orchestration/media/orchestrator-indicator/` (CSS, optional fonts/icons)
  341  
  342  **Touches:**
  343  - `tools/dabbler-ai-orchestration/package.json` (view registration, command, version)
  344  - `tools/dabbler-ai-orchestration/src/extension.ts` (register provider + command)
  345  - `tools/dabbler-ai-orchestration/CHANGELOG.md`
  346  - `CLAUDE.md` (brief note under "VS Code extension" pointing at the new view)
  347  
  348  **Ends with:** Claude Code path live; Playwright smoke passing locally;
  349  0.13.18 packaged but not yet published (publish in S4).
  350  
  351  **Progress keys:** `session-002/webview-registered`, `session-002/provider-implemented`,
  352  `session-002/marker-watcher-wired`, `session-002/claude-hook-installer-shipped`,
  353  `session-002/playwright-smoke-green`, `session-002/version-bumped`
  354  
  355  **Estimated cost:** $0.10–$0.30 (single end-of-session verification;
  356  implementation work is all local Claude tokens).
  357  
  358  ---
  359  
  360  ### Session 3 of 4: Non-Claude provider detection + manual override

--- docs/session-sets/029-orchestrator-model-effort-gauges/spec.md lines 360-440 ---
  360  ### Session 3 of 4: Non-Claude provider detection + manual override
  361  
  362  **Goal:** Add detection paths per the Session 1 audit's locked
  363  resolutions: Codex auto-detect via `~/.codex/config.toml` watcher
  364  (configured-default signal); Gemini Code Assist and GitHub Copilot
  365  manual-only in v1 (no documented persisted state). Universal
  366  manual-override quickpick with MRU + hotkey-bindable args.
  367  
  368  **Steps (REVISED per audit 2026-05-17):**
  369  
  370  1. **Codex detection (auto).** Read `~/.codex/config.toml` on extension
  371     activation and via filesystem watcher. Parse `model` and
  372     `model_reasoning_effort` fields. Write marker with
  373     `signalKind: "configured-default"`, `confidence: "medium"`,
  374     `effort.signalKind: "configured-default"`. **Document honestly**
  375     in the hover tooltip: "configured default from `~/.codex/config.toml` —
  376     does not track runtime `/model` changes". Marker writer reuses the
  377     retry-loop helper from Session 2.
  378  2. **Gemini Code Assist: manual-only.** Per audit Q2 — no documented
  379     persisted state. The `Dabbler: Install Orchestrator Hook (Gemini Code Assist)`
  380     command opens the manual-override quickpick with `provider: "google"`
  381     pre-selected. No actual hook is installed.
  382  3. **GitHub Copilot: manual-only.** Per audit Q4 — old settings keys
  383     deprecated, no current public key. The `… (GitHub Copilot)` command
  384     opens the manual-override quickpick with `provider: "github"`
  385     pre-selected. No actual hook installed.
  386  4. **Manual-override quickpick** (`dabbler.setOrchestrator`):
  387     - Multi-step quickpick: provider → model → effort → thinking on/off
  388       → writes marker file with `signalKind: "manual"`, `confidence: "high"`.
  389     - **MRU ordering**: most recently used `<provider, model, effort, thinking>`
  390       tuples surface first. Stored in `~/.dabbler/orchestrator-mru.json`.
  391     - **Accepts command palette args** for hotkey-bindable presets per
  392       audit E4. Example: operator binds `Ctrl+Shift+Alt+O` to
  393       `dabbler.setOrchestrator` with args `{"provider":"anthropic","model":"claude-opus-4-7","effort":"high","thinking":true}`
  394       for one-keystroke "back to Opus full power".
  395     - "(create new hotkey binding)" item at bottom of quickpick: copies
  396       the `keybindings.json` snippet to clipboard pre-filled with the
  397       current selection.
  398  5. **Smart empty-state CTA.** Webview detects which orchestrator
  399     extensions/CLIs are installed (presence of Claude Code, Gemini Code
  400     Assist extension, Codex CLI on PATH, GitHub Copilot extension) and
  401     surfaces the *right* installer/preset command in the "No signal"
  402     CTA — not a generic "install hook" link. If multiple are detected,
  403     show the most-recently-used per MRU.
  404  6. **Playwright smoke expansion.** Add scenarios:
  405     - `signalKind: "configured-default"` for Codex — verify striped fill
  406       visual treatment on both gauges
  407     - `signalKind: "manual"` for Gemini and Copilot — verify operator-icon
  408       overlay visual treatment
  409     - MRU quickpick reordering (write 3 manual overrides, reopen
  410       quickpick, assert MRU order)
  411  7. **Version bump:** 0.13.18 → 0.14.0 (minor — multi-provider
  412     feature-complete).
  413  
  414  **Creates:**
  415  - `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
  416  - `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCodex.ts`
  417  - `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
  418  - `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts`
  419  - (possibly) provider-specific shim scripts under
  420    `tools/dabbler-ai-orchestration/scripts/`
  421  
  422  **Touches:**
  423  - `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  424    (smarter empty-state CTA)
  425  - `tools/dabbler-ai-orchestration/package.json` (4 new commands, version)
  426  - `tools/dabbler-ai-orchestration/src/extension.ts`
  427  - `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`
  428  - `tools/dabbler-ai-orchestration/CHANGELOG.md`
  429  
  430  **Ends with:** All four orchestrator surfaces are supported (auto
  431  where viable, manual override where not). Layer 3 smoke green for
  432  all four. 0.14.0 packaged but not published.
  433  
  434  **Progress keys:** `session-003/gemini-detection`, `session-003/codex-detection`,
  435  `session-003/copilot-detection`, `session-003/manual-override-shipped`,
  436  `session-003/smart-empty-state`, `session-003/playwright-smoke-all-four`
  437  
  438  **Estimated cost:** $0.10–$0.30.
  439  
  440  ---

--- docs/session-sets/029-orchestrator-model-effort-gauges/spec.md lines 490-534 ---
  490  ## Risks
  491  
  492  - **R1 — Detection viability.** The audit may discover that
  493    Gemini/Codex/Copilot expose no programmatic way to read current
  494    effort/model. Mitigation: manual-override command is the universal
  495    fallback; v1 ships honestly with "manual only" for any surface
  496    that can't be auto-detected.
  497  - **R2 — Hook payload format drift.** Claude Code's Stop hook payload
  498    schema may change between extension versions. Mitigation: the
  499    helper script (`write-orchestrator-marker.js`) parses defensively
  500    and falls back to a "Claude (unknown model)" marker on schema
  501    miss; no crash.
  502  - **R3 — 100px is tight.** If audit reviewers prefer larger gauges
  503    for legibility, we may need to compromise: ≤100px content area
  504    (excluding VS Code's view header). Audit reviews this explicitly.
  505  - **R4 — Marker-file race conditions.** Multiple orchestrator
  506    surfaces writing the same marker file could race. Mitigation:
  507    atomic writes (write + rename) per the audit's Q1 resolution.
  508  - **R5 — Windows atomic-write contention** (added per audit S5).
  509    Atomic write-and-rename on Windows 11 intermittently throws
  510    `PermissionError` when the VS Code file watcher is active on the
  511    target. Mitigation: all marker writers (Claude SessionStart hook
  512    script, Codex config.toml watcher, manual-override quickpick)
  513    implement retry loop with exponential backoff: 3 attempts at
  514    50ms / 150ms / 400ms. Helper shared across all four writer paths.
  515  - **R6 — `UserPromptSubmit` hook may not expose message text**
  516    (added per audit). Required to detect `/think*` invocations for
  517    Claude effort tracking. Mitigation: Session 2 step 6 verifies field
  518    availability first; if not available, falls back to Medium-only
  519    effort for Claude (already the audit-locked default) and documents
  520    the limitation in CHANGELOG. No code crash either way.
  521  
  522  ## Routing notes
  523  
  524  - Audit calls (S1): `task_type='cross-provider-audit'`, two
  525    verifiers (gpt-5-4 + gemini-pro).
  526  - Session-end verification (S1, S2, S3, S4): `task_type='session-verification'`,
  527    single verifier (gpt-5-4).
  528  - Implementation work (S2, S3, S4): pure Claude tokens, no router
  529    invocation per memory `feedback_ai_router_usage`.
  530  
  531  ## Total estimated cost
  532  
  533  $0.55 – $1.55 (sum of per-session estimates above; mostly S1's
  534  two-verifier audit). Well within the operator's typical NTE range.