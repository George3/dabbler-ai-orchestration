# Cross-repo CLAUDE.md notice — orchestrator check-out / check-in

**Authored:** 2026-05-21 (Set 033 Session 6 — implementation close-out)
**Audience:** consumer-repo CLAUDE.md authors (dabbler-platform,
dabbler-access-harvester, dabbler-homehealthcare-accessdb).

## Purpose

This is a one-time copy source. Paste the body below into each
consumer repo's top-level `CLAUDE.md` so its in-repo orchestrators
discover the new check-out / check-in model the next time they read
their instruction file. The dabbler-ai-orchestration extension and
`dabbler-ai-router` PyPI package are already wired; this notice is
purely an instructions-side update.

No PRs are filed from this repo — the operator pulls the snippet
into each consumer manually per the established pattern.

## What changed (one-paragraph summary)

`session-state.json`'s `orchestrator` block is now the authoritative
**check-out record** for the session set. `start_session` REFUSES
when the set is held by a different `engine + provider` (the "H4"
identity); the refusal names the holder and the two release paths.
`close_session` clears the block on every successful close (the
"check-in"). Within-set work is sequential; across-set work can run
in parallel. Force-override is the one explicit deviation, logged to
`~/.dabbler/orchestrator-writer.log`.

Ships in `dabbler-ai-router` `0.6.0` (PyPI) and the
`DarndestDabbler.dabbler-ai-orchestration` VS Code Marketplace
extension `0.18.0`.

---

## Snippet to paste into each consumer's CLAUDE.md

> Copy from the next horizontal-rule line through the trailing
> horizontal-rule line. The snippet is self-contained: it uses
> external links rather than referencing the consumer repo's own
> file layout, so it works unchanged in all three target repos.

---

### Orchestrator check-out / check-in (dabbler-ai-router 0.6.0 +
### dabbler-ai-orchestration 0.18.0)

The orchestration framework treats `session-state.json`'s
`orchestrator` block as a check-out record. Two invariants apply:

- **Within-set sequential.** At most one in-progress session per
  session set. `start_session` refuses a second simultaneous claim.
- **Across-set parallel.** Different session sets can each have
  their own in-progress session at the same time — possibly with
  different holders.

**Holder identity** is `engine + provider`. Same engine and provider
across `model` changes (e.g., `claude-opus` ↔ `claude-sonnet` both
on `claude + anthropic`) counts as the same holder.

**Refusal.** If `python -m ai_router.start_session` exits non-zero
with a message like:

> start_session: refused — session set is checked out by a
> different orchestrator (claude + anthropic); caller is gpt-5-4 +
> openai. Release the check-out before starting: re-run with
> --force to override, or invoke the "Release Check-Out" Command
> Palette action.

…the set is held by a different orchestrator. Three ways forward:

1. **Wait and retry.** If the holder is actively working, just wait
   until their next `close_session` clears the block. The extension
   offers a "Poll for release" affordance on the conflict toast.
2. **`start_session --force`** from the would-be holder. Used when
   the prior holder is stranded (crashed, network gone, abandoned).
   Logs the handoff to `~/.dabbler/orchestrator-writer.log`.
3. **"Release Check-Out"** in the VS Code Command Palette
   (`Dabbler:` prefix). Wraps `--force` with a confirmation
   prompt.

**Close-out clears the check-out.** `close_session` writes
`orchestrator: null` to `session-state.json` on every successful
close. Idempotent — re-running on an already-cleared block is a
no-op. The check-in applies on Full tier (via the writer) and on
Lightweight tier (the human writes `null` by hand at the same
boundary, alongside the manual `completedSessions[]` update).

**Documentation aliases.** In operator-facing prose,
`work_checked_out` ↔ `work_started` and `work_checked_in` ↔
`closeout_succeeded`. The events ledger event names are unchanged
(no schema break).

**Tier reminder.**

- **Full tier** — every session runs `start_session` and
  `close_session`; the writer maintains the block automatically.
- **Lightweight tier** — the human edits `session-state.json` by
  hand; same invariants, same `orchestrator: null` on close.

See the canonical references in `dabbler-ai-orchestration`:

- [`docs/session-state-schema.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/session-state-schema.md)
  "Check-out / check-in (Set 033)" — full schema + holder identity
- [`ai_router/docs/close-out.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/ai_router/docs/close-out.md)
  Section 4 — stranded-check-out recovery
- [`docs/ai-led-session-workflow.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/ai-led-session-workflow.md)
  "Orchestrator check-out / check-in (Set 033)" — workflow-level
  invariants

---

## Notes for the paster

- The snippet has its own H3 heading, so it can drop into any
  existing CLAUDE.md without colliding with the surrounding
  structure. Pick an insertion point near other framework-version
  notes (e.g., next to existing references to `dabbler-ai-router`
  or the extension version).
- The links above are absolute GitHub URLs against `master` so they
  resolve regardless of which consumer repo the snippet lives in.
  If a consumer has its own mirror or fork that lags master, the
  paster should point those links at their own mirror — but that's
  a per-consumer adjustment, not part of the canonical snippet.
- If a consumer is on the **Lightweight tier**
  (`dabbler-homehealthcare-accessdb` per
  [[project_consumer_repos]]), the snippet is still accurate but
  the "Wait and retry" / "Poll for release" line refers to a
  Full-tier orchestrator affordance the Lightweight project won't
  exercise directly. Leaving it in is fine — the document is the
  same across tiers.
- After paste, no further code changes are needed. The next time
  the consumer's orchestrator starts a session via
  `python -m ai_router.start_session`, the writer enforces H3+H4
  automatically.
