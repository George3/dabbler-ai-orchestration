**Right question?** Mostly yes. The more useful question is: **can Lightweight actually enforce dedicated verification without an events ledger?** My answer: **only if this set includes writer-owned structured mutations plus a hard close-time/state validator; otherwise defer the feature.**

## Q1 Writer target
**Recommendation:** Use the **structured files only**: append typed entries to `session-state.json.sessions[]` and create/seed `sN-issues.json` for verification/remediation sessions. **Do not mutate `spec.md`.** The authored spec session count stays fixed; the **runtime session count grows only through the blessed writer**, one increment per appended typed session, atomically with the append.

**Rationale:** `spec.md` is the authored plan, not runtime state. Markdown mutation is higher-risk, less auditable, and clashes with the v4 derived-state mechanics; the count/truncation problem is contained if one writer owns the state-side growth path.

**Defect flags:** **CONCRETE DEFECT in L3 if enforcement is assumed to come from D3 or docs alone.** On Lightweight, D3 is inert/content-blind, so “never freehand” is only real if the writer plus validator/gate enforce it.

## Q2 Vocabulary surface
**Recommendation:** Lock `session.type = work | verification | remediation` with default `work` as the **only new session field**. Promote finding field name **`issueType`** (not issue-level `type`) with values `deterministic-defect | contingent-risk | standards-departure | missing-context`; in the shared schema keep `issueId`, `issueType`, `verificationMethod`, and `suggestedTestOrCheck` **OPTIONAL**, but in Lightweight dedicated verification require **`issueId` + `issueType` + `verificationMethod`** on verifier-created open issues; keep `suggestedTestOrCheck` **OPTIONAL**. Lock `resolution_status` to `fixed | not-reproducible | accepted-risk | accepted-consequence | advisory-disagreement | needs-more-context | escalate-human` and **validator-enforce it when present** under a bumped issues `schemaVersion`.

**Rationale:** This preserves shared-schema backward compatibility while giving Lightweight enough structure to bound re-verification. `suggestedTestOrCheck` is often redundant with `verificationMethod`; making it required adds churn without much control value. Enforcing the enum fixes spelling drift without making `resolution_status` generically gate-driving outside this workflow.

## Q3 Derived states
**Recommendation:** Yes: all seven set states are **derived only**, never persisted as a new field. Use this precedence:

1. If `verificationMode = out-of-band-or-none`: terminal set => `closed-no-verification`; otherwise => `work-in-progress`.
2. Else, if the latest session is nonterminal: `work` => `work-in-progress`; `verification` => `awaiting-verification`; `remediation` => `awaiting-remediation`.
3. Else, in dedicated mode:
   - authored/planned work sessions still remain incomplete => `work-in-progress`
   - last completed session is `work` and all authored work sessions are complete => `awaiting-verification`
   - last completed `verification` with pass / no open issues => `closed-verified`
   - last completed `verification` with open issues and no human-stop condition => `awaiting-remediation`
   - last completed `verification` with escalation, round-limit hit, or no falsifiable check => `awaiting-human`
   - last completed `remediation` with code/doc changes => `awaiting-verification`
   - last completed `remediation` with no code/doc changes and all issues terminally dispositioned => `closed-dispositioned`
   - last completed `remediation` with human-required closure/dispute/escalation => `awaiting-human`
   - while in `awaiting-human`, the latest existing human disposition decides the exit: reverify => `awaiting-verification`; remediate => `awaiting-remediation`; human closes remaining issues => `closed-dispositioned`; human declares no open issues => `closed-verified`.

**Rationale:** Set 047 already says workflow summary fields are derived, so persisting another state field is the wrong pattern. Also, `closed-dispositioned` and some `awaiting-human` cases cannot be derived from the session tuple alone; they require the latest issues envelope and human disposition record.

## Q4 Tie-breaker shape
**Recommendation:** Confirm exactly L4: reuse the existing Full-tier **`second-opinion`** path, operator-initiated from `awaiting-human`, with **no new machine state**.

**Rationale:** The code path already exists and matches the current adjudication model. Adding a Lightweight-only tie-break mechanism would be duplicate workflow machinery for no gain.

## Q5 How `verificationMode` is captured
**Recommendation:** **(b) only** — capture it once at set start as the existing Set 048 **`suggestion_disposition`** pattern, and read that durable record anywhere the workflow needs `verificationMode`. Default absent value to `out-of-band-or-none`.

**Rationale:** This is an operator runtime choice, not authored plan text. Using the existing disposition pattern avoids mutating `spec.md` and avoids adding another schema field, which keeps faith with L2.

## Q6 Close-out gate
**Recommendation:** **HARD-BLOCK** terminal close when `verificationMode = dedicated-sessions` and the set has not satisfied the dedicated verification path. **TTY and non-TTY both block**; TTY prints the corrective action, non-TTY exits non-zero with the same structured error; no force-bypass except an explicit human close disposition.

**Rationale:** A soft warning makes the opt-in mode meaningless and leaves L3 unenforced. Because dedicated mode is elective up front, the opted-in path should be strict.

**Defect flags:** **CONCRETE DEFECT in L3 unless this hard validator/gate exists.** Without it, Lightweight still permits hand-added typed sessions and set closure without real verification.

## Q7 Extension/Explorer scope
**Recommendation:** **Defer rendering** of session `type` to a follow-on set. Do not include Explorer/UI work now.

**Rationale:** Rendering has zero control-plane value and expands the blast radius into read surfaces. Land schema, writer, derivation, and gate first.

## Scope/risk
**Biggest risk:** faux enforcement on Lightweight — i.e., acting as if D3 or documentation can prevent freehand typed sessions when there is no events ledger.  
**Cut to stay bounded:** all `spec.md` mutation, all Explorer/rendering work, and any extra taxonomy tightening beyond `session.type`, `issueType`, and the `resolution_status` enum.

**No concrete defect found in L1, L2, or L4.** The only concrete defect is the **L3 enforcement gap** unless Q6’s hard validation is part of the lock.