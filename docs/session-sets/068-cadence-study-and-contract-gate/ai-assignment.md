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

## Session 2 of 6: Experiment A symmetric re-grade + Experiment B pre-registration

**Orchestrator:** Claude Code — claude-opus-4-8, high effort. The S1 routed
recommendation was to switch to claude-sonnet-4-6/medium on cost grounds, with a
recorded caveat that the symmetric re-grade carries a statistical-honesty burden
(the 0.21.1 erratum) and the comparable Set 067 S3 used opus-4-8 high. **The
operator confirmed at the S2 boundary to stay on opus-4-8 high** (rigor over cost;
also keeps the orchestrator constant with how the original Experiment A was run).

| Step / task | Engine / model | Why |
|---|---|---|
| Register + read guidance / Set 067 experiment artifacts | orchestrator (Claude) | Bootstrap reading; no routed call warranted. |
| Symmetric re-grade of Experiment A (audit-symmetric.json + regrade.py + experiment-a-regrade.md) | orchestrator (Claude) | Mechanical re-analysis over committed data; the inference is the orchestrator's own work, cross-provider verified at close. Deterministic, no API. |
| Pre-register Experiment B (preregistration + cost_model.py + harness-skeleton.md) | orchestrator (Claude) | Single-author experimental-design authoring against the Set 065/067 settled design; the routed pass is the verification. |
| End-of-session verification | **gpt-5.4 (openai)** | Cross-provider for the Claude orchestrator (Rule 2). L-067-1 (GPT over-probes) is about the pull-verifier loop, not single-shot session verification, so gpt-5.4 remains the right reviewer. R1 ISSUES_FOUND (1 Minor floor-overclaim + 2 Major: Exp B union-primary not stability-binding; missing vis_at_close_for_Q) -> R2 (Finding1 RESOLVED; 2/3 PARTIAL: median made binding w/o band, Q-surface contradiction) -> R3 **VERIFIED** (1 Minor wording fixed). |
| Next-orchestrator recommendation | **routed analysis** | L-064-6: never self-opine on the next orchestrator. |

**Routed next-orchestrator recommendation for Session 3:** **claude-sonnet-4-6
(anthropic) / medium** via the Claude Code orchestrator. Rationale: Session 3
("Experiment B — the cadence study") is substantial-but-well-defined harness
production code + a metered experiment sweep + statistical-honesty analysis, all
against the design pre-registered this session — capable work for sonnet-class at
lower cost than opus. **Explicitly avoids gpt-5.4 as orchestrator** (L-067-1
budget-exhaustion as a loop driver), preserving gpt-5.4 and gemini-2.5-pro as the
two experiment SUBJECT providers and the cross-provider verifier. The decision is
the operator's to confirm at the Session 3 boundary (the same statistical-honesty
weighting that kept S2 on opus may apply to S3's analysis step).

**Verification spend (gpt-5.4):** R1 $0.350 + R2 $0.146 + R3 $0.107 = ~$0.603.
Routed next-orch analysis: $0.0028. Session total (routed): ~$0.606.

## Session 3 of 6: Experiment B — the cadence study

**Orchestrator:** Claude Code — claude-opus-4-8, high effort. The S2 routed
recommendation was claude-sonnet-4-6/medium on cost grounds, with a recorded
caveat that S3's statistical-honesty analysis step may again warrant opus (as S1
and S2 stayed on opus). The operator started this session on opus-4-8 high —
consistent with that caveat and the S1/S2 precedent (rigor over cost; orchestrator
kept constant for the experimental-analysis sessions).

| Step / task | Engine / model | Why |
|---|---|---|
| Register + read guidance / prereg / run_test contract / Exp A harness | orchestrator (Claude) | Bootstrap reading; no routed call warranted. |
| Build the staged-snapshot harness (build_snapshots.py, catalogue.json, run_arms.py, grade.py) | orchestrator (Claude) | Production-style harness implementation against the S2 pre-registration + the Set 067 Experiment A harness shape; deterministic builder/grader, no API. The orchestrator implements; the routed pass is the verification. |
| Run the arms (pilot + K=3 two-provider sweep) | **routed: gpt-5.4 + gemini-2.5-pro (SUBJECTS)** | The experiment IS the metered routing — arms R/Q via providers.call_model, arm E via pull_route + the run_test cage. Held provider/reasoning constant across contrasts (mirrors Exp A). |
| Grade + symmetric mechanism audit + write the cadence verdict | orchestrator (Claude) | Deterministic grading (cost_model + per-repeat contrasts) + the inference against the FIXED decision rule; the orchestrator's own analysis, cross-provider verified at close. |
| End-of-session verification | **gpt-5.4 (openai)** | Cross-provider for the Claude orchestrator (Rule 2). L-067-1 (GPT over-probes) is about the pull-verifier loop, not single-shot session verification. R1 ISSUES_FOUND (1 Major arm-E capability overstatement + 3 Minor) -> all fixed + echoes propagated (L-065-1) -> R2 (resolved, 1 trivial new nit) -> R3 **VERIFIED**. |
| Next-orchestrator recommendation | **routed analysis** | L-064-6: never self-opine on the next orchestrator. |

**Routed next-orchestrator recommendation for Session 4:** **claude-sonnet-4-6
(anthropic) / medium** via the Claude Code orchestrator. Rationale: Session 4
("Routed keep / demote / retire decision") routes the decision through
cross-provider consensus + operator confirmation and implements a small,
well-scoped config/doc change (possibly "no code change — keep") — a decision +
small implementation, not a large coding session, since the hard analysis (the
cadence verdict) is already done and verified. Avoids the L-067-1 gpt-5.4-as-
orchestrator budget risk; reserves the flagship models as consensus participants
and cross-provider verifier. **Caveat for the S4 operator:** the Experiment B
verdict is nuanced (cadence mechanism real but confounded; "does not hold" via the
control clause, with a genuine narrow rework-timing edge for routed) — the same
statistical-honesty weighting that kept S1–S3 on opus may again warrant opus for
the decision-weighing step; the operator confirms at the S4 boundary, and the
decision itself must be routed to multiple providers.

**Verification spend (gpt-5.4):** R1 $0.426 + R2 $0.127 + R3 $0.003 = ~$0.556.
Experiment sweep + pilot (gpt-5.4 + gemini-2.5-pro subjects): ~$0.85. Routed
next-orch analysis: $0.0031. Session total (metered): ~$1.41.
