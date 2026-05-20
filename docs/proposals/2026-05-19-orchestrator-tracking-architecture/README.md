# Orchestrator-tracking architecture — pre-audit + audit artifacts

> **Status as of 2026-05-19 (audit resolved):** Direction agreed
> across the operator + GPT-5.4 + Gemini Pro since the pre-audit
> rounds. **All six design items resolved via Set 032 Session 1.**
> Set 033's implementation spec is authored from these verdicts in
> Set 032 Session 2.
>
> **Consuming session sets (two-set audit-then-spec per
> `feedback_audit_then_spec_for_substantial_features`):**
> `032-orchestrator-checkout-checkin-audit` — Session 1 (audit
> resolution, complete 2026-05-19) + Session 2 (drafts Set 033's
> implementation spec) → `033-orchestrator-checkout-checkin-
> implementation` (executes the authored spec; placeholder spec
> currently). Numbering bumped from the originally-planned `030-...`
> after `030-session-state-v3-sessions-ledger` was rediscovered as
> the existing 030 slot (complete since 2026-05-17) and
> `031-delegation-consensus-config` took the next slot.

## What's here

| File | What it is | Status |
|---|---|---|
| [`proposal.md`](proposal.md) | v1 design proposal — multi-writer precedence vs. check-out / check-in | Frozen 2026-05-19 |
| [`proposal-addendum.md`](proposal-addendum.md) | v1.5 clarifications + responses to GPT-5.4 round-1 findings | Frozen 2026-05-19 |
| [`consensus-gemini-pro.txt`](consensus-gemini-pro.txt) / `.json` | Gemini Pro round 1 verdict (against `proposal.md`) | Final |
| [`consensus-gpt-5-4.txt`](consensus-gpt-5-4.txt) | GPT-5.4 round 1 verdict (manual paste) | Final |
| [`consensus-gpt-5-4-round-2.txt`](consensus-gpt-5-4-round-2.txt) | GPT-5.4 round 2 verdict (against `proposal-addendum.md`, manual paste) | Final |
| `route_consensus.py` / `route_gemini_only.py` / `route_gpt_only.py` | Round-1/2 routing scripts (Gemini ran; GPT hit 429 twice → manual paste) | Historical |
| [`audit-resolution-request.md`](audit-resolution-request.md) | Set 032 S1 audit packet (5 items: H1, H2, H3, OQ1, OQ2) | Final |
| [`audit-resolution-gemini-pro.txt`](audit-resolution-gemini-pro.txt) / `.json` | Gemini Pro audit verdict — all 5 confirmed | Final |
| [`audit-resolution-gpt-5-4.txt`](audit-resolution-gpt-5-4.txt) | GPT-5.4 audit verdict — 5/5 confirmed + raised H4 | Final |
| [`audit-resolution-paste-for-gpt-5-4.md`](audit-resolution-paste-for-gpt-5-4.md) | Paste-ready packet (manual GPT paste; 429 fallback) | Historical |
| [`audit-resolution-h4-request.md`](audit-resolution-h4-request.md) | H4 follow-up packet (holder identity key) | Final |
| [`audit-resolution-h4-gemini-pro.txt`](audit-resolution-h4-gemini-pro.txt) / `.json` | Gemini Pro H4 verdict — refined → `engine + provider` | Final |
| `route_audit_resolution.py` / `route_h4_gemini.py` | Set 032 S1 routing scripts | Historical |

## How we got here

1. **Operator pushback** on the `Set Orchestrator…` and `Writer Log`
   buttons during the Session 6 HTML-preview iteration loop. The
   `Set Orchestrator…` button declares an orchestrator without
   actually setting one (writes a marker, doesn't change the running
   AI). Operator asked: is this the right architecture, or should we
   migrate to a check-out / check-in lock-like model?
2. **v1 proposal.md authored** by Claude — laid out the multi-writer
   precedence (status quo) vs. check-out / check-in (proposed) trade-
   off. Asked 6 questions for cross-provider review.
3. **Round 1 verdicts (2026-05-19):**
   - Gemini Pro: clear support for migration; ship banner removal in
     v0.17.x.
   - GPT-5.4: not approved — three highs (banner removal alone hides
     symptom; "simplification" is actually unscoped lease protocol;
     `close_session` not universal across tiers) + two open questions.
4. **Operator pushback on GPT-5.4 verdict** — clarified:
   - Within-set sessions are sequential by design.
   - Mid-session orchestrator change is the failure mode the lock
     prevents; between-session handoff is normal.
   - Lightweight tier doesn't excuse skipping the lock (Lightweight
     refers to human adoption complexity, not coordination
     correctness).
   - Queueing / polling across orchestrators is a positive feature
     check-out unlocks.
5. **proposal-addendum.md authored** capturing operator's clarifications
   + sketching concrete two-state model + multi-set rendering framing.
6. **Round 2 verdicts (2026-05-19):**
   - GPT-5.4: progressed from "not approved" to "credible follow-on
     direction, but not yet fully specified." Three new must-resolve
     items + two open questions remain.
   - Gemini Pro round 2: not run. Operator + Claude agreed to freeze
     consensus iteration — the must-resolve items are the audit's
     job, not another quick consensus pass.

## Audit resolution — Set 032 Session 1 (2026-05-19)

All six items below are **RESOLVED**. Set 033 implementation spec
authoring uses these verdicts as the backbone. Full reasoning and
cross-provider verdict trail live in
[`proposal-addendum.md`](proposal-addendum.md) §9.

### High issues — resolved

**H1 — Writer authority. RESOLVED: router-only writes; hooks become
invokers.** Full-tier check-out state is mutated only by the existing
boundary CLIs (`start_session.py`, `close_session.py`). Hooks
detect + invoke; they do not race the writer. *Cross-provider: both
engines confirmed.*

**H2 — Single source of truth. RESOLVED: `session-state.json` is
canonical; `.dabbler/orchestrator.json` is RETIRED.** Set 033 removes
the per-set marker file and `MarkerWatchService`'s precedence logic.
The "derived UI cache" alternative was explicitly rejected (cache
invalidation adds complexity for no payoff at trivial read cost).
*Cross-provider: both engines confirmed.*

**H3 — Hard coordination vs. advisory. RESOLVED: hard coordination
at write time + explicit operator override safety valve.**
`start_session` refuses to write when a different holder owns the
check-out (per H4's equality rule). The refusal error must name
the current holder (engine + provider) and the available release
paths (`--force`, "Release Check-Out") so the operator can act on
it without consulting docs. Overrides: `--force` flag, Command
Palette "Release Check-Out", queueing/polling conflict prompt.
The addendum's earlier "purely advisory" framing is retracted.
*Cross-provider: both engines confirmed.*

**H4 — Holder identity key. RESOLVED: `engine + provider` composite.**
(NEW item raised by GPT-5.4 during the audit pass.) Conflict-
equality compares `engine` AND `provider` fields; `model` and
`effort` are mutable holder-state and excluded from identity.
*Cross-provider: Gemini Pro refined to composite key over pre-audit's
engine-only on future-proofing grounds; GPT permitted any stable
subset; operator adjudicated 2026-05-19 = lock the composite.*

### Open questions — resolved

**OQ1 — Field merge. RESOLVED: MERGE into existing `orchestrator`
block.** Schema delta is +2 nested fields under `orchestrator`:
`checkedOutAt` (ISO timestamp, set on transition to
`status: in-progress`) and `lastActivityAt` (ISO timestamp, bumped
on in-state updates). `orchestrator` is null between sessions.
*Cross-provider: both engines confirmed.*

**OQ2 — Events as new types or aliases. RESOLVED: ALIASES.**
`work_checked_out` / `work_checked_in` are documentation
terminology aliases for the existing `work_started` /
`closeout_succeeded` events; no schema change to the ledger.
Documentation updates land in `docs/session-state-schema.md` +
`ai_router/docs/close-out.md`. *Cross-provider: both engines
confirmed.*

## Cost record

- Gemini Pro round 1: $0.015 (routed)
- GPT-5.4 round 1: $0.000 (429 twice; recovered via manual paste)
- GPT-5.4 round 2: $0.000 (manual paste, no router involvement)
- Gemini Pro round 2: not run (consensus frozen 2026-05-19)
- Set 032 S1 audit Gemini Pro: $0.008 (5-item packet)
- Set 032 S1 audit GPT-5.4: $0.000 (429 → manual paste)
- Set 032 S1 H4 follow-up Gemini Pro: $0.004
- **Total architectural-decision spend: ~$0.027**

## What ships in Session 6 v0.17.x (NO architecture migration)

Per cross-engine consensus (Gemini R1 + GPT R2 alignment) on
sequencing: ship v0.17.x as polish-only. Specifically:

- Styling iteration → land in `tree.css`
- **Relegate** (NOT rename) `dabbler.setOrchestrator` + Writer Log
  out of the accordion body to Command Palette + right-click context
  menu — addresses GPT R2 Q4 must-fix without architecture commitment
- Banner stays (its removal is coupled to the resolver refactor that
  belongs to Sets 032 + 033)
- README + CHANGELOG + CLAUDE.md updates
- Marketplace publish (operator-gated)

## What ships across Sets 032 + 033

Set 032's audit cycle resolved H1 / H2 / H3 / H4 / OQ1 / OQ2 in
Session 1 (this document). Session 2 produces Set 033's
implementation spec.md from those verdicts. Together Sets 032 + 033
ship:

- Check-out / check-in state machine in `session-state.json`
- `start_session` becomes the canonical writer (refuses on conflict
  without operator override); hooks become invokers
- Multi-in-progress rendering (resolver returns all in-progress sets;
  each row reads from its own session-state.json)
- Banner removal
- Rename `dabbler.setOrchestrator` → `dabbler.checkOutOrchestrator`
  ("Check Out As…")
- Writer Log narrows to force-override + stalled-recovery + attach-
  conflict audit trail
- Cross-orchestrator queueing / polling feature
- `close_session` check-in for all tiers (Full + Lightweight)
- `docs/ai-led-session-workflow.md` updated to make the within-set
  sequential invariant explicit

The audit cycle reads this directory as input. The implementation
session(s) follow the audit's spec.
