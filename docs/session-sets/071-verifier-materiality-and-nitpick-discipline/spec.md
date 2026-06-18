# Verifier Materiality Gate + Nitpick-Churn Discipline Spec (Set 071)

> **Purpose:** Stop the adversarial verifier from **manufacturing immaterial
> findings** to avoid a "rubber-stamp," and stop the re-verify loop from
> **churning rounds on nits** — *without* blunting the strong adversarial framing
> that catches real cross-file/correctness defects. Set 070 gave both surfaces
> their strongest devil's-advocate framing (steelman push, L-069-2); the field
> test of that framing in `../kick-the-orchestrator-tires` surfaced the predicted
> side effect: strong framing with **no materiality bar** produces Minor
> false-positive findings, and the loop re-litigates them across rounds. This set
> adds the **materiality "so what?" gate**, the **severity-anchored
> Minor-is-non-blocking loop discipline**, and the **cross-round issue ledger**
> that together kill nitpick churn while leaving the Critical/Major catch ceiling
> untouched.
>
> **Design rationale (required reading):** the cross-provider consult that scoped
> this set (GPT-5.4 + Gemini-Pro, 2026-06-18) is summarized in §*Design inputs*
> below; **L-069-2** in
> [`docs/planning/lessons-learned.md`](../../planning/lessons-learned.md) (never
> weaken framing to fix this) is the hard constraint.
> **Created:** 2026-06-18.
> **Session Set:** `docs/session-sets/071-verifier-materiality-and-nitpick-discipline/`
> **Prerequisite:** Set 070 complete (it shipped the strong-framing `verification.md`,
> the framing-pin test `test_verification_framing.py`, and `dual_surface_verify`'s
> `classify_framing_strength` — all of which this set must extend additively, never
> weaken).
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification (gated:
> run `python -m ai_router.routed_gate` per session; this set touches the shared
> verifier surface + the re-verify loop, so expect REQUIRED throughout).

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
pathAwareCritique: required   # touches the shared verification surface (high blast radius); continue the dogfood norm
contractGate: advisory        # light dogfood of the floor; record the durable seed at set start (070 shipped the start_session fix)
prerequisites:
  - slug: 070-dual-surface-verification-telemetry
    condition: complete
```

> Rationale: pure `ai_router` machinery + a PyPI release; **no UI surface**, so no
> UAT/E2E gate. **Full tier** — every session is cross-provider verified (gated).
> `pathAwareCritique: required` because this set changes the **shared verification
> surface** (both reviewer templates, the verdict-parse/blocking logic, and the
> re-verify loop rules); the blast-radius predicate scores it `required`.
> `contractGate: advisory` — Session 1 records the durable `contractGate` seed at
> set start (the Set 070 S1 `start_session` fix is in place, so this is the normal
> path, not a new fix).

---

## Project Overview

### Background

Set 070 upgraded `verification.md` to the devil's-advocate framing pull already
used (the steelman-push deliverable, L-069-2) so the per-session push surface runs
at its strongest before any RETIRE decision. The operator's live test of the new
verification capabilities in `../kick-the-orchestrator-tires` confirmed the framing
works — and surfaced its cost: with a strong "assume it's flawed, a rubber-stamp is
a failure" stance and **no materiality bar**, the verifier sometimes manufactures a
**Minor / False-Positive** finding rather than return clean, and the re-verify loop
then **churns rounds on it**.

The canonical observed instance (Set 001 of the tires repo, three consecutive
rounds on one immaterial point):

- **Round 2** — `ISSUES_FOUND / Minor / False-Positive`: "claimed pytest run result
  is unsubstantiated ... tests appear likely to pass, but execution result not
  proven by what is shown."
- **Round 3** — `ISSUES_FOUND / Minor / False-Positive`: "task says `pytest`; response
  shows `python -m pytest -v` output — usually equivalent but not the same command."
- **Round 4** — `ISSUES_FOUND / Minor / False-Positive`: "response says it shows bare
  `pytest` but the block is labeled `pytest -v` — not the same command."

Three remediation rounds spent on `pytest` vs `python -m pytest -v` — a distinction
with no behavioral difference, on work that was correct.

### Design inputs (the cross-provider consult)

The scoping question — *"options to prevent nitpicking without over-restraining the
verifier"* — was put to **GPT-5.4** and **Gemini-Pro** independently (2026-06-18).
Both converged:

1. **The primary fix is the loop, not the prompt.** Any `ISSUES_FOUND` (including a
   manufactured Minor) triggers another remediation round. Redefine the *blocking*
   threshold so **Minor-only never blocks and never reopens the loop**; a round may
   continue only on **new or unresolved Critical/Major** findings. GPT added the
   **issue ledger**: each round marks prior blockers `RESOLVED`/`UNRESOLVED` and may
   not resurrect a settled point under fresh wording (the exact pattern in the
   churn above). This works **without** lowering the real-defect ceiling — Major/
   Critical block exactly as before — and does not depend on perfect model
   calibration.
2. **A materiality "so what?" gate (self-filtered).** Every blocking finding must
   state (a) the exact requirement/claim violated, (b) the concrete impact, (c) the
   evidence; a finding that cannot produce all three is a nit, not a blocker. Prompt
   text alone is "too soft" — it is calibration layered on top of the loop fix.
3. **Anti-laundering guardrail (the shared failure mode both flagged).** Making
   Minor non-blocking risks a real bug being mislabeled Minor and waved through.
   Guardrail: anchor **Major** to *merge impact* ("would this change a reasonable
   merge decision?") and require a **plausible-path-to-harm** escalation ("to call
   it Minor you must be confident there is no plausible path to a Major/Critical
   failure; when in doubt, escalate").

The two diverged only on the **verdict grammar**: Gemini proposed a third verdict
state (`VERIFIED_WITH_NITS`); GPT proposed **keeping the binary** verdict and
redefining the blocking threshold (Minor → a non-blocking `NITS` section, verdict
stays `VERIFIED`). **This set adopts GPT's binary approach** because it preserves
the machine contract `parse_verification_response` and the Set 070 framing-pin test
depend on (`VERIFIED` / `ISSUES FOUND` tokens), avoiding a parser change. (Operator
may override to the three-state grammar at Session 2; the spec'd default is binary.)

### What this set delivers

1. **A materiality + anti-nitpick layer** added to **both** reviewer templates
   (`verification.md` and `path-aware-critique.md`) — the "so what?" three-part
   blocking test, the explicit anti-nitpick clause (a correct+complete response
   *should* be VERIFIED; manufacturing a Minor to avoid a rubber-stamp is itself a
   false-positive failure; judge **semantic equivalence**, not textual identity,
   unless the exact text *is* the contract), and the severity anchoring (Major =
   changes a reasonable merge decision; plausible-path-to-harm → escalate). A
   non-blocking **`NITS`** output section so true-but-immaterial observations have a
   home that does not trip the loop.
2. **Severity-anchored blocking logic** in `ai_router/verification.py`: a function
   that derives the *blocking* decision from parsed findings (≥1 Critical/Major →
   blocking; Minor-only / nits-only → non-blocking), leaving `parse_verification_response`'s
   raw verdict intact for the record.
3. **The re-verify loop discipline** encoded in `docs/ai-led-session-workflow.md`
   Step 6: Minor-only ⇒ the round is effectively VERIFIED and opens **no**
   remediation round; a round continues only on **new or unresolved Critical/Major**;
   the **issue ledger** (prior blocker IDs tracked RESOLVED/UNRESOLVED, no
   resurrection of a settled point under new wording).
4. A synthesis update, focused tests (including the verbatim `pytest`-vs-`python -m
   pytest -v` churn as a regression fixture that must classify **non-blocking**), an
   `ai_router` **PyPI release**, dogfood (`pathAwareCritique: required`), and
   `change-log.md`.

### Scope (in)

- Additive edits to `ai_router/prompt-templates/verification.md` and
  `ai_router/prompt-templates/path-aware-critique.md`: the materiality "so what?"
  gate, the anti-nitpick clause, the severity-anchoring + plausible-path-to-harm
  guardrail, and a non-blocking `NITS` section.
- `ai_router/verification.py`: a severity-aware blocking classifier
  (`is_blocking_verdict` / equivalent) consumed by the re-verify loop; no change to
  `parse_verification_response`'s public `(verdict, issues)` contract beyond
  additive parsing of the `NITS` section if needed.
- `docs/ai-led-session-workflow.md` Step 6: the Minor-non-blocking rule + the
  cross-round issue ledger + bounded-round interaction (the existing 1–2 automatic /
  3+ human rule stays; this narrows what *counts* as a round-justifying finding).
- Tests: extend `test_verification_framing.py` (the strong-framing pins must still
  pass — additivity proof) and add coverage for the materiality/anti-nitpick
  language, the blocking classifier, and the churn regression fixture.
- A test asserting `dual_surface_verify.classify_framing_strength` still returns
  `ADVERSARIAL` for both edited templates (so the dual-surface equal-framing gate
  does not break — the edits must not disturb the `_ADVERSARIAL_MARKERS`).

### Non-goals (out)

- **Weakening the adversarial framing.** L-069-2 is a hard constraint: the
  devil's-advocate stance and the `_ADVERSARIAL_MARKERS` phrases
  ("devil's advocate", "assume the work is flawed") **stay verbatim**. This set is
  strictly *additive* — a materiality bar layered on strong framing, never a
  softening of it.
- **A third verdict state.** The binary `VERIFIED` / `ISSUES FOUND` grammar is
  preserved (operator may override at S2). No change to the `sN-issues.json`
  envelope schema or `session-issues-schema.md`.
- **Changing the Mode B (`dedicated-sessions`) disposition enum.** Its
  fixed/not-reproducible/accepted-consequence/advisory-disagreement machinery
  already exists; this set's loop rule is the Full-tier Step-6 analogue and reuses,
  not replaces, that vocabulary.
- **Explorer / extension UI**; any Marketplace bump.
- Field pilots in consumer repos (downstream consumers of the shipped 0.25.x
  behavior).

### Standards

- **Additive over strong framing.** Every template edit must leave the Set 070
  framing-pin test green and `classify_framing_strength` returning `ADVERSARIAL`.
  A change that drops a strong-framing phrase is invalid (L-069-2).
- **Materiality has a guardrail.** Minor-is-non-blocking ships *only* with the
  merge-impact severity anchor and the plausible-path-to-harm escalation, so the
  fix cannot silently launder a real Major into an ignored Minor.
- **Propagate every echo (L-065-1).** The materiality language appears in two
  templates and the workflow doc; a consistency fix during verification must update
  all echoes in one pass.
- **Dogfood honestly (L-070-1).** The end-of-set path-aware critique is iterative;
  keep the final round as the gate artifact and adjudicate every finding in the
  disposition — do not chase a pristine post-fix snapshot.

---

## Sessions

### Session 1 of 3: Materiality + anti-nitpick layer in both reviewer templates

**Steps:**
1. Register; **record the durable `contractGate: advisory` seed at set start** (via
   `start_session --contract-gate advisory`). Read §*Design inputs* above, L-069-2,
   `verification.md`, `path-aware-critique.md`, `verification.py`
   (`build_verification_prompt` / `parse_verification_response`),
   `test_verification_framing.py`, and `dual_surface_verify.classify_framing_strength`.
2. **Edit `verification.md`** (additively): add the materiality "so what?"
   three-part blocking test, the anti-nitpick clause (semantic-equivalence-not-
   textual-identity; manufacturing-a-Minor-is-a-false-positive; the `pytest`-vs-
   `python -m pytest -v` example named as a worthless finding), the severity anchor
   (Major = changes a reasonable merge decision) + plausible-path-to-harm
   escalation, and a non-blocking **`NITS`** output section. **Preserve** the
   `_ADVERSARIAL_MARKERS` phrases, the `{original_task}`/`{task_type}`/
   `{original_response}` placeholders, and the `VERIFIED` / `ISSUES FOUND` tokens.
3. **Mirror the same layer into `path-aware-critique.md`**, fitting its
   `VERDICT: VERIFIED | ISSUES_FOUND` + Findings grammar (add a `NITS` subsection;
   keep the per-finding Severity/Category/Location shape).
4. Extend `test_verification_framing.py`: keep all Set 070 strong-framing pins, add
   (a) assertions the materiality/anti-nitpick language is present in **both**
   templates, and (b) a test that `classify_framing_strength` returns `ADVERSARIAL`
   for both edited templates (additivity / dual-surface-equality proof).
5. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Ends with:** both reviewer templates carry the materiality + anti-nitpick layer,
the strong framing is provably intact, and the dual-surface equal-framing gate still
classifies both as `ADVERSARIAL`; session **VERIFIED**.
**Progress keys:** `materiality-push-template`, `materiality-pull-template`, `framing-pins-green`, `s1-verified`.

### Session 2 of 3: Severity-anchored blocking logic + the re-verify loop discipline

**Steps:**
1. Register; read S1 deliverables, `verification.py`, and the Step 6 re-verify /
   bounded-round rules in `docs/ai-led-session-workflow.md` (and the Mode B
   disposition enum, for vocabulary alignment).
2. Add the **blocking classifier** to `verification.py` (e.g. `is_blocking_verdict(issues)`
   / `classify_blocking(verdict, issues)`): a verdict blocks a re-verify round only
   when ≥1 finding is Critical or Major; Minor-only / nits-only is **non-blocking**
   (recorded, not loop-opening). Keep `parse_verification_response`'s `(verdict,
   issues)` contract; if a `NITS` section is parsed, surface it without breaking
   existing callers.
3. Encode the **loop discipline** in `docs/ai-led-session-workflow.md` Step 6: a
   Minor-only round is effectively VERIFIED and opens **no** remediation round; a
   round continues only on **new or unresolved Critical/Major**; the **issue ledger**
   (prior blocker IDs marked RESOLVED/UNRESOLVED, no resurrecting a settled point
   under new wording) layered on the existing 1–2-automatic / 3+-human bound.
4. Tests: the blocking classifier (Minor-only → non-blocking; mixed → blocking;
   Critical → blocking); the **verbatim `pytest`-vs-`python -m pytest -v` churn**
   from the tires repo as a regression fixture that must classify **non-blocking**;
   the issue-ledger no-resurrection rule if expressed in code.
5. **Operator decision point (binary vs three-state verdict):** the spec'd default
   is binary; if the operator prefers Gemini's `VERIFIED_WITH_NITS`, fold the parser
   + envelope change here. Cross-provider verification; `disposition.json`; commit +
   push; `close_session`.

**Ends with:** a Minor-only verifier verdict does not trigger another remediation
round, the loop is ledgered against resurrected nits, and the real-defect (Critical/
Major) ceiling is unchanged; session **VERIFIED**.
**Progress keys:** `blocking-classifier`, `loop-discipline-doc`, `churn-regression-fixture`, `s2-verified`.

### Session 3 of 3: Synthesis + docs + release + dogfood + close

**Steps:**
1. Register; read S1–S2 deliverables.
2. Update `docs/verification-surface-strategy.md` (record that strong framing now
   ships with a materiality gate + Minor-non-blocking loop discipline — the
   calibration layer the steelman-push framing needed) and
   `ai_router/docs/pull-verifier.md`. **Author lesson L-071-1** (strong adversarial
   framing without a materiality bar manufactures Minor-finding churn; the fix is a
   materiality "so what?" gate + Minor-non-blocking loop discipline + a cross-round
   issue ledger + a merge-impact/plausible-path-to-harm anti-laundering guardrail —
   never a framing weakening, per L-069-2). Cite L-069-2, L-065-1, L-070-1.
3. Finalize tests; bump `ai_router` (minor); ship the **PyPI release** per the
   publish runbook (green-`Test`-on-the-tagged-SHA; verify tag commit == fixed SHA,
   Set 068 lesson; operator pushes/approves the tag). Record the publish run id
   post-release.
4. `change-log.md`; route the next-session-set recommendation via
   `route(task_type="analysis")` (candidate: the consumer-repo field pilot, or the
   previously-recommended Set 071-as-was telemetry-readiness work — now renumbered);
   cross-provider verification; **dogfood** (`pathAwareCritique: required`;
   `contractGate: advisory`) over this set's own diff (per L-070-1, keep the final
   round as the gate artifact and adjudicate every finding in the disposition);
   `close_session`; set closes.

**Creates:** the synthesis update, lesson L-071-1, `change-log.md`, this set's
dogfood / path-aware-critique artifact.
**Touches:** `docs/verification-surface-strategy.md`, `ai_router/docs/pull-verifier.md`,
`docs/planning/lessons-learned.md`, `ai_router/CHANGELOG.md`, version metadata.
**Ends with:** the verifier runs at its adversarial best *with* a materiality bar and
a churn-proof loop, `ai_router` released; set closed.
**Progress keys:** `synthesis-updated`, `lesson-l-071-1`, `released`, `change-log-written`, `dogfooded`, `s3-verified`.

---

## End-of-set deliverables

- The **materiality + anti-nitpick layer** in both `verification.md` and
  `path-aware-critique.md` (S1), with the Set 070 strong-framing pins provably
  intact and `classify_framing_strength` still `ADVERSARIAL` for both.
- The **severity-anchored blocking classifier** in `ai_router/verification.py` and
  the **re-verify loop discipline** (Minor-non-blocking + issue ledger) in
  `docs/ai-led-session-workflow.md` Step 6 (S2), with the `pytest`-vs-`python -m
  pytest -v` churn pinned as a non-blocking regression fixture.
- The synthesis update, lesson **L-071-1**, an `ai_router` **PyPI release**, this
  set's dogfood artifact, and `change-log.md` (S3).

A verifier that keeps its strong adversarial framing — and so keeps catching the real
cross-file/correctness defects — but no longer manufactures immaterial findings or
churns re-verify rounds on nits, because a finding must clear a merge-impact
materiality bar to block and a settled point can never be resurrected under fresh
wording.
