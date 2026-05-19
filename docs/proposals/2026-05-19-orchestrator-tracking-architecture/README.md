# Orchestrator-tracking architecture — pre-audit artifacts

> **Status as of 2026-05-19:** Pre-audit. Direction agreed across the
> operator + GPT-5.4 + Gemini Pro. Three Highs + two open questions
> remain to resolve in the audit-then-spec cycle of the follow-on
> session set.
>
> **Consuming session set (planned):** `030-orchestrator-checkout-checkin`
> (NOT YET CREATED). The session set's audit cycle reads this directory
> as input and produces the implementable spec.

## What's here

| File | What it is | Status |
|---|---|---|
| [`proposal.md`](proposal.md) | v1 design proposal — multi-writer precedence vs. check-out / check-in | Frozen 2026-05-19 |
| [`proposal-addendum.md`](proposal-addendum.md) | v1.5 clarifications + responses to GPT-5.4 round-1 findings | Frozen 2026-05-19 |
| [`consensus-gemini-pro.txt`](consensus-gemini-pro.txt) / `.json` | Gemini Pro round 1 verdict (against `proposal.md`) | Final |
| [`consensus-gpt-5-4.txt`](consensus-gpt-5-4.txt) | GPT-5.4 round 1 verdict (manual paste) | Final |
| [`consensus-gpt-5-4-round-2.txt`](consensus-gpt-5-4-round-2.txt) | GPT-5.4 round 2 verdict (against `proposal-addendum.md`, manual paste) | Final |
| `route_consensus.py` / `route_gemini_only.py` / `route_gpt_only.py` | Routing scripts (Gemini ran; GPT hit 429 twice → manual paste) | Historical |

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

## Must-resolve in the audit-then-spec cycle of the follow-on set

These are GPT-5.4 round 2's three Highs + two open questions. They
are not yet decided; the audit cycle should produce specific design
verdicts on each.

### High issues

**H1 — Writer authority.** In Full tier, the existing close-out
contract names exactly two router-driven boundary writes
(`start_session.py` / `close_session.py`). The check-out architecture
must NOT introduce additional writers of the canonical lifecycle
field. Hooks (Claude `SessionStart`, Codex config-toml watcher)
should DETECT changes and INVOKE the canonical writers, never write
the lifecycle field directly. Recommended verdict: **router-only
writes; hooks become invokers.**

**H2 — Single source of truth.** The addendum oscillates between
`session-state.json` (existing lifecycle authority) and
`<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`
(per-set marker introduced in Set 029 S3) as the home for check-out
state. Pick one. Recommended verdict: **`session-state.json` is
canonical; the `.dabbler/orchestrator.json` marker either becomes
derived UI cache or is retired.**

**H3 — Hard coordination vs. advisory.** The addendum frames check-
out as both a hard lock (prevents concurrent AI work) and an
advisory marker (no data at stake; override anytime). These are
materially different failure models. Pick one — override, auto-
release, and audit semantics depend on it. Recommended verdict:
**hard coordination at write time** (`start_session` refuses to write
when held by a different orchestrator); **explicit operator override
is the safety valve**, not the default-allow.

### Open questions

**OQ1 — Field merge.** How does proposed `checkedOut` / `checkedOutBy`
relate to the existing top-level `orchestrator` field in
`docs/session-state-schema.md`? Recommended verdict: **they MERGE.**
The existing `orchestrator: { engine, provider, model, effort }`
already carries identity. Augmentations needed: `checkedOutAt`
timestamp and `lastActivityAt`. `currentSession` already covers the
session number.

**OQ2 — Events as new types or aliases.** Are `work_checked_out` /
`work_checked_in` new ledger event types or aliases for the existing
`work_started` / `closeout_succeeded`? Recommended verdict:
**aliases.** No new event types needed; check-out semantics are
derived from the existing event progression.

## Cost record

- Gemini Pro round 1: $0.015 (routed)
- GPT-5.4 round 1: $0.000 (429 twice; recovered via manual paste)
- GPT-5.4 round 2: $0.000 (manual paste, no router involvement)
- Gemini Pro round 2: not run (consensus frozen 2026-05-19)
- **Total architectural-decision spend: $0.015**

## What ships in Session 6 v0.17.x (NO architecture migration)

Per cross-engine consensus (Gemini R1 + GPT R2 alignment) on
sequencing: ship v0.17.x as polish-only. Specifically:

- Styling iteration → land in `tree.css`
- **Relegate** (NOT rename) `dabbler.setOrchestrator` + Writer Log
  out of the accordion body to Command Palette + right-click context
  menu — addresses GPT R2 Q4 must-fix without architecture commitment
- Banner stays (its removal is coupled to the resolver refactor that
  belongs to Set 030)
- README + CHANGELOG + CLAUDE.md updates
- Marketplace publish (operator-gated)

## What ships in Set 030

The audit cycle resolves H1 / H2 / H3 / OQ1 / OQ2, then produces a
spec.md that implements:

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
