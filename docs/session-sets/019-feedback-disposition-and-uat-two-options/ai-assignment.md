# Set 019 Session 1 — AI Assignment

**Status:** Authored 2026-05-11; awaiting operator approval before any edits.

**Scope** — disposition-gate discoverability. Three concrete fixes
in response to `dabbler-platform`'s
[upstream-feedback-disposition-gate.md](../../../../dabbler-platform/docs/session-sets/admin-users-cross-links/upstream-feedback-disposition-gate.md):

1. A canonical schema doc at `docs/disposition-schema.md`.
2. Step 8 of `docs/ai-led-session-workflow.md` names
   `disposition.json` explicitly and links to the schema doc.
3. Both `CloseoutGateFailure` / `invalid_invocation` messages in
   `ai_router/close_session.py` link to the schema doc and inline
   the required-field list.

`--write-template` is **deferred** per operator decision
2026-05-11. Recorded in `change-log.md` at session close as a
follow-up candidate.

The UAT two-options split and the W0-runner upstream-feedback file
are **Session 2**, not this session.

---

## 1. Findings (from prerequisite reads)

### 1a. `Disposition` dataclass surface

[ai_router/disposition.py](../../../ai_router/disposition.py)
defines `Disposition` with seven fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `str` | always | One of `DISPOSITION_STATUSES` (`"completed"`, `"requires_review"`, `"in_progress"`, `"blocked"`, plus the others enumerated in the module). |
| `summary` | `str` | always | One-paragraph human description; lives in `change-log.md` first paragraph in practice. |
| `files_changed` | `List[str]` | always | Paths created/modified during the session. |
| `verification_method` | `str` | always | `"api"` (synchronous, outsource-first) or `"queue"` (outsource-last) or other entries in `VERIFICATION_METHODS`. |
| `verification_message_ids` | `List[str]` | conditional | Non-empty **iff** `verification_method == "queue"`. Empty for `"api"`. |
| `next_orchestrator` | `Optional[NextOrchestrator]` | conditional | **Required when `status == "completed"` AND the session is not the final session of the set.** Specifies who runs the next session and a reason code. |
| `blockers` | `List[str]` | conditional | **Non-empty when `next_orchestrator.reason.code == "switch-due-to-blocker"`.** Empty otherwise (best practice). |

Three fields the feedback file flagged as "non-obvious semantics
an orchestrator without docs can't guess correctly" —
`verification_method`, `next_orchestrator`, `blockers` — are exactly
the three conditional fields. The new schema doc must give each one
explicit treatment with an example.

### 1b. Current error-message sites (two of them)

- **[ai_router/close_session.py:670-688](../../../ai_router/close_session.py#L670-L688)** — `run_gate_checks()` synthesizes a `GateResult(check="disposition_present", passed=False, remediation=...)` when the file is absent. This is the gate surface that `mark_session_complete()` calls. The text is:
  > `"disposition.json is required for close-out — write it before calling mark_session_complete (or pass force=True to bypass the gate; incident-recovery use only)."`

- **[ai_router/close_session.py:1304-1311](../../../ai_router/close_session.py#L1304-L1311)** — `run()` CLI flow, the `disposition is None and not args.force` branch. Sets `result = "invalid_invocation"` with the text:
  > `"disposition.json is required (or pass --force to bypass; incident-recovery use only — see ai_router/docs/close-out.md Section 5)"`

Both messages get the same improvement: file path, required-field
list, schema doc link, preserved `--force` clause.

### 1c. Current Step 8 of `docs/ai-led-session-workflow.md`

Lines 1099–1126. The current text names commit/push,
`close_session`, and the notification — and explicitly says the
script "writes idempotent state" — but **never says
`disposition.json`** in prose. The feedback's exact diagnosis: an
orchestrator reading Step 8 with no prior knowledge of the gate
has no signal that authoring `disposition.json` is a Step 8
deliverable.

### 1d. Test sites asserting the existing error strings

To be confirmed by Grep at execution time. The test files that
plausibly cover this:

- [ai_router/tests/test_close_session_session4.py](../../../ai_router/tests/test_close_session_session4.py) — most likely site for `mark_session_complete` ↔ gate interaction tests.
- [ai_router/tests/test_close_session_skeleton.py](../../../ai_router/tests/test_close_session_skeleton.py) — covers the CLI `invalid_invocation` path.
- Possibly [ai_router/tests/test_close_session_integration.py](../../../ai_router/tests/test_close_session_integration.py).

The first edit step will be a grep across `ai_router/tests/` for
the literal strings `"disposition.json is required"` and
`"disposition_present"`; every match gets its matcher updated.

### 1e. Existing schema-adjacent docs

No `docs/disposition-schema.md` exists today (verified via Glob).
[ai_router/docs/close-out.md](../../../ai_router/docs/close-out.md)
exists and is referenced by the second error message; it's the
operator-facing close-out CLI reference, not a disposition schema.
A new top-level `docs/disposition-schema.md` is the right place —
discoverable from the workflow doc and from error messages,
parallel to `docs/ai-led-session-workflow.md`.

---

## 2. Edit plan (concrete)

All edits are local to this repo. **No version bump, no VSIX
rebuild** — the extension does not read disposition or close-out
state mechanically beyond the snapshot, which is unchanged.

### 2a. New file: `docs/disposition-schema.md`

Target ~150 lines. Sections in order:

- **Purpose** (one paragraph) — what disposition is, when it's
  written, who writes it, who reads it.
- **When to author** — the canonical place is Step 8 of
  `ai-led-session-workflow.md`, before `python -m
  ai_router.close_session` runs. The gate validates presence; the
  schema validates shape.
- **File location** — `docs/session-sets/<slug>/disposition.json`.
- **Fields table** — every field, type, required-conditions, a
  one-line example.
- **Invariants the gate enforces** — three explicit rules:
  1. `verification_method` ↔ `verification_message_ids` empty/non-empty pairing.
  2. `status == "completed"` AND not final session ⇒ `next_orchestrator` required.
  3. `next_orchestrator.reason.code == "switch-due-to-blocker"` ⇒ `blockers` non-empty.
- **Minimal viable template** — copy-paste JSON for the common
  case (outsource-first, status: completed, mid-set continuation).
- **Common variations** — examples for outsource-last (queue
  method with message ids), `status: "blocked"`, and the
  `is_final_session: true` case (no `next_orchestrator`).
- **Reference** — pointer to [ai_router/disposition.py](../../../ai_router/disposition.py) as the authoritative source; the doc rephrases the dataclass but doesn't re-derive validation logic.
- **`--force` is not a substitute** — short paragraph: `--force`
  bypasses the gate for incident recovery and emits a
  `closeout_force_used` event with the operator's reason. Routine
  closeouts must author `disposition.json`.

### 2b. Edit Step 8 of `docs/ai-led-session-workflow.md`

Target site: lines 1099–1126 (the prose introduction to Step 8).
Replace the third sentence ("It does **not** run git commit /
push / notification …") with an expanded version that:

1. Names `disposition.json` as a Step 8 author-deliverable, before
   `close_session` runs.
2. Links to `docs/disposition-schema.md`.
3. Flags `next_orchestrator` and `blockers` as the two
   most-frequently-missed fields — `next_orchestrator` is required
   when the session is not the last and status is `completed`;
   `blockers` is required when the reason code is
   `switch-due-to-blocker`.
4. Keeps the existing pointer to `ai_router/docs/close-out.md`
   Section 1 for the ownership contract; the new schema doc is the
   *what* the operator authors, close-out.md is the *how* of
   invoking close_session.

Target net delta: +12 lines, -1 line.

### 2c. Edit `ai_router/close_session.py` — Site 1 (gate)

Replace the remediation string at
[ai_router/close_session.py:677-681](../../../ai_router/close_session.py#L677-L681) with (line-wrapped for the source code):

```python
remediation=(
    "disposition.json is required for close-out at "
    "<session_set_dir>/disposition.json. Required fields: "
    "status, summary, verification_method, files_changed, "
    "next_orchestrator (when status='completed' and not the "
    "final session), blockers (when reason='switch-due-to-"
    "blocker'). Schema: docs/disposition-schema.md (or the "
    "Disposition dataclass in ai_router/disposition.py). "
    "Pass force=True to bypass — incident-recovery only; "
    "emits closeout_force_used event."
),
```

`<session_set_dir>` is a placeholder string in the message, not an
f-string substitution — the gate runs before the caller resolves a
path. The schema-doc relative path is what an orchestrator can
search for in the repo.

### 2d. Edit `ai_router/close_session.py` — Site 2 (CLI)

Replace the message at
[ai_router/close_session.py:1306-1311](../../../ai_router/close_session.py#L1306-L1311) with:

```python
outcome.messages.append(
    "disposition.json is required at <session-set-dir>/"
    "disposition.json. Required fields: status, summary, "
    "verification_method, files_changed, next_orchestrator "
    "(when status='completed' and not the final session), "
    "blockers (when reason='switch-due-to-blocker'). "
    "Schema: docs/disposition-schema.md "
    "(or the Disposition dataclass in ai_router/disposition.py). "
    "Pass --force to bypass — incident-recovery use only; see "
    "ai_router/docs/close-out.md Section 5."
)
```

### 2e. Update test string matchers

Grep across `ai_router/tests/` for occurrences of:
- `"disposition.json is required"`
- `"disposition_present"`
- `"incident-recovery"` (in disposition-related contexts)

For each match, update the assertion to match the new prefix
("disposition.json is required for close-out at …" or
"disposition.json is required at …"). Most matchers should be
relaxed to a substring check on a stable phrase
(`"disposition.json is required"` + a schema-doc reference fragment
like `"docs/disposition-schema.md"`) so future minor wording tweaks
don't require test churn.

### 2f. Smoke test (manual; no scratch artifacts committed)

Create a temporary scratch directory; do not commit it. Run:

```
python -m ai_router.close_session --session-set-dir <scratch>
```

Confirm the new `invalid_invocation` message renders with the
schema-doc link and the required-field list. Discard the scratch
dir.

### 2g. Close-out artifacts (Session 1 only — set stays open)

- `docs/session-sets/019-feedback-disposition-and-uat-two-options/session-reviews/session-001-prompt.md` — verification prompt template for the eventual end-of-set verifier (Session 2 owns the actual route).
- `session-state.json` snapshot updates (Session 1 → closed; Session 2 pending).
- `session-events.jsonl` lifecycle events.
- **No `change-log.md` yet** — that's authored at end-of-set in Session 2.
- **No `disposition.json` yet** — same; final disposition is end-of-set in Session 2.
- Git commit of the Session 1 deliverables. **Do not push** until end-of-set, so the whole Set 019 lands as a coherent unit. (Or push after Session 1 if the operator prefers — flag the choice in the action checklist.)
- **No router routes** — Session 1 has zero metered cost.

---

## 3. Risk callouts

- **Test churn.** Test files asserting the old string verbatim
  will fail until the matchers are updated. Mitigation: relax to
  substring matchers on stable phrases as part of the same diff;
  fast-fail test feedback loop (run `pytest` immediately after
  the source edit).
- **Two error-text sites drifting apart over time.** Sites 1
  (gate) and 2 (CLI) carry the same intent but slightly different
  wording today, and the edits keep them similar but not
  identical. Mitigation: not worth deduping into a module-level
  constant — the two contexts are real (one is a `GateResult`
  remediation surfaced in lists alongside other gate failures;
  the other is a top-level `invalid_invocation` message). A
  future cleanup could DRY them, but the spec's scope is "make
  the messages discoverable", not "refactor the error surface."
- **Schema doc + dataclass drift.** Authoring a separate
  `docs/disposition-schema.md` creates a doc that must stay in
  sync with `Disposition` in code. Mitigation: the doc explicitly
  names the dataclass as the authoritative source and rephrases
  it rather than re-deriving validation. Future field additions
  must update both the dataclass and the doc; that ordering rule
  goes into the doc itself.
- **`<session-set-dir>` placeholder confuses the reader.** The
  gate runs in a context where the path *is* known
  (`session_set_dir` is the function argument), but the remediation
  string is generated before the caller decides how to format it.
  Mitigation: the placeholder convention (`<session-set-dir>`) is
  visibly a placeholder. If the operator prefers, the message can
  be parameterized with the actual path at the gate level — that
  changes the gate function signature slightly and is a small
  bonus polish, flagged below.
- **Bonus polish, opt-in:** make the remediation message
  parameterized so the actual `session_set_dir` substitutes for
  `<session-set-dir>`. ~5 lines + 1 test. I'd recommend doing
  this — it's small enough that the cost is genuinely trivial
  and the gain (an orchestrator's error message names the exact
  path) is real. Flagging here so the operator can include or
  exclude in the action checklist.

---

## 4. Out of scope (Session 1)

- **`uatStyle` field, UAT rule split, authoring-guide edits.** Session 2.
- **`docs/upstream-feedback/...` file for W0 runner.** Session 2.
- **Wizard prompt edits in the extension.** Session 2 (and only
  if the wizard's session-gen prompt enumerates config-block
  fields — check first).
- **`--write-template` flag.** Deferred per operator decision.
  Recorded in `change-log.md` at end-of-set as a follow-up
  candidate.
- **Reference from `ai_router/docs/close-out.md` to the new
  schema doc.** That file already references the gate's failure
  modes; the back-link can land in Session 2 or a follow-up. Not
  Session 1's deliverable.
- **Cross-provider verification of the doc edits.** Session 1 has
  no router routes. End-of-set verification is Session 2's job
  per the spec.

---

## 5. Acceptance criteria for Session 1

- [ ] `docs/disposition-schema.md` exists; documents all seven fields, three invariants, minimal viable template, three variation examples.
- [ ] `docs/ai-led-session-workflow.md` Step 8 names `disposition.json` in prose and links to the schema doc; flags `next_orchestrator` and `blockers` as the most-frequently-missed fields.
- [ ] `ai_router/close_session.py` lines ~677-681 and ~1306-1311 — both messages link to the schema doc and name the required-field list.
- [ ] `python -m pytest ai_router/tests/` green.
- [ ] Smoke test: `python -m ai_router.close_session --session-set-dir <scratch>` (no `disposition.json` present) renders the new message text with the schema-doc reference.
- [ ] Session 1 close-out artifacts authored (session prompt, snapshot, events). Git commit.
- [ ] **Set 019 stays open.** Session 2 follows on a later turn.

---

## 6. Decisions still open (waiting on operator)

1. **`<session-set-dir>` placeholder vs parameterized path** —
   2c/2d use a literal placeholder; the alternative is to
   parameterize the gate's remediation message with the actual
   path. Recommendation: **parameterize**. ~5 extra lines, real
   value for orchestrators that copy the error into a doc search.
2. **Push after Session 1, or hold for end-of-set?** Recommendation:
   **hold** — Set 019 lands as one coherent unit. Operator can
   override if they want intermediate visibility on the disposition
   fixes.

---

**Awaiting operator approval. After approval, edits land in the
order 2a → 2b → 2c → 2d → 2e (with the test grep first inside 2e)
→ 2f (smoke test) → 2g (close-out artifacts).**
