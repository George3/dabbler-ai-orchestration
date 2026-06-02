# Proposal — Structured Verification Issue Artifacts

> **Set:** `055-structured-verification-issue-artifacts`, Session 1
> **Created:** 2026-06-02
> **Author:** GitHub Copilot (GPT-5.4)
> **Status:** Recommended dispositions for cross-provider consensus, then lock.

This proposal records the **re-verified diagnosis** and a **recommended
disposition for each open S1 question** in
`docs/session-sets/055-structured-verification-issue-artifacts/spec.md`.
It is the input to the Session-1 cross-provider consensus; the locked
design lives in `verdict.md` and the scope-lock block appended to the
set spec.

---

## 1. Re-verified diagnosis (fresh against current code, 2026-06-02)

All three root-cause layers in the spec's Motivation hold against the
current tree.

**Layer 1 — the structured issue list already exists at verification time.**
`ai_router/verification.py:parse_verification_response()` returns
`(verdict, issues)` where `issues` is a list of plain dicts. Each parsed
issue always carries `description` and may also carry `category` and
`severity`; if the verifier returned `ISSUES_FOUND` prose but no
structured `Issue:` sections, the parser falls back to a single issue
dict with `category: "unknown"` and `severity: "unknown"`.

That means this set is wiring a **real, already-computed in-memory
structure** to disk; it is not inventing new classification logic.

**Layer 2 — the live workflow preserves prose only.** Recent modern sets
in this repo use root-level verification narratives (`sN-verification.md`)
and close-out handoff (`disposition.json`), but no canonical structured
issue artifact:

- `docs/session-sets/052-cost-metrics-icon-redesign/`
- `docs/session-sets/053-ci-agnostic-schema-drift-enforcement/`

Both directories contain `sN-verification.md` and `disposition.json`, but
no `sN-issues.json` equivalent. The current artifact contract therefore
preserves the verifier's prose, not the issue list the verifier parser
already computed.

**Layer 3 — the only built-in durable structured sink is the legacy
SessionLog helper.** `ai_router/session_log.py` still scaffolds
`issue-logs/` in `SessionLog.__init__()` and writes raw issue arrays via
`save_issue_log(session_number, issues)` to
`issue-logs/session-<N>.json`. That helper is explicitly outside the
modern canonical workflow and is Python-only scaffolding — exactly the
coupling this set is meant to avoid reviving.

**Load-bearing shape finding — the parser output is intentionally loose.**
The current issue objects are not a strict enum schema:

- `description` is the only reliable required field.
- `category` and `severity` may be absent.
- fallback parsing may emit the literal string `"unknown"` for either.

That means the v1 artifact contract should preserve the verifier fields
verbatim and avoid over-normalizing them into a more rigid schema than
the parser actually guarantees.

---

## 2. Data-path map (verification -> durable issue artifact)

```text
Step 6 verification:
  route()/verify() -> raw verifier prose
  parse_verification_response(raw) -> ("VERIFIED"|"ISSUES_FOUND", issues[])
                                                |
                                                v
  VerificationResult.issues (in memory only)
                                                |
                                                v
  NEW: write root-level sN-issues*.json only when issues[] is non-empty
                                                |
                                                v
  keep disposition.json as the close-out handoff, not the long-lived
  per-round findings archive
```

The key design choice is that the new artifact should persist the parsed
issue list **beside** the existing verification narrative, not embed it
into `disposition.json` and not route it back through the legacy
`issue-logs/` folder.

---

## 3. Recommended dispositions (open S1 questions)

### Q1 — Filename convention and round semantics

**Disposition: one file per findings-bearing verification round, never
overwrite.**

- Round 1 findings -> `sN-issues.json`
- Round 2 findings -> `sN-issues-round-2.json`
- Round 3 findings -> `sN-issues-round-3.json`

The unsuffixed file is therefore a shorthand for the first verification
round only, not a moving "latest issues" pointer. This keeps file naming
aligned with the existing root-level `sN-*` artifact style and avoids
history loss.

### Q2 — Top-level JSON shape: envelope vs raw array

**Disposition: use a small envelope, not a bare top-level issue array.**

Recommended v1 shape:

```json
{
  "schemaVersion": 1,
  "sessionNumber": 1,
  "verificationRound": 1,
  "verificationVerdict": "ISSUES_FOUND",
  "issues": [
    {
      "description": "...",
      "category": "...",
      "severity": "..."
    }
  ]
}
```

Why the envelope is worth the few extra bytes:

- gives the artifact its own evolution point (`schemaVersion`)
- makes the file self-describing off-path (`sessionNumber`, round)
- preserves the verifier verdict explicitly without consulting another
  artifact
- leaves the `issues` list untouched and easy to query

### Q3 — Issue object contract and resolution fields

**Disposition: preserve verifier issue fields verbatim and allow additive
orchestrator-side resolution fields, omit-null.**

Required / verifier-originated field:

- `description: string`

Optional verifier-originated fields:

- `category?: string`
- `severity?: string`

Optional orchestrator-originated fields:

- `resolution_status?: "open" | "fixed" | "dismissed" | "deferred"`
- `resolution_notes?: string`
- `resolved_in_round?: number`

Two important constraints:

1. Session 2 should **not rewrite** parser output into stricter enums for
   `category` / `severity`; absent values and the literal `"unknown"`
   must both remain valid.
2. The orchestrator fields are genuinely optional. A freshly-written
   artifact from the verifier path may carry no resolution fields at all.

### Q4 — Clean later rounds

**Disposition: no empty issue file for a VERIFIED round.**

Only findings-bearing rounds get `sN-issues*.json`. The clean round is
already preserved by the verification narrative and the close-out
hand-off. Writing an empty JSON file would add another artifact without
new information and would blur the invariant that the presence of an
issues file means "a verifier actually found issues in this round."

### Q5 — Manual / `--no-router` flows

**Disposition: allow hand-authored issue artifacts when structured
findings exist, but do not require them.**

If a human or `--no-router` flow produced a structured issue list, it may
persist the same envelope shape manually. If the review exists only as
prose, the workflow does not invent issue JSON after the fact.

This keeps the artifact engine-agnostic without pretending every manual
review has machine-readable structure.

### Q6 — Helper surface

**Disposition: no required helper. Prefer docs + example fixture first.**

The writing logic is intentionally small: choose the filename, wrap the
issues list in the envelope, dump JSON. A helper is acceptable only if
Session 2 finds real duplication worth centralizing, and then only under
these rules:

- convenience only, never a required dependency for Copilot/Codex/Gemini
  workflows
- no hidden parsing or routing behavior
- no runtime reader/gate coupling

The default recommendation is therefore **docs-first, helper-optional**.

### Q7 — Runtime readers and close-out behavior

**Disposition: no runtime readers in this set.**

`close_session`, gate checks, metrics, and the Explorer should continue
to ignore `sN-issues*.json` in Set 055. This set is about durable
persistence and documentation, not state transitions or UI behavior.

### Q8 — Release impact

**Disposition: release only if Session 2 ships Python code.**

- If Session 2 lands only docs/schema/example fixtures, there is no PyPI
  or Marketplace release work.
- If Session 2 adds a small `ai_router` helper, that is a PyPI-side
  change only; the extension remains untouched.

This keeps release discipline proportional to actual shipped runtime
surface.

---

## 4. Locked implementation list if consensus agrees

**Session 2 should ship:**

- a canonical schema/example for the `sN-issues*.json` envelope
- workflow docs updated to name the root-level artifact and explicitly
  keep `issue-logs/` retired
- at least one concrete example fixture proving the shape is real
- optional helper only if it removes real duplication without becoming a
  required workflow dependency

**Session 2 should not ship:**

- runtime readers or gate dependencies
- Explorer/UI surfaces
- `disposition.json` embedding of the full issue array
- historical backfill of older sets
- any restoration of nested `issue-logs/`

---

## 5. Open points to pressure-test in consensus

The strongest places to challenge this proposal are:

1. **Envelope vs raw array.** Is `schemaVersion/sessionNumber/round` worth
   the additional wrapper, or is a plain list the more durable minimal
   contract?
2. **Resolution fields in v1.** Are optional orchestrator-side
   resolution fields genuinely useful now, or should v1 stay pure
   verifier output only?
3. **Helper default.** Is "docs-first, helper-optional" the right scope,
   or is the filename/envelope write path important enough to centralize
   immediately?

Those are the only places where the current recommendation risks either
over-designing the artifact or under-serving future automation.