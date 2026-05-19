# Orchestrator-tracking architecture: multi-writer precedence vs. check-out / check-in

> **Date:** 2026-05-19
> **Set:** 029 (Session 6 polish pass, pre-marketplace publish)
> **Trigger:** operator pushback on the `Set Orchestrator…` and `Writer Log`
> buttons during the Session 6 HTML-preview iteration loop
> **Routing:** GPT-5.4 + Gemini Pro for consensus (operator-authorized
> 2026-05-19 mid-session, override on the standing `feedback_ai_router_usage`
> end-of-session restriction)
> **Scope:** v0.17.0 shipped a working multi-writer marker model. This
> proposal does NOT propose ripping it out in Session 6. The implementation
> work, if approved, would open a follow-on session set. What this packet
> wants is a verdict on direction so Session 6 can either ship 0.17.x to
> Marketplace as-is (with renamed/relegated buttons) or pause publish until
> the architecture lands.

## Status quo (v0.17.0 — shipped Session 5 of Set 029)

Per-set marker files live at
`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json` (schema v3,
introduced in Set 029 Session 3). The marker carries `provider`, `model`,
`tier`, `effort`, `signalKind`, `confidence`, and `updatedAt`.

**Four writers** feed the marker, ordered by **precedence**:

| Precedence | Writer | Triggered by | `signalKind` | Confidence |
|---|---|---|---|---|
| 1 (strongest) | Claude Code `SessionStart` hook | Claude session start (auto) | `current` | high (or low if hook payload lacks `model`) |
| 2 | Manual quickpick (`dabbler.setOrchestrator`) | Operator command | `manual` | high |
| 3 | `/think*` listener (Claude only) | `UserPromptSubmit` hook text match | `last-observed` (effort only) | high in detection, time-decayed |
| 4 (weakest) | Codex `~/.codex/config.toml` watcher | Codex config change (auto) | `configured-default` | medium |

Every writer reads the existing target, compares precedence, re-reads
immediately before the atomic rename (TOCTOU race close), and **skips
the write** if the proposed signal is weaker than a fresh existing signal.
Skipped writes append one JSON-lines entry to
`~/.dabbler/orchestrator-writer.log`.

**Operator-facing surfaces (the things this packet is questioning):**

1. **`Dabbler: Set Orchestrator…` quickpick + accordion button.** Universal
   manual-override surface. Multi-step (provider → model → effort →
   thinking), MRU-backed at `~/.dabbler/orchestrator-mru.json`, hotkey-
   bindable args. **Crucially, it does not change what the underlying
   orchestrator actually is** — it writes a `manual`-kind marker that the
   gauges display.
2. **`Dabbler: Open Orchestrator Writer Log` accordion button.** Opens the
   writer-log file. Diagnostic-only — losing it does not change behavior,
   only visibility.

**Operator-facing surfaces that just work and aren't in question:**

- The gauges themselves (model tier + effort) and the per-set accordion.
- The `SessionStart` hook + `/think*` listener for Claude. Fully automatic.
- The Codex watcher. Fully automatic.
- The Gemini Code Assist and GitHub Copilot manual-only installer shims —
  these surfaces have **no introspection API** and lean entirely on the
  manual quickpick.

## Operator's discomfort

> "I'm still not sure why we need the Set Orchestrator and the Writer Log.
> Are we concerned about two orchestrators working on the same session
> set? If so, maybe we need some kind of check-out and check-in system
> for session sets that the orchestrators are responsible for at the
> beginning and end of a session. … If a checked-out session is suspended
> before check-in (or if for some reason a check-in doesn't occur), then
> the orchestrator should (a) just notify the user if the current
> orchestrator and the most recent checked-out orchestrator are the same
> model … etc. and (b) warn the user if the current orchestrator is
> different from the checked out orchestrator. This can get a little
> messy and convoluted."
>
> "I'm not a big fan of having extra buttons in the user interface. If
> these are really needed, OK. but it seems a little confusing to have
> 'Set Orchestrator …' that doesn't actually set the orchestrator. I was
> hoping that the AI orchestrator could introspect that provide the
> information that it needs. If an AI orchestrator doesn't have what it
> needs then it can ask the human for clarification and then update the
> data behind the gauges."

The discomfort decomposes into three threads:

- **Threadcount:** "Set Orchestrator…" is a misnomer — it declares, doesn't
  set.
- **UI minimalism:** two extra buttons in an already-information-dense view.
- **Architecture:** is the multi-writer precedence model the right
  abstraction, or would check-out / check-in be cleaner?

## The check-out / check-in proposal

Each session set has a **check-out record** that names the orchestrator
currently driving it. Lifecycle:

1. **Check out at session start.** An orchestrator (Claude, Codex,
   Gemini, Copilot, …) checks out the set with its identity (provider +
   model + effort + thinking). This is what the marker file already
   stores; the rename reframes it as a coordination record rather than
   a precedence-resolved snapshot.
2. **Check in at session close.** When `close_session` runs, the check-out
   is released. The set returns to "between sessions" with no active
   orchestrator.
3. **Resumption with same orchestrator → silent notify.** Operator stops
   for the day, resumes tomorrow in the same Claude window. SessionStart
   re-checks-out the same identity; the system notes "Claude Opus 4.7
   resumed" without ceremony.
4. **Resumption with different orchestrator → warn.** Operator stopped
   under Claude, resumes under Codex. Codex's watcher (or manual
   declaration) writes the new check-out; the system flags "previous:
   Claude Opus 4.7; now: Codex GPT-5 — proceed?" The operator can
   accept (proceed) or revert (close the new check-out, keep the prior).
5. **Stalled check-out → warn on next attach.** Process died,
   check-out never released. On next attach, "Stalled check-out from
   2026-05-15: Claude Opus 4.7 — release?" with a one-click action.

**What changes in implementation terms:**

- The four-precedence writer model collapses to **one writer per session**
  — whoever checked out. The writer-log becomes a check-out-conflict log
  (much narrower scope).
- "Set Orchestrator…" becomes "Check Out As…" (or eliminated if the
  startup hook always does the check-out, with conflict prompts handled
  inline).
- "Writer Log" becomes "Show Check-Out History" (or eliminated in v1).
- Multi-in-progress sets each have their own check-out — no global
  ambiguity. (This is already partly true under v0.17.0's per-set
  markers; check-out semantics make it explicit.)

**What stays the same:**

- Hooks for Claude and Codex still auto-write. The hook performs the
  check-out instead of the precedence-aware marker write — same writer,
  different name.
- Gemini and Copilot still depend on a manual surface (no hook). The
  manual surface is now "Check Out As Gemini" rather than "Set
  Orchestrator… → Gemini".
- The per-set marker file path and schema stay; the precedence + writer-
  log fields can be slimmed.

## Questions

**Q1. Does the check-out / check-in model meaningfully simplify the
existing multi-writer + writer-log architecture, or just re-encode the
same complexity under different names?**

Specifically: the current model handles "Claude SessionStart fires
mid-session while a manual override is in place" via precedence
(SessionStart=current > manual; SessionStart wins → operator's manual is
overwritten, logged). The check-out model would handle the same case by
"check-out conflict prompt" (warn the operator that Claude wants to
take the check-out while the manual one is in place; let them choose).
Is the prompt strictly better than the silent precedence + logged
override, or just a different point in the friction-vs-determinism
tradeoff?

**Q2. What concrete failure modes does the current multi-writer model
handle that check-out / check-in would NOT handle?**

I.e., what does precedence + writer-log earn that check-out / check-in
wouldn't?

Two candidates to consider:
- (a) **Effort time-decay** via `/think*` `last-observed`. Under
  check-out semantics, `/think*` would have to either update the check-
  out record (which means the check-out's effort can drift from the
  initial check-out values) or live as a side-channel signal. Is either
  workable?
- (b) **Multiple legitimate writers for the same set in the same
  session.** E.g., a Claude session that runs both a `SessionStart`
  hook and a Codex config-toml watcher in the same workspace because
  the operator opened a Codex sub-terminal. The precedence model
  resolves this; the check-out model would deny the second writer
  (or prompt). Is the prompt the right answer?

**Q3. The hooks-as-checkout framing.**

Claude's `SessionStart` hook already performs an auto-write. Under
check-out / check-in, the same hook performs the check-out — same
writer, different semantics, and a release step at close-out. Is that
the right framing, or is there a subtle bug where the hook fires for
something that isn't actually a session start (e.g., `/clear`,
window-reload) and produces stale check-outs?

The hook events available are `SessionStart`, `UserPromptSubmit`, and
related. Per the audit (Set 029 Session 1), `SessionStart` is the
only one that reliably fires at conversation start with model identity
in the payload. `/clear` does NOT fire `SessionStart` (verified
post-audit). This means a `/clear` mid-session would NOT release the
check-out, which seems right (the same orchestrator is continuing).
Window reload, however, will fire `SessionStart` again — would that
look like a check-in / check-out churn, or just a no-op re-check-out?

**Q4. Rename, relegate, or eliminate `dabbler.setOrchestrator`?**

Three options:
- (a) **Rename** to "Check Out As…" and keep the quickpick button +
  Command Palette + (per operator's UI-minimalism note) **right-click
  context menu** on a session-set row.
- (b) **Relegate** to a Command Palette entry + right-click context
  menu only; remove the accordion-body button. Hook does the auto-
  check-out for Claude/Codex; manual surface stays for Gemini/Copilot
  but isn't a visible button by default.
- (c) **Eliminate the button entirely**; hook does it for hookable
  orchestrators, and Gemini/Copilot get a Command Palette entry the
  operator runs once after switching. The accordion-body has no manual
  affordance.

What's the right answer here, especially given (b) and (c) leave
Gemini/Copilot operators with no in-pane way to declare their
orchestrator?

**Q5. Writer Log — same three options.**

(a) **Keep** as accordion-body button. (b) **Relegate** to Command
Palette + right-click context menu. (c) **Eliminate**. If we go check-
out / check-in, the writer log becomes a check-out-conflict log; is
that diagnostic still operator-facing in v1, or developer-facing-
only behind a setting?

**Q6. Multi-in-progress rendering.**

Today's resolver fails closed under multiple in-progress sets (banner
fires, no accordion shown). With per-set markers + check-out semantics,
each in-progress set could render its own gauges independently. Is the
fail-closed banner still earning its keep (preventing operator
confusion), or is it an obsolete safety from the pre-pivot single-
marker world that should be removed in favor of rendering all
in-progress sets' gauges?

## What we're committing to

The follow-on implementation work, if either of you (or both) say the
check-out / check-in model is meaningfully better, opens a new session
set. Session 6's published v0.17.x will ship with renamed buttons + the
ambiguity banner removed (if Q6 is "remove"), but the underlying writer
model remains v0.17.0 (precedence + writer-log). The check-out / check-
in migration becomes a clean session set with its own audit + spec +
implementation cycle.

If both of you say the current model is fine and the only operator-
facing change should be rename/relegate, we ship 0.17.x and don't open
the follow-on.

## Response format

Per question:
- **Verdict:** one of: `keep current architecture`, `migrate to check-
  out/check-in`, `hybrid (specify)`, `unclear`.
- **Reasoning:** 2–5 sentences.
- **Must-fix or follow-up notes if any.**

Plus an **overall recommendation** paragraph at the end.

Plain text or JSON — your call. The other reviewer is **__OTHER__**.
We're looking for three-way agreement (you, the other reviewer, the
operator) before locking direction.
