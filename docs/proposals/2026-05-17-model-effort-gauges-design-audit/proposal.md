# Design audit: orchestrator model & effort indicator gauges

**Audience:** GPT-5.4 and Gemini Pro acting as cross-provider design
reviewers. Each reviewer reads this doc independently; the operator
synthesizes both verdicts into a single locked summary.

**Reviewer role:** Senior software engineer / UX-engineer hybrid.
Familiar with VS Code extension architecture, multi-provider AI
coding tools (Claude Code, Gemini Code Assist Agent, Codex CLI,
GitHub Copilot), and the realities of detecting "current state"
across heterogeneous IDE-integrated AI agents.

**Decision posture:** Ten design decisions are **locked** (the
operator has chosen; the reviewer should not relitigate them —
flag any showstopper concerns explicitly, otherwise move on). Six
questions are **open** — these are the focus of the audit.

**Output format requested:** at the end of this document. Please
return a JSON object plus freeform commentary as specified.

---

## 1. Problem statement

The operator routinely runs four different AI orchestrator surfaces
from inside VS Code: **Claude Code** (CLI/IDE), **Gemini Code Assist
Agent** (VS Code extension), **Codex** (CLI), and **GitHub Copilot**
(VS Code extension). Each has independent controls for *which model*
is active and *what effort level* it's exerting:

| Surface | Model control | Effort control | "Thinking" toggle |
|---|---|---|---|
| Claude Code | `/model` command | `/think`, `/megathink`, `/ultrathink` invocations | implicit (any `/think*` = on) |
| Gemini Code Assist | model picker UI | Effort: Low / Medium / High / Extra-High / Max | Thinking: on / off |
| Codex | model flag | Intelligence: Low / Medium / High / Extra-High | (no native concept) |
| GitHub Copilot | model picker | Thinking Effort: Low / Medium / High / Extra-High | (no native concept) |

The operator's failure mode: they intentionally flip *down* to a
cheaper model for a quick throwaway task (rename a file, summarize
a directory), then start the next substantive session 30 minutes
later and **forget to flip back up**. The orchestrator silently
does substantive work on a lower-tier model; quality is wrong;
the session is aborted or salvaged 15 minutes in.

The cost is two-sided:

1. **Quality loss** — substantive work on a lower-tier model
   produces weaker output that needs to be redone.
2. **Cost waste** — even a "cheap" model burns budget on work it
   can't complete well, plus the redo cost.

The remedy is a **passive, always-visible signal** — not a command
to query state, not a notification, not a log entry. The operator
needs to glance at the VS Code activity bar and *immediately see*
"I'm on Opus 4.7, effort=high, thinking=on" or "I'm on Haiku 4.5,
effort=low, thinking=off."

---

## 2. Proposed solution (≤100px visible content)

A new **webview view** pinned above the existing Session Set
Explorer tree, in the same activity-bar view container ("Dabbler
AI Orchestration"). The view contains two side-by-side CSS
semi-circle gauges (style reference:
https://dev.to/madsstoumann/how-to-create-gauges-in-css-3581) plus
a thin "Thinking" LED indicator beside the effort gauge.

ASCII mock-up (constraints: ≤100px tall total, VS Code's standard
view header adds ~22px chrome above the content area):

```
┌─ Orchestrator ───────────────────────────────────────────────┐
│                                                              │
│   ▁▁███▁          MODEL    ▁▁███▁          EFFORT  ●Thinking │
│  ◜─────◝                  ◜─────◝                            │
│  └──┬──┘                  └──┬──┘                            │
│  Claude Opus 4.7          High                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Left gauge — Model.** Needle position encodes tier-within-provider.
  Bottom-left zone (red) = low-tier (Haiku / Flash / 4o-mini /
  Copilot's cheapest); middle zone (yellow) = mid-tier (Sonnet /
  Flash 2.5 / 4o); top-right zone (green) = flagship (Opus / Pro /
  o1 / GPT-5). Sublabel shows `<Provider> <Model>` text.
- **Right gauge — Effort.** Normalized 5-tier scale (Low / Medium /
  High / Extra-High / Max). Same red→yellow→green polarity.
  Sublabel shows the tier name.
- **Thinking LED.** Solid green dot when on, hollow grey when off,
  hidden entirely when the active surface has no native "thinking"
  concept.
- **Empty state.** When the marker file is missing or stale, gauges
  render greyed-out with a "No signal — install hook" CTA below.

The view subscribes to a filesystem watcher on
`~/.dabbler/current-orchestrator.json`. Each orchestrator surface
writes to this file via a hook (Claude Code's Stop hook), a shim
script, or a manual-override quickpick command — see Section 4.

---

## 3. Locked design decisions (do not relitigate unless showstopper)

| # | Decision | Locked value |
|---|---|---|
| D1 | Provider scope | All four surfaces. Auto-detect where viable; manual-override quickpick as universal fallback. |
| D2 | Layout | Two side-by-side semi-circle gauges + binary Thinking LED. Three-gauge variants rejected. |
| D3 | Height budget | ≤100px content area (excludes VS Code's ~22px view header). Operator's hard constraint. |
| D4 | Location | New webview view pinned above the existing Session Set Explorer in the same activity-bar container. Not a status-bar item. |
| D5 | Color polarity | **Red = low-tier / low-effort (warning), green = flagship / max-effort (preferred).** Inverts the conventional "red = expensive" mapping because the operator's failure mode is *forgetting to switch back up*, not overspending. |
| D6 | Effort scale | 5 normalized levels (Low / Medium / High / Extra-High / Max). Mapping table in §5 below. |
| D7 | Marker file path | `~/.dabbler/current-orchestrator.json`. Single canonical file, multi-writer. |
| D8 | Hook installers | One per provider (`Dabbler: Install Orchestrator Hook (Claude Code)`, `… (Gemini Code Assist)`, etc.) plus a universal manual-override quickpick (`Dabbler: Set Orchestrator Model & Effort`). |
| D9 | Audit-then-implement | Single session set with 4 sessions: audit → core webview + Claude path → non-Claude providers → polish + publish. |
| D10 | Backwards compatibility | None — net-new view; no migration concerns. Empty marker file = empty state with install CTA. |

---

## 4. Detection strategy per orchestrator surface

**Claude Code.** Claude Code has a `hooks` system in
`~/.claude/settings.json`. A `Stop` hook fires after every assistant
turn and receives a JSON payload on stdin that includes the current
session's model. The hook installer writes a hook entry that pipes
the payload through a small helper script which extracts model +
effort (most recent `/think*` invocation, decaying to Medium on
`SessionStart`) and writes `~/.dabbler/current-orchestrator.json`
atomically (write + rename). **Q5 below: confirm the exact field
name(s) in the Stop hook payload.**

**Gemini Code Assist Agent.** Operator believes the Effort and
Thinking controls are surfaced in the IDE panel. **Q2: does the
agent persist this state to a known location** (VS Code workspace
settings? `~/.gemini/`? IDE output channel?) that an extension can
watch? If no, we ship as "manual-override only" for Gemini.

**Codex.** Intelligence is a per-invocation parameter on the Codex
CLI. **Q3: is there any persistent representation** (config file,
env var the operator typically exports, a recent-invocations log)
we could read? If strictly per-invocation, we ship as manual-only.

**GitHub Copilot.** Thinking Effort is exposed in the chat UI.
**Q4: is this a VS Code setting** (`github.copilot.advanced.*`)
that another extension can read, or is it private to the Copilot
chat session? If the former, watch the settings key. If the latter,
manual-only.

**Manual override (universal fallback).** A single VS Code command
opens a quickpick: provider → model → effort → thinking on/off →
writes the marker file. This is the *guaranteed* path for any
surface auto-detection can't handle.

---

## 5. Effort-level normalization table

| Normalized tier | Claude Code | Gemini Code Assist | Codex | GitHub Copilot |
|---|---|---|---|---|
| Low (0-25) | (no native control)\* | Low | Low | Low |
| Medium (26-50) | (default) | Medium | Medium | Medium |
| High (51-75) | `/think` | High | High | High |
| Extra-High (76-90) | `/megathink` | Extra-High | Extra-High | Extra-High |
| Max (91-100) | `/ultrathink` | Max | (not exposed) | (not exposed) |

\* Claude Code has no per-message effort slider. The "effort" column
for Claude reflects the most recent `/think*` invocation in the
current session. When no `/think*` has been issued, effort = Medium
(the implicit default). On `SessionStart`, effort decays back to
Medium. **The audit may push back on this design** — see Q1 below.

---

## 6. Proposed marker file schema

```json
{
  "schemaVersion": 1,
  "updatedAt": "2026-05-17T14:32:00-04:00",
  "writer": "claude-code-stop-hook",
  "provider": "anthropic",
  "providerDisplayName": "Claude",
  "model": "claude-opus-4-7",
  "modelDisplayName": "Opus 4.7",
  "tier": "flagship",
  "effort": {
    "normalized": "high",
    "native": "/think",
    "thinking": true
  },
  "stalenessMaxSec": 3600
}
```

Field semantics:

- `schemaVersion`: int, bumped on breaking change.
- `updatedAt`: ISO 8601, write timestamp.
- `writer`: which hook/shim wrote this file (for debugging multi-writer
  collisions).
- `provider`: machine key (`anthropic`, `google`, `openai`, `github`).
- `providerDisplayName`: human-readable provider name shown in gauge
  sublabel.
- `model`: machine ID of the current model.
- `modelDisplayName`: human-readable model name shown in gauge
  sublabel.
- `tier`: `"low"` / `"mid"` / `"flagship"`. Drives model-gauge needle
  position.
- `effort.normalized`: `"low"` / `"medium"` / `"high"` / `"extra-high"` /
  `"max"`. Drives effort-gauge needle position.
- `effort.native`: the original provider-native value (`/think`,
  `"Extra-High"`, etc.), preserved for diagnostic hover-text.
- `effort.thinking`: bool, drives the Thinking LED.
- `stalenessMaxSec`: int, after which the view treats the file as
  stale and shows the "stale" empty state.

---

## 7. Open design questions (the audit focus)

The reviewer's job is to answer each of these six questions. For
each, please give:

- A **direct answer** (one of the proposed options, or a new option).
- A **rationale** (1-3 sentences).
- A **confidence level** (`high` / `medium` / `low`) — be honest;
  low-confidence answers on questions you don't have current data
  on are *more useful* than confident-sounding guesses.

---

### Q1 — Claude Code "effort" as most-recent `/think*` invocation

**Proposal:** Track the most recent `/think*` family invocation as
Claude's "effort" tier, decaying to Medium on `SessionStart`. Show
this in the effort gauge for Claude sessions.

**Concerns:**
- `/think*` invocations are per-message, not per-session. Treating
  the most recent as "current effort" may mislead — the next message
  could be back to default.
- Effort gauge would then be a *lagging* indicator for Claude, not
  a *current-state* one.

**Question:** Is the proposed design (most-recent-wins, decay on
SessionStart) sound, or should we (a) hide the effort gauge entirely
for Claude sessions, (b) show Claude's effort as always-Medium with
a footnote, (c) treat the effort gauge as a "last invocation"
indicator and label it as such?

---

### Q2 — Gemini Code Assist detection mechanism

**Proposal:** Watch a VS Code workspace setting or `~/.gemini/`
config file. Fall back to manual override if neither exists.

**Question:** As of 2026-05, does the Gemini Code Assist Agent
expose its current Effort and Thinking state via:

- A VS Code setting key under `geminicodeassist.*`?
- A user-config file at `~/.gemini/<something>`?
- An output channel or log file we could tail?
- Nothing — it's strictly UI-state, internal to the extension?

If you're uncertain, say so. We'd rather ship "manual-only for
Gemini in v1" than ship a broken auto-detect.

---

### Q3 — Codex detection mechanism

**Proposal:** Codex's Intelligence parameter is a CLI flag — likely
ephemeral, no persistent state to read. Ship as manual-override-only.

**Question:** Are we missing a Codex persistence mechanism? Examples:

- A `~/.codex/` or `~/.config/codex/` config file storing the
  default Intelligence?
- An environment variable convention (`CODEX_INTELLIGENCE=high`)
  that operators commonly export?
- A recent-invocations log we could tail to infer "current"
  Intelligence?

Or is "manual-only for Codex" genuinely the right v1 ship?

---

### Q4 — GitHub Copilot detection mechanism

**Proposal:** Watch `github.copilot.*` VS Code settings keys for
Thinking Effort.

**Question:** As of 2026-05, is GitHub Copilot's "Thinking Effort"
exposed as:

- A VS Code setting (`github.copilot.advanced.thinkingEffort` or
  similar)?
- Per-chat-session state, private to the Copilot extension?
- Some other surface (workspace state API, command output)?

What's the actual setting key name, if it exists? If it doesn't
exist as a settable key, manual-only is the answer.

---

### Q5 — Claude Code Stop hook payload field name

**Proposal:** The Stop hook receives a JSON payload on stdin
including a `model` field. The helper script extracts `.model`
and writes the marker file.

**Question:** As of Claude Code's current hook spec (please cite
the version of the docs you're working from if you can):

- What is the exact field name for the active model in the Stop
  hook payload? (`model`, `current_model`, `assistant_model`,
  something nested like `session.model`?)
- Is there a `session_id`, `transcript_path`, or other field worth
  capturing for diagnostic purposes?
- Are there *other* hooks (`SessionStart`, `UserPromptSubmit`,
  `PreToolUse`) that would be more reliable signal sources than
  `Stop` for "current model"?

---

### Q6 — Stale-signal recovery UX

**Proposal:** If the marker file is older than `stalenessMaxSec`
(default 3600s = 1h), the view shows greyed gauges with a "stale —
last update Xh ago" annotation. The "install hook" CTA is NOT shown
in stale state (since a hook was clearly installed at some point).

**Concerns:**
- 1h is arbitrary. Long Claude Code sessions (no Stop hook fires
  if the operator is reading) can exceed this.
- "Stale" and "no signal" are visually similar; the operator might
  conflate them.

**Question:** Is the 1h default sensible? Should the stale state be
visually *more* distinct from "no signal" (e.g., a striped fill
pattern, a different empty-state color)? Or should we drop the
stale concept entirely and trust that the next Stop hook fires
eventually?

---

## 8. Specific asks the reviewer can flag (escalation list)

Beyond the six numbered questions, please flag any of the following
if you spot them — these are showstoppers:

- **Marker file path conflict.** Is `~/.dabbler/current-orchestrator.json`
  already in use by some convention we're stomping on?
- **Atomic-write portability.** Does write-and-rename work on Windows
  the same way as POSIX for this use case? The operator is on
  Windows 11.
- **VS Code webview view `initialSize`.** Is this a real property,
  or does VS Code ignore it for webview views in mixed-type view
  containers? Workaround if not?
- **VS Code 1.85+ API gaps.** The extension's engine is `^1.85.0`.
  Any webview-view APIs we're relying on that require a higher
  baseline?
- **Multi-writer race conditions.** Two surfaces writing the same
  marker file in rapid succession (e.g., operator runs Claude
  Code and Gemini Code Assist in parallel). Is atomic write
  sufficient, or do we need write-locks?

---

## 9. Out of scope (please do not opine on)

- Whether the feature should be built (the operator has decided yes).
- Whether to use TreeView vs webview (locked at webview per D4).
- Whether to use status bar (locked at activity-bar view per D4).
- Whether to use full-circle vs semi-circle gauges (locked at
  semi-circle per D2 — full-circle won't fit in 100px).
- Whether to support more than 4 providers in v1.
- Marketing / copywriting of the README or marketplace listing.

---

## 10. Expected response format

Please return your verdict as a JSON object with the following
shape, followed by freeform commentary:

```json
{
  "reviewer": "<gpt-5.4 | gemini-pro>",
  "reviewedAt": "<ISO 8601>",
  "showstoppers": [
    { "id": "<short-id>", "concern": "<text>", "severity": "blocker|major|minor" }
  ],
  "answers": {
    "Q1": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" },
    "Q2": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" },
    "Q3": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" },
    "Q4": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" },
    "Q5": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" },
    "Q6": { "answer": "<text>", "rationale": "<text>", "confidence": "high|medium|low" }
  },
  "escalations": [
    { "id": "<short-id>", "concern": "<text>" }
  ],
  "summary": "<2-3 sentence overall verdict>"
}
```

Below the JSON, freeform commentary is welcome — particularly any
*alternative designs* you'd suggest that aren't covered by the open
questions. Keep it under ~500 words; the operator wants signal,
not volume.

Thank you for the review.
