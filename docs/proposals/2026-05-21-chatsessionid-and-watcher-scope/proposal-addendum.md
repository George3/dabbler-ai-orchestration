# Addendum — locked verdicts (post-external-review)

> **Date:** 2026-05-21
> **Authored by:** Claude Opus 4.7 (operator-adjudicated)
> **Status:** FROZEN — verdicts locked; ready to drive an implementation
> spec.
> **Reviewers:**
> - Gemini Pro (Round A, routed via `ai_router`, $0.025) —
>   verdicts in [`audit-resolution-gemini-pro.txt`](audit-resolution-gemini-pro.txt) / [`.json`](audit-resolution-gemini-pro.json)
> - GPT-5.4 (Round A, operator manual paste) — verdict in
>   [`audit-resolution-gpt-5-4.txt`](audit-resolution-gpt-5-4.txt)
> **Adjudicator:** operator.

---

## Adjudication principle

The operator's locked rule of decision for this round:

> **Accept Gemini where it agrees on direction, but let GPT-5.4
> govern Q1, Q5, and Q6 because those are correctness and safety
> issues, not stylistic ones.**

Concretely:

- Direction (D1, D2): both reviewers ratify; GPT's sharpenings are
  adopted because they tighten wording without redirecting the
  proposal.
- Detailed items (Q1–Q7): GPT-5.4 controls wherever it tightens
  correctness or replaces an unsupported assumption. Gemini's
  refinements stand where the two providers agree.
- Q6 specifically: GPT's REJECTED verdict wins on safety grounds.
  Marketplace download count is still 3 ([[project_marketplace_download_count]]);
  alpha-stage tools should default to the safer invariant.

---

## Locked verdicts (compact)

| Item | Locked verdict | Source |
|---|---|---|
| **D1** Watcher-scope discipline | **REFINED** — discipline applies to *orchestrator-state inference*, not all extension watchers | GPT-5.4 |
| **D2** MVC-shaped agent API | **REFINED** — token source is the agent's native per-chat metadata surface (env, hook, or fallback CLI), not env-var-only | GPT-5.4 |
| **Q1** chatSessionId source per orchestrator | **REFINED** — no env var confirmed for any orchestrator; Claude Code uses hook-payload `session_id`; others use the fallback CLI until vendor docs prove otherwise | GPT-5.4 |
| **Q2** Cadence of identity checks | **REFINED** — per-boundary, with "destructive ops" narrowly defined | GPT-5.4 (refinement); Gemini (cadence) |
| **Q3** Takeover UX | **REFINED** — modal in IDE; CLI in terminal; toast is secondary notification only | Cross-provider consensus |
| **Q4** chatSessionId on close | **REFINED** — clear from `session-state.json`; persist in `closeout_succeeded` payload | Cross-provider consensus |
| **Q5** Hybrid migration tolerance | **REFINED** — hybrid only with explicit cross-process serialization (shared per-set lifecycle lock) | GPT-5.4 |
| **Q6** `requireExplicitTakeover` setting | **REJECTED** — no persistent off-switch; if friction proves real later, ship a one-shot affordance | GPT-5.4 |
| **Q7** Watcher-scope enforcement | **REFINED** — allowlisted watcher-inventory test (not raw grep) | GPT-5.4 |

---

## Item-by-item locked text

### D1 — Watcher-scope discipline

**Locked wording (replaces `proposal.md` §"Core compromise"):**

The extension's permitted watcher targets are partitioned by purpose:

- **For orchestrator identity/state inference:** the ONLY permitted
  watcher targets are:
  - `session-state.json` (the canonical truth source)
  - `~/.dabbler/checkout-conflicts/` (the H3 conflict-prompt
    surface, written explicitly by orchestrators on
    `EXIT_CHECKOUT_CONFLICT`)
- **For non-orchestrator UI refresh** (e.g., session-set folder
  enumeration, `activity-log.json` re-rendering, change-log
  preview refresh): file watchers are permitted as long as they
  **neither infer nor mutate orchestrator state**.

Specifically forbidden under this discipline:

- Watching `~/.codex/config.toml`, `~/.claude/settings.json`, or
  any other agent-configuration file to infer "the user is now
  using engine X" or to write orchestrator-identity data.
- Watching MRU files, writer logs, or any other home-directory
  files for orchestrator-state inference.
- Watching workspace-level config (`.vscode/settings.json`, etc.)
  to infer orchestrator state.

The `codex/configWatcher.ts` watcher is retired entirely (not
just refactored). Codex users invoke `start_session` via their
native per-chat token source plus the fallback CLI (see Q1).

### D2 — MVC-shaped agent-facing API

**Locked wording (replaces `proposal.md` §"chatSessionId source per orchestrator"
intro paragraph):**

Agents interact with the framework through a clean read/write API.
Each agent type obtains its `chatSessionId` from a **native per-chat
metadata surface** appropriate to that agent's runtime:

- An environment variable, if the agent's host provides one.
- A hook-payload stdin JSON field, if the agent's host provides
  a SessionStart hook with payload metadata (Claude Code).
- The `python -m ai_router.new_chat_id` fallback CLI, for any
  agent whose host does not surface a per-chat identifier.

The agent passes the token to `python -m ai_router.start_session`
at session check-out via `--chat-session-id <value>`. The agent
passes the same token to `python -m ai_router.close_session`
at check-in (or relies on the writer reading it from state).

Agents never watch files, never react to gauge state, never
import the extension's code. The extension's job is to render
whatever the state file says.

### Q1 — chatSessionId source per orchestrator (locked transport table)

**Locked deliverable shape — the spec must include this table
populated authoritatively:**

| Orchestrator | SourceKind | Identifier | Confidence | Notes |
|---|---|---|---|---|
| Claude Code | hook-payload stdin JSON | `session_id` | **High** | Already wired in `scripts/claude-session-start-invoker.js`; just needs to pass through to `start_session --chat-session-id` |
| Codex CLI | fallback CLI | `new_chat_id`-emitted GUID | **High** | No documented per-chat env var or stdin surface as of 2026-05-21 |
| Gemini Code Assist | fallback CLI | `new_chat_id`-emitted GUID | **High** | No documented per-chat env var as of 2026-05-21 |
| GitHub Copilot | fallback CLI | `new_chat_id`-emitted GUID | **High** | No documented per-chat env var as of 2026-05-21 |
| Manual / Lightweight tier | fallback CLI | `new_chat_id`-emitted GUID | **High** | Operator generates one at session start and reuses for the session's duration |

**Hard rule:** **no env-var name is locked in the implementation
spec without vendor documentation.** The audit reviewers
(Gemini Pro and GPT-5.4) were both unable to authoritatively
confirm an env var for any of the four agents above. If a vendor
documents a per-chat env var in the future, the spec can be
extended additively.

**`new_chat_id` CLI behavior** (locked):

- `python -m ai_router.new_chat_id` prints a v4 UUID to stdout.
- `python -m ai_router.new_chat_id --export` prints a
  shell-eval-able line like `export CHAT_SESSION_ID=<uuid>`
  (or `$env:CHAT_SESSION_ID = '<uuid>'` for PowerShell, selected
  via `--shell powershell|bash`).
- Idempotent within a single shell session: re-running emits
  the same ID if `$CHAT_SESSION_ID` (or `$env:CHAT_SESSION_ID`)
  is already set; emits a fresh one otherwise.

### Q2 — Cadence of identity checks (locked)

**Cadence:** per-boundary.

**"Destructive ops" — locked definition** (narrower than "any
disk write"):

- Session ownership transitions: `start_session`, takeover (a
  fresh `start_session` against a different existing
  chatSessionId), `close_session`.
- `--force` invocations of `start_session` or `close_session`.
- Repo-wide git operations: `commit`, `push`, `reset`, `clean`,
  `checkout` (when it changes branches), `merge`, `rebase`.
- Repo-wide scripts or migrations (e.g., the
  `ai_router/migrate_router_config.py`-style operations that
  touch broad swaths of files).

**Explicitly NOT destructive ops (no identity re-read required):**

- Routine `Edit` / `Write` tool calls on individual source files.
- Routine `Bash` invocations that don't fall under the
  "repo-wide" or "ownership-transition" categories.
- Routine reads (`Read`, `Grep`, `Glob`).

The implementation should provide a single helper (e.g.,
`assert_owning_chat_session()`) that the orchestrator-side code
calls at the right boundaries; the helper does the
read-check-prompt-on-mismatch flow.

### Q3 — Takeover UX (locked)

**In the VS Code IDE:** modal prompt at the takeover boundary.
The prompt names the existing chatSessionId (or a human-readable
prefix), the proposing orchestrator's identity, and offers
three actions:

- **Take over** — proceeds via `start_session --force`.
- **Open in read-only mode** — agent works against the set
  without claiming the check-out; state mutations refused.
- **Cancel** — abort the session start.

**In a CLI-only flow:** CLI prompt with the same three actions
via stdin (single-character selection). When the CLI is
invoked non-interactively (no TTY), refuse with
`EXIT_CHECKOUT_CONFLICT` (the existing H3 exit code) and direct
the operator to re-run with `--force` if takeover is intended.

**Toast notifications** stay in the design for *secondary
awareness only*. Examples:

- "Another orchestrator is waiting on this set." (visible to
  the current holder)
- "Forced check-out applied by `<identity>`." (audit toast,
  visible to other watchers)

A toast is never the primary mismatch-resolution path.

### Q4 — chatSessionId on close (locked)

**`session-state.json` behavior on close** (unchanged from
Set 033): `orchestrator: null`. The live snapshot reflects only
current state.

**`session-events.jsonl` behavior on close** (new for this
proposal): the `closeout_succeeded` event payload gains
mandatory fields:

```json
{
  "event_type": "closeout_succeeded",
  "session_number": <int>,
  "timestamp": "<ISO>",
  "chatSessionId": "<uuid>",
  "engine": "<engine>",
  "provider": "<provider>",
  "model": "<model>"  // optional but recommended
}
```

This is an additive payload extension. The event ledger schema
remains open-shape per OQ2 (no schema break); readers that ignore
the new fields continue to work.

`work_started` events SHOULD also gain `chatSessionId` for
symmetry, but the priority is `closeout_succeeded` (the audit
endpoint).

### Q5 — Hybrid migration tolerance + locking (locked)

**Migration semantics:** tolerant-on-read, strict-on-write
(unchanged from the proposal's recommendation).

**Concurrency requirement (NEW — added per GPT-5.4):**
`start_session` MUST acquire a per-set serialization lock around
the read/check/write sequence. Without this, two simultaneous
`start_session` invocations against a legacy in-flight set can
both pass the tolerant-read branch and both attempt to
"first-populate" the field — exactly the race the feature is
supposed to close.

**Locking design (locked direction):**

- Use a shared per-set lifecycle lock at
  `<session-set-dir>/.lifecycle.lock` (or extend the existing
  `.close_session.lock` if scope allows).
- Both `start_session` and `close_session` acquire this lock for
  their full read-check-write window.
- Lock acquisition follows the same stale-window reaping
  semantics as the existing `close_session.lock`
  (PID-tracked, time-stamped, reapable).
- Lock contention: blocks for a short bounded timeout (default
  30 seconds), then exits with a new `EXIT_LOCK_CONTENTION = 5`
  (or reuses an existing lock-contention exit code if one is
  already defined in `start_session.py`).

Implementation note: the audit-set Session 1 should confirm
whether to extend the existing `close_session.lock` (cleaner; one
file) or introduce a new `.lifecycle.lock` (more explicit; two
files). Recommendation: extend the existing one, rename it to
`.lifecycle.lock`, update both writers.

### Q6 — `requireExplicitTakeover` setting (locked: REJECTED)

**Setting NOT shipped.** Explicit takeover is a hard rule in the
implementation set. Same-workstation, same-account, same-engine
scenarios still require a prompt at the takeover boundary.

**Mitigation, if real-world friction proves high:** add a
one-shot affordance — e.g., a "Skip prompt for this takeover
only" button on the modal that proceeds with the takeover
without writing a global preference. This affordance does NOT
persist across takeovers; each takeover gets its own decision.

**Rationale (locked):** the takeover prompt only fires at session
boundaries (per Q2's narrow destructive-ops definition), not on
every tool call. The friction surface is bounded. The risk
surface of a global off-switch is unbounded — once shipped, the
feature lives forever and operators can opt out of the
invariant that the whole design exists to enforce. Marketplace
download count at the time of this lock is 3 (all operator's
own), so the framework can default to safer-but-stricter without
penalizing existing users.

**Re-opener clause:** the implementation set's S6 (release) is
the natural place to re-evaluate. If operators report real
pain, the audit-set Session 1 of a follow-on cycle can ratify
the one-shot affordance.

### Q7 — Watcher-scope enforcement (locked)

**Mechanism:** allowlisted watcher-inventory unit test.

**Test shape (locked):**

```python
# ai_router/tests/test_watcher_inventory.py  (or .ts equivalent)

WATCHER_ALLOWLIST = [
    {
        "callsite": "src/providers/inProgressSetsService.ts:NN",
        "target": "session-state.json",
        "purpose": "orchestrator-state truth-source watcher (D1)",
    },
    {
        "callsite": "src/providers/CheckoutPollService.ts:NN",
        "target": "~/.dabbler/checkout-conflicts/",
        "purpose": "H3 conflict-prompt watcher (D1)",
    },
    {
        "callsite": "src/providers/CustomSessionSetsView.ts:NN",
        "target": "<workspace>/docs/session-sets/*/activity-log.json",
        "purpose": "non-orchestrator UI refresh (allowed per D1)",
    },
    # ... additional approved callsites with inline rationale ...
]
```

The test:

1. Greps the source for `fs.watch`,
   `vscode.workspace.createFileSystemWatcher`, `chokidar`, and any
   other watcher primitives.
2. Maps each match to a `(file, line)` callsite.
3. Asserts each callsite is in the allowlist.
4. Fails with a clear message naming any new watcher callsite
   that isn't pre-approved.

**Adding a new watcher** requires:

- Updating the allowlist entry (the test enforces this).
- Inline comment at the watcher callsite explaining the purpose
  and citing the allowlist entry.
- Code-review reviewer sees the allowlist diff and the inline
  comment side-by-side.

---

## What ships in the follow-on implementation spec

The implementation set (Set-037-candidate) needs to ship:

1. **`chat-session-id` flag** on `start_session` and `close_session`.
   Per-set lifecycle lock acquired around read-check-write
   (Q5 locked requirement).
2. **`new_chat_id` CLI** in `ai_router/`.
3. **Claude Code hook invoker update** —
   `scripts/claude-session-start-invoker.js` parses
   `session_id` from the stdin JSON and forwards as
   `--chat-session-id` (Q1 confirmed-source).
4. **Codex / Copilot / Gemini Code Assist installer shims** —
   document the manual `start_session` step using `new_chat_id`.
   Retire the Codex config-toml watcher entirely (D1 locked
   policy).
5. **`closeout_succeeded` payload extension** — `chatSessionId`,
   `engine`, `provider`, `model` fields added; reader-side
   tolerance for older payloads without these fields.
6. **Takeover UX** — modal in VS Code, CLI prompt in terminal,
   `EXIT_CHECKOUT_CONFLICT` on non-interactive CLI (Q3 locked).
7. **`signalKind` retirement** — `OrchestratorAccordion.ts`
   simplified; clock-overlay UI retired; "configured default"
   qualifier retired.
8. **Watcher-inventory convention test** (Q7 locked).
9. **Cross-tier doc updates** — `docs/session-state-schema.md`,
   `ai_router/docs/close-out.md`, `docs/ai-led-session-workflow.md`,
   and an update to `docs/cross-repo-checkout-notice.md` for the
   three consumer repos.
10. **PyPI release** (next ai_router minor, e.g., 0.7.0) +
    **Marketplace publish** of the next extension minor (0.19.0)
    once the Set 033 Marketplace publish completes and an
    appropriate window opens.

---

## What's deferred to the audit-set Session 1

The verdicts above are sufficient to start authoring the
implementation spec. A few items belong in audit-set Session 1
or the implementation spec's design block, not in this addendum:

- **Lock file naming** — extend the existing `.close_session.lock`
  to `.lifecycle.lock`, or introduce a separate
  `.start_session.lock`? Recommendation in Q5 favors extending
  the existing one; implementation Session 1 confirms.
- **Modal copy** — exact wording of the takeover prompt. Belongs
  in the implementation spec, not here.
- **`new_chat_id` shell-flavor coverage** — which shells does
  `--export` support out of the box? bash, PowerShell, fish?
  Belongs in the implementation spec.
- **`requireExplicitTakeover` re-evaluation cadence** — exact
  trigger (operator complaint? telemetry signal? scheduled
  re-audit?). Defer to the implementation set's S6 wrap.

These are implementation-detail decisions that don't change the
locked verdicts above.

---

## Cross-references

- **Proposal:** [`proposal.md`](proposal.md)
- **Audit request:** [`audit-resolution-request.md`](audit-resolution-request.md)
- **Gemini Pro verdict:** [`audit-resolution-gemini-pro.txt`](audit-resolution-gemini-pro.txt) /
  [`.json`](audit-resolution-gemini-pro.json)
- **GPT-5.4 verdict:** [`audit-resolution-gpt-5-4.txt`](audit-resolution-gpt-5-4.txt)
- **Routing script:** [`route_gemini_audit.py`](route_gemini_audit.py)
- **Prerequisite session set:** Set 033 (closed 2026-05-21) —
  [`docs/session-sets/033-orchestrator-checkout-checkin-implementation/change-log.md`](../../session-sets/033-orchestrator-checkout-checkin-implementation/change-log.md)
- **Prerequisite audit:** Set 032 (closed 2026-05-19) —
  [`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`](../2026-05-19-orchestrator-tracking-architecture/)
- **Queued ahead in the audit pipeline:** Set 034/035 (state-file
  sole truth) per [[project_034_035_state_file_sole_truth_audit]]
