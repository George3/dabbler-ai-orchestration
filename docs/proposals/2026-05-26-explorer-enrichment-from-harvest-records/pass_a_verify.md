# PASS A — Cross-provider verification

- **Provider:** openai
- **Model:** gpt-5-4-mini
- **Cost:** 0.03274199999999999
- **Tokens (in/out):** 6462/6199
- **Verdict:** ISSUES_FOUND

---

**ISSUES FOUND**

- **Issue 1:** §3.3 and §3.4 are likely misclassified as **DEFER** instead of **ALREADY SHIPPED**
  - **Category:** Correctness
  - **Severity:** Major
  - **Details:** The proposal itself says the writer-bypass warning signal is already visible in 0.21.0 and that the engine-mismatch conflict pill is already shipped. If the core UI signal exists already, the correct disposition is **ALREADY SHIPPED** with any refinements deferred, not **DEFER**. The reviewed response endorsed both classifications without flagging this.

- **Issue 2:** The forced split of Session 5 into two sessions is an unsupported false positive
  - **Category:** False Positive
  - **Severity:** Major
  - **Details:** The proposal explicitly justifies bundling the time-since-last-activity work with the migration expansion because both are relatively small and adjacent to the same row-template area. The response escalates that into a required 7-session arc without showing that the original 6-session plan is actually unbalanced or over-scoped.

- **Issue 3:** The “missing leverage point” identified by the response is not missing from the proposal
  - **Category:** False Positive
  - **Severity:** Minor
  - **Details:** The response says the canonical-state vs Harvest Records discrepancy is a missing leverage point, but the proposal already surfaces that exact tension in §7 Bias 1 and Bias 2, including the idea of a divergence pill. The real question is whether to scope it now, not whether it was surfaced.

- **Issue 4:** The response missed the actual open leverage point around retroactive `totalSessions: null` migration
  - **Category:** Completeness
  - **Severity:** Major
  - **Details:** Q1 in the proposal asks whether the new `totalSessions: null` semantics should be retroactively applied to existing not-started session sets via a one-time migration. That is directly relevant to deliverable (a) and the long-term correctness of `0/?` behavior, but the response did not address it.