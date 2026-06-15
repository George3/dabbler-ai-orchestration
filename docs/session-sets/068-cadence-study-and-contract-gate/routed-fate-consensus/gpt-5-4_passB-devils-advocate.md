# Consensus consult -- gpt-5-4 -- passB-devils-advocate

> model_used=None cost_usd=0.080097 chars=9097

## Scope check

The more useful question is not **“Is per-session routed verification valuable at all?”** It is **“Does the evidence justify keeping it mandatory on every session, unchanged, as the default verification surface?”** Those are different standards.

A second useful question is **timing**: **“Should policy change before the S5 contract-test gate exists and is proven?”** That matters because the case for major reduction depends on a replacement stack that is not fully live yet.

---

## Strongest honest case for `KEEP`

### 1. The experiments likely under-measure the real operational value of R
Experiment A and B are strong on mechanism, but narrow on scope:

- one toy unit
- 12 seeded defects
- K=3
- staged snapshots rather than full live workflow pressure

That tests **defect-detection capability and timing**, not the broader value of a **mandatory every-session external gate** in a real iterative build process.

The strongest KEEP argument is that per-session routed verification is functioning as a **process-control safety net**, not just a classifier for seeded defect types. The prompt explicitly notes that this live gate has **repeatedly caught real workflow defects before commit**, including multi-round convergence on the very sets that built this machinery. That evidence is anecdotal, but highly relevant: it is closer to the actual use case than the toy study.

### 2. The cadence benefit is real, large, and operationally meaningful
Even under the pre-registered “cadence defense does not hold” ruling, one thing is still clear:

- R caught **5/5 migrating coupling defects at introduction**
- in **both providers**
- with large **timing** and **rework-saving** advantages

That is not a rounding error. It means R can prevent defect growth during construction, not just clean it up at set close. If those coupling defects are costly in real work, then an every-session gate has real operational bite.

### 3. E is better overall, but not a perfect ceiling
The proposed replacement surface is not flawless:

- one provider’s path-aware E missed a **Critical cross-file defect (BD6)**

That matters because replacing a repeated gate with a single late pass increases **single-pass miss risk**. Even if E is better on average, “better at set close” is not the same as “safe enough to replace repeated independent challenge.”

### 4. The replacement stack is incomplete today
The demote/retire case leans heavily on the planned deterministic floor:

- **S5 contract-test / CDC gate is not built yet**

So the strongest KEEP position is procedural: **do not remove a live guardrail before the replacement floor exists and has proven it handles the probeable bulk.** That is especially compelling because the proposed architecture is additive in theory but not yet validated as a complete replacement in practice.

### 5. Risk-gating reintroduces a human-judgment failure mode
A demoted policy needs someone or something to decide when a session is “risky enough” to trigger R.

That creates a new failure mode:

- the most dangerous sessions are often the ones whose risk is **under-recognized at the time**
- “coupling risk” is exactly the kind of thing that can be hidden until it migrates

Mandatory every-session routing avoids that classification error entirely. KEEP can fairly argue that **uniform enforcement beats selective enforcement** when selective enforcement depends on fallible judgment.

### 6. KEEP is cheap in absolute dollars
In the experiment:

- R cost per 5-session set: **~$0.04–0.14**
- E cost per set: **~$0.15–0.24**

Even if R is less capable than E on some classes, the cost to keep it is not obviously prohibitive. If the system prioritizes safety over small marginal spend and latency, KEEP can credibly be framed as **cheap insurance**.

### 7. Cross-provider independence still has governance value
Experiment A shows **provider multiplicity does not improve capability** once context is fixed. But KEEP can still argue for **cross-provider independence as a governance control**, especially here:

- the orchestrator is itself an Anthropic model
- the routed verifier is part of how that orchestrator checks its own work

A mandatory different-provider check on every session helps guard against **process self-confirmation**. That is not the same claim as “second provider catches more seeded bugs”; it is a stronger organizational-control claim.

---

## Why the `KEEP` case is still not decisive

### 1. `KEEP` requires proof for a universal unchanged policy, not proof of some value
The evidence absolutely supports: **R has residual value**.

It does **not** support: **R should remain mandatory on every session, unchanged**.

That distinction is decisive.

### 2. Experiment A directly undercuts the main capability rationale for unchanged R
A shows:

- path-aware catches severe cross-file defects that routed structurally cannot
- the key lever is **context access**
- adding a second routed provider buys **nothing**

So mandatory per-session routed is not the best primary capability surface. The stronger surface is the one that can actually inspect the repository context.

### 3. Experiment B leaves only a narrow residual advantage for R
B does show a real early-window benefit, but by the pre-registered rule the broader cadence defense fails because the controls are contaminated by:

- surface-coverage artifacts
- pure earliness effects

So the honest reading is:

- R’s edge is real
- but it is **narrower than “mandatory every session unchanged” implies**
- specifically: **earlier catch of migrating coupling defects during construction**

That is a textbook argument for **targeted retention**, not blanket retention.

### 4. `KEEP` overpays for coverage where R’s distinctive advantage is absent
If R’s demonstrated unique value is concentrated in a small class of sessions/defects, then firing it on every low-risk session is policy overreach.

The evidence supports:

- **E as the stronger end-of-set capability surface**
- **contract tests as the deterministic floor** for probeable defects
- **R reserved for the early-coupling residual**

That is the shape of DEMOTE.

### 5. The operational anecdotes block `RETIRE`, but they do not rescue `KEEP`
The live-history argument is meaningful, but it mainly says:

- do not remove routed verification entirely yet
- do not rely on an unbuilt S5 gate
- do not trust a single end-of-set pass as a perfect replacement

That is enough to argue against **RETIRE**.

It is not enough to justify **mandatory every-session unchanged** in the face of A and B.

---

## Bottom line

## Decision: `DEMOTE`

### Why not `KEEP`
Because the experiments do not justify the specific policy **“mandatory on every session, unchanged.”** They justify only a **narrow residual value**: early interception of migrating coupling defects during construction, plus some unquantified operational safety-net value.

### Why not `RETIRE`
Because:

- the contract-test gate is not live yet
- E is not perfect
- real operational value of the live per-session gate is not fully captured by the toy study

Retiring now would be an evidence jump.

---

## Concrete recommendation

### Strategic policy
Adopt **DEMOTE** as the target state:

- make **end-of-set path-aware critique + contract-test / CDC gate** the primary verification surface
- retain **per-session routed verification** only where its demonstrated residual value is strongest

### Operational rollout
Do **not** implement that demotion as a hard cut until S5 exists and is stable.

### Suggested per-session routed triggers
Require routed verification for sessions with clear coupling/blast-radius indicators:

- changes spanning multiple files/modules/packages
- public API / schema / contract changes
- moves, renames, deletions, or logic extraction across files
- build/CI/infrastructure changes
- auth/security/persistence/concurrency/stateful code
- large diffs or high-churn sessions
- sessions following a failed verification/fix loop
- low-confidence sessions or ambiguous scope boundaries

### What to measure before any future `RETIRE` decision
Run the demoted policy long enough to collect:

- escaped-defect rate
- intro-stage vs end-of-set catch timing
- rework saved by per-session R
- false-positive churn
- sessions where risk-gating failed to trigger but should have

---

## Final answer to the contrarian hypothesis

The strongest honest steelman for `KEEP` is:

- the experiments are externally narrow
- the live gate has proven operational value
- R’s early-catch benefit for migrating coupling is real and large
- the replacement stack is incomplete
- risk-gating adds a dangerous judgment failure mode
- KEEP is cheap enough to defend as insurance

But after making that case, it is **not decisive**.

The evidence still points to **`DEMOTE`**, not `KEEP` and not `RETIRE`. The right reading is: **retain routed verification for its narrow demonstrated residual and for transitional safety, but stop treating mandatory every-session routed review as the default primary verification surface.**
