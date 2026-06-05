# Set 057 S1 — Cross-provider audit verdict

> **What this is.** The synthesized design-lock verdict for
> `057-lightweight-dedicated-verification-sessions`, produced from a
> cross-provider consensus on Q1–Q7 with the operator-decided anchors
> L1–L4 fed as context. The orchestrator (Claude / claude-opus-4-8) was
> excluded from the consensus pool; both consensus engines are
> non-Anthropic.
>
> **Inputs (raw, never edited):**
> [`consensus-gpt-5-4.md`](consensus-gpt-5-4.md) and
> [`consensus-gemini-pro.md`](consensus-gemini-pro.md).
> **Proposal of record:**
> [`../2026-06-05-lightweight-dedicated-verification-sessions.md`](../2026-06-05-lightweight-dedicated-verification-sessions.md).
> **Date:** 2026-06-05. **Consensus cost:** $0.2709
> (gpt-5-4 high-effort $0.2533; gemini-pro $0.0176).

---

## Method

- Orchestrator: claude-code / claude-opus-4-8 (excluded from the vote).
- Consensus engines: **gpt-5-4** (OpenAI, reasoning_effort=high) and
  **gemini-pro** (Google, thinking_budget=8192) — both different providers
  from the orchestrator.
- Always-on bias-cautions preamble applied. L1–L4 supplied as decided
  context with instruction to stress-test but not reopen without a concrete
  defect. Seven verified grounding facts about the live tree were supplied
  so the engines reasoned against real mechanics (derive-top-level v4,
  `_build_sessions_array` truncation, the content-blind/Lightweight-inert D3
  check, the advisory-only `resolution_status`, the soft Lightweight gate,
  the existing `second-opinion` path).
- Q6 split materially; per the decision-consensus guidance (gate-strength /
  workflow-blocking is operator-owned) it was surfaced to the operator via
  `AskUserQuestion`. The operator chose **hard TTY / soft non-TTY**.

## Agreement summary

| Q | gpt-5-4 | gemini-pro | Outcome |
|---|---|---|---|
| Q1 writer target | structured files only; bump `totalSessions` | structured files only; increment `totalSessions` | **Aligned** |
| Q2 vocabulary | `type` only new field; enum validator-enforced; `issueType`; promoted fields optional | same; require core finding fields | **Aligned** (required-field nuance reconciled below) |
| Q3 derived states | derived; full precedence ladder | derived; concrete mapping | **Aligned** |
| Q4 tie-breaker | confirm L4 `second-opinion` | confirm L4 | **Aligned** |
| Q5 verificationMode capture | (b) suggestion_disposition only | (c) spec-flag default + prompt | **Aligned** (reconciled: durable record = suggestion_disposition, optional spec default) |
| Q6 close gate | hard both | hard TTY / soft non-TTY | **Split → operator: hard TTY / soft non-TTY** |
| Q7 Explorer | defer | defer | **Aligned** |

Both engines independently flagged **one concrete defect** (L3 mechanism)
and found **no concrete defect in L1, L2, or L4**.

---

## Locked answers

### Q1 — Writer target: STRUCTURED FILES ONLY
The blessed writer creates typed sessions by appending a `sessions[]` entry
to `session-state.json` and (for a verification session that finds issues)
seeding the `sN-issues.json` envelope. It **never mutates `spec.md`**. The
authored spec session count stays fixed; the **runtime** session count grows
only through the writer, which **increments `totalSessions` atomically with
each appended typed session** (required because `_build_sessions_array`
truncates/fails-loud against `totalSessions`). Markdown mutation is rejected
as higher-risk, regex-fragile, and at odds with v4 derived-state mechanics.

### Q2 — Vocabulary surface
- `session.type = work | verification | remediation`, default `work`, is the
  **only** new session field. Absent/`work` for all existing and Full-tier
  entries.
- Promoted finding fields use the name **`issueType`** (not an issue-level
  `type`, to avoid collision), with values `deterministic-defect |
  contingent-risk | standards-departure | missing-context`. The four
  promoted fields — `issueId`, `issueType`, `verificationMethod`,
  `suggestedTestOrCheck` — are **OPTIONAL in the shared `sN-issues.json`
  schema** (additive, backward-compatible for Full tier and existing
  fixtures).
- **Lightweight dedicated-verification flow requirement** (enforced by the
  flow, not the shared schema): a verifier-created **open** issue must carry
  `issueId` + `issueType` + `verificationMethod`. `description` is already
  required by the base envelope; `suggestedTestOrCheck` stays optional
  (often redundant with `verificationMethod`).
- `resolution_status` is locked to the seven-value enum: `fixed`,
  `not-reproducible`, `accepted-risk`, `accepted-consequence`,
  `advisory-disagreement`, `needs-more-context`, `escalate-human`. It is
  **validator-enforced when present**, under a **bumped `sN-issues.json`
  schemaVersion** (the field stays advisory in semantics — no runtime gate
  reads it — but spelling drift is caught by the schema validator).

### Q3 — Derived states: DERIVED, never persisted
The seven workflow states are derived (per the Set 047 derive-top-level
rule) from `sessions[]` + per-session `verificationVerdict` + the latest
`sN-issues.json` + the operator `suggestion_disposition` record. No new
persisted state field. Canonical derivation precedence (gpt-5-4's ladder,
corroborated by gemini-pro):

1. `verificationMode = out-of-band-or-none`: set terminal ⇒
   `closed-no-verification`; else ⇒ `work-in-progress`.
2. Latest session non-terminal (in-flight): `work` ⇒ `work-in-progress`;
   `verification` ⇒ `awaiting-verification`; `remediation` ⇒
   `awaiting-remediation`.
3. Dedicated mode, latest session complete:
   - authored work sessions still incomplete ⇒ `work-in-progress`;
   - last completed `work` and all authored work complete ⇒
     `awaiting-verification`;
   - last completed `verification`, no open issues / `VERIFIED` ⇒
     `closed-verified`;
   - last completed `verification`, open issues, no human-stop ⇒
     `awaiting-remediation`;
   - last completed `verification` with escalation / round-limit / no
     falsifiable check ⇒ `awaiting-human`;
   - last completed `remediation` with code/doc changes ⇒
     `awaiting-verification`;
   - last completed `remediation`, no changes, all issues terminally
     dispositioned ⇒ `closed-dispositioned`;
   - last completed `remediation` needing Critical/Major non-fix closure or
     dispute ⇒ `awaiting-human`;
   - in `awaiting-human`, the latest human disposition decides the exit
     (reverify ⇒ `awaiting-verification`; remediate ⇒ `awaiting-remediation`;
     accept ⇒ `closed-dispositioned`; declare-complete ⇒ `closed-verified`).

Note (both engines): `closed-dispositioned` and some `awaiting-human` cases
cannot be derived from the session tuple alone — they require the latest
issues envelope + human-disposition record. The derivation helper must read
those, not just `sessions[]`.

### Q4 — Tie-breaker: confirm L4 exactly
The tie-breaker is the existing Full-tier **`second-opinion`** resolution
(`verification.settings.on_disagreement` / `tiebreaker_model`),
**operator-initiated** only, reachable from `awaiting-human`, with **no new
machine state** and wording consistent with the Full-tier adjudication
vocabulary.

### Q5 — `verificationMode` capture
**Primary, durable record = the Set-048 `suggestion_disposition`** written
once at set start (the value every workflow step reads). An **optional**
Session Set Configuration `verificationMode` field may seed the start-of-set
prompt's default. **Default when neither is present = `out-of-band-or-none`**
(preserves current Lightweight behavior; the feature is strictly opt-in). No
new derived state field and no `spec.md` mutation — faithful to L2.

### Q6 — Close-out gate: HARD TTY / SOFT non-TTY  *(operator decision)*
When `verificationMode = dedicated-sessions` and no verification session
ran, `close_session` **hard-blocks in an interactive TTY** (prints the
corrective action and refuses) and **soft-warns in non-TTY/headless** (emits
the warning, allows the close so automation degrades gracefully). This
strengthens the common interactive path while preserving the established
soft-gate posture of today's `external-verification.md` gate and not
breaking scripted/CI close-outs. (Whether an explicit override flag such as
`--accept-suggestions` may force-bypass the interactive block is an **S3
implementation detail**, to be designed consistent with the Set-048 gate —
it was not part of the consensus or the operator's Q6 choice and is not
locked here.)

### Q7 — Extension/Explorer scope: DEFER
No Explorer/UI rendering of session `type` in this set. Land schema, writer,
derivation, and gate first; rendering has no control-plane value and expands
the blast radius into read surfaces. A follow-on set may add it.

---

## Concrete defect found (L3 mechanism — both engines)

**The spec's S2 step 4 — "Extend the `writer-bypass` (D3) check so freehand
creation of verification/remediation sessions is flagged" — is unsound and
is replaced.** D3 (`detect_writer_bypass`) is a content-blind, mtime-vs-
events-ledger check, and it is **inert on the Lightweight tier** (no events
ledger exists there — exactly the tier this feature targets). It cannot see
session `type` and cannot fire on Lightweight, so it can never flag a
freehand typed session.

**L3's core stands** (both engines affirm the blessed writer is the real
enforcement). What changes is the enforcement mechanism in the spec:

- **D3 is left as-is** (general writer-discipline mtime check) and is **NOT**
  extended.
- Enforcement of "typed sessions are writer-created, not freehand" rests on
  **(a)** the blessed writer being the only sanctioned creator, and **(b)** a
  **new content-aware close-time validator** that confirms the dedicated-
  verification path was actually followed (a verification session by a
  different engine ran before terminal close) — this validator is the same
  mechanism that backs the Q6 gate. On Lightweight (no ledger), this
  writer + close-time validator pair is the *entire* enforcement surface.

**Action for S2/S3:** rewrite spec S2 step 4 to "Add the content-aware
close-time validator (and wire it to the Q6 gate)"; drop the D3-extension
language wherever it appears in the spec's deliverables list and S2 steps.

No concrete defect was found in **L1** (per-set verification), **L2**
(promote-to-shared-schema), or **L4** (tie-breaker).

## Residual risks (carry to S2/S3 verifier)

1. **Faux enforcement on Lightweight** (gpt-5-4's top risk): treating the
   writer/docs as enforcement without the close-time validator leaves the
   opt-in mode toothless on the tier with no ledger. Mitigation: the Q6 gate
   + validator are in-scope for S3, not deferred.
2. **Derived-state correctness** (gemini-pro's top risk): the seven-state
   derivation must have full unit coverage over the edge cases above,
   especially the issues-envelope-dependent `closed-dispositioned` /
   `awaiting-human` branches. Mitigation: S2 derivation-helper tests must
   exercise every ladder branch.
