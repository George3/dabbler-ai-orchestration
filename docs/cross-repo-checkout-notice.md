# Cross-repo CLAUDE.md notice — deprecate the check-out / check-in snippet

**Authored:** 2026-05-21 (Set 033 Session 6 — base composite)
**Updated:** 2026-05-23 (Set 036 Session 5 — chatSessionId refinement +
`new_chat_id` CLI + takeover UX)
**Deprecated:** 2026-05-27 (Set 049 Session 4 — orchestrator
coordination rip-out)
**Audience:** consumer-repo CLAUDE.md authors (dabbler-platform,
dabbler-access-harvester, dabbler-homehealthcare-accessdb).

## Status — REMOVE THIS CONTENT FROM YOUR CLAUDE.md

The Set 033 / Set 036 check-out / check-in snippet this doc previously
asked you to paste into your consumer repo's `CLAUDE.md` is
**deprecated**. The orchestrator coordination layer it described — the
`engine + provider + chatSessionId` holder-identity composite, the
hard-coordination refusal with `EXIT_CHECKOUT_CONFLICT`, the
chatSessionId-mismatch takeover modal, the
`python -m ai_router.new_chat_id` workflow, the
`dabbler.checkOutOrchestrator` / `dabbler.releaseCheckOut` extension
commands, and the `~/.dabbler/orchestrator-writer.log` force-override
audit trail — was rolled back end-to-end in Set 049
(`dabbler-ai-router 0.11.0` + `dabbler-ai-orchestration 0.24.0`).

If a consumer repo's `CLAUDE.md` still contains the old H3 block
("Orchestrator check-out / check-in (dabbler-ai-router 0.7.0 +
dabbler-ai-orchestration 0.20.0)"), delete that block in full and
commit the change. The framework no longer enforces any of the
behaviors the block described, so its presence in operator-facing
instructions misdirects in-repo orchestrators toward affordances that
no longer exist.

## How to remove

In each consumer repo:

1. Open `CLAUDE.md` and find the H3 heading beginning with
   `### Orchestrator check-out / check-in`. Some repos may have the
   Set 033 wording (`engine + provider` only) and some the Set 036
   wording (`engine + provider + chatSessionId`); either way, delete
   the whole block from that H3 heading through the closing
   horizontal rule (or through the end of the references list, which
   is the last paragraph of the snippet).
2. If the block sat between two unrelated framework-version notes,
   leave their headings intact — only the orchestrator-checkout block
   goes.
3. Commit with a message like `Remove deprecated orchestrator
   check-out / check-in CLAUDE.md block (Set 049 rip-out)`.

No further code changes are needed. `python -m ai_router.start_session`
continues to write the `orchestrator` block on `session-state.json` on
every session start (now a 4-field omit-null record:
`{engine, provider, model, effort}`) and `close_session` continues to
flip the per-session `status` to `complete` on every close.
`session-state.json` is the canonical lifecycle record; there is no
separate check-out / check-in semantic on top of it.

## What survives

- **`session-state.json` orchestrator block.** Written by
  `start_session` per the Set 049 T3 contract (subset-of-known fields,
  omit-null). Read by the Session Set Explorer for nothing other than
  passive display; coordination behavior is gone.
- **`python -m ai_router.start_session --chat-session-id <id>`.**
  Accept-with-warning for backwards compatibility per Set 049 T2 — the
  flag still parses on the CLI, the value is ignored by the writer,
  and a one-line stderr deprecation notice is printed. Consumer-repo
  invokers that still pass the flag keep working without changes; the
  cleanup is in your hands when convenient.
- **`~/.dabbler/orchestrator-writer.log`.** Retained provisionally per
  Set 049 T5 as a generic "start_session ran" record. The
  `Dabbler: Open Orchestrator Writer Log` Command Palette action stays.
- **`writer-bypass` detector** in `ai_router/joiner/`. Decoupled from
  the retired coordination context per Set 049 D3 — preserved as a
  general writer-discipline check for state-file edits that bypass
  the canonical writer.

## What was retired

- **Holder-identity coordination.** `start_session` no longer refuses
  on `engine + provider + chatSessionId` mismatches; there is no
  `EXIT_CHECKOUT_CONFLICT` exit code, no
  `~/.dabbler/checkout-conflicts/` sentinel-record directory, no
  in-extension poll/force/dismiss prompt.
- **`python -m ai_router.new_chat_id`** CLI and its wrapping
  `dabbler.newChatIdWorkflowToast` extension command.
- **Extension commands** `dabbler.checkOutOrchestrator` ("Check Out
  As…") and `dabbler.releaseCheckOut` ("Release Check-Out").
- **Gemini / Copilot installer shims**
  (`dabbler.installOrchestratorHook.gemini`,
  `dabbler.installOrchestratorHook.copilot`) — these wrapped the
  retired check-out quickpick and the retired `new_chat_id` toast.
  Claude Code's `SessionStart` hook installer
  (`dabbler.installOrchestratorHook.claudeCode`) stays.
- **`chatSessionMismatchModal` + `CheckoutPollService` +
  `ReadOnlyIntentService`** — the entire chat-mismatch takeover surface.
- **Set 045 Explorer harvest-record badges (W / N / M / B) and
  coordination-conflict pills.** The Python joiner CLI (the underlying
  log-harvest infrastructure) survives, but the rendering of harvested
  signals and coordination conflicts in the Session Set Explorer is
  gone.

## See also

- [`docs/session-state-schema.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/session-state-schema.md)
  — canonical schema reference including the post-Set-049 orchestrator
  block contract.
- [`docs/proposals/2026-05-27-set-049-orchestrator-coordination-removal/verdict.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/proposals/2026-05-27-set-049-orchestrator-coordination-removal/verdict.md)
  — audit-locked rationale for the rip-out (operator-locked premises
  P1–P5, audit dispositions T1–T7, detector dispositions D1–D3,
  feature roll-call FR1–FR5).
