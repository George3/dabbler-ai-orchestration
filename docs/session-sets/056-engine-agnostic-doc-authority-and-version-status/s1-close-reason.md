Set 056 Session 1 (1 of 2) close-out — Audit & design-lock.

Session 1 completed the audit-only half of the set. Its central finding:
the substantive migration this set was scoped to deliver in Session 2
was already applied **out of band** by the operator in commit `e5a3476`
("misc fixes to guidance."), BEFORE this audit ran, while
`session-state.json` still showed both sessions `not-started`. Session 1
therefore became **audit-and-ratify** the committed migration, lock the
contract, and supply the decision trail that out-of-band edit lacked.

Authoritative record: `s1-audit-record.md`, summarized in `spec.md` →
`S1 Audit Lock`.

The locked documentation-authority contract:

- Shared operational facts a future orchestrator/human needs live in an
  engine-agnostic doc (`docs/…`) or canonical package metadata — never
  *only* in `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`.
- `docs/repository-reference.md` → `Documentation authority and release
  status` is the single canonical home for the consumer table, release
  status, and the concise recent version walk.
- Root engine files carry only concise stable bootstrap facts plus a
  pointer; no independent version history. A short consumer table may be
  duplicated for convenience, with the canonical copy authoritative.
- Live planning/review docs cite the engine-agnostic source, not
  `CLAUDE.md`.

All four open design questions resolved to their *recommended* option,
which is exactly what `e5a3476` implemented — no design reversal.

Migration verified complete and faithful: the canonical section exists;
all three engine files point to it with the version walk removed;
AGENTS.md's stale v0.8.0 `Extension versioning` block (the
19-versions-behind drift that motivated the set) is gone; the principle
is recorded in `docs/planning/project-guidance.md`; and a repo-wide grep
finds no live straggler treating an engine file as the canonical source
of shared facts (only this set's `spec.md` and one historical closed-set
artifact, which is an explicit non-goal to rewrite).

Verification: API path. A cross-provider end-of-session verification via
`gemini-2.5-pro` (a different provider from this claude/anthropic
orchestrator) returned `VERIFIED_WITH_NOTES`; all four claim-checks held
`true` and the contract was judged sound. Raw output: `s1-verification.md`.
The two findings were dispositioned in-flight:

- IMPORTANT "Incomplete centralization" (CLAUDE.md carries richer shared
  content than AGENTS.md/GEMINI.md) — ACKNOWLEDGED, OUT OF SCOPE per the
  set's explicit non-goal; the named sections already point to
  engine-agnostic canonical docs, so they are not sole-sourced. Recorded
  as a follow-on candidate (a systematic shared-fact sweep set).
- NICE-TO-HAVE consumer-table header drift (`ai_router` vs `ai_router
  copy`) — accepted into Session 2 residual scope.

Session 2 is a thin validation + close pass: align the consumer-table
header across the three engine files, markdown render check, final grep
sweep, write `change-log.md`, and flip the set to complete. No code, no
release.
