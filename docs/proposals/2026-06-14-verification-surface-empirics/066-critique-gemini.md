# 066 Decomposition - Devil's Advocate Critique (Gemini)

## Forks

**1. Scope.**
**Verdict:** `sound` (on deferred integration) but `blocker` (on set sizing). 
**Revision:** Deferring Path-Aware workflow integration and the contract gate to 067 is correct; the A/B test acts as the consumer to validate the adapter in 066. However, 066 itself remains hopelessly overloaded because the A/B test is two massive and distinct experiments. 

**2. Build-order risk.**
**Verdict:** `sound`.
**Revision:** The qualitative evidence from the S1 retrospective and S2 spike already establishes that path-aware critique finds severe defects routed cannot see. The A/B test's primary purpose is to decide *routed's* fate (verifying its cadence/capability edge), not to repeatedly justify path-awareness. Hardening the adapter first is logical.

**3. Release timing.**
**Verdict:** `change`.
**Revision:** Do not ship the PyPI release in 066. Shipping a dormant, disconnected adapter into production before the framework actually integrates it (Set 067) introduces an unconsumed API surface. Validate it against the A/B test in 066 using local worktrees, then release the adapter and its workflow integration simultaneously in 067.

**4. Multi-provider necessity & feasibility.**
**Verdict:** `blocker`.
**Revision:** S2 is dangerously over-scoped. Anthropic, OpenAI, and Gemini all process tool use/function calling differently (OpenAI's `tool_calls` vs. Gemini's `function_declarations`). Implementing both of these new driver loops *and* engineering a disposable Git worktree sandbox for `run_test` will blow up a single session. Split S2 into two sessions: one for provider bindings, one for the worktree sandbox. 

**5. A/B sizing.**
**Verdict:** `blocker`.
**Revision:** S3 tries to cram Experiment A (mutation testing on static frozen trees with seeded defects) and Experiment B (a multi-session staged snapshot replay to measure cadence) into one session. They require fundamentally different test harnesses. S3 should be restricted strictly to Experiment A (Capability). Defer Experiment B to a later session or Set 067.

**6. Feasibility against the actual code.**
**Verdict:** `change`.
**Revision:** The instruction to wire the adapter as a "new provider-kind" within the existing `router-config.yaml` / `providers.call_model` paradigm is a severe architectural mismatch. `route()` expects a stateless, one-shot push. A multi-turn agentic loop cannot transparently masquerade as a stateless LLM without breaking timeout assumptions, retry logic, and token accounting in `ai_router`. The adapter must be a distinct parallel entrypoint (e.g., `pull_route()`), not nested inside `call_model`.

**7. Anything unforeseen.**
**Verdict:** `change`.
**Revision:** The deterministic servant abstraction built in S1 (read-only tools) will need to be refactored in S2 when `run_test` drops in, because `run_test` execution happens in a distinct sandbox while read/grep happen in the host. The S1 architecture needs to anticipate the split execution context.

## Findings
- **Major:** Stashing stateful tool loops inside `providers.py` will corrupt the router's current deterministic error handling and cost metrics if not explicitly walled off.
- **Minor:** S4 directs synthesis into a `keep / demote / retire` recommendation for the routed arm. If Experiment B (cadence) is removed from this set for sizing reasons, the keep/demote decision *cannot* be made yet. `ab-results.md` will only establish capability overlap.

## Recommended decomposition

**Set 066 (Revised):**
- **S1 — Adapter core + Anthropic binding.** Stateful driver, deterministic read-only servant (`read_file`, `grep`), tool-call trace instrumentation. Built as a parallel entry point to `route()`, not inside `providers.py`.
- **S2 — Multi-provider bindings.** Implement OpenAI and Gemini tool loop bindings to match the Anthropic capability. 
- **S3 — Sandboxed `run_test`.** Build the disposable git worktree harness and wire the execution tool.
- **S4 — Forward A/B (Experiment A ONLY).** Run the capability assessment on frozen trees with seeded defects. Synthesize `ab-results.md`. 
*(Experiment B, keep/demote decision, and PyPI release deferred to 067).*

**BOTTOM LINE:** The build order is sound, but attempting to cram multi-provider bindings, a git sandbox codebase, and a two-harness A/B experiment into four sessions guarantees a bloated, failed set; split the bindings from the sandbox, scope the A/B test to Experiment A only, and delay the PyPI release.