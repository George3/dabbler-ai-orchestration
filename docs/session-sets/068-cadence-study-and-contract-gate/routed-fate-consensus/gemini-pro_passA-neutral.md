# Consensus consult -- gemini-pro -- passA-neutral

> model_used=None cost_usd=0.008807 chars=3054

**Recommendation:** DEMOTE

### Justification

The most effective path forward is to `DEMOTE` the per-session routed verification from a mandatory gate to a risk-gated, specialized tool. The evidence does not support the extremes of either keeping the status quo or retiring the capability entirely. This decision correctly balances the demonstrated superiority of the new end-of-set verification surfaces with the narrow, but significant, value of the per-session check.

The case against `KEEP` is definitive. Experiment A demonstrates that the end-of-set path-aware critique is structurally more capable, catching high-severity cross-file defects that the snippet-fed routed verifier cannot. To continue mandating an inferior tool on every session would be to ignore a clear, evidence-backed improvement. The new tools represent a higher capability ceiling, and the workflow's primary verification surface should reflect that.

Conversely, the case against `RETIRE` is premature. Experiment B confirms that the per-session cadence has one unique and valuable payoff: it catches migrating coupling defects at the moment of introduction, realizing a significant rework saving (s=27-66) over an end-of-set-only approach. While the pre-registered verdict found fault with the controls, it did not disprove this core mechanism. To retire the tool would be to discard this demonstrated value and remove a safety net that has caught real operational defects, before its replacement (the contract-test gate) is fully proven.

The `DEMOTE` strategy correctly synthesizes these findings. It promotes the superior end-of-set path-aware critique and the forthcoming contract-test gate to be the primary, default verification layer. This new baseline will provide a higher capability ceiling and a deterministic floor. It simultaneously preserves the per-session routed verifier as a specialized tool, retaining its one demonstrated advantage.

This specialization should be implemented via risk-based gating. The per-session check is most valuable when cross-file coupling defects are likely to be introduced. Therefore, it should be triggered not on every session, but on sessions whose changes have a significant blast radiusâ€”for instance, modifying a public API, refactoring shared logic, or touching multiple core implementation files. Simple, localized changes would bypass this check, reducing friction and cost.

Concretely, the following changes should be made:
*   **Configuration:** The workflow default for per-session routed verification should change from mandatory to opt-in or gated.
*   **Logic:** The orchestrator should implement a heuristic to trigger the verification based on the session's diff (e.g., `files_changed > 1 AND involves non-test/doc code`) or on an explicit signal from the AI or human operator.
*   **Documentation:** The workflow documentation must be updated to reflect that the primary verification happens at set-close, with the per-session check reserved for high-risk changes. The capability itself must not be removed.
