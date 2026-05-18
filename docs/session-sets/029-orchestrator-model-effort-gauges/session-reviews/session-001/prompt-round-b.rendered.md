# Round B verification — Set 029 Session 1 (orchestrator model & effort indicator gauges)

## Context

Round A (your previous verification call on this synthesis) returned
**REJECTED** with concrete must-fix items spanning two buckets:

**Bucket 1 — doc-accuracy drift fixes (no design judgment):**

1. Audit-summary "Both reviewers agreed" wording for Q1 and
   "accepts fallback dominance" for Q2/Q3/Q4 overstated Gemini's
   participation. Should reword as GPT-explicit / Gemini-silent.
2. Audit-summary schema bullet referred to `model.signalKind` but
   no `model` object exists in v2 — top-level `signalKind` applies
   to the model signal.
3. Spec R2 still talked about Stop-hook payload drift even though
   Stop was rejected. Should reference SessionStart / UserPromptSubmit.
4. Spec routing notes + total cost still assumed router-based S1
   audit. Reality is $0.00 manual paste-and-collect; waiver should
   be durably documented in spec.md.
5. Audit-summary single-quickpick vs spec multi-step quickpick
   inconsistency. Pick one and align both docs.

**Bucket 2 — design refinements (each routed through cross-engine
consensus call, both engines accepted the direction):**

1. Multi-writer precedence policy (Q7 #1 — only true architectural
   gap). Policy: `current` > `manual` > `last-observed` >
   `configured-default`; writers read-check-rewrite with re-read
   immediately before atomic rename to close the TOCTOU race.
   Manual-override has force-override escape hatch.
2. `configured-default` vs stale visual collision. Stripes now
   stale-only; `configured-default` uses dashed rim + "DEFAULT"
   pill badge.
3. `last-observed` strengthened: hollow rim + filled needle +
   clock-icon overlay + time-elapsed sublabel.
4. Windows retry ceiling bumped from 3 attempts / 600ms to 5
   attempts (initial + 4 retries) / 50/200/600/1200ms / ~2050ms.
5. Initial-size limitation documented explicitly (container height
   cannot be guaranteed; drag divider to reset; content scrollable
   if compressed).
6. `confidence` field operationalized: Claude hook helper emits
   `confidence: "low"` + `model: "unknown"` on missing/null/
   unparseable payload; tooltip surfaces the reason.
7. `/clear`-vs-`SessionStart` dual-condition verification added to
   Session 2 step 5; **R7** added to Risks; clobber gated on BOTH
   `/clear` firing SessionStart AND resetting effort semantically.

## What you're being asked in Round B

For each Round-A must-fix item above, verify the fix is present in
the updated artifacts inlined below. Specifically:

- **Bucket 1 #1:** check `audit-summary.md` convergence table +
  Q1 reasoning + post-audit-verification note.
- **Bucket 1 #2:** check `audit-summary.md` "Changes from the
  original proposal" bullets.
- **Bucket 1 #3:** check `spec.md` R2.
- **Bucket 1 #4:** check `spec.md` "Routing notes" + "Total
  estimated cost" + Session 1 step 2 (waiver).
- **Bucket 1 #5:** check `audit-summary.md` "Manual-override
  quickpick UX" + `spec.md` Session 3 step 4.
- **Bucket 2 #1:** check `audit-summary.md` "Multi-writer
  precedence" + `spec.md` R4 + Session 2 step 5 + Session 3 step 1
  (Codex writer reuse note).
- **Bucket 2 #2:** check `audit-summary.md` "Visual treatment by
  signalKind" + `spec.md` Session 2 step 2 + Session 3 step 6
  (Playwright reflects no-stripes-for-configured-default).
- **Bucket 2 #3:** check `audit-summary.md` visual matrix + Q1
  reasoning + `spec.md` D6 footnote + Session 2 step 2.
- **Bucket 2 #4:** check `audit-summary.md` S5 mitigation +
  `spec.md` R5 + Session 2 step 5.
- **Bucket 2 #5:** check `audit-summary.md` S3 mitigation + `spec.md`
  Session 2 step 9 CHANGELOG bullets.
- **Bucket 2 #6:** check `audit-summary.md` "Changes from the
  original proposal" confidence bullet + `spec.md` Session 2 step 5.
- **Bucket 2 #7:** check `spec.md` D6 footnote + Session 2 step 5
  pre-implementation verification + R7.

Format response as:

```
B1-1: ADDRESSED | PARTIAL (…) | NOT ADDRESSED (…)
B1-2: …
…
B2-7: …
```

Then a final verdict line:

```
VERDICT: VERIFIED | REJECTED (<bulleted new issues>)
```

VERIFIED if all 12 items are addressed and no NEW must-fix issues
surface. REJECTED if any item remains or new issues appear. Cite
specific line numbers for any remaining issue; skip stylistic nits.


---

## Doc 1: audit-summary.md (updated)

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

The two reviewers converged on the most consequential finding (Q5).
Where one was silent and the other spoke, the speaker's verdict
stands; the table below distinguishes "agreed" from "carried by one
reviewer" rather than overclaiming consensus.

| Topic | GPT-5.4 | Gemini Pro | Outcome |
|---|---|---|---|
| Q5 — Claude Stop hook | Wrong on field-availability (Stop has no `model`) | Wrong on timing (Stop is lagging) | **Strong agreement**: reject Stop, use SessionStart |
| Q1 — Claude effort | Explicit: Medium default; `/think*` as `last-observed`, not current | Did not directly address `/think*` persistence; spoke to the broader anti-lagging-signal concern via `Stop` framing | **GPT-5.4 explicit; Gemini supports broader anti-lagging-signal concern** |
| Q2 — Gemini Code Assist detection | Manual-only for v1 (no documented persisted state) | Silent | **GPT-5.4 carries; no contradiction** |
| Q3 — Codex detection | Read `config.toml` as `configured-default` | Silent | **GPT-5.4 carries; no contradiction** |
| Q4 — GitHub Copilot detection | Manual-only for v1 (deprecated keys, no public replacement) | Silent | **GPT-5.4 carries; no contradiction** |
| Q6 — staleness | 8h default; distinct from no-signal | Silent | **GPT-5.4 carries** |
| Windows atomic-write contention | Not raised | Raised as showstopper (retry loop + backoff required) | **Unique to Gemini, accepted** |
| Schema additions (signalKind, confidence) | Strongly raised | Not raised | **Unique to GPT, accepted** |
| Manual override UX (MRU + hotkeys) | Not raised | Raised as escalation | **Unique to Gemini, accepted** |

There were no substantive contradictions between the reviewers.

> **Post-audit verification (2026-05-18).** A session-verification
> call against this synthesis (gpt-5-4, $0.26) flagged that the
> original "Both reviewers agreed" framing on Q1 and "accepts
> fallback dominance" framing on Q2/Q3/Q4 overstated Gemini's
> participation. The table above is the post-verification rewording.
> A subsequent cross-engine consensus call (gpt-5-4 + gemini-pro,
> $0.085 total) approved the seven design refinements below
> (multi-writer precedence policy, visual-treatment matrix update,
> retry-ceiling bump, etc.) before Session 1 close-out.

---

## Locked resolutions for Q1–Q6

### Q1 — Claude Code effort representation
**LOCKED: option (b)+(c) hybrid.**

For Claude Code sessions, the effort gauge shows **Medium (default)**
unless a `/think*` invocation has been observed within the current
session, in which case the gauge displays the corresponding tier
with `signalKind: "last-observed"` and the time-elapsed in the
sublabel (e.g., "High (last /think 12m ago)"). On `SessionStart`,
the effort tier resets to Medium — provided that `/clear` also
resets effort semantically; otherwise the `last-observed` signal is
preserved across `/clear` (see Session 2 pre-implementation
verification step in `spec.md` and **R7** in the spec's Risks
section).

**Reasoning:** GPT-5.4 explicitly recommended Medium-default with
`/think*` shown only as `last-observed`. Gemini did not address
`/think*` persistence directly but voiced the broader anti-lagging-
signal concern (against treating any post-hoc reading as a current
indicator); the hybrid honors both. The time-elapsed suffix replaces
the bare "(last)" qualifier because the elapsed time visibly ages
on screen — a stronger "this is not live" cue than rim styling alone
at small gauge sizes (per post-audit verifier finding 2026-05-18).

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
| S3 | `initialSize` is not in VS Code's contributes.views spec | GPT-5.4 | Drop `initialSize` from the proposal. Treat ordering/sizing as best-effort. Add Playwright screenshot assertions in Session 2 (clean-profile only). **Container height cannot be guaranteed**: VS Code persists user-resized view heights across sessions and extension updates; if the operator has previously dragged the view divider, that height is restored. To reset, drag the divider back. The CSS uses `overflow: auto` so content remains scrollable if compressed below 100px. Document this limitation in `CHANGELOG.md` for 0.13.18. |
| S4 | Stop hook timing makes gauge lagging | Gemini | Same fix as S1 (SessionStart fires before turn starts) |
| S5 | Windows atomic-write contention with file watcher → PermissionError | Gemini | Shim script implements retry loop with exponential backoff. **REVISED 2026-05-18** (post-audit verifier finding): 5 total attempts (initial + 4 retries) at 50/200/600/1200ms backoff between attempts, ~2050ms total ceiling. The previous 3-attempt/600ms ceiling was too short for typical Windows file-watcher + antivirus contention. Reused across all four provider writers via shared helper. |

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
  `"last-observed"` | `"manual"`. Top-level `signalKind` describes
  the **model** signal. Drives visual treatment of the model gauge.
- **`confidence`** (new, top-level): `"high"` | `"medium"` | `"low"`.
  Top-level `confidence` describes the **model** signal. Surfaced in
  tooltip copy (see "Visual treatment by signalKind" below);
  doesn't drive gauge color directly. **Concrete producer rule
  (REVISED 2026-05-18 per consensus call):** Session 2's Claude
  hook helper script emits `confidence: "low"` + `model: "unknown"`
  when the SessionStart hook payload's `.model` field is missing,
  null, or unparseable — exercising the field in v1 rather than
  reserving it for future use.
- **`effort.signalKind`** + **`effort.confidence`** (new, nested):
  effort can have a *different* signalKind from the top-level
  (model) signal — e.g., Claude with top-level `signalKind="current"`
  (just session-started) but `effort.signalKind="last-observed"`
  (a `/think*` was issued mid-session).
- **`stalenessMaxSec`**: default raised from 3600 (1h) to 28800 (8h).

### Visual treatment by signalKind (REVISED 2026-05-18)

The previous matrix collided `configured-default` (diagonal stripes)
with the stale-state treatment (also stripes). Diagonal stripes are
now **stale-only** (signal-agnostic, overlaid at 50% opacity on
whatever the underlying signalKind treatment is). `configured-default`
gets a dashed rim plus a small "DEFAULT" pill badge. The
`last-observed` treatment additionally gets a small clock-icon
overlay and a time-elapsed sublabel suffix, because hollow rim alone
proved too easy to misread as live at small gauge sizes.

| signalKind | Gauge fill | Rim | Sublabel suffix | Badge / overlay | Tooltip |
|---|---|---|---|---|---|
| `current` | Solid color | Solid | (none) | (none) | "live signal (high confidence)" |
| `configured-default` | Solid color (~85% opacity) | Dashed | "(default)" | "DEFAULT" pill below model name | "configured default (medium confidence — does not track runtime changes from ~/.codex/config.toml)" |
| `last-observed` | Hollow rim + filled needle | Solid | "(last /think Xm ago)" | small clock-icon overlay (top-right of gauge, ~12×12px) | "last observed Xm ago via /think (high confidence in detection, but may not reflect current message)" |
| `manual` | Solid + small operator-icon overlay | Solid | "(manual)" | (overlay only) | "set manually at HH:MM (high confidence)" |

Stale state (signal-agnostic): diagonal hatch overlay at 50% opacity
over whatever the underlying signalKind treatment is, plus "last
updated Xh ago" annotation. No install-hook CTA. When the underlying
signalKind has its own pattern (e.g., `configured-default`'s dashed
rim), the stripes overlay on top — the two cues are distinguishable
because stale stripes hatch the entire gauge while `configured-default`
only modifies the rim.

If `confidence: "low"` is set (e.g., Claude hook payload missing
the `model` field), the tooltip's confidence parenthetical reflects
that: "live signal (low confidence — hook payload missing model)".

---

## Multi-writer precedence (NEW — locked 2026-05-18)

Marker file `~/.dabbler/current-orchestrator.json` is global and
single-canonical; four providers may write it concurrently. Without
arbitration, a Codex `configured-default` background write could
stomp a fresh Claude `current` signal — exactly the failure mode
this feature exists to prevent.

**Policy.** Marker writers MUST read the current file, compare
`signalKind` precedence, and skip the write if the proposed signal
is weaker than the existing fresh signal.

Precedence (high → low): `current` > `manual` > `last-observed` >
`configured-default`.

Decision tree (run by every writer, including the Codex config.toml
watcher, the Claude SessionStart hook helper, and the manual-override
quickpick):

1. Read existing marker. If missing → write unconditionally.
2. If existing `updatedAt` is older than `stalenessMaxSec` (8h
   default) → write unconditionally; stale signals never block a
   fresh write.
3. **Immediately before the atomic write+rename**, re-read the
   target. If `signalKind` precedence of the proposed write ≥
   precedence of the existing target → proceed with rename. The
   re-read closes the time-of-check / time-of-use race between an
   initial precedence check and the rename.
4. If the rename detects the target was modified mid-flight (e.g.,
   another writer raced ahead between the re-read and the rename),
   retry the read-and-precedence-check up to the same 5-attempt
   ceiling as S5 (50/200/600/1200ms backoff). After exhaustion,
   skip the write.
5. On skipped writes, append a line to
   `~/.dabbler/orchestrator-writer.log` (`{timestamp, writer,
   proposed, existing, reason}`) for operator diagnostics.

**Manual-override escape hatch.** The manual-override quickpick has
explicit "force override" semantics: if it detects a fresher
`current`-precedence signal from another writer, it shows a
"Override existing live signal from <writer>?" confirmation. This
keeps the operator in control when they explicitly want to set the
gauge despite a live signal.

**Implementation surface.** ~30 LOC added to the shared
`write-orchestrator-marker.js` helper (Session 2); the manual-override
command (Session 3) layers the force-override confirmation on top.

---

## Manual-override quickpick UX (NEW REQUIREMENT — locked)

Per Gemini's E4 escalation, the manual-override command must:

1. Open a quickpick whose top section lists the most recently used
   `<provider> + <model> + <effort> + <thinking>` **tuples**
   ("Anthropic Opus 4.7 — High effort, Thinking on"), one tuple per
   row, sorted MRU. Selecting a tuple applies it directly. A
   bottom row "(set new combination…)" enters a multi-step flow
   (provider → model → effort → thinking on/off) for novel
   combinations. Store MRU in `~/.dabbler/orchestrator-mru.json`.
   *Note: the spec.md text describing this UX was previously
   inconsistent — both docs now use this single-picker-with-MRU-plus-
   multi-step-fallback shape.*
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
- [ ] Pre-implementation verification: check whether `/clear` fires
      `SessionStart` AND whether `/clear` resets effort to Medium
      semantically. Only clobber a fresh `last-observed` signal on
      `/clear` if BOTH are true; otherwise preserve. Document the
      asymmetry in CHANGELOG and as **R7** in spec.md.
- [ ] Implement marker schema v2 with `signalKind` + `confidence`.
      Claude hook helper script emits `confidence: "low"` + `model:
      "unknown"` when payload's `.model` is missing/null/unparseable
      (exercises the confidence field in v1).
- [ ] Helper script uses write-and-rename with retry loop (**5
      attempts: initial + 4 retries, 50/200/600/1200ms backoff,
      ~2050ms total**) per S5 REVISED 2026-05-18.
- [ ] **Multi-writer precedence**: helper script implements the
      read-check-rewrite decision tree with re-read immediately
      before atomic rename. ~30 LOC; reused by Session 3 writers.
- [ ] Effort gauge: Medium default for Claude; `last-observed`
      styling (hollow rim + filled needle + clock-icon overlay +
      time-elapsed sublabel) if a `/think*` is detected via
      `UserPromptSubmit` hook (verify field availability — fall
      back to Medium-only if not).
- [ ] Webview HTML/CSS implements REVISED visual-treatment matrix:
      stripes are stale-only; `configured-default` uses dashed rim
      + "DEFAULT" pill badge; `last-observed` gets clock-icon
      overlay + time-elapsed suffix; `manual` gets operator-icon
      overlay.
- [ ] Drop `initialSize` from package.json view contribution.
      Document in CHANGELOG that container height cannot be
      guaranteed (VS Code persists user-resized heights; reset by
      dragging the divider back).
- [ ] Playwright smoke includes signalKind=current AND signalKind=last-observed
      AND signalKind=configured-default scenarios (clean profile).
- [ ] Last-updated timestamp visible in all states.
- [ ] Tooltip copy embeds confidence-level explicitly (per matrix
      above): "live signal (high confidence)", "configured default
      (medium confidence — does not track runtime changes)", etc.

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

- **Audit calls (original synthesis, 2026-05-17): $0.00.** Manual
  paste-and-collect — no `ai_router.route()` invocation per memory
  `feedback_ai_router_usage`. The pre-authored `route_audit.py`
  helper from spec step 2 was waived as part of this; operator
  confirmed the waiver 2026-05-18 at Session 1 resume time.
- **Round A verification call (2026-05-18, gpt-5-4): $0.26.**
  Caught overclaimed-agreement wording (Q1, Q2/Q3/Q4 convergence
  rows), schema wording bug, Stop-hook drift in spec R2, routing
  notes drift, the multi-writer arbitration gap (Q7 #1), retry-
  ceiling underspecification, and stale/configured-default visual
  collision. All resolved before close-out.
- **Bucket-2 consensus call (2026-05-18, gpt-5-4 + gemini-pro):
  $0.085** ($0.08 gpt + $0.004 gemini). Both engines accepted the
  proposed direction on all seven Bucket-2 items; gpt-5-4 added
  tightening modifications on five of them (race-window re-read,
  attempt-count math, scrollable-not-horizontally wording,
  confidence-low producer rule, dual-condition `/clear` check).
  All absorbed in this revision.
- **Round B verification call (2026-05-18, gpt-5-4): pending** — to
  confirm the Bucket-1 and Bucket-2 fixes are coherently applied
  before close-out.
- **Total Session 1 cost: $0.345** before Round B (forecast ~$0.55
  inclusive of Round B). Well within the operator's $5.00 NTE
  ceiling for the set.
- Forecast for remaining set (S2-S4): $0.30-$0.90 across three
  end-of-session verification calls (range based on memory
  `project_verification_cost_empirical` p50=$0.13, p95=$1.82).


---

## Doc 2: spec.md (updated)

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
totalSessions: 4
```

> **Rationale on `effort: high`:** the hard part isn't the gauge; it's
> the cross-provider detection (Claude has hooks, others don't), and
> verifying the design holds up across four orchestrator surfaces
> before committing the implementation. The audit session (S1) plus
> the multi-provider detection session (S3) are both Opus-class work.
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
  (via filesystem watch on a marker file written by per-surface hooks)
- Shows a graceful "No signal — install hook" CTA when the marker file
  is missing or stale (>1h since last update)
- Exposes a one-click "Install Orchestrator Hook" command that writes
  the appropriate hook for the active orchestrator surface (Claude
  Code = Stop hook in `~/.claude/settings.json`; others = best-effort
  per provider; manual override quickpick as universal fallback)

---

## Decisions locked from operator dialogue (do not re-litigate)

| # | Decision | Locked value |
|---|---|---|
| D1 | Provider scope | **All four orchestrator surfaces**: Claude Code, Gemini Code Assist Agent, Codex, GitHub Copilot. v1 ships best-effort detection for each plus manual override as universal fallback. |
| D2 | Layout | **Two side-by-side semi-circle gauges** plus a binary "Thinking" LED beside the effort gauge. Three-gauge variants rejected; binary thinking-on/off doesn't warrant a third gauge. |
| D3 | Height budget | **≤100px total visible content** (operator's hard constraint). VS Code's standard view header (~22px) sits above this. Semi-circle gauges at ~70-80px tall fit comfortably; full-circle gauges do not. |
| D4 | Location | **New webview view (`dabblerOrchestratorIndicator`) pinned above `dabblerSessionSets` in the existing `dabblerSessionSetsContainer`.** Not a status-bar item (operator's framing was "panel at the top of Session Set Explorer"). |
| D5 | Color polarity | **Red = low-tier / low-effort (warning state), green = flagship / max-effort (preferred state).** Inverts the conventional "red = expensive" mapping because the operator's stated failure mode is *forgetting to switch back up*, not *spending too much*. |
| D6 | Effort scale | **Five normalized levels** (Low / Medium / High / Extra-High / Max), mapping from provider-native scales as follows. Thinking on/off is a separate binary LED. |
| D7 | Marker file | **`~/.dabbler/current-orchestrator.json`** (global, user-home, single canonical file). Multi-writer: each provider's hook/shim writes the same file. Schema in Session 1 audit deliverable. |
| D8 | Hook installer | **Per-provider commands, but only Claude installs an actual hook** (per audit Q2/Q4/Q5): Claude = `SessionStart` hook in `~/.claude/settings.json` (NOT `Stop` — Stop has no `model` field per audit S1). Codex = `~/.codex/config.toml` watcher (no user-facing install; auto-activates). Gemini/Copilot = "installer" command opens the manual-override quickpick with provider preset (manual-only in v1). Universal manual-override (`Dabbler: Set Orchestrator Model & Effort`) supports MRU ordering + hotkey-bindable command args per audit E4. |
| D9 | Set structure | **Single set, audit-then-implement.** 4 sessions: S1 design audit, S2 core webview + Claude path, S3 non-Claude detection, S4 polish + release. |
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
  total ceiling) in all marker writers (Session 2 / Session 3
  implementation). Shared helper also implements multi-writer
  precedence read-check-rewrite (see audit-summary §"Multi-writer
  precedence").

### Marker schema bumped to v2

The audit introduced two new schema fields (`signalKind` and
`confidence`) with breaking semantics; canonical schema lives in
`audit-summary.md` "Marker file schema (REVISED — locked)" section.

---

## Sessions

### Session 1 of 4: Cross-provider design audit

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

### Session 2 of 4: Core webview + Claude detection + hook installer

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
   reused by Session 3 writers.
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
0.13.18 packaged but not yet published (publish in S4).

**Progress keys:** `session-002/webview-registered`, `session-002/provider-implemented`,
`session-002/marker-watcher-wired`, `session-002/claude-hook-installer-shipped`,
`session-002/playwright-smoke-green`, `session-002/version-bumped`

**Estimated cost:** $0.10–$0.30 (single end-of-session verification;
implementation work is all local Claude tokens).

---

### Session 3 of 4: Non-Claude provider detection + manual override

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
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCodex.ts`
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
- `tools/dabbler-ai-orchestration/src/commands/setOrchestratorManual.ts`
- (possibly) provider-specific shim scripts under
  `tools/dabbler-ai-orchestration/scripts/`

**Touches:**
- `tools/dabbler-ai-orchestration/src/providers/orchestratorIndicatorProvider.ts`
  (smarter empty-state CTA)
- `tools/dabbler-ai-orchestration/package.json` (4 new commands, version)
- `tools/dabbler-ai-orchestration/src/extension.ts`
- `tools/dabbler-ai-orchestration/tests/playwright/orchestrator-indicator.spec.ts`
- `tools/dabbler-ai-orchestration/CHANGELOG.md`

**Ends with:** All four orchestrator surfaces are supported (auto
where viable, manual override where not). Layer 3 smoke green for
all four. 0.14.0 packaged but not published.

**Progress keys:** `session-003/gemini-detection`, `session-003/codex-detection`,
`session-003/copilot-detection`, `session-003/manual-override-shipped`,
`session-003/smart-empty-state`, `session-003/playwright-smoke-all-four`

**Estimated cost:** $0.10–$0.30.

---

### Session 4 of 4: Polish, README, marketplace publish

**Goal:** Final polish, README update with screenshot, version bump to
0.14.1 if anything moves, publish to Marketplace.

**Steps:**

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

**Progress keys:** `session-004/readme-updated`, `session-004/changelog-merged`,
`session-004/claudemd-expanded`, `session-004/marketplace-published`,
`session-004/consumer-repos-notified`

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
- **R4 — Marker-file race conditions.** Multiple orchestrator
  surfaces writing the same marker file could race. Mitigation:
  atomic writes (write + rename) plus **multi-writer precedence**
  (REVISED 2026-05-18 per audit-summary §"Multi-writer precedence"):
  every writer reads the existing target, compares `signalKind`
  precedence (`current` > `manual` > `last-observed` >
  `configured-default`), re-reads immediately before the atomic
  rename to close the TOCTOU race window, and skips the write if
  the proposed signal is weaker than a fresh existing signal.
  Skipped writes are logged to `~/.dabbler/orchestrator-writer.log`.
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

## Routing notes (REVISED 2026-05-18)

- **Audit calls (S1): WAIVED.** The originally-planned
  `route_audit.py` call was waived per memory `feedback_ai_router_usage`
  (router reserved for end-of-session verification). The audit was
  conducted by manual paste-and-collect against GPT-5.4 + Gemini
  Pro; raw responses preserved at
  `docs/proposals/2026-05-17-model-effort-gauges-design-audit/{gpt-5-4,gemini-pro}-result.json`.
  Cost: **$0.00**.
- **Session-end verification (S1, S2, S3, S4):**
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
  implementation work in S2/S3/S4 still uses pure Claude tokens.
- **Implementation work (S2, S3, S4):** pure Claude tokens, no
  router invocation.

## Total estimated cost (REVISED 2026-05-18)

- **Session 1 actual: $0.345** (Round A verification $0.26 +
  cross-engine consensus $0.085); plus forecast Round B ~$0.20 =
  **~$0.55 inclusive of Round B**.
- **Sessions 2–4 forecast: $0.30 – $0.90** (three session-end
  verifications; range based on memory `project_verification_cost_empirical`
  p50=$0.13, p95=$1.82).
- **Total forecast: $0.85 – $1.45**, against the operator's
  **$5.00 NTE ceiling** for the set (confirmed 2026-05-18 at S1
  resume time).
