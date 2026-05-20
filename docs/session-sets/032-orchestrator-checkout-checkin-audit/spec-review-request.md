# Cross-provider review — Set 033 implementation spec

> **Context:** Set 032 Session 2 (2026-05-19), `dabbler-ai-orchestration`.
> Set 032 is the AUDIT half of an audit-then-spec cycle for the
> orchestrator check-out / check-in migration; Session 1 locked 6
> verdicts (H1, H2, H3, H4, OQ1, OQ2) via cross-engine consensus
> (Gemini Pro routed + GPT-5.4 manual-paste). Session 2 authored the
> Set 033 implementation `spec.md` — a 6-session implementation plan
> that translates those verdicts into code. This is the cross-provider
> sanity check on the drafted spec.

## Your task

Review the drafted Set 033 spec below. Your job is to catch
**sequencing / dependency mistakes**, **missing surface area**,
**scope creep beyond the locked verdicts**, and **anti-patterns**
before Set 033 starts executing. Approve, approve-with-suggestions,
or must-fix.

You are NOT being asked to redesign the architecture — the 6 verdicts
are locked. You ARE being asked to confirm the spec faithfully
translates them and that the per-session split is implementable in
the order given.

## What I specifically want you to check

1. **Verdict traceability.** Does each of H1, H2, H3, H4, OQ1, OQ2
   map to one or more concrete steps in the spec? Any verdict
   without a clear landing point?
2. **Sequencing.** Does each session's work depend only on work that
   prior sessions completed? Specifically:
   - S2 (reader refactor) depends on S1's writer being correct.
   - S3 (UI rename) depends on S1's writer being callable + S2's
     reader being on the canonical authority.
   - S4 (Playwright tests) depends on the visible behaviors S1–S3
     produced.
   - S5 (queueing) depends on S1's refusal error + S3's hook
     refactor.
   - S6 (close-out parity + docs + release) depends on everything
     before it.
3. **Missing surface area.** Anything the verdicts imply that the
   spec doesn't explicitly address?
4. **Scope creep.** Anything in the spec that goes BEYOND the six
   locked verdicts? (Feature additions, refactors, dependencies not
   justified by the audit.)
5. **Risk coverage.** Are the named Risks (R1–R6) the right ones?
   Anything load-bearing missing?

## Response format

For each of (1)–(5), answer with:

- **Verdict:** `approve` / `approve-with-suggestions` / `must-fix`
- **Reasoning:** 1–3 sentences.
- **Suggestions or must-fix items:** bulleted; explicit file path
  and section name when applicable.

End with an **overall verdict** (one line) and an **overall cost
sanity check** (does the $0.45–$1.25 forecast seem reasonable for
6 sessions of work as described, given the precedents cited?).

Constrain your response to ~500 words.

---

## Reference: the six locked verdicts

(Restating verbatim from
`docs/proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md` §9.)

- **H1 — Writer authority:** ROUTER-ONLY WRITES; hooks become
  invokers. Full-tier check-out state is mutated only at
  `start_session.py` / `close_session.py`. Hooks INVOKE the writer,
  do not write directly. Both engines confirmed.
- **H2 — Single source of truth:** `session-state.json` is canonical;
  `.dabbler/orchestrator.json` is RETIRED. Reader consumes
  `session-state.json` directly per in-progress set. Both engines
  confirmed.
- **H3 — Hard coordination, not advisory:** `start_session` REFUSES
  when held by a different `engine+provider`; refusal error MUST
  name (a) the current holder and (b) the two release paths
  (`--force`, "Release Check-Out"). Both engines confirmed.
- **H4 — Holder identity key:** `engine + provider` composite.
  Other fields (`model`, `effort`) are mutable holder-state. GPT
  raised; Gemini refined to composite; operator adjudicated 2026-05-19.
- **OQ1 — Field merge:** Merge into existing `orchestrator` block;
  +2 nested fields (`checkedOutAt`, `lastActivityAt`). Block is
  `null` when `status != in-progress`. Both engines confirmed.
- **OQ2 — Events:** ALIASES for `work_started` / `closeout_succeeded`.
  No ledger schema change. Both engines confirmed.

---

## The drafted spec

See `docs/session-sets/033-orchestrator-checkout-checkin-implementation/spec.md`.
The full text is appended below.

---

__SPEC_BODY__
