# Set 068 — AI Assignment Ledger

Per-session record of the cheapest-capable AI for each step and the routed
next-session recommendation. Authored at Session 1; appended each session.

> The per-step and next-orchestrator recommendations are produced via
> `route(task_type="analysis")` (L-064-6: never self-opine). The analysis model
> returned its reasoning against an out-of-date model lineup (it invented
> `claude-3.5-sonnet-20240620` / `claude-code-1.0-opus` and treated only
> `gpt-5.4` as real); the *substance* of each recommendation is preserved below,
> with model ids normalized to this repo's actual lineup
> (`claude-opus-4-8`, `claude-sonnet-4-6`, `gpt-5.4`, `gemini-2.5-pro`).

## Session 1 of 6: `run_test` disposable-worktree sandbox + tool (+ ReDoS isolation)

**Orchestrator:** Claude Code — claude-opus-4-8, high effort (implementation +
judgment over a new write-capable execution cage with subprocess / filesystem /
ReDoS safety surface).

| Step / task | Engine / model | Why |
|---|---|---|
| Register + read guidance / contract docs | orchestrator (Claude) | Bootstrap reading; no routed call warranted. |
| Finalize the `run_test` contract note | orchestrator (Claude) | Single-file design authoring against the Set 065/067 settled architecture (mirrors the S1 tool-contract precedent in Set 067). |
| Implement `run_test_sandbox.py` (worktree create/teardown, write-confinement, timeout-kill, output cap, raw-result + trace) | orchestrator (Claude) | Core production-code build — security-critical process + filesystem cage; the orchestrator's own work, not a routed reasoning task. Routed analysis agreed this is the highest-capability step. |
| Relocate the `grep` ReDoS defense onto subprocess/cage machinery | orchestrator (Claude) | Same — subprocess management + ReDoS isolation behind the kept cheap heuristic pre-filter. |
| Register `run_test` in the pull_verifier registry + config caps + exports | orchestrator (Claude) | Mechanical wiring against the S1/Set 067 surface. |
| Unit tests (cage lifecycle, timeout-kill, output cap, write-confinement, ReDoS isolation) | orchestrator (Claude) | Authored alongside the code; the routed pass is the cross-provider verification, not test-writing. |
| End-of-session verification | **gpt-5.4 (openai)** | Cross-provider for the Claude orchestrator (Rule 2). L-067-1 (GPT over-probes) is about the *pull-verifier loop*, not single-shot session verification, so gpt-5.4 remains the right cross-provider reviewer here. R1 ISSUES_FOUND (1 Critical write-confinement overclaim + 1 Major teardown + 1 Minor elision) -> R2 (Critical re-scope incomplete, Major prune `--expire`, new Minor leak-render dropped output) -> R3 VERIFIED. |
| Next-orchestrator recommendation | **routed analysis** | L-064-6: never self-opine on the next orchestrator. |

**Routed next-orchestrator recommendation for Session 2:** switch from
claude-opus-4-8 to a **sonnet-class reasoning model**
(`claude-sonnet-4-6` / anthropic, medium effort), on the rationale that
Session 2 ("Experiment A symmetric re-grade + Experiment B pre-registration")
is analysis + experimental-design reasoning with **no production code**, so it
does not need opus-class code-generation capability. *Caveat recorded for the
S2 operator:* the symmetric re-grade carries a statistical-honesty burden (the
0.21.1 erratum) and Set 067 S3 used opus-4-8 **high** for the comparable
Experiment A capability study; the operator should weigh the routed
cost-optimization against that precedent at S2 start. The decision is the
operator's to confirm at the Session 2 boundary.

**Verification spend (gpt-5.4):** R1 $0.244 + R2 $0.148 + R3 $0.044 = ~$0.436.
Routed next-orch analysis: $0.0056. Session total: ~$0.442.
