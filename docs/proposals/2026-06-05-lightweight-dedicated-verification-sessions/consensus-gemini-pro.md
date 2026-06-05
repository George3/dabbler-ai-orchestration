Here is a review of the design lock.

---

### **Q1: Writer target**

**Recommendation:** The blessed writer MUST target the structured files: `session-state.json` (appending to `sessions[]` and incrementing `totalSessions`) and `sN-issues.json` (creating the envelope).

**Rationale:** `spec.md` represents authored intent, not runtime state. Mutating it mid-set corrupts the plan of record and relies on fragile regex parsing. The session state file is the canonical source of truth for execution history; extending it is the architecturally correct path.

### **Q2: Vocabulary surface**

**Recommendation:**
1.  Confirm `type: work | verification | remediation` is the only new session field.
2.  Lock the `resolution_status` enum to the seven proposed values.
3.  `issueId`, `description`, `type`, and `verificationMethod` MUST be REQUIRED fields in a finding. `suggestedTestOrCheck` is OPTIONAL. Confirm all are optional for Full tier to prevent breaking changes.
4.  The tightened `resolution_status` enum MUST be enforced by a validator.
5.  `issueType` is the correct field for the proposal's finding `type` values.

**Rationale:** A contract is meaningless without enforcement; the validator must enforce the enum. Requiring the core finding fields ensures every issue is actionable and trackable across rounds. Keeping other fields optional minimizes friction.

### **Q3: Derived states**

**Recommendation:** Confirm the seven states are derived and not persisted. The derivation rules are based on `verificationMode` and the `type`, `status`, and `verificationVerdict` of the last completed session in `sessions[]`.

**Rationale:** Persisting derived state creates synchronization hazards. The derivation logic must be concrete:
*   `closed-no-verification`: `verificationMode` is `out-of-band-or-none` and all `work` sessions are `completed`.
*   `awaiting-verification`: Last completed session `type` is `work` or `remediation`.
*   `awaiting-remediation`: Last completed session `type` is `verification` with `verificationVerdict: issues-found`.
*   `awaiting-human`: An `sN-issues.json` contains an issue with `resolution_status: escalate-human`, or the session `orchestrator` block indicates a required manual step.
*   `closed-verified`: The last `verification` session has `verificationVerdict: passed`.
*   `closed-dispositioned`: Last `verification` or `remediation` session completed and all issues in `sN-issues.json` have a terminal disposition (`fixed`, `accepted-risk`, etc.).
*   `work-in-progress`: Default state when none of the above conditions are met.

### **Q4: Tie-breaker shape**

**Recommendation:** Confirm. The tie-breaker is the existing `second-opinion` resolution path.

**Rationale:** This correctly reuses an existing, human-initiated workflow from the `awaiting-human` state, avoiding new machine states and code paths as specified in L4 and grounding fact #6.

### **Q5: How `verificationMode` is captured**

**Recommendation:** Both (c). Use a start-of-set operator prompt whose default is read from a Session Set Configuration flag.

**Rationale:** This provides the best of both worlds: support for interactive configuration and headless automation. The chosen mode should be stored in a non-derived, set-level configuration file, following the Set 048 `suggestion_disposition` pattern.

### **Q6: Close-out gate**

**Recommendation:** The `close_session` gate should HARD-BLOCK in an interactive TTY session and SOFT-WARN in a non-TTY (headless) session.

**Rationale:** This enforces the workflow for interactive users while preventing automated scripts from failing unexpectedly. It mirrors the principle of graceful degradation and adapts to the execution context.

### **Q7: Extension/Explorer scope**

**Recommendation:** Defer all UI/rendering work to a follow-on set.

**Rationale:** Scope containment is critical. The immediate value is in the structured data and the state machine logic. UI work can be addressed once the core workflow is proven stable.

---

### **Defect Flags**

**CONCRETE DEFECT L3:** The premise of *extending* writer-discipline check D3 is flawed. Grounding fact #3 confirms D3 is content-blind, mtime-based, and inert on the Lightweight tier. The required check is a new, content-aware validation, not an extension of D3. The enforcement mechanism is the blessed writer (L3), not a faulty detection paradigm. The spec and all related work items must be corrected to reflect this.

### **Scope/risk Note**

**Biggest Risk:** The derived state logic (Q3). If the rules for deriving the seven workflow states are ambiguous or incorrectly implemented, the state machine will be unreliable. This logic must have 100% unit test coverage against all edge cases.

**Recommendation to Cut:** Defer all UI rendering of the session `type` (Q7). The proposal is already minimal; this is the only remaining component that is not core to the state machine's function.