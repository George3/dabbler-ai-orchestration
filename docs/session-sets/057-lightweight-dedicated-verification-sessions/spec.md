# Lightweight Dedicated Verification Sessions Spec

> **Purpose:** Replace the Lightweight tier's semi-manual copy/paste
> review-prompt step with an optional, bounded **dedicated
> verification-session** workflow: the generating engine plans a per-set
> verification session, the operator runs it on a different engine, and a
> failing verification authors exactly one remediation session so the work
> never silently stops. The design reuses existing artifacts
> (`sN-issues.json`, `disposition.json`, `session-state.json`) rather than
> inventing a parallel vocabulary, and is enforced through a blessed
> writer rather than freehand edits.
> **Created:** 2026-06-05
> **Session Set:** `docs/session-sets/057-lightweight-dedicated-verification-sessions/`
> **Prerequisite:** `055-structured-verification-issue-artifacts` (the
> `sN-issues.json` envelope this set extends; transitively builds on Set
> 048 Lightweight tier and Set 054 `verificationVerdict`).
> **Design input:** `docs/proposals/2026-06-05-lightweight-dedicated-verification-sessions.md`
> (authored by GPT-5.4, Gemini feedback incorporated; Claude review
> 2026-06-05).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
prerequisites:
  - slug: 055-structured-verification-issue-artifacts
    condition: complete
```

> Rationale: this set **builds** Lightweight-tier workflow machinery, but
> the set itself is a full-tier tooling/docs effort (Python helpers +
> schema + workflow docs) verified by cross-provider review. No
> browser-visible UI, no E2E surface. Release only if the packaged
> `ai_router` surface changes (PyPI); no Marketplace bump unless the
> extension is touched (see Q7).

---

## Project Overview

### Motivation

The Lightweight tier (`--no-router`, no metered calls) verifies work today
through **copyable review prompts** the operator pastes into a second AI
assistant, then records a verdict by hand in `external-verification.md`
with only a soft presence gate (`docs/ai-led-session-workflow.md` Step 6,
Lightweight branch). That flow is forgettable, unstructured, and easy to
skip.

The design input proposal (GPT-5.4 + Gemini) replaces it with **dedicated
verification and remediation sessions** governed by a small explicit state
machine. Claude's review (2026-06-05) accepted the workflow logic and the
bounded-loop discipline, and converged with the operator on four
dispositions (below). The remaining forks are narrow and are the S1 audit
agenda.

The non-negotiable design constraint is **consistency, simplicity, and
crystal-clarity for AI engines** — every rule must be followable
mechanically, with a hard stop to a human whenever it cannot be.

### What this set delivers

1. A **per-set** Lightweight verification workflow (one verification
   session after the implementation sessions complete), an optional
   **remediation session** authored by the verifier when issues are found,
   and a bounded re-verification loop.
2. A **minimal, mostly-reused vocabulary**: one new session field
   (`type: work | verification | remediation`), the existing
   `sN-issues.json` `resolution_status` field tightened into a locked
   disposition enum, and a handful of optional finding fields promoted onto
   the shared issue object so both tiers benefit.
3. A **blessed writer** (the existing writer-discipline pattern) that
   creates typed verification/remediation sessions in a single consistent
   way, plus a **content-aware close-time validator** that confirms the
   dedicated-verification path actually ran. (The S1 audit rejected the
   original "extend the D3 check" plan — D3 is content-blind and inert on
   Lightweight; see S1 Audit Lock → Concrete defect.)
4. Workflow + authoring + schema docs made **consistent on per-set
   verification** and the bounded-round rules.

### Non-goals

- **No Full-tier change to verifier selection or inline verification.**
  Full tier keeps automatic, rule-based cross-provider verification.
  Shared-schema additions (`type` defaulting to `work`, the
  `resolution_status` enum, the optional finding fields) are additive and
  backward-compatible there.
- **No new persisted state enum.** The workflow states are *derived* from
  `sessions[]` + verdicts, not stored (see L2/Q3).
- **No resurrection of `issue-logs/` or `session-reviews/`.** Findings stay
  in the root-level `sN-issues.json`.
- **No Explorer/UI rendering of session `type` in this set** (Q7 may defer
  it to a follow-on).
- **No `spec.md` mid-set surgery** unless S1 consensus overrides the
  recommended writer target (Q1).

---

## Pre-locked dispositions (operator + Claude, 2026-06-05)

These enter the S1 audit as decided; consensus stress-tests them but does
not re-open them without a concrete defect.

- **L1 — Per-set verification for Lightweight.** Verification runs **once**,
  after the set's implementation sessions complete (not per work session).
  Rationale: AI-driven sets often finish within a day or an hour, so the
  rework risk of late detection is low, and per-set keeps the state machine
  and operator burden small. **All documentation must be made consistent on
  this** — scrub per-session phrasing from the design input and the
  workflow doc.

- **L2 — Do not reinvent vocabulary; promote to shared schema where useful.**
  The proposal's finding fields and dispositions overlap with the shipped
  `sN-issues.json` envelope. Bind them to what exists: tighten
  `resolution_status` into a shared enum and add the new finding fields as
  optional shared fields (usable by Full tier too). The only genuinely-new
  vocabulary should be a single session `type` field. If something new is
  truly needed for Lightweight, confirm whether Full tier wants it too.

- **L3 — A blessed Python writer enforces consistency.** Verification and
  remediation sessions are created through one forced writer (the existing
  writer-discipline pattern, e.g. a `start_session` `--type` flag), never
  freehand, so structure and placement are identical every time. The
  *write target* is the one open detail (Q1).

- **L4 — Keep the tie-breaker, for Full-tier consistency, but crystal-clear.**
  A third-engine re-verification stays available and reuses Full tier's
  existing `second-opinion` **resolution** (not a new machine state). It is
  **operator-initiated only**, reachable from `awaiting-human`. The rule
  must be unambiguous about who triggers it and when.

---

## Open design questions (S1 audit)

1. **Writer target (L3 detail).** Should the blessed writer create typed
   sessions in the **structured files** (`session-state.json` `sessions[]`
   + seed the `sN-issues.json` envelope) — **Claude's recommendation**,
   because it edits no markdown, adds zero new artifacts, and matches the
   canonical surfaces the Explorer/close-out already read — or insert
   session blocks into `spec.md` markdown as the proposal originally
   suggested? Resolve, with the markdown-fragility and
   surface-minimization trade-offs on the record.

2. **Vocabulary surface (L2 detail).** Confirm `type: work | verification |
   remediation` (default `work`) is the *only* new session field. Lock the
   `resolution_status` enum membership (`fixed`, `not-reproducible`,
   `accepted-risk`, `accepted-consequence`, `advisory-disagreement`,
   `needs-more-context`, `escalate-human`). Decide which promoted finding
   fields (`issueId`, `issueType`, `verificationMethod`,
   `suggestedTestOrCheck`) are required vs optional, and confirm they are
   additive/optional for Full tier.

3. **Derived states (L2/Q3).** Confirm the seven workflow states
   (`work-in-progress`, `awaiting-verification`, `awaiting-remediation`,
   `awaiting-human`, `closed-verified`, `closed-dispositioned`,
   `closed-no-verification`) are **derived** from `sessions[]` + verdicts
   (per the Set 047 derive-top-level rule) and never persisted as a new
   field. Lock the derivation rules.

4. **Tie-breaker shape (L4 detail).** Confirm the tie-breaker is the
   existing `second-opinion` resolution, operator-initiated from
   `awaiting-human`, with no new machine state, and that the wording is
   consistent with the Full-tier adjudication vocabulary.

5. **How `verificationMode` is captured.** Is `dedicated-sessions |
   out-of-band-or-none` a Session Set Configuration flag (opt-in, default
   to current behavior), a start-of-set operator prompt recorded once as a
   `suggestion_disposition` (the Set 048 pattern), or both?

6. **Close-out gate.** When `verificationMode = dedicated-sessions`, does
   `close_session` **hard-block** or **soft-warn** if no verification
   session ran? (Lightweight is `--no-router`; today's `external-verification.md`
   gate is soft.) Lock the gate strength and its TTY/non-TTY behavior.

7. **Extension/Explorer scope.** Defer rendering of the session `type`
   (icon/label for verification/remediation rows) to a follow-on set —
   **Claude's recommendation, to keep this set bounded** — or include a
   minimal surface now?

---

## S1 Audit Lock (LOCKED 2026-06-05)

> Locked from the cross-provider consensus verdict at
> [`docs/proposals/2026-06-05-lightweight-dedicated-verification-sessions/verdict.md`](../../proposals/2026-06-05-lightweight-dedicated-verification-sessions/verdict.md)
> (raw inputs `consensus-gpt-5-4.md` + `consensus-gemini-pro.md`).
> Orchestrator (claude-opus-4-8) excluded from the vote; engines gpt-5-4 +
> gemini-pro. Q1–Q5 + Q7 converged; Q6 split and was operator-decided.
> L1–L4 stand with **one correction to L3's spec mechanism** (Q-defect
> below). Consensus cost $0.2709.

**Q1 — Writer target: STRUCTURED FILES ONLY.** The blessed writer appends a
typed entry to `session-state.json` `sessions[]` and seeds the
`sN-issues.json` envelope for a verification session that finds issues. It
**never mutates `spec.md`**. The authored spec session count is fixed; the
writer grows the **runtime** count by **incrementing `totalSessions`
atomically with each appended typed session** (required — `_build_sessions_array`
truncates/fails-loud against `totalSessions`).

**Q2 — Vocabulary surface.**
- `session.type = work | verification | remediation` (default `work`) is the
  **only** new session field; absent/`work` for existing + Full-tier entries.
- Promoted finding fields use the name **`issueType`** (values
  `deterministic-defect | contingent-risk | standards-departure |
  missing-context`). The four promoted fields (`issueId`, `issueType`,
  `verificationMethod`, `suggestedTestOrCheck`) are **OPTIONAL in the shared
  `sN-issues.json` schema** (additive / Full-tier-safe). The **Lightweight
  dedicated-verification flow** additionally requires `issueId` + `issueType`
  + `verificationMethod` on a verifier-created **open** issue
  (`suggestedTestOrCheck` optional; `description` already required).
- `resolution_status` locked to the enum `fixed | not-reproducible |
  accepted-risk | accepted-consequence | advisory-disagreement |
  needs-more-context | escalate-human`, **validator-enforced when present**
  under a **bumped `sN-issues.json` schemaVersion** (semantics stay
  advisory — no runtime gate reads it — but spelling drift is caught).

**Q3 — Derived states: DERIVED, never persisted.** The seven states are
derived (Set 047 rule) from `sessions[]` + per-session `verificationVerdict`
+ the latest `sN-issues.json` + the `verificationMode` `suggestion_disposition`.
No new persisted field. Canonical derivation ladder is in the verdict (§Q3);
the helper must read the issues envelope + human disposition, not just
`sessions[]` (the `closed-dispositioned` / `awaiting-human` branches require
them).

**Q4 — Tie-breaker: confirm L4 exactly.** The existing Full-tier
`second-opinion` resolution (`verification.settings.on_disagreement` /
`tiebreaker_model`), **operator-initiated only**, reachable from
`awaiting-human`, **no new machine state**.

**Q5 — `verificationMode` capture.** Durable record = the Set-048
`suggestion_disposition` written once at set start (every step reads it); an
**optional** Session Set Configuration `verificationMode` field may seed the
prompt default. **Default when neither present = `out-of-band-or-none`**
(opt-in; preserves current behavior). No `spec.md` mutation, no new derived
field.

**Q6 — Close-out gate: HARD TTY / SOFT non-TTY** *(operator decision —
the engines split)*. When `verificationMode = dedicated-sessions` and no
verification session ran, `close_session` **hard-blocks in an interactive
TTY** (prints corrective action, refuses) and **soft-warns in non-TTY /
headless** (warns, allows close). Matches the established soft posture of
today's `external-verification.md` gate while strengthening the interactive
path. *(S3 implementation detail, not locked here: whether an explicit
override flag such as `--accept-suggestions` may force-bypass the TTY block
should be designed in S3 consistent with the Set-048 gate; it was not part
of the consensus or the operator's Q6 choice.)*

**Q7 — Extension/Explorer: DEFER.** No rendering of session `type` in this
set; land schema + writer + derivation + gate first.

### Concrete defect (L3 mechanism — corrects S2 step 4)

Both engines flagged that **S2 step 4's "extend the `writer-bypass` (D3)
check" is unsound**: D3 is a content-blind mtime-vs-events-ledger check and
is **inert on Lightweight** (no events ledger — the exact tier this feature
targets), so it can never see session `type` or fire on a freehand typed
session. **L3's core stands** (the blessed writer is the real enforcement).
The mechanism is corrected:

- **D3 is left unchanged and NOT extended.**
- Enforcement = (a) the blessed writer as the only sanctioned creator of
  typed sessions, plus (b) a **new content-aware close-time validator** that
  confirms the dedicated-verification path ran (a different-engine
  verification session before terminal close). This validator backs the Q6
  gate. On Lightweight (no ledger) this writer + validator pair is the entire
  enforcement surface.
- **S2/S3 adjustment:** replace S2 step 4 with "add the content-aware
  close-time validator (wired to the Q6 gate)"; drop D3-extension language
  from the deliverables list and S2 steps. No defect in L1, L2, or L4.

---

## Sessions

### Session 1 of 3: Audit & design-lock

**Steps:**
1. Re-verify the current tree: the Lightweight copyable-prompt flow and
   soft `external-verification.md` gate (`docs/ai-led-session-workflow.md`
   Step 6 Lightweight branch); the `sN-issues.json` envelope and
   `resolution_status` field (`docs/session-issues-schema.md`, Set 055);
   the disposition vocabulary (`docs/disposition-schema.md`); the
   `sessions[]` shape and the derive-top-level-from-`sessions[]` rule
   (`docs/session-state-schema.md`, Set 047); the `writer-bypass` (D3)
   check in `ai_router/writer_discipline.py`; and how `start_session`
   writes session entries today.
2. Consolidate the design input: **de-duplicate**
   `docs/proposals/2026-06-05-lightweight-dedicated-verification-sessions.md`
   (it currently contains two concatenated drafts — keep the cleaner second
   draft) and treat it as the proposal of record.
3. Run cross-provider consensus on **Q1–Q7**, feeding L1–L4 as decided
   context (route via a provider different from this orchestrator; persist
   raw output to a UTF-8 file before display).
4. Capture the audit record as a proposal/verdict pair under
   `docs/proposals/` and write the locked design into this spec's
   **S1 Audit Lock** block.

**Creates:** `docs/proposals/2026-06-05-.../verdict.md` (+ raw consensus),
`s1-audit-record.md`.
**Touches:** `spec.md` (S1 Audit Lock block); the design-input proposal
(de-dup).
**Ends with:** a design-locked contract — writer target, vocabulary
surface, derivation rules, gate strength, and `verificationMode` capture
all decided.
**Progress keys:** Q1–Q7 resolved; vocabulary surface locked; writer target
locked; gate strength locked; audit-lock block written.

---

### Session 2 of 3: Schema + forced writer

**Steps:**
1. Add `type: work | verification | remediation` to the session-entry
   schema (default `work`; absent/`work` for existing and Full-tier
   entries). Update `docs/session-state-schema.md` and the v4 invariants.
2. Extend `sN-issues.json` per the S1 lock: promote the optional finding
   fields and tighten `resolution_status` into the locked enum. Update
   `docs/session-issues-schema.md` and the example fixture.
3. Implement the blessed writer at the S1-locked target (recommended:
   `start_session --type verification|remediation`, which appends a typed
   `sessions[]` entry and, for a verification session that finds issues,
   seeds the `sN-issues.json` envelope). Keep it engine-agnostic — plain
   JSON the writer emits, never a Python-import requirement for
   Copilot/Codex/Gemini flows.
4. **(Corrected by S1 audit — was "extend the D3 check".)** Add the
   **content-aware close-time validator** that confirms the dedicated-
   verification path actually ran (a different-engine verification session
   exists before terminal close); wire it to the S3 close-out gate (Q6).
   Leave the `writer-bypass` (D3) check **unchanged** — it is content-blind
   and inert on Lightweight, so it cannot flag freehand typed sessions; the
   blessed writer plus this validator are the enforcement (see S1 Audit Lock
   → Concrete defect).
5. Add the **state-derivation** helper that computes the seven workflow
   states from `sessions[]` + verdicts (derivation only; no persisted
   enum).
6. Tests for the schema additions, the writer, the content-aware close-time
   validator, and the derivation helper.

**Creates:** writer/derivation helper(s), the content-aware close-time
validator, `sN-issues.json` example fixture, tests.
**Touches:** `ai_router/start_session*`, `ai_router/close_session*`,
`docs/session-state-schema.md`, `docs/session-issues-schema.md`.
(`ai_router/writer_discipline.py` is **not** touched — D3 stays unchanged.)
**Ends with:** the typed-session + extended-issue schema, the forced writer,
and the close-time validator, all tests green.
**Progress keys:** `type` field landed; issue schema extended; forced
writer landed; close-time validator landed; derivation helper landed; tests
green.

---

### Session 3 of 3: Workflow, operator-choice, close-out, ship

**Steps:**
1. Rewrite the Lightweight verification section of
   `docs/ai-led-session-workflow.md`: the `verificationMode` operator choice
   (per S1/Q5), the **per-set** verification rule (L1, made consistent
   everywhere), bounded rounds (1–2 automatic, 3+ human), re-verify-only-
   after-real-changes, later-rounds-stay-narrow, remediation-evaluates-the-
   verification-method-first, Critical/Major non-fix → `awaiting-human`,
   and the tie-breaker as the `second-opinion` resolution reachable from
   `awaiting-human` (L4).
2. Update `docs/planning/session-set-authoring-guide.md`: the
   `verificationMode` capture mechanism and the session `type` values.
3. Wire the operator-choice capture and the `close_session` gate strength
   locked in S1 (Q5/Q6).
4. Author an end-to-end fixture that exercises the dedicated-sessions flow
   (work → verification finds issues → remediation → re-verify → close) on
   a throwaway set.
5. Cross-provider verification; version-bump + held release note if the
   packaged `ai_router` surface changed (PyPI tag `v<X.Y.Z>`, held for
   operator-initiated push; no Marketplace bump unless the extension was
   touched); close-out (final session → `change-log.md` required).

**Creates:** workflow fixture; held release note if needed.
**Touches:** `docs/ai-led-session-workflow.md`,
`docs/planning/session-set-authoring-guide.md`, `ai_router/close_session*`,
version files (`pyproject.toml`, `CHANGELOG.md`, CLAUDE.md version walk).
**Ends with:** a documented, consistent, bounded Lightweight dedicated-
verification workflow, verified and closed.
**Progress keys:** workflow doc rewritten (per-set consistent); authoring
guide updated; operator-choice + close gate wired; fixture green; verified;
release note written if needed.

---

## End-of-set deliverables

- One new session field `type: work | verification | remediation` (default
  `work`), documented in `docs/session-state-schema.md`.
- Extended `sN-issues.json`: the locked `resolution_status` disposition
  enum + promoted optional finding fields, in `docs/session-issues-schema.md`
  with a concrete example fixture.
- A blessed writer for typed verification/remediation sessions, a
  **content-aware close-time validator** (replacing the S1-rejected D3
  extension; D3 itself is unchanged), and a state-derivation helper — all
  tested.
- `docs/ai-led-session-workflow.md` and
  `docs/planning/session-set-authoring-guide.md` consistent on **per-set**
  Lightweight verification, the `verificationMode` choice, bounded rounds,
  disposition vocabulary, and the operator-initiated `second-opinion`
  tie-breaker.
- A de-duplicated design-input proposal and an audit proposal/verdict pair
  under `docs/proposals/`.
- A held PyPI release note if the packaged `ai_router` surface changed.
