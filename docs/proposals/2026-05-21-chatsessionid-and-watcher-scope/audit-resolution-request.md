# Audit-resolution request: chatSessionId + MVVM watcher scope

> **For:** Gemini Pro and GPT-5.4 — external review of the design
> direction proposed in [`proposal.md`](proposal.md).
> **Asked by:** the operator + Claude Opus 4.7 (Set-033 post-close
> session). The two architectural concerns surfaced after Set 033
> shipped successfully; the operator wants a cross-provider sanity
> check before kicking off a Set-036-candidate audit cycle.

---

## How to read this request

Please respond with **VERIFIED** or **REJECTED** for each of the
seven open questions (Q1–Q7) and the two core direction claims
(D1, D2). Cite specific quoted phrases from the proposal when
flagging concerns. Skip stylistic nits — the proposal is a
direction-setting document, not the implementation spec.

If you mark any item REJECTED, name the specific failure mode and
(if you can) suggest a concrete refinement. The operator
adjudicates final verdicts; your job is to flag the failures the
operator should consider before locking the direction.

The proposal is in [`proposal.md`](proposal.md). Read it first,
then return here for the structured questions.

---

## D1 — MVVM-with-scope-discipline

**Claim:** the system should keep MVVM for UI reactivity but
constrain its watching scope to two paths only:

- `session-state.json` (the canonical truth source)
- `~/.dabbler/checkout-conflicts/` (the H3 conflict-prompt
  surface, written by an orchestrator's explicit
  `EXIT_CHECKOUT_CONFLICT` exit)

All other file-watching for the purpose of inferring orchestrator
state is forbidden. Specifically: the
`~/.codex/config.toml` watcher (which caused today's stale-gauge
bug) is retired. The next contributor cannot add a similar
"watch this file to detect orchestrator change" pattern without
violating the policy.

**Question:** is the scope discipline correct, or is there a
specific category of indirect signal that the framework
legitimately needs to watch (and the proposal misses)?

Specifically consider:
- Workspace-config file changes (e.g., `.vscode/settings.json`)
  → does the framework currently watch these? Should it?
- The user's home-directory `.dabbler/` files other than
  `checkout-conflicts/` (MRU, writer log, etc.)
- Cross-workspace state (e.g., a second VS Code window opening
  the same repo)

---

## D2 — MVC-shaped agent-facing API on top of MVVM internals

**Claim:** agents (Claude Code, Codex, Gemini Code Assist,
Copilot, manual operators) interact with a clean read/write API
that looks MVC-shaped. They:

- Read `chatSessionId` from their environment at session start.
- Pass it to `python -m ai_router.start_session --chat-session-id <value>`
  at session check-out.
- Pass it to `python -m ai_router.close_session` (or equivalent
  Lightweight-tier hand-write) at session check-in.
- Never watch files; never react to gauge state; never know
  about the view.

The extension (the view) reads `session-state.json` and renders
whatever's there. The two surfaces (agent ↔ writer, writer ↔
extension reader) are decoupled.

**Question:** is the MVC-on-top-of-MVVM split coherent? Or is
there a case where agents need to read state mid-session (not
just at boundaries) and the proposal doesn't handle it?

Specifically consider:
- An agent that wants to "warn the user before destructive
  action": should it consult `session-state.json` first to
  confirm it still owns the check-out? The proposal's Q2
  per-boundary recommendation says yes-but-rarely. Is that
  right?
- An agent that wants to check "is the same set in flight in
  another window": that's a different question (state of
  *other* sets, not own check-out). The proposal doesn't make
  agents read sibling sets. Is that a gap?

---

## Q1 — chatSessionId env var name per orchestrator

The proposal asserts:

- Claude Code: a per-chat session-ID env var exists (exact name
  TBD via this audit).
- Codex CLI: TBD.
- Gemini Code Assist: TBD.
- Copilot: TBD.
- Manual / Lightweight: fallback CLI
  `python -m ai_router.new_chat_id` emits a GUID.

**Question:** for each orchestrator type, name the canonical
per-chat session-ID env var (or confirm absence). If you don't
have authoritative knowledge of one of them, say so explicitly
rather than guess — the audit's downstream spec depends on the
correct name.

If two or more orchestrators use the same env var name (unlikely
but possible if the convention is shared), call that out.

---

## Q2 — Cadence of chatSessionId checks

Three options:
- **Per-task** — re-read `session-state.json` before every tool
  call.
- **Per-boundary** — re-read at session start, before close,
  before destructive ops. (Proposal's recommendation.)
- **On-demand** — re-read only when the agent's own activity-log
  entry triggers a state mutation.

**Question:** is per-boundary the right cadence? Or does the
chatSessionId mismatch case require more frequent checks (because
the cost of acting under stale identity is higher than the cost
of a per-task disk read)?

Specifically: how should "before destructive ops" be defined? Is
"any tool call that writes to disk" too broad (would re-read on
every Edit), or is it the right boundary?

---

## Q3 — Takeover UX when chatSessionId mismatches

Options:
- **Modal prompt** (blocking) — chat halts until user responds.
- **Toast prompt** (non-blocking) — chat proceeds in "no
  check-out" mode until user responds.
- **CLI prompt** — for invocations outside VS Code.

**Question:** which default? Does the answer depend on the
context (in-IDE vs. CLI-only)?

A modal prompt in the middle of a long-running agent task is
disruptive. A toast that gets ignored leaves the chat in an
unclaimed state, which the agent might not handle gracefully.
Which failure mode is worse?

---

## Q4 — chatSessionId on close: clear or retain?

Options:
- **Clear on close** — consistent with current
  `orchestrator: null` invariant. The closed set has no holder
  identity recorded.
- **Retain on close (move to closure record)** — closed set
  carries an audit field like `lastClosedBy: { chatSessionId, engine, closedAt }`.

The proposal recommends **clear on close** on parsimony grounds
(events ledger already records `closeout_succeeded`; holder
identity in the closure record is redundant audit data).

**Question:** confirm or refine. Specifically: is there an
audit-trail use case where the events ledger's
`closeout_succeeded` event needs to gain a `chatSessionId`
field (no schema break — the event payload is open-shape),
in lieu of a closure record?

---

## Q5 — Migration tolerance for in-flight sets without chatSessionId

Options:
- **Strict** — missing `chatSessionId` is treated as a third-
  party identity; requires `--force` to claim.
- **Tolerant** — missing `chatSessionId` is treated as "same
  holder by engine + provider rule"; first new check-out
  populates the field; subsequent reads enforce strictly.
- **Hybrid** — tolerant-on-read, strict-on-write. (Proposal's
  recommendation.)

**Question:** is the hybrid right? Does it leave any window of
inconsistency that an adversarial sequence could exploit (e.g.,
two new chats both populating the field "first")?

Specifically: under the hybrid, what's the writer's behavior
when two start_session calls race on a legacy set? Does the
file-lock serialize them sufficiently?

---

## Q6 — `requireExplicitTakeover` setting

Proposal: a `dabblerSessionSets.requireExplicitTakeover` boolean
setting (default `true`) lets power users opt out of the takeover
prompt for same-workstation, same-account scenarios.

**Question:** is the setting needed, or is the friction
bearable as a hard rule?

Specifically: under what realistic workflow does an operator
legitimately want to skip the takeover prompt? If "I open two
chats on the same repo by design" — should those two chats
*share* a chatSessionId (in which case the setting isn't needed)
or should the proposal accept that the prompt fires every time
(in which case the setting is needed)?

---

## Q7 — Watcher-scope policy enforcement

Options:
- **Documentation only** — this proposal + comment block in
  `OrchestratorAccordion.ts`.
- **Lint rule** — custom ESLint rule flagging unauthorized
  `fs.watch` / `vscode.workspace.createFileSystemWatcher` calls.
- **Convention test** — unit test that greps source for
  forbidden watcher patterns. (Proposal's recommendation.)

**Question:** is the convention test sufficient, or does the
policy need to be enforced at code-review time (which doc / lint
both achieve via different mechanisms)?

Specifically: how does the convention test handle the legitimate
case where a future feature genuinely needs a new watcher? Is
the allowlist easy to update, with a comment explaining the
exception?

---

## What to skip

- The implementation specifics (signatures, file layouts,
  module names) — those belong in the implementation spec, not
  this direction-setting audit.
- The exact session count of the implementation set — the
  proposal suggests four to six; the audit doesn't need to
  ratify that until the spec is authored.
- The Marketplace publish gating (operator-driven).
- The non-negotiables (H1, H2, H3, OQ1, OQ2) — these are
  locked, do not relitigate.

---

## Response format

For each item:

```
[D1 | D2 | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7] — [VERIFIED | REJECTED | REFINED]
Verdict: <one-sentence summary>
Reasoning: <up to ~100 words>
Cited concern (if REJECTED or REFINED): <quoted phrase from proposal.md + the specific failure mode>
Suggested refinement (if applicable): <one or two sentences>
```

Total response budget: roughly **800–1500 words** across all 9
items. If you need more, prioritize D1, D2, Q1, and Q5 — these
are the load-bearing items.
