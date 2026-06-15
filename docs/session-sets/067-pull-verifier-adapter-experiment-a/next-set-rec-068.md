# Set 067 -> next-session-set (068) recommendation (routed)

> Routed via route(task_type='analysis'). Model: ?

### Recommendation for Next Session Set

**Set Slug:** Set 068

**Goal:** Implement the `run_test` tool and its disposable worktree sandbox to enable the cadence and intervention study (Experiment B). This experiment will provide the final data needed to decide the future role of the routed per-session verifier.

**Estimated Sessions:** 7

### Ordering of Deferred Items

The four deferred items must be sequenced as follows due to direct dependencies.

1.  **Implement the disposable-worktree `run_test` sandbox.**
    *   **Why first:** This is a hard prerequisite for Experiment B. Experiment B is an "intervention study" that requires an agent to make and test code changes. The existing read-only tools are insufficient; the `run_test` tool provides the necessary write-caged execution capability.

2.  **Execute Experiment B (cadence / staged-snapshot intervention study).**
    *   **Why second:** This experiment depends directly on the `run_test` tool. Its purpose is to gather the data required to make the final strategic decision about the routed verifier.

3.  **Make the routed keep / demote / retire decision.**
    *   **Why third:** This decision is explicitly gated on the results of Experiment B. The experiment's outcome will determine if the cadence defense for routed verification is viable.

4.  **Formalize the contract-test / CDC gate.**
    *   **Why last:** This is a strategic policy decision that codifies the findings from both Experiment A and Experiment B. It formalizes the new workflow where agents are used to author deterministic falsifiers rather than perform verification runs directly. This is the logical conclusion after the agent's role has been fully evaluated and defined in the preceding steps.
