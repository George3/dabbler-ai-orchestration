# Set 057 Change Log

**Lightweight dedicated verification sessions — audit & design-lock (S1),
typed-session schema + blessed writer (S2), workflow + operator-choice +
close-out + ship (S3).**

This set replaces the Lightweight tier's semi-manual copy/paste
review-prompt step with an optional, bounded **dedicated
verification/remediation-session** workflow. When a set opts in
(`verificationMode: dedicated-sessions`), the generating engine plans a
per-set verification session, the operator runs it on a *different* engine,
and a failing verification authors a remediation session so the work never
silently stops — a bounded re-verification loop (rounds 1–2 automatic, 3+
human) with a hard stop to a human whenever a rule cannot be followed
mechanically. The design reuses the existing `sN-issues.json` /
`disposition.json` / `session-state.json` artifacts rather than inventing a
parallel vocabulary, and is enforced through blessed writers plus a
content-aware close-time gate rather than freehand edits.

Audit-locked spec at [`spec.md`](spec.md) (S1 Audit Lock, Q1–Q7 +
L1–L4). Package release: **`dabbler-ai-router` 0.15.0 → 0.16.0**, PyPI
publish **held** for operator tag-push `v0.16.0`; the VS Code extension is
untouched (no Marketplace bump — Explorer rendering of session `type` was
deferred to a follow-on per Q7).

## Session 1 — Audit & design-lock

Closed 2026-06-05 with disposition `completed`. Verdict: `VERIFIED`
(round 1 ISSUES_FOUND → round 2 VERIFIED).

- De-duplicated the design-input proposal (two concatenated drafts → kept
  the cleaner second as the proposal of record) and ran cross-provider
  consensus (gpt-5-4 + gemini-pro; orchestrator excluded) on Q1–Q7 with
  L1–L4 fed as decided context.
- **Locked the contract** (S1 Audit Lock in `spec.md`): Q1 writer target =
  structured files only (never mutate `spec.md`); Q2 `session.type` +
  promoted optional finding fields + the 7-value `resolution_status` enum;
  Q3 seven workflow states **derived, never persisted**; Q4 tie-breaker =
  existing `second-opinion` resolution; Q5 `verificationMode` captured once
  at set start; Q6 close gate = **hard-TTY / soft-non-TTY** (operator
  decision; the engines split); Q7 defer all Explorer rendering.
- **Concrete defect corrected:** both engines flagged that the original
  "extend the D3 `writer-bypass` check" plan was unsound — D3 is
  content-blind and inert on Lightweight (no events ledger). Replaced with
  a new content-aware close-time validator; **D3 left unchanged**.
- Cost: $0.4749 routed.

## Session 2 — Schema + forced writer

Closed 2026-06-05 with disposition `completed`. Verdict: `VERIFIED`
(round 1 ISSUES_FOUND, 3 Major fixed in-flight → round 2 VERIFIED).

- Added the per-session **`type`** field (`work | verification |
  remediation`, default `work`; absent == work) to `progress.py`, preserved
  across writer rebuilds in `session_state.py`.
- Extended `sN-issues.json` to **schemaVersion 2**: promoted four optional
  finding fields (`issueId` / `issueType` / `verificationMethod` /
  `suggestedTestOrCheck`) and enum-enforced `resolution_status` +
  `issueType` when present; v1 files stay valid.
- Implemented the blessed writer `register_typed_session_start` (+ the
  `start_session --type` CLI branch and announcement banner) and
  `ai_router/dedicated_verification.py`: the content-aware close-time
  validator (wired as a non-blocking advisory — gate strength deferred to
  S3), the `verificationMode` record reader/writer, the `sN-issues` seeder,
  and the seven-state derivation helper.
- The three round-1 Major findings (validator empty-baseline false
  positive; `advisory-disagreement` mis-classified as terminal; seeder
  accepted a VERIFIED verdict) were all real and fixed with regression
  tests. Cost: $0.2842 routed.

## Session 3 — Workflow, operator-choice, close-out, ship

Closed 2026-06-05 with disposition `completed`. Verdict: `VERIFIED`
(round 1 ISSUES_FOUND, 2 Major + 1 Minor fixed in-flight → round 2
VERIFIED).

- **Workflow doc** (`docs/ai-led-session-workflow.md`): rewrote Lightweight
  verification as **per-set** (L1) with two `verificationMode` modes — Mode
  A (`out-of-band-or-none`, the preserved copyable-prompt flow) and Mode B
  (`dedicated-sessions`). Mode B documents the operator-choice capture, the
  generic typed-session procedure (typed sessions take their step list from
  the workflow doc, not `spec.md`), bounded rounds, re-verify-only-after-
  real-changes, narrow later rounds, remediation-evaluates-the-verification-
  method-first, Critical/Major-non-fix → `awaiting-human`, the seven
  derived states, the Q6 close-out gate, and the operator-initiated
  `second-opinion` tie-breaker (L4).
- **Authoring guide**: `verificationMode` field semantics + once-at-set-
  start capture mechanism and the session `type` values.
- **Code:**
  - `register_typed_session_handoff` — the verification→remediation /
    remediation→re-verification **hand-off close** (atomic close-typed +
    open-next-typed). Solves the carried rule-6 problem (a standalone
    non-terminal typed close would leave `sessions[]` all-complete while
    in-progress). Exposed via the sanctioned `start_session --type …
    --handoff` CLI so non-Python flows stay on a blessed writer.
  - Operator-choice capture: `start_session --verification-mode …` + a
    spec-config `verificationMode:` seed, recorded once at set start and
    **immutable thereafter**.
  - The **Q6 close-out gate** in `close_session`: hard-blocks the
    set-terminal close in an interactive TTY when no different-engine
    verification ran, soft-warns headless / under `--accept-suggestions`;
    fires only on the terminal close. D3 unchanged.
- **End-to-end fixture** test exercising work → verification finds issues →
  remediation → re-verify → terminal close.
- **Release:** `dabbler-ai-router` 0.15.0 → 0.16.0 (`pyproject.toml`,
  `ai_router/__init__.py`, `ai_router/CHANGELOG.md`,
  `docs/repository-reference.md` walk). PyPI publish **held** for
  operator-initiated tag-push `v0.16.0`.
- The two round-1 Major findings (`verificationMode` mutable mid-set, which
  could silently disable the gate; the doc authorizing freehand
  typed-session edits) and one Minor (overlapping `closed-verified` /
  `closed-dispositioned` table rows) were all real and fixed: capture made
  immutable, the freehand guidance replaced with the `--handoff` CLI, the
  states table clarified by latest session type. Cost: $0.3378 routed.

## Cumulative

Routed spend across the set: **$1.0969** (S1 $0.4749 + S2 $0.2842 + S3
$0.3378) of the $10 NTE. Final Python suite: 1164 passed / 1 skipped. One
held release: PyPI `dabbler-ai-router v0.16.0`.
