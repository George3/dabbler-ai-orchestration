# chatSessionId + MVVM watcher-scope discipline — audit complete, awaiting implementation spec

> **Status as of 2026-05-21:** **audit complete + verdicts locked.**
> Both Gemini Pro (routed) and GPT-5.4 (operator manual paste)
> returned Round-A verdicts; the operator adjudicated and locked
> the verdict pattern in [`proposal-addendum.md`](proposal-addendum.md).
>
> **Consuming session sets (audit-then-spec):** the audit work is
> done (this directory). The next move is an **implementation spec
> set** (Set-037-candidate) authored from the locked verdicts.
> Sits behind the already-queued Set 034/035 (state-file-sole-truth
> audit per [[project_034_035_state_file_sole_truth_audit]]) in
> the queue.

## What's here

| File | What it is | Status |
|---|---|---|
| [`proposal.md`](proposal.md) | The design proposal — direction + open questions | FROZEN (any further changes go in the addendum) |
| [`audit-resolution-request.md`](audit-resolution-request.md) | The focused review packet for GPT-5.4 + Gemini Pro | FROZEN |
| [`audit-resolution-gemini-pro.txt`](audit-resolution-gemini-pro.txt) / [`.json`](audit-resolution-gemini-pro.json) | Gemini Pro Round-A verdict (routed via `ai_router`, $0.025) | FROZEN |
| [`audit-resolution-gpt-5-4.txt`](audit-resolution-gpt-5-4.txt) | GPT-5.4 Round-A verdict (operator manual paste) | FROZEN |
| [`proposal-addendum.md`](proposal-addendum.md) | **LOCKED verdicts** — operator-adjudicated post-review decision record | FROZEN |
| [`route_gemini_audit.py`](route_gemini_audit.py) | Routing script for the Gemini Round-A call | Historical |

The audit is complete. The next consumer of this directory is the
implementation-spec-set author who reads the
[`proposal-addendum.md`](proposal-addendum.md) "What ships in the
follow-on implementation spec" section and authors a
spec for Set-037-candidate.

## What problem this addresses

Set 033 closed cleanly on 2026-05-21 with the orchestrator
check-out / check-in migration shipped across writer (Python),
reader (TypeScript extension), Layer-3 tests, canonical docs, and
the PyPI release. But two architectural concerns surfaced during
the implementation that the Set 032 audit hadn't anticipated:

1. **H4 identity is coarser than the runtime granularity.** The
   audit's `engine + provider` composite treats two distinct
   chat instances of the same engine as the same holder. Two
   Claude Code windows on the same workspace can each call
   `start_session`; the second is treated as a "re-attach" and
   neither becomes aware of the other.

2. **MVVM inference watchers produce false UI state.** A
   buggy moment during Set 033 Session 6: the operator's
   gauge displayed `Codex gpt-5.4` even though the operator
   was demonstrably running Claude Code. Root cause: the
   v0.17.1 extension's `~/.codex/config.toml` watcher had
   inferred a Codex session from a config-file modification at
   some earlier point and written a stale marker file. The
   v0.18.0 release retires the marker-writer path, but the
   underlying architectural pattern (watch indirect signals,
   update state from them) remains a latent risk for future
   contributions.

The operator proposed a compromise direction during the post-S6
debrief: keep MVVM for UI reactivity, but discipline its scope
to truth-source watching only; introduce `chatSessionId` to
refine H4 from `engine + provider` to
`engine + provider + chatSessionId`; expose an MVC-shaped
agent-facing API so agents read/write the identity field via env
+ explicit CLI args without ever knowing about watchers or
gauges. This package writes that direction up for external
review.

## How we got here

1. **Set 033 closed cleanly** at 04:29 EDT on 2026-05-21. The
   cross-tier `close_session` check-in writer (the very migration
   Set 033 shipped) self-tested on its own close: post-close
   `orchestrator: null`. Six sessions complete; PyPI 0.6.0 live;
   Marketplace 0.18.0 publish deferred pending operator PAT
   rotation.

2. **Mid-session stale-gauge bug** surfaced when the operator
   noticed the accordion's orchestrator gauge showed
   `Codex gpt-5.4` despite running Claude Code. Diagnosis:
   a `.dabbler/orchestrator.json` runtime marker file, written
   *today* by the still-installed v0.17.1 extension's
   codex-config-watcher, was the source. The on-disk
   `session-state.json` was correct (Claude Opus 4.7); the v0.17.1
   UI was reading the marker file instead. Deleted; v0.18.0's
   reader doesn't consult marker files.

3. **Post-close architecture discussion** (interactive, between
   the operator and Claude Opus 4.7) raised:
   - "Shouldn't instructions to the orchestrator be sufficient?
     Why do we need watchers at all?"
   - "It seems like we're implementing MVVM rather than MVC.
     Both are defensible, but MVC is simpler for in-process
     updates."
   - "Could we add a chatSessionId GUID that distinguishes
     chat instances and prevents two-chat collisions on the
     same set?"

4. **Operator's stated compromise** (the basis for this
   proposal):
   - Keep MVVM, limit it to `session-state.json` watching only.
   - Add `chatSessionId` to refine H4.
   - Make the agent-facing API MVC-shaped: agents read the ID
     from an env var and pass it on `start_session` / `close_session`.
   - Retire the codex config-toml watcher (the inference
     pattern that produced today's bug).
   - Retire the `signalKind` confidence-level variants (they
     exist to express inference, which there's no need for
     under explicit-only updates).

5. **External review requested** — same audit-then-spec rhythm as
   Set 032/033. Operator handles GPT-5.4 manually (per the
   429-rate-limit history); Gemini Pro path is operator's call.

## Suggested decomposition (out of this proposal)

If the audit ratifies the direction, the implementation lands as
a separate session set (Set-037-candidate) behind the
Set 034/035 audit cycle:

- **Audit set (Set-036-candidate):** 1–2 sessions; resolves the
  Q1–Q7 open questions; authors the implementation spec.
- **Implementation set (Set-037-candidate):** 4–6 sessions;
  ships the writer change, the agent-instruction updates, the
  codex-watcher retirement, the `signalKind` cleanup, the
  takeover UX, the Layer-3 tests, and the cross-tier doc
  updates.

The proposal explicitly does NOT relitigate the six locked
verdicts from Set 032 (H1, H2, H3, H4 base composite, OQ1, OQ2).
This proposal **refines** H4 (adds chatSessionId), and otherwise
builds on top of the Set 033 implementation.

## Post-audit summary (landed 2026-05-21)

The audit's final outcome:

- **Direction ratified** by both providers (D1 + D2). Gemini
  VERIFIED both; GPT-5.4 REFINED both with wording sharpenings
  that the addendum adopted.
- **Six items refined** via cross-provider consensus (Q1, Q2, Q3,
  Q4, Q5, Q7). The addendum captures the locked text.
- **One item rejected** (Q6): no persistent
  `requireExplicitTakeover` setting. GPT-5.4's safety-first
  argument won; if real friction surfaces later, the
  implementation set ships a one-shot affordance instead.
- **One critical empirical correction** (Q1): no per-chat env
  var is confirmed for any orchestrator. Claude Code uses its
  hook-payload `session_id`; all other orchestrators use a new
  `python -m ai_router.new_chat_id` fallback CLI.
- **One load-bearing concurrency requirement** (Q5): the hybrid
  migration's read/check/write sequence must be serialized via
  a per-set lifecycle lock, otherwise the split-brain race the
  feature is meant to prevent still happens.

See [`proposal-addendum.md`](proposal-addendum.md) "Locked
verdicts" and "What ships in the follow-on implementation spec"
for the complete decision record.

## Cross-references

- **Prerequisite session set:** Set 033 (closed 2026-05-21) —
  [`docs/session-sets/033-orchestrator-checkout-checkin-implementation/change-log.md`](../../session-sets/033-orchestrator-checkout-checkin-implementation/change-log.md)
- **Prerequisite audit:** Set 032 (closed 2026-05-19) —
  [`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`](../2026-05-19-orchestrator-tracking-architecture/)
- **Memory:**
  - [[project_set_032_033_orchestrator_checkout_checkin]] —
    Set 032+033 closure record
  - [[feedback_audit_then_spec_for_substantial_features]] —
    the audit-then-spec discipline this proposal follows
  - [[feedback_no_env_var_probing]] — secret-handling lesson
    from the in-session token leak
  - [[project_034_035_state_file_sole_truth_audit]] —
    queued ahead of this proposal's eventual audit set
