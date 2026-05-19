# Addendum: operator clarifications + responses to GPT-5.4 round-1 findings

> **Date:** 2026-05-19 (same day as the v1 proposal — addendum produced
> after both engines returned round-1 verdicts and the operator pushed
> back on parts of the GPT-5.4 verdict)
> **Read order:** v1 proposal.md FIRST, then this addendum. The
> addendum sharpens the v1 design and answers GPT-5.4's three highs +
> two open questions. Gemini Pro's round-1 verdict already aligns
> with the addendum's direction; we're asking both engines to
> re-evaluate with the new context.

---

## 1. Foundational design assumption (was implicit; now explicit)

**Sessions within a session set are SEQUENTIAL by design. Concurrent
sessions within the same set are NOT supported and SHOULD be
prevented.**

**Multiple session sets MAY run in parallel** (this is documented; the
parallel-trigger phrase in `docs/ai-led-session-workflow.md` activates
a worktree for the parallel set).

The within-set-sequential constraint was implicit in the workflow doc
but not stated as a hard invariant. Surfacing it explicitly is
load-bearing for this proposal: **a sequential-within-set workflow in
a multi-process / multi-AI-orchestrator environment is exactly the
case where a lock-like coordination primitive earns its keep.** A
"perfect" operator wouldn't need it; no operator is perfect, including
the one running this project.

This invariant should also be added to `docs/ai-led-session-workflow.md`
as part of the follow-on implementation — but it stands as the
load-bearing assumption *before* the implementation.

## 2. Mid-session vs. between-session orchestrator change

GPT-5.4 open question #1 asked whether "different orchestrator on
resume → warn" clashes with the documented handoff model in
`docs/ai-led-session-workflow.md` (which says any orchestrator can pick
up between sessions). Clarification:

**Between sessions ≠ mid-session.** They are governed by completely
different rules in the proposed model.

| State | Trigger | Lock state | Conflict semantics |
|---|---|---|---|
| Between sessions | Prior session completed close-out | not-checked-out | None — next orchestrator simply checks out. This is the documented handoff. |
| Mid-session | Orchestrator started but not yet checked in | checked-out | A different orchestrator attempting to attach is one of: (a) operator's purposeful switch — proceed after confirmation; (b) operator's accidental switch — surface the conflict + ask; (c) second orchestrator running in parallel by mistake — the failure case the lock exists to prevent. |

So the workflow doc and the check-out model are **complementary, not
contradictory**. The check-out IS the durable record of "we are
mid-session"; check-in IS the released-for-next-orchestrator signal.

This also retires GPT's framing of "resume" as ambiguous. There is no
ambiguous "resume." Either the set is checked-in (= between sessions,
any orchestrator may check out) or checked-out (= mid-session, only
the same orchestrator may resume without conflict).

## 3. Lightweight tier does NOT excuse skipping the lock

GPT-5.4 Medium #1 said `close_session`-as-check-in breaks portability
because Lightweight tier has no automated close. Operator response:

> "Just because we have a lightweight option doesn't mean that we
> should ignore potentially problematic issues. The lightweight-ness
> is in the eye of the human operator more so than in the eye of the
> AI engines. Even in the lightweight model, we have the problematic
> situation of a human operator inadvertently having two AI
> orchestrators work on the same session (or session set) at the
> same time. That is a problem that we need to prevent."

**Lightweight refers to the human's adoption complexity (no router
setup, no API keys, no cross-provider verification). It does NOT
refer to the underlying coordination correctness.** Two AIs
inadvertently driving the same session set is a failure mode in
**every** tier.

The requirement becomes: **all tiers MUST perform check-in at session
close.** For Full tier, `close_session` does it automatically. For
Lightweight, the orchestrator (or human) hand-writes the same
release into `session-state.json` (one extra field, same pattern as
the existing hand-maintained `completedSessions[]`). This isn't a new
mandatory step — it makes explicit what was already implicit.

Schema delta for Lightweight close-out (`docs/session-state-schema.md`):
```json
{
  "checkedOut": null,             // was an object during the session; now null
  "checkedOutBy": null,           // historical record of last check-out clearable
  "lastCheckedOutAt": "<ISO>"     // bumped at every check-out
}
```

The Lightweight tier's documentation already requires hand-maintaining
`completedSessions[]` on every close — extending that to include the
check-out clear is a one-line addition, not a structural change.

## 4. Queueing / polling (NEW feature, not in v1 proposal)

The operator surfaced a positive feature the v1 proposal didn't
articulate. **A check-out / check-in model UNLOCKS this; the
current precedence model can't cleanly support it.**

**Scenario:** operator has Claude actively driving Session N of
`docs/session-sets/029-foo`. They want Codex to pick up Session N+1
once Claude finishes. They tell Codex "start the next session of
029-foo". Without check-out:

- Codex doesn't know Claude is mid-session.
- Codex blindly starts, potentially writing into the same activity-
  log / state file Claude is still updating. The failure mode the
  whole proposal is trying to prevent.

With check-out:

- Codex reads `session-state.json` → sees set is `checkedOut: {
  orchestrator: "claude-code", model: "opus-4-7", session: N }`.
- Codex surfaces a prompt: "029-foo Session N is currently checked
  out by Claude. Options: **(a)** poll every 5 min and start the next
  session automatically when Claude checks in; **(b)** abort —
  nothing to do; **(c)** force-override Claude's check-out (warns
  about potential data races)."
- Operator picks (a). Codex polls. Operator goes to lunch / bed /
  home. Claude finishes; check-in fires. Codex auto-picks-up Session
  N+1.

This is a genuine productivity unlock: the operator can queue
sessions across orchestrators before stepping away.

A nice property: this scenario also surfaces operator mistakes. If
the operator thought Claude had finished but it hadn't, Codex's
prompt makes the active state visible — the operator notices and
adjusts.

## 5. State model (concrete answer to GPT-5.4 High #2)

GPT-5.4 said the v1 proposal "is not yet a simplification of snapshot
+ precedence; it is an unscoped lease protocol plus history plus
conflict UI." Fair — v1 didn't spell the state model out. Here:

**States per session set** (carried in `session-state.json` alongside
the existing fields, NOT in a separate file):

- `not-checked-out` — between sessions, or new set. Open to any
  orchestrator's check-out. (This is also today's `status: "in-
  progress"` state between sessions.)
- `checked-out{ orchestrator, model, effort, thinking, sessionNumber,
  startedAt, lastActivityAt }` — exactly one orchestrator owns the
  set's active session.

That's it. Two states.

**Transitions:**

| Event | From | To | Producer |
|---|---|---|---|
| Check out (Session N start) | `not-checked-out` | `checked-out{...}` | `register_session_start()` / `start_session` CLI / SessionStart hook |
| Same-orchestrator continuation (window reload, /clear) | `checked-out{A}` | `checked-out{A}` (no-op refresh, bump `lastActivityAt`) | Hook payload identity match |
| Different-orchestrator attach attempt | `checked-out{A}` | (prompt) → `checked-out{B}` if force-override, else stays `checked-out{A}` | Quickpick / second-orchestrator session start |
| Check in (Session N close) | `checked-out{...}` | `not-checked-out` | `close_session` CLI / Lightweight hand-write |
| Stalled-checkout recovery | `checked-out{stalled}` | `not-checked-out` | Operator command, or auto if `lastActivityAt` > N hours and `auto_release` setting on |
| `/think*` effort update | `checked-out{..., effort: X}` | `checked-out{..., effort: Y}` (in-state update, not a transition) | `/think*` listener |

**That collapses GPT's "lease + history + conflict UI" complaint.**
The lease protocol IS the state machine — 2 states + 6 transitions.
History is just the append-only `session-events.jsonl` ledger that
already exists (`work_started`, `work_completed` events get
`work_checked_out` / `work_checked_in` aliases). Conflict UI is one
QuickPick on different-orchestrator attach, and one notification on
stalled-checkout detect — that's it.

**Crucially, an override:** the operator can force-release a
check-out via Command Palette ("Release Check-Out") at any time. No
data is at stake — the marker is purely advisory. If the system
gets stuck, one command unsticks it.

## 6. Multi-set rendering, post-check-out (concrete answer to
   GPT-5.4 High #1 + clarifies operator's "I don't get why
   multi-set rendering would be a problem")

GPT-5.4 High #1 was a CODE-LEVEL critique of the v1 proposal:
removing the multi-in-progress banner without refactoring
`MarkerWatchService.resolveActiveSet()` would leave both rows with
no accordion — the resolver still says `unresolved` so no row gets
marker data.

**Under check-out / check-in, this critique evaporates because
there's no "pick one" resolver to refactor away from — every set's
state is in its own per-set marker file already.**

Concrete reader contract under the new model:

```typescript
// New shape:
type ResolverResult = {
  inProgress: Array<{ slug, setDir, checkOut: CheckOutRecord | null }>;
  // No "resolved" / "unresolved" — just the list of in-progress sets,
  // each with its own check-out (or null for between-sessions).
};
```

The view iterates `inProgress` and renders an accordion-body for
each row from THAT row's `checkOut`. There is no global
disambiguation step. There is no banner. **There never were two
sets fighting for "the resolved one" — that was an artifact of the
pre-pivot single-marker architecture.**

So multi-set rendering and check-out/check-in are the **same change,
not two**. The v1 proposal's separation between them was wrong; this
addendum corrects it. The migration replaces:

- `resolveActiveSet()` → `listInProgressSets()` (no fail-closed)
- Old precedence-aware marker write → check-out-aware write that
  refuses to clobber a held check-out without override
- Banner → gone

## 7. Decoupling rename/relegate from migration (GPT-5.4 open
   question #2)

GPT-5.4 said the operator's original objection was about naming and
affordance — separate from the deeper architecture rewrite. Operator
disagrees with that decoupling **only insofar as** the
rename/relegate alone doesn't address the inadvertent-two-AIs
failure mode that motivates the lock.

Concretely:

- "Declare Orchestrator…" as a renamed declaration-without-lock is
  cosmetic. The two-AI failure stays possible.
- "Check Out As…" as a check-out-aware action prevents the two-AI
  failure by design. The rename IS the relabel.

So the rename is a tell about which architecture you've picked. If
the check-out architecture is approved, rename → "Check Out As…"; if
keeping precedence, rename → "Declare Orchestrator…". Both can
relegate to Command Palette + right-click context menu. Pick the
architecture first; the rename follows.

## 8. Revised summary of changes

If both engines (and the operator) align on the addendum's framing,
the cleanest path is:

**Session 6 (in flight) — UI polish only:**
- Round-N styling iteration → land in `tree.css`.
- README / CHANGELOG / CLAUDE.md / Marketplace publish for v0.17.x
  WITHOUT any architecture migration. The current precedence +
  banner ship as-is; the misnamed "Set Orchestrator…" button stays.
- *Reason:* publishing the check-out architecture in a half-day is
  irresponsible; we want the audit-then-spec discipline.

**Follow-on session set `030-orchestrator-checkout-checkin`:**
- Audit + spec per memory `feedback_audit_then_spec_for_substantial_features`.
- Implement check-out / check-in state model per §5 here.
- Replace `resolveActiveSet()` with `listInProgressSets()` per §6.
- Rename + relegate `dabbler.setOrchestrator` to "Check Out As…"
  in Command Palette + right-click context menu.
- Replace the precedence model + writer log with the conflict
  prompt + force-release command.
- Add the queueing/polling feature per §4 (could be a sub-session
  within the set, or a separate slice — to be sized during audit).
- All tiers (Lightweight + Full) check in at session close.

## Questions for round 2

For each engine: re-evaluate your round-1 verdict on Q1–Q6 with §1–§7
above as additional context. Specifically:

- **Q1 (simplification):** does §5's two-states-six-transitions state
  model + operator-override-via-Command-Palette change your "lease +
  history + conflict UI" framing?
- **Q2 (failure modes):** does §4's queueing/polling feature change
  the equation? Are there failure modes you flagged in round 1 that
  this addendum has not addressed?
- **Q3 (hooks-as-checkout):** does §2's mid-session-vs-between-
  sessions distinction resolve the "stale check-out on window
  reload" concern (window reload = same orchestrator = no-op
  refresh of `lastActivityAt`)?
- **Q4 (rename fate):** given §7, do you still prefer "rename only"
  as a separable step, or do you agree the rename should follow the
  architecture choice?
- **Q5 (Writer Log fate):** under check-out, the writer log
  becomes a force-override + stalled-recovery audit trail —
  much narrower scope. Keep as Command Palette / right-click
  context menu, or eliminate?
- **Q6 (multi-set rendering):** does §6's "no resolver to refactor,
  it's the same change" argument change your round-1 framing? Is
  removing the banner + rendering per-set gauges under check-out
  the cleaner path?

Same response format as round 1: verdict + reasoning + must-fix /
follow-up notes per question, plus an overall recommendation.

The other reviewer is **__OTHER__**.
