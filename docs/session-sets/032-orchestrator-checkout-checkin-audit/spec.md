# Orchestrator check-out / check-in — audit cycle

> **Purpose:** resolve the three Highs and two open questions GPT-5.4
> raised in round 2 against the pre-audit proposal + addendum.
> Produce the implementation spec.md that Set 033 executes.
> **Created:** 2026-05-19
> **Session Set:** `docs/session-sets/032-orchestrator-checkout-checkin-audit/`
> **Prerequisite:** [`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`](../../proposals/2026-05-19-orchestrator-tracking-architecture/)
> — full pre-audit artifacts: proposal.md, proposal-addendum.md,
> consensus-gemini-pro.{txt,json}, consensus-gpt-5-4.txt (R1),
> consensus-gpt-5-4-round-2.txt (R2), README.md (must-resolve items).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification
> **Pattern:** Audit-then-spec per [[feedback_audit_then_spec_for_substantial_features]]
> — this set is the AUDIT half; Set 033 is the IMPLEMENTATION half.

---

## Session Set Configuration

```yaml
totalSessions: 2
requiresUAT: false
requiresE2E: false
```

> **Rationale:** the audit produces a spec.md (a markdown document)
> as its primary deliverable. No code, no UI, no browser behavior.
> UAT and E2E gates do not apply.

---

## Project Overview

The orchestrator-tracking architecture discussion in Set 029
Session 6 produced cross-provider verdicts (Gemini Pro R1 +
GPT-5.4 R1 & R2) endorsing migration to a check-out / check-in
model, with three Highs + two open questions left to resolve
before the implementation can be honestly specced.

Set 032 = the audit cycle that resolves those items. The output is
Set 033's spec.md, plus a small set of updates to the
canonical workflow doc + schema doc.

### Three Highs to resolve (from GPT-5.4 R2 must-fix list)

- **H1 — Writer authority.** Full-tier writes today are
  router-only (`start_session` + `close_session` CLIs per
  `ai_router/docs/close-out.md`). Under the check-out model, hooks
  (Claude `SessionStart`, Codex config-toml watcher) cannot become
  peer writers — they must remain *invokers* / *detectors*. Pre-
  audit recommendation: router-only writes; hooks invoke
  `start_session` instead of writing the lifecycle field
  themselves. Audit confirms or refines this.

- **H2 — Single source of truth.** The pre-audit oscillates
  between `session-state.json` (existing lifecycle authority per
  `docs/session-state-schema.md`) and the per-set marker file at
  `<workspace>/docs/session-sets/<slug>/.dabbler/orchestrator.json`
  (introduced in Set 029 S3). Pick one. Pre-audit recommendation:
  `session-state.json` is canonical; the `.dabbler/orchestrator.json`
  marker either becomes derived UI cache or is retired entirely.
  Audit confirms one of those two paths.

- **H3 — Hard coordination vs. advisory.** The pre-audit framed
  check-out as both a hard lock and an advisory marker. Pick one.
  Pre-audit recommendation: hard coordination at write time
  (`start_session` refuses to write when held by a different
  orchestrator); explicit operator `--force` flag + Command Palette
  release action is the safety valve. Audit confirms.

### Two open questions

- **OQ1 — Field merge.** How do proposed `checkedOut` /
  `checkedOutBy` fields relate to the existing top-level
  `orchestrator` field in `docs/session-state-schema.md`? Pre-
  audit answer: they merge — `orchestrator` becomes the active
  check-out record when `status=in-progress`, augmented with
  `lastActivityAt`.

- **OQ2 — Events as new types or aliases.** Are
  `work_checked_out` / `work_checked_in` new ledger event types
  or aliases for the existing `work_started` /
  `closeout_succeeded`? Pre-audit answer: aliases — no new event
  types needed; check-out semantics are derived from the existing
  event progression.

---

## Session 1 of 2: Resolve Highs + open questions via cross-engine consensus

**Goal:** route each of H1 / H2 / H3 / OQ1 / OQ2 through GPT-5.4 +
Gemini Pro for cross-provider verdict. Synthesize answers. Update
proposal + addendum with resolution.

**Steps:**

1. **Read all pre-audit artifacts.** proposal.md, proposal-addendum.md,
   both engines' R1+R2 verdicts, audit-input README's must-resolve
   list. Verify operator's clarifications from Set 029 S6 chat are
   captured.
2. **Author audit-request packet** at
   `docs/proposals/2026-05-19-orchestrator-tracking-architecture/audit-resolution-request.md`
   — narrows the five items to specific verdicts the engines must
   choose between, with the pre-audit recommendation called out as
   the default answer.
3. **Route audit-resolution packet through both engines.** Gemini Pro
   via `ai_router.query`; GPT-5.4 via routed call OR manual paste
   per `feedback_split_large_verification_bundles`. Save raw
   responses at
   `docs/proposals/2026-05-19-orchestrator-tracking-architecture/audit-resolution-{gpt-5-4,gemini-pro}.{txt,json}`.
4. **Synthesize verdicts.** Convergence on H1 / H2 / H3 = lock the
   answer. Divergence = surface via `AskUserQuestion` for operator
   adjudication.
5. **Update proposal-addendum.md** with the resolved verdicts and
   any operator adjudications, replacing the "must-resolve" framing
   with "resolved" framing.
6. **End-of-session verification** (gemini-pro per recent pattern).

**Creates:**
- `docs/proposals/2026-05-19-orchestrator-tracking-architecture/audit-resolution-request.md`
- `docs/proposals/2026-05-19-orchestrator-tracking-architecture/audit-resolution-{gpt-5-4,gemini-pro}.{txt,json}`

**Touches:**
- `docs/proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md` (resolved framing)
- `docs/proposals/2026-05-19-orchestrator-tracking-architecture/README.md` (updated must-resolve → resolved)

**Ends with:** All three Highs + two open questions have committed
verdicts. The pre-audit artifacts directory now reflects "resolved"
status.

**Progress keys:** `session-001/audit-resolution-routed`,
`session-001/verdicts-synthesized`, `session-001/addendum-updated`,
`session-001/round-a-verification`

**Estimated cost:** $0.05–$0.20 (cross-engine consensus on five
items + verification).

---

## Session 2 of 2: Draft Set 033 implementation spec + close-out

**Goal:** produce the implementation spec.md that Set 033 executes.
Update Set 033's session-set folder (which exists with a placeholder
spec) with the authored spec.

**Steps:**

1. **Read resolved verdicts** from S1's output. Cache the canonical
   answers to H1 / H2 / H3 / OQ1 / OQ2.
2. **Draft Set 033 spec.md** at
   `docs/session-sets/033-orchestrator-checkout-checkin-implementation/spec.md`.
   Replace the placeholder. Structure follows the canonical spec
   template (Session Set Configuration + Project Overview + per-
   feature Scope + per-session Steps/Creates/Touches/Ends-with/
   Progress-keys + Risks + Routing notes + Cost estimates).
   Per-session split:
   - S1: state machine in `session-state.json` + `start_session`
     refactor (hard-coordination refusal + `--force` override)
   - S2: per-set marker retirement (per H2 verdict) + resolver
     refactor (multi-set rendering) + banner removal
   - S3: UI rename (`dabbler.setOrchestrator` →
     `dabbler.checkOutOrchestrator`) + ActionRegistry update +
     Command Palette release action
   - S4: Playwright tests for multi-set rendering + check-out
     conflict scenarios
   - S5: queueing / polling feature (second orchestrator detects
     held check-out, offers poll/abort/force-override)
   - S6: cross-tier check-in on `close_session` (Lightweight +
     Full) + cross-repo CLAUDE.md notifications + workflow-doc
     within-set-sequential invariant + PyPI release
3. **Cross-provider review of the drafted spec.** Route to Gemini
   Pro for the implementation spec sanity check (catch
   sequencing / dependency mistakes early). GPT-5.4 via manual
   paste if budget warrants. Cost-cap at $0.15 — the spec is
   bounded; verification doesn't need to be exhaustive.
4. **Apply any must-fix items** from the review. Re-circulate only
   if material changes.
5. **Update audit-input README** at
   `docs/proposals/2026-05-19-orchestrator-tracking-architecture/README.md`
   — mark must-resolves as resolved; point at the now-authored
   Set 033 spec.
6. **Author change-log.md** for Set 032 (final-session
   aggregation pattern).
7. **End-of-session verification.**
8. **close_session** invocation.

**Creates:**
- `docs/session-sets/033-orchestrator-checkout-checkin-implementation/spec.md`
  (REPLACES the placeholder spec)
- `docs/session-sets/032-orchestrator-checkout-checkin-audit/change-log.md`

**Touches:**
- `docs/session-sets/033-orchestrator-checkout-checkin-implementation/session-state.json`
  (update totalSessions / sessions[] titles per the authored spec)
- `docs/proposals/2026-05-19-orchestrator-tracking-architecture/README.md`

**Ends with:** Set 033 has a real, audit-vetted, implementable
spec.md. Set 032 closes cleanly.

**Progress keys:** `session-002/set-033-spec-drafted`,
`session-002/spec-cross-review`, `session-002/spec-finalized`,
`session-002/audit-input-readme-updated`, `session-002/round-a-verification`,
`session-002/change-log-generated`, `session-002/close-session-succeeded`

**Estimated cost:** $0.05–$0.20 (spec review + close-out).

---

## Risks

- **R1 — Engine divergence on a load-bearing High.** If GPT and
  Gemini disagree on (e.g.) H2 (single source of truth), the
  audit can't lock the design. Mitigation: pre-audit recommends a
  specific answer for each; engines are asked to confirm or
  refute, not to redesign. If both reject the same recommendation,
  operator adjudicates via `AskUserQuestion` per `unresolved_action`
  default (the very pattern delegation-consensus formalizes — Set
  031 ships first).
- **R2 — Spec sequencing missteps.** A 6-session implementation
  spec is bigger than recent precedent (Set 029 was 6 with a heavy
  audit; the actual implementation work was 4-5 sessions). Risk
  of mid-set re-shaping. Mitigation: Session 2's cross-provider
  spec review catches sequencing / dependency mistakes before
  Set 033 starts.
- **R3 — Audit-input artifact drift.** If pre-audit consensus
  artifacts get edited mid-audit, the audit's basis shifts.
  Mitigation: pre-audit artifacts are FROZEN as of Set 029 close-
  out 2026-05-19; the audit's input is the historical snapshot,
  not a live document. Updates land in proposal-addendum.md's
  "resolved" section, not in the original proposal.md.

---

## Routing notes

- **Audit consensus call (S1):** GPT-5.4 + Gemini Pro on the
  audit-resolution packet. Per
  `feedback_split_large_verification_bundles`, both engines
  receive ~2-4k char packets (well under the 700-LOC threshold).
  Estimated $0.05-$0.15 routed.
- **Session-end verification (S1, S2):** gemini-pro per recent
  pattern; single verifier; Round-A only unless must-fix surfaces.
- **Implementation work:** none in this set — the deliverable is a
  spec.md. The implementation work is Set 033.

---

## Total estimated cost

- Session 1: $0.05–$0.20.
- Session 2: $0.05–$0.20.
- **Total Set 032 forecast: $0.10–$0.40.**
