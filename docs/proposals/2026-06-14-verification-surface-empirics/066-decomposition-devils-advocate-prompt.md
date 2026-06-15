# Path-Aware Devil's-Advocate Prompt — Set 066 Decomposition (pre-spec)

> **How to run this (operator):** Open this repo in an editor with **GitHub
> Copilot** (so the reviewer has real, path-aware access to the workspace —
> this is a Mode-2 *pull* review, the kind the routed `route()` path cannot do).
> Paste everything below the `=== PROMPT ===` line into Copilot Chat **once
> under Gemini** and **once under GPT** (two independent passes, per the
> harvester two-provider pattern). Save each verdict back into this folder as
> `066-critique-gemini.md` and `066-critique-gpt.md`. Then hand them back to the
> orchestrator to fold into the authored `spec.md`.

---

=== PROMPT ===

You are an adversarial design reviewer with **full read access to this
repository**. Your job is to find what is **wrong, risky, or mis-scoped** in a
proposed decomposition for an upcoming session set (**Set 066**) *before* it is
written up as a `spec.md`. Be a genuine devil's advocate: assume the
decomposition below is flawed and try to prove it. A rubber-stamp is a failure.

**Anti-bias instruction (important):** Do **not** rely on my summary of the
repo. **Open and read the actual files yourself** and reason from what is on
disk. Where my description and the code/docs disagree, the repository wins —
call that out. Pull ground truth; do not trust flattering paraphrase.

## Read these first (ground truth)

- `docs/proposals/2026-06-14-verification-surface-empirics/proposal.md` — the
  approved, cross-provider-verified proposal Set 066 implements. Pay special
  attention to §9 (sequencing) and §7 (the `P_task`/`P_set` predicate).
- `docs/proposals/2026-06-14-verification-surface-empirics/consensus-journal.md`
- `docs/session-sets/065-verification-surface-empirics/spike-report.md` — the S2
  spike that proved feasibility (first-party httpx adapter + Copilot CLI).
- `docs/session-sets/065-verification-surface-empirics/spike_first_party_adapter.py`
  — the ~150-LOC throwaway adapter to be hardened into production.
- `docs/session-sets/065-verification-surface-empirics/forward-ab-design.md` —
  the forward A/B design (Experiment A capability + Experiment B cadence) that
  Set 066 is meant to execute.
- `docs/session-sets/065-verification-surface-empirics/bake-off-results.md` — the
  S1 evidence (~92% probeable; routed-value unanswered).
- `ai_router/` — the actual router package the adapter must live in. In
  particular look at how `route()` and `providers.call_model` / the provider
  layer are structured (the adapter is a new "provider kind" — an agentic tool
  loop, not a new model), how `router-config.yaml` is shaped, and how existing
  modules are tested.
- `docs/planning/session-set-authoring-guide.md` — the rules the spec must obey
  (slug naming, **sizing** heuristics, the Session Set Configuration block,
  anti-patterns "set too broad" / "set too narrow").
- `docs/ai-led-session-workflow.md` — execution mechanics, the close-out gate,
  release runbook expectations.

## What Set 066 is meant to deliver

The proposal recommends building a **first-party tool-loop adapter** — a
`route()`-based agentic "pull" verifier (the orchestrator becomes the *servant*
of the verifier, serving raw `read_file`/`grep`/`list_dir`/`run_test` results;
the servant must return **raw ground truth**, never a model-summarized view) —
as both (a) the production "Mode-2" verification engine and (b) the execution
vehicle for the forward A/B that finally settles whether per-session routed
verification keeps its place.

## The PROPOSED decomposition you must attack

- **Slug:** `066-mode2-pull-verifier-adapter`. **Tier:** full. **requiresUAT:**
  false, **requiresE2E:** false (pure `ai_router` tooling, no UI).
  **Prerequisite:** Set 065 complete.
- **Ships a release:** PyPI `ai_router` only (new capability); **no** Marketplace
  bump (no extension change).
- **Four sessions:**
  1. **S1 — Adapter core (Anthropic binding).** Harden `spike_first_party_adapter.py`
     into a production `ai_router` module: agentic loop driver with
     turn/token/cost caps, the deterministic-servant toolset
     (`read_file`/`grep`/`list_dir`, **read-only — no `run_test` yet**), a forced
     `sN-issues.json`-schema verdict, and tool-call-trace instrumentation. Unit
     tests. Cross-provider verify.
  2. **S2 — Multi-provider bindings + sandboxed `run_test`.** Add OpenAI
     `tool_calls` and Gemini function-calling bindings (**required** — the A/B's
     GPT and Gemini path-aware arms need them; S2 spike only ran Anthropic). Add
     `run_test` executing inside a **disposable git worktree** (the only tool
     that needs the sandbox cage). Wire the new provider-kind into
     `router-config.yaml`. Tests. Verify.
  3. **S3 — Run the forward A/B (Experiments A + B).** Per `forward-ab-design.md`:
     frozen pre-remediation trees (harvester 008–012) and/or a seeded
     calculator mock-repo; path-aware arms (B1/B2) via the new adapter, routed
     arms (A1/A2) via `route()`; K-repeats for the stochastic arms; measure
     context-access vs provider-multiplicity, probeable coverage, and routed's
     marginal value (capability **and** cadence). Produce `ab-results.md`.
  4. **S4 — Synthesize + release.** Turn the A/B data into an explicit routed
     **keep / demote / retire** recommendation; bump and ship the `ai_router`
     PyPI release carrying the adapter; author `change-log.md` and the routed
     next-set recommendation (expected next set 067 = ship "Path-Aware Critique"
     as a workflow stage + the contract-test gate).
- **Deliberately deferred to a later set (067):** integrating Path-Aware
  Critique as a per-set attribute + close-out gate, and the contract-test/CDC
  gate. Rationale: keep 066 from sprawling past the authoring guide's sizing band.

## Attack these specific forks (and anything else you find)

1. **Scope.** Is deferring the Path-Aware-Critique workflow integration + the
   contract gate to 067 correct, or does it strand the adapter as unused
   infrastructure with no consumer in 066? Conversely, is 066 *still* too broad?
2. **Build-order risk.** S1+S2 build a production adapter *before* S3's A/B
   confirms path-aware's value. Is that backwards? Should the A/B run on a
   throwaway harness first and productionize only if it pays off? Or does the S1
   evidence + S2 feasibility already justify productionizing?
3. **Release timing.** Should 066 ship a PyPI release at all, given the
   routed-fate decision (which could change the verification story) lands in the
   *same* set's S4? Ship the capability regardless, or hold the release?
4. **Multi-provider necessity & feasibility.** Are the OpenAI + Gemini tool-loop
   bindings genuinely required in 066, and are they realistically a *single*
   session (S2) alongside the sandbox, given the spike only exercised Anthropic?
5. **A/B sizing.** Is the full forward A/B (Experiments A **and** B, 2×2 arms,
   seeded defects across multiple frozen trees, K-repeats) realistically **one**
   session (S3)? If not, how should it split — and does that push 066 to 5+
   sessions or argue for moving Experiment B to its own set?
6. **Feasibility against the actual code.** Does the proposed adapter design fit
   how `ai_router` is actually structured (provider layer, config, test
   harness)? Name any concrete mismatch you find by reading the code.
7. **Anything unforeseen** — sandbox/safety holes, the deterministic-servant
   guardrail being undermined, cost blowups, hidden dependencies, a wrong
   prerequisite, a config-block error.

## Output format

For each fork (1–7), give a one-line **verdict** (`sound` / `change` /
`blocker`) and, where you say `change`/`blocker`, a concrete recommended
revision. Add a **Findings** list of anything else (severity
Critical/Major/Minor, the exact file/line where relevant, and the fix). End
with a **Recommended decomposition** — either "adopt as proposed" or your
revised session breakdown — and a one-line **BOTTOM LINE**.
