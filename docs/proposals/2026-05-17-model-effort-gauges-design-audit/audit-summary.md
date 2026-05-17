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
