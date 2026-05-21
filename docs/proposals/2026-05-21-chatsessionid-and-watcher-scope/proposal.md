# Orchestrator coordination tightening — chatSessionId + MVVM watcher-scope discipline

> **Date:** 2026-05-21
> **Authored by:** Claude Opus 4.7 (interactive session, post-Set-033 close)
> **Status:** draft, pending audit
> **Prerequisites closed:**
> - Set 032 (`032-orchestrator-checkout-checkin-audit`) — locked H1–H4, OQ1, OQ2
> - Set 033 (`033-orchestrator-checkout-checkin-implementation`) — shipped
>   the writer (start_session H3 refusal + +2 nested timestamps), the
>   reader-side marker retirement (H2), the UI rename + Release Check-Out
>   command, Layer-3 Playwright coverage, the polling/queueing UX, and
>   the cross-tier `close_session` check-in.
> **Pattern:** audit-then-spec per
> [[feedback_audit_then_spec_for_substantial_features]].

---

## TL;DR

Set 033 closed cleanly but surfaced two architectural concerns the
audit didn't address:

1. **H4 identity is too coarse.** The current rule
   `engine + provider` treats two distinct chat instances of the
   same engine as the same holder. Two Claude Code windows on the
   same workspace can each call `start_session`; the second one is
   treated as a "re-attach" and silently overwrites the first
   instance's identity-block fields. The instances never become
   aware of each other.

2. **MVVM inference watchers produce false-positive UI state.**
   The codex config-toml watcher in v0.17.1 wrote a runtime marker
   file today claiming the operator's orchestrator was
   `Codex gpt-5.4`, even though the operator was demonstrably
   running Claude Code. The watcher inferred session intent from a
   file modification that wasn't actually session intent. The gauge
   displayed the false reading. v0.18.0 already retires this
   watcher's writer path, but the underlying architectural pattern
   — watch any signal and update the model — invites similar
   bugs at the next addition.

The operator's proposed compromise direction (the subject of this
audit):

- **Keep MVVM, but discipline its scope.** Watching is permitted
  only on `session-state.json` (the canonical truth-source file).
  No watching of indirect signals (config files, MRU files, etc.).
- **Introduce `chatSessionId` coordination.** A per-chat GUID
  enters the orchestrator-identity composite, refining H4 from
  `engine + provider` to `engine + provider + chatSessionId`.
- **Make the agent-facing API MVC-shaped.** Agents read
  `chatSessionId` from an environment variable (per-chat,
  ephemeral), write it to `session-state.json` at check-out, clear
  it at check-in. Agents have no awareness of the view or
  watchers; the extension's job is to render whatever the state
  file says.
- **Retire the `signalKind` variants** (`current` /
  `configured-default` / `last-observed` / `manual`). These
  exist because the current design tolerates indirect signals.
  Under the discipline above, every signal is `current` by
  definition.

This document proposes the direction. An audit-then-spec follow-on
(Set 036-candidate, behind the already-queued Set 034/035) would
ratify the verdicts and ship the migration.

---

## What's already locked (NOT in scope)

These verdicts from the Set 032 audit stand. The proposal builds
on them and does not relitigate them.

| Item | Verdict | Status |
|---|---|---|
| **H1** Writer authority | Router-only writes; hooks become invokers | SHIPPED v0.18.0 |
| **H2** Single source of truth | `session-state.json` canonical; `.dabbler/orchestrator.json` retired | SHIPPED v0.18.0 |
| **H3** Hard coordination | `start_session` refuses different-holder writes; refusal names holder + release paths | SHIPPED v0.18.0 |
| **H4** Holder identity (composite) | `engine + provider` composite (not engine-alone, not engine+provider+model) | SHIPPED v0.18.0 — **REFINED by this proposal** |
| **OQ1** Field merge | +2 nested fields (`checkedOutAt`, `lastActivityAt`); block is `null` when `status != in-progress` | SHIPPED v0.18.0 — chatSessionId joins these |
| **OQ2** Event aliases | `work_checked_out` / `work_checked_in` are doc-only aliases for `work_started` / `closeout_succeeded`; no ledger schema change | SHIPPED v0.18.0 — unaffected |
| Cross-tier check-in | `close_session` clears the orchestrator block on every successful close, idempotent | SHIPPED v0.18.0 |

---

## Problem statement (detailed)

### Problem 1: H4 identity is coarser than the runtime granularity

The Set 032 audit chose `engine + provider` over `engine` alone (too
permissive) and `engine + provider + model` (too restrictive — would
have refused a `claude-opus → claude-sonnet` model swap within the
same chat). The composite was correct for the conflicts the audit
had in mind: "different orchestrator software is now running" or
"the chat re-attached after a context reset."

The audit did not consider: **two simultaneous chat instances of
the same engine, same provider, opened against the same workspace.**
In that case both instances satisfy the H4 identity predicate, and
the second instance's `start_session` is treated as a benign
re-attach. Both instances now believe they own the check-out;
neither is aware of the other. Whichever one runs `close_session`
first releases the check-out — but the other instance keeps writing
to the same session set, with no coordination.

This is plausible to hit in practice:

- An operator with two VS Code windows open on the same repo (one
  in each worktree, but pointing at the same session set).
- A developer running Claude Code in two terminals against the
  same project root.
- An operator who opens a new Claude Code chat without closing the
  old one (common during long-running sessions).

The Set 033 implementation does not detect any of these.

### Problem 2: MVVM inference watchers produce false UI state

The system has three categories of file watcher:

1. **Truth-source watcher** — on `session-state.json`. Triggers
   UI re-render when the state file changes. Necessary; standard
   reactive-UI pattern.
2. **Conflict-prompt watcher** — on
   `~/.dabbler/checkout-conflicts/`. Triggers the
   "Poll / Force / Dismiss" toast when a different orchestrator
   hits `EXIT_CHECKOUT_CONFLICT`. Necessary for multi-orchestrator
   UX over the H3 refusal.
3. **Inference watcher** — on `~/.codex/config.toml`. Watches for
   changes to the operator's Codex configuration and *infers*
   "user is now using Codex." Writes a marker file claiming Codex
   is the active orchestrator. **Caused the bug observed
   2026-05-21:** the operator's gauge showed `Codex gpt-5.4`
   despite the operator running Claude Code. The watcher had
   fired at some earlier moment when the config file was touched,
   wrote a stale marker, and the v0.17.1 reader picked it up.

v0.18.0 already retires the v0.17.1 marker-writer behavior in
this watcher (per Set 033 Session 3 H1 refactor: "hooks become
invokers, not writers"). But the *architectural pattern* — watch
indirect signals and update state from them — remains in the
codebase as a latent capability. The next contributor who wants
to add "auto-detect Cursor" or "auto-detect Aider" would likely
add another inference watcher and reproduce the same failure
mode.

The cleanest discipline is: **the only thing the extension
watches is `session-state.json`**. Everything else either calls
`start_session` explicitly or doesn't appear in the UI.

---

## Proposed direction

### Core compromise: MVVM-with-discipline + MVC-shaped agent API

The user-visible architecture stays MVVM:

- `session-state.json` is the model.
- The extension's accordion view watches the file and re-renders.
- Anything that wants to update the gauge writes to the file.

The **scope** of watching is constrained:

- **Permitted:** watching `session-state.json` (the truth source).
- **Permitted:** watching `~/.dabbler/checkout-conflicts/` (the
  H3 conflict-prompt surface).
- **Forbidden:** watching any other file or directory to *infer*
  session state. Specifically: no watching `~/.codex/config.toml`,
  no watching `~/.claude/settings.json` for orchestrator-intent
  signals, no MRU-file watching, no per-workspace-config-file
  watching.

The agent-facing API is MVC-shaped:

- Agents (Claude Code, Codex, Gemini Code Assist, Copilot, manual
  operators) read their `chatSessionId` from an environment
  variable at session start.
- Agents pass `--chat-session-id <value>` to
  `python -m ai_router.start_session`.
- The writer puts the value into `session-state.json`'s
  `orchestrator.chatSessionId`.
- Agents pass the same value to
  `python -m ai_router.close_session` (or rely on the close
  finding it in state and clearing it).
- Agents never watch files, never react to state changes, never
  know about the gauge.

The extension's role is purely the view:

- Watch `session-state.json` (the truth source).
- Render the accordion + gauge from whatever's there.
- Surface the H3 conflict prompt when a sentinel appears.

### chatSessionId field

A new nested field joins the existing orchestrator block:

```json
{
  "orchestrator": {
    "engine": "claude",
    "provider": "anthropic",
    "model": "claude-opus-4-7",
    "effort": "high",
    "chatSessionId": "ba9f1c43-...-...",
    "checkedOutAt": "2026-05-21T02:35:14-04:00",
    "lastActivityAt": "2026-05-21T05:25:38-04:00"
  }
}
```

Refines H4's identity predicate:

```
existing.engine == new.engine
AND existing.provider == new.provider
AND existing.chatSessionId == new.chatSessionId
```

A different `chatSessionId` (even with matching engine + provider)
triggers the H3 hard-coordination refusal. The refusal message
names the existing chatSessionId and offers the two release paths
(`--force`, "Release Check-Out").

### chatSessionId source per orchestrator type

| Orchestrator | Source | Status |
|---|---|---|
| Claude Code | `$CLAUDE_SESSION_ID` env (or equivalent) | Per-chat, ephemeral by design |
| Codex | TBD via audit — Codex CLI session var? | Open question |
| Gemini Code Assist | TBD via audit — Gemini Code Assist session var? | Open question |
| Copilot | TBD via audit | Open question |
| Manual / Lightweight tier | Human-generated UUID, passed to start_session | Operator picks one at session start |

For orchestrators without a per-chat session-ID env var, a
fallback CLI like `python -m ai_router.new_chat_id` would emit a
GUID the operator pastes into the orchestrator's first message.
The orchestrator then includes it on every subsequent
`start_session` / `close_session` call.

### signalKind retirement

The current `signalKind` enum
(`current` / `configured-default` / `last-observed` / `manual`)
exists to express confidence in orchestrator inferences. Under
the MVC-shaped API:

- All writes go through `start_session` with explicit operator/
  agent intent.
- There is no inference path; all signals are `current` by
  definition.
- The clock-overlay UI ⏱ that visualizes `last-observed` is
  retired.
- The "configured default" qualifier on the model line in the
  accordion is retired.

This simplifies the rendering code in
`tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
significantly. The `OrchestratorMarker` view-model becomes
identical to the on-disk `orchestrator` block plus minor display
metadata (color tier, name normalization).

### Codex config-toml watcher retirement

The watcher at
`tools/dabbler-ai-orchestration/src/codex/configWatcher.ts` is
retired entirely (not just refactored). Codex users invoke
`python -m ai_router.start_session` manually, the same way other
non-hook-supporting orchestrator types already do (Gemini Code
Assist, Copilot, manual). The UX cost is a one-time onboarding
step ("run start_session when you start a Codex session"); the
gain is no more false-positive gauge state from indirect signals.

The Set 033 Session 5 polling/queueing service stays — it watches
`~/.dabbler/checkout-conflicts/`, which is a *direct* signal
(an orchestrator's `EXIT_CHECKOUT_CONFLICT` exit explicitly wrote
the sentinel), not an inferred one.

---

## Open questions for the audit

The proposal's direction is operator-endorsed. The audit needs to
settle these specifics before the implementation set can begin.

### Q1 — chatSessionId env var name per orchestrator

Each orchestrator type's per-chat session ID lives under a
different env var (or no env var at all, requiring a fallback
CLI). The audit should produce a definitive table:

- Claude Code: confirm the exact env var (or other available
  per-chat token).
- Codex CLI: confirm the equivalent env var (or absence).
- Gemini Code Assist / Copilot: confirm.
- Fallback CLI design: `python -m ai_router.new_chat_id`
  → prints a UUID, with an `--export` flag that emits a
  shell-eval-able line for convenience.

### Q2 — Cadence of chatSessionId checks

Three reasonable cadences:

- **Per-task:** the agent re-reads `session-state.json` before
  every tool call. Maximum safety, small per-task cost.
- **Per-boundary:** the agent re-reads only at session start /
  session close / before any destructive operation. Less overhead,
  similar safety in practice.
- **On-demand:** the agent re-reads only when its own activity
  log entry triggers a state mutation. Minimal overhead, weaker
  safety.

Recommendation under audit: **per-boundary**. The audit should
ratify or refine.

### Q3 — Takeover UX when chatSessionId mismatches

When a new chat instance opens against an in-progress set whose
`orchestrator.chatSessionId` is non-null and differs:

- **Modal prompt** (blocking): "Set X is held by chatSessionId
  Y. Take over? [Yes / No / Open in read-only mode]"
- **Toast prompt** (non-blocking): same content, but the chat
  proceeds in a "no current check-out" mode until the operator
  responds.
- **CLI prompt** (terminal-only): for invocations outside VS
  Code.

Audit should settle the default and the order of preference.

### Q4 — chatSessionId on close: clear or retain for audit?

Two options:

- **Clear on close:** consistent with the current `orchestrator: null`
  invariant. The closed set has no holder identity recorded.
- **Retain on close (move to closure record):** the closed set
  carries an audit field like `lastClosedBy: { chatSessionId: ..., engine: ..., closedAt: ... }`
  so post-hoc audits can reconstruct who closed which session.

Audit should settle. Recommendation under audit: **clear on
close** (parsimony — the events ledger
`session-events.jsonl` already records `closeout_succeeded` with
session-number and timestamp; the holder identity is redundant
audit data).

### Q5 — Migration tolerance for in-flight sets without chatSessionId

Sets started under v0.18.0 (or earlier) have no `chatSessionId`
field. When the new code starts running:

- **Strict:** treat missing `chatSessionId` as a third-party
  identity that must be force-overridden. Maximum safety; UX
  friction at every legacy set.
- **Tolerant:** treat missing `chatSessionId` as "same holder by
  engine + provider rule only." The first new check-out
  populates the field; subsequent reads enforce strictly.
- **Hybrid:** tolerant on read, strict on write. Reads see legacy
  state correctly; the first write under the new code fills in
  the field.

Recommendation under audit: **tolerant on read, strict on
write** (matches the OQ1 migration pattern used for
`checkedOutAt`).

### Q6 — `requireExplicitTakeover` setting

If the takeover prompt is too frequent in practice, a
`dabblerSessionSets.requireExplicitTakeover` boolean setting could
let power users disable it for same-workstation, same-account
scenarios. Default `true`; off-switch for users who run multiple
chat instances by design.

Audit should settle whether the setting is needed (premature
optimization?) or whether the friction is bearable as a hard
rule.

### Q7 — Watcher-scope policy as a code-level invariant

The "no inference watchers" discipline is operator-stated policy.
Should it be encoded as:

- **Documentation only** (this proposal + a comment block in
  `OrchestratorAccordion.ts`)?
- **Lint rule** (a custom ESLint rule that flags `fs.watch` or
  `vscode.workspace.createFileSystemWatcher` calls outside an
  allowlist of paths)?
- **Convention test** (a unit test that greps the source for
  forbidden watcher patterns)?

Audit should settle. Recommendation: **convention test** —
cheap to implement, catches the regression, doesn't require
custom lint plumbing.

---

## Suggested decomposition (for the implementation spec)

Two session sets, audit-then-spec per the Set 032/033 pattern:

### Audit set (Set 036-candidate)

One or two sessions:

- S1 — Resolve Q1–Q7 via cross-engine consensus (Gemini Pro +
  GPT-5.4). Lock verdicts in a `proposal-addendum.md`.
- S2 (if needed) — Author the implementation spec for the
  follow-on set; cross-review.

### Implementation set (Set 037-candidate)

Four to six sessions:

- S1 — `start_session` accepts `--chat-session-id`; writer
  emits `chatSessionId` into the orchestrator block; H4
  predicate refined; refusal message gains the chatSessionId.
- S2 — Codex config-toml watcher retirement; `signalKind`
  enum + clock-overlay UI retirement; `OrchestratorMarker` view
  model simplification.
- S3 — Agent-instruction file updates (Claude Code installer,
  Gemini installer, Copilot installer): each is taught to read
  its per-chat ID and pass it on every start/close call.
  Fallback CLI `new_chat_id` shipped.
- S4 — Takeover UX (modal + toast variants, the
  `requireExplicitTakeover` setting if Q6 ratifies it).
  Convention test for the no-inference-watchers rule.
- S5 — Layer-3 Playwright coverage: two-chat-instance
  takeover scenario, missing-chatSessionId tolerance, manual-CLI
  scenario.
- S6 — Cross-tier doc updates (schema, close-out, workflow);
  cross-repo notification; PyPI + Marketplace release; cumulative
  change-log.

---

## Risks

- **R1 — Onboarding friction for non-hook orchestrators.**
  Codex users currently get auto-detect via the config-toml
  watcher; retiring it means manual `start_session` invocations.
  Mitigation: a clear onboarding doc + a one-command shell alias
  recipe.
- **R2 — chatSessionId env var availability inconsistency.**
  Claude Code has a per-chat ID; Codex / Gemini Code Assist /
  Copilot may or may not. The fallback CLI covers the gap, but
  introduces UX friction for those orchestrators.
- **R3 — Legacy in-flight sets at migration cutover.**
  Mitigated by the Q5 hybrid (tolerant-on-read, strict-on-write)
  approach.
- **R4 — Modal prompt fatigue.** If users genuinely run multiple
  chats per session set as their workflow, the prompt becomes
  noise. The Q6 `requireExplicitTakeover` setting mitigates.
- **R5 — `signalKind` retirement breaks any reader that depended
  on the field.** Marketplace download count is 3 (all operator's
  own per [[project_marketplace_download_count]]), so external
  consumers are negligible. Internal consumers (the accordion
  renderer) are co-located with the schema and update in lockstep.
- **R6 — Convention test false positives.** A unit test that
  greps for forbidden watcher patterns may snag legitimate
  watcher usage (e.g., file watchers on user-content files).
  Mitigation: allowlist of permitted watcher targets in the test,
  documented inline.

---

## Why this matters

Set 033 closed cleanly, but it also exposed two coordination gaps
that the audit-then-spec pattern was supposed to catch. The H4
identity gap is a real correctness hole (two chats step on each
other and neither knows). The MVVM inference-watcher pattern is a
real surface-area risk (today's stale-gauge bug is one example;
the next addition could be worse).

The proposed direction — chatSessionId for identity, MVVM
discipline for watchers, MVC-shaped agent API — closes both gaps
with a single coherent architectural move. The audit set should
ratify or refine; the implementation set should ship.

The shipping date is not urgent. Set 033 is correct as-shipped;
this proposal makes it *more* correct. The right time to start
the audit set is after operator review of this document and
external review by GPT-5.4 and Gemini Pro.
