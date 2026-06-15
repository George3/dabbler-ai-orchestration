# Routed per-session verification — keep / demote / retire decision (Set 068 S4)

> **Decision:** **DEMOTE**, with a **transition guard** (the demotion does not take
> effect until the Set 068 S5 contract-test / CDC gate is live and stable).
> **Routed via** decision-time cross-provider consensus (the two non-orchestrator
> providers, `gpt-5-4` + `gemini-pro`, devil's-advocate two-pass) **and confirmed
> by the operator** on 2026-06-15.
> **Created:** 2026-06-15 (Session 4).
> **Evidence:** [`experiment-a-regrade.md`](experiment-a-regrade.md) (capability) +
> [`experiment-b-results.md`](experiment-b-results.md) (cadence).
> **Consult artifacts:** `routed-fate-consensus/` (4 raw outputs) +
> `routed-fate-consensus-journal.jsonl` (one record per call).

---

## 0. TL;DR

The two experiments that Set 067–068 ran to settle the fate of **per-session
routed verification** (the every-session cross-provider review that closes each
session) reached this verdict: its **capability** rationale is ruled out
(Experiment A — the lever is *repository context-access*, which the end-of-set
**path-aware critique** provides and snippet-fed routed structurally cannot; a
second routed provider buys nothing), and its **cadence** defense **does not hold**
under the pre-registered rule (Experiment B — clause B3: R's measured edge over
end-of-set is largely a surface-coverage artifact + pure earliness, not
Q-invisible cadence). **But** the cadence *mechanism* is real and the one genuine
residual value survives: R catches **migrating cross-file coupling defects at
their introduction** (5/5 early window, both providers), saving rework that even
the path-aware replacement does not on that class.

On that evidence, cross-provider consensus (4/4 consults, including both
devil's-advocate passes that steelmanned KEEP and then found it not decisive) and
the operator chose **DEMOTE**: make the **end-of-set path-aware critique + the S5
contract-test / CDC gate** the primary verification surface, and **retain
per-session routed gated on blast-radius / coupling** rather than mandatory on
every session — **but do not execute the cut until the S5 gate exists** (no live
safety net is removed before its replacement floor is in place).

---

## 1. The options as decided

| Option | Decided? | Why |
|---|---|---|
| **KEEP** (mandatory every session, unchanged) | rejected | Experiment A removes the capability case for routed-as-default; at set close the path-aware surface materially outperforms routed (E 11–12/12 vs R 10/12), and the evidence supports retaining a *narrow residual*, not a *universal unchanged* mandate. |
| **DEMOTE** (gated, path-aware + contract gate primary) | **CHOSEN** | Retains routed's one demonstrated residual (early catch of migrating coupling defects) and its transitional safety-net value, while promoting the stronger end-of-set surface to primary. The only option that fits the evidence without over- or under-reacting. |
| **RETIRE** (drop routed; replace with path-aware + gate) | rejected (premature) | The S5 contract-test gate is **not built yet**; path-aware E is **not a perfect ceiling** (one provider's E missed the Critical cross-file BD6); the live per-session gate has repeatedly caught real pre-commit defects the toy study does not bound. Reopen only on later telemetry (§5). |

## 2. What the consensus said

Routed through the decision-time-consensus mechanism
(`docs/ai-led-session-workflow.md` → *Decision-time consensus*) with the
**bias-cautions preamble always on** and the **devil's-advocate two-pass** pattern
(this decision binds a long-lived workflow contract). The two consulted engines are
the **two non-orchestrator providers** (`gpt-5-4`, `gemini-pro`); the orchestrator
is Anthropic/opus and per-session routed verification is what that orchestrator uses
to check its own work, so an independent-provider consult is the correct instrument.

- **Pass A (neutral 3-option):** `gpt-5-4` → DEMOTE; `gemini-pro` → DEMOTE.
- **Pass B (steelman KEEP):** both engines built the strongest honest KEEP case
  (the experiments are externally narrow; the live gate has proven operational
  value; R's early-coupling catch is real and large; the replacement stack is
  incomplete; risk-gating reintroduces a human-judgment failure mode; KEEP is cheap
  insurance) and **both explicitly concluded it is not decisive** — the evidence
  still points to DEMOTE, not KEEP and not RETIRE.

**No material disagreement** across providers or passes. Two convergent refinements
the consult added, both adopted below:

1. **Transition guard (timing).** Do **not** implement the demotion as a hard cut
   until the S5 contract-test gate exists and is stable. The demote/retire case
   leans on a deterministic floor that is not yet live; removing a working guardrail
   before its replacement is built is the one move all four consults warned against.
2. **Programmatic gating, not subjective judgment.** Both engines flagged that
   "decide per session whether it's risky enough" reintroduces the failure mode the
   mandatory gate exists to prevent (the most dangerous sessions are the ones whose
   risk is under-recognized at the time). The gating predicate must therefore be a
   **programmatic diff heuristic**, not an operator's per-session feeling.

## 3. The DEMOTE policy (target state)

Once the transition guard (§4) clears, the verification-surface model becomes a
layered defense:

- **Primary (capability ceiling):** the **end-of-set path-aware critique** (Set
  066/067) — multi-provider, reads the repository, run at set close — plus the
  **S5 contract-test / CDC gate** as the deterministic floor for the ~95%-probeable
  defect bulk, reserving the agent for the non-probeable residual.
- **Targeted (retained routed):** **per-session routed verification is retained but
  gated** — it fires on a session only when a **programmatic blast-radius / coupling
  predicate** over the session diff is true. Indicative triggers (final predicate to
  be finalized alongside the S5 gate, which owns the diff-inspection machinery):
  - changes spanning **multiple files / modules / packages**;
  - **public API / schema / contract** changes;
  - cross-module **refactors, moves, renames, or logic extraction across files**;
  - **build / CI / config** changes;
  - the changed surface **lacks deterministic probes** (no contract test covers it);
  - the session is marked **high-blast-radius / hotfix**, or **follows a failed
    verification/fix loop**.
  A session whose diff is small, single-file, and probe-covered bypasses the
  per-session routed call; everything above still gets it. This preserves routed's
  one demonstrated unique value (early interception of migrating coupling defects)
  without paying for it on every low-risk session.
- **Unchanged:** the path-aware producer and the manual flow remain (this set is
  additive); a retained routed call still routes to a **different provider** than the
  orchestrator; `verification.preferred_pairings` is untouched.

## 4. Transition guard (what changes WHEN)

| Phase | State of per-session routed | Gate |
|---|---|---|
| **Now → S5 gate live** (this session through the S5/S6 landing) | **MANDATORY on every Full-tier session, unchanged** | The decision is recorded; the policy is written; **behavior is not yet cut over.** |
| **After the S5 contract-test gate is live + stable** | **Gated** per §3 | S5 builds the gate (and owns the diff-inspection seam the gating predicate needs); S6 synthesis wires the predicate + flips the workflow default. |

This session (S4) **makes and records the decision** and **writes the target-state
policy** into the workflow doc; it deliberately does **not** flip live behavior,
because the replacement floor (S5) does not exist yet. That sequencing is itself
part of the operator-confirmed decision — it is the honest reading of "change
routed's status only on the Experiment B evidence" combined with the consult's
unanimous timing caution.

## 5. Reopening RETIRE (future, telemetry-gated)

RETIRE is rejected **now**, not forever. Reopen it only after the demoted policy has
run long enough to collect, under the S5-era stack:

- escaped-defect rate (defects that reached commit);
- intro-stage vs end-of-set catch timing;
- rework saved by the retained gated routed calls;
- false-positive churn from routed;
- sessions where the gating predicate failed to trigger but should have.

If that telemetry shows the retained routed calls are no longer catching unique
high-severity defects or producing meaningful rework savings, RETIRE becomes the
evidence-backed next step. Until then, routed stays — gated, not gone.

## 6. Implementation in this session

- **This decision record** (`routed-fate-decision.md`) — the consensus + operator
  rationale, durable.
- **`docs/ai-led-session-workflow.md`** — a new *Verification-surface policy (Set
  068)* subsection records the DEMOTE target state + the transition guard, and Step 6
  + the Cross-Provider Verification concept carry a forward-pointer noting the policy
  is changing while **MANDATORY remains in force until the S5 gate lands**.
- **`ai_router/router-config.yaml`** — a comment anchor in the `verification:` block
  documents the policy and points here (no behavioral flag is flipped — there is no
  live cutover this session).

No `router-config.yaml` behavioral flag changes and no per-session verification is
skipped this session; S4's own close-out is itself verified by the still-mandatory
per-session routed call.
