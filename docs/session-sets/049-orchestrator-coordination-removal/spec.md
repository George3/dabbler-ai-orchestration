# Orchestrator Coordination Removal — Audit Pending

> **Purpose:** rip out the check-out / check-in coordination layer
> shipped in Set 033 / refined in Set 036, simplify the
> `session-state.json` orchestrator block to four fields with an
> omit-null writer pattern, and remove all orchestrator-related
> rendering from the Session Set Explorer.
> **Created:** 2026-05-26 (stub).
> **Status:** STUB — AUDIT PENDING.
> **Session Set:** `docs/session-sets/049-orchestrator-coordination-removal/`
> **Prerequisite:** Set 047
> (`047-state-file-schema-v4-audit`) CLOSED and Set 048
> (`048-lightweight-tier-parity`) CLOSED. v4 schema must be canonical
> and the Lightweight tier must be on parity before the orchestrator
> block reshape lands; otherwise Set 049's writers would step on
> in-flight Set 048 work.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification.

---

## Why this is a STUB

Per `feedback_audit_then_spec_for_substantial_features` and the
operator directive locked 2026-05-26
(`feedback_orchestrator_block_omit_null_no_explorer.md` in memory):
the rip-out touches multiple long-shipped surfaces (PyPI `dabbler-ai-router`,
Marketplace `dabbler-ai-orchestration`, CLAUDE.md, four+ test suites,
the Set 045 dual-primary Explorer surface, the joiner conflict
detection logic), and a fresh cross-provider audit-S1 should run
before this spec is detailed.

---

## Operator-locked premises (NOT open to challenge in S1 audit)

- **P1.** Orchestrator block fields = `engine`, `provider`, `model`,
  `effort`. Nothing else.
- **P2.** Writers use omit-null. Missing keys allowed in the on-disk
  shape; no `null` values, no `"unknown"` placeholder strings.
- **P3.** `checkedOutAt`, `lastActivityAt`, `chatSessionId` — all
  dropped from the on-disk shape and the writer code paths that
  populate them.
- **P4.** No orchestrator information in the Session Set Explorer
  rendering. No harvest-record badges (W / N / M / B). No
  coordination-conflict pills. The Explorer's orchestrator-info
  dimension reverts to its pre-Set-045 shape.
- **P5.** CLI backward compatibility for `python -m ai_router.start_session`:
  existing flags continue to work. Concrete behavior for now-meaningless
  flags (`--chat-session-id`, etc.) is an audit-S1 topic.

These premises are operator-confirmed and inherit from the
2026-05-26 design call captured in the memory entries cited above.

---

## Background — what's being removed and why

The check-out / check-in coordination layer shipped in Set 033 (0.18.0)
and was refined in Set 036 (0.20.0) with the `chatSessionId` identity
composite. Its enforcement was disabled by default mid-Set-046 after a
staff-onboarding incident, with mechanics retained behind
`DABBLER_ENFORCE_CHECKOUT_COORDINATION=1`. The longer-term decision —
parked at the time as "Set 048+ behind audit-then-spec discipline" —
has now been made: full rip-out, not preservation-with-flag.

Triggering observation (operator, 2026-05-26): session-state.json for
Set 047 S4 and S5 recorded `engine=codex, model=gpt-5.4` while the
operator was actually running Claude Opus Max. The recorded orchestrator
identity is unreliable. The `lastActivityAt` field was observed as
*earlier* than `completedAt`, which is nonsense. Better to show no
information than wrong information.

---

## Pre-audit material — what Set 049 is expected to ship

### Code removals/simplifications

1. **`ai_router/start_session.py`** — remove `EXIT_CHECKOUT_CONFLICT`,
   `prior_engine_provider` matching, takeover modal / TTY prompt,
   `_coordination_enforced()` gate. Writer reduces to: write the
   orchestrator block with whatever subset of engine/provider/model/effort
   was supplied; omit any null/missing key.
2. **`ai_router/new_chat_id.py`** — whole CLI retired.
3. **`ai_router/close_session.py`** — check-in branch removed.
4. **`tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`**
   — chatSessionId forwarding and conflict-record emission removed.
   Hook continues to fire `start_session` with `--engine claude
   --provider anthropic` (the model/effort question is part of audit
   topic #3 below).
5. **TS commands and services** — `dabbler.checkOutOrchestrator`,
   `dabbler.releaseCheckOut`, `CheckoutPollService`, the
   chatSessionMismatchModal — all retired.
6. **Joiner conflict-kinds** — `engine-mismatch`,
   `stale-checkout-touch`, `writer-bypass`, `bare-touch` removed from
   `ai_router/joiner/`.
7. **Explorer surface** — harvest-record badges and
   coordination-conflict pills removed from
   `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`
   and adjacent renderers. The harvest CLI shell-out
   (`python -m ai_router.joiner`) is no longer invoked.
8. **Tests** — `test_chatsessionid_writer.py`, `test_checkout_writer.py`,
   `test_start_session_takeover_prompt.py`, and their TS-side
   counterparts retired.

### Schema

Reshape on-disk orchestrator block to:

```json
"orchestrator": {
  "engine": "claude",
  "model": "claude-opus-4-7"
}
```

(example — `provider` and `effort` omitted because not declared)

Two paths for the schema version:

- **v4-compatible** (preferred per pre-audit signal): writers stop
  emitting the three dropped fields; readers ignore extras. The
  enforcement already being disabled means no read site depends on the
  dropped fields for control flow.
- **v5 bump**: clean break, explicit migration.

Audit-S1 disposes.

### Docs

- `CLAUDE.md` — "hard-coordination enforcement" section retired;
  H1/H3/H4 references rewritten as historical
- `docs/session-state-schema.md` — orchestrator-block definition
  reshaped to 4 fields + omit-null pattern
- `docs/session-sets/032/033/036/045/046/047` specs — preserved as
  history (per existing repo convention); only `CLAUDE.md`'s
  current-state sections are rewritten
- `docs/cross-repo-checkout-notice.md` — retired or rewritten as a
  "no longer applies" stub for consumer repos that paste-in'd it
- `~/.dabbler/orchestrator-writer.log` — disposition decided in
  audit topic #5 below

### Releases

- **PyPI `dabbler-ai-router`**: feature-removal version bump. Operator
  chooses major/minor/patch in audit-S1. Consumer-repo count is 3 per
  `project_consumer_repos`; Marketplace download count was 3 as of
  2026-05-15 (`project_marketplace_download_count`). Backward-
  incompatible removal is reasonable given those numbers, but the
  audit should ratify.
- **Marketplace `dabbler-ai-orchestration`**: parallel version bump.

---

## Open audit topics (S1 audit disposes)

1. **Schema version**: v4-compatible (preferred) vs. v5 bump. What's
   the read-site survey across the codebase? Are there any silent
   reads of the dropped fields outside the disabled enforcement
   paths?
2. **CLI compatibility surface**: now-meaningless flags
   (`--chat-session-id`, etc.) — accept-and-ignore, accept-with-warning,
   or refuse with a deprecation error? What does the H1 router-only-writes
   contract require?
3. **How does the orchestrator declare engine/provider/model/effort to
   the writer?** Hook-driven is the current pattern (the
   `claude-session-start-invoker.js` and Codex-equivalent), but hooks
   hard-code engine/provider and pull model/effort from a preserved
   marker file. Under omit-null with no hooks-side mandatory fields,
   should the orchestrator pass these on the CLI explicitly each
   session? Should the hook just call `start_session` with the
   subset it knows and let omit-null handle the rest?
4. **Migration of existing session-state.json files** (47+ historical
   sets): keep their bloated orchestrator blocks (no-op on read), or
   sweep-and-normalize? Implication for the v3→v4 migrator shipped in
   Set 047 S3.
5. **`~/.dabbler/orchestrator-writer.log`**: retained as audit-history
   artifact, or retired with the rest of the coordination layer?
6. **Session-events.jsonl event types**: `holder_change` and
   `checkout_conflict` — retire, or keep emitting as no-op-but-recorded
   for downstream consumers?
7. **Cross-repo CLAUDE.md insertion text** at
   [`docs/cross-repo-checkout-notice.md`](../../cross-repo-checkout-notice.md):
   what's the replacement message for consumer repos that paste-in'd
   the original?

---

## Estimated session arc (audit-deliverable)

Provisional: **3-5 sessions** (audit-S1 + 2-4 implementation sessions).
The rip-out is substantial in line-count but conceptually narrow —
removal-only on most surfaces. Audit-S1 will lock the exact count.

---

## Non-goals

- **Re-design of the orchestrator-identity capture pipeline.** Set 049
  is rip-out only. If a future need for accurate orchestrator-identity
  capture arises, it's a separate green-field audit set, not a Set 049
  extension.
- **Set 045 dual-primary log harvest as a whole.** Only the
  orchestrator-rendering and coordination-conflict pieces of the
  harvest surface are removed. The underlying log-harvest infrastructure
  (wrapper-launched detection, native-log parsing) survives — it has
  uses beyond orchestrator coordination. Audit-S1 should explicitly
  scope the harvest-surface removal to the orchestrator-rendering /
  conflict-pill code paths only.
- **Lightweight-tier-specific changes.** Set 048's territory.

---

## Cross-references

- Predecessor for v4 schema: [`docs/session-sets/047-state-file-schema-v4-audit/`](../047-state-file-schema-v4-audit/)
- Predecessor for Lightweight parity: [`docs/session-sets/048-lightweight-tier-parity/`](../048-lightweight-tier-parity/)
- Memory: `project_set_033_enforcement_disabled.md`
  (the Set 046 incident that triggered the disabled-by-default state)
- Memory: `feedback_orchestrator_block_omit_null_no_explorer.md`
  (the locked design rules)
- Memory: `project_set_049_stubbed.md` (this stub's memory entry)
- Pre-rollback architecture audit (for historical context):
  [`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/)
