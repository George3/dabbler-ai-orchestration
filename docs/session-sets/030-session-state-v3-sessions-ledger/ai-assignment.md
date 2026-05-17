# Set 030 — AI Assignment

> **Status:** Authored at set-creation time (2026-05-17) by Claude
> Opus 4.7 during the spec-authoring conversation. Per memory
> `feedback_ai_router_usage`, the router is reserved for
> end-of-session verification — this file was authored directly by
> the spec-author without router invocation.

---

## Session 1 of 5: Schema doc + `get_progress()` helper + v2-read synthesizer

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Foundation session: gets the schema
doc and the read helper right or every later session inherits the
mistake. Python + TypeScript parity matters; Opus is better than
Sonnet at keeping two-codebase implementations aligned.

### Rationale

The schema doc is the contract that close-out gates, the extension,
and consumer repos all depend on. Errors here are expensive to walk
back. The 8 invariants must be enforceable AND testable; the
synthesizer must handle every shape a v2 state file can take in the
wild. High effort warranted.

### Estimated routed cost

$0.10 – $0.30 (single end-of-session verification with gpt-5-4).

### Constraint reminders

- `feedback_ai_router_route_result_handling`: not invoked this
  session (no router calls beyond verification).
- `project_canonical_schemas_shipped`: schema doc is the canonical
  source of truth.

---

## Session 2 of 5: Phase 2 dual-write writers + scaffolding

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Writer code in `ai_router/` is the
hottest path — a bug here corrupts state. Comprehensive pytest
coverage matters; Opus is right.

### Rationale

Dual-write parity must hold across every transition. Invariant
enforcement (fail loud) is a behavior change consumer repos will
notice immediately. Get this wrong and the next set spends sessions
on hotfixes (per memory `project_026_session1_partial` — that set
had a partial-stop because of a writer-side issue; we don't want to
repeat that pattern).

### Estimated routed cost

$0.10 – $0.30.

---

## Session 3 of 5: Phase 3 reader migration + Explorer label

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Cross-cutting refactor touching many
files in both codebases. The grep audit + lint-rule design needs
careful judgment to avoid both false positives and missed reads.

### Rationale

Reader migration is the load-bearing change that closes the
ambiguity. The grep audit is rote, but the *decision* about
whether each hit is a reader (replace) or a writer (already done in
S2) requires careful reading. Lint rule design balances strictness
vs maintainability.

### Estimated routed cost

$0.10 – $0.30.

---

## Session 4 of 5: Phase 4 stop writing legacy + bulk migrator + release

### Recommended orchestrator

Claude Sonnet 4.6 @ effort=medium. The hard design decisions are
behind us. Session 4 is execution: writers drop legacy emission,
CLI bulk migrator runs, versions bump, packages release.
Sonnet at medium effort is sufficient.

### Rationale

This is the highest-stakes session for *user-visible* impact
(release to PyPI + Marketplace) but the *code complexity* is
modest by this point. Reduce cost by stepping down from Opus where
the decision space is small.

### Estimated routed cost

$0.10 – $0.30.

### Pre-release gates

- All Layer 1/2/3 tests green
- Bulk migrator dry-run shows expected diffs on this repo's 28+
  state files
- Operator confirms before PyPI publish
- Operator confirms before Marketplace publish

---

## Session 5 of 5: Alignment migration UX + loading state

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. UX-sensitive session. The loading
state, migration CTA, and AI-fallback path each have multiple
correctness criteria; Opus catches edge cases (e.g., what if the
scan errors silently? What if a spec.md has no headings at all?).

### Rationale

This is the operator's *first* visible interaction with v3 (every
prior session is internal/behind-the-scenes from their view). The
loading state replaces a long-standing minor irritation; the
migration CTA is the operator's path to fix any state file the
bulk migrator missed. Both must feel right.

### Estimated routed cost

$0.10 – $0.30 verification. Operator-driven AI-fallback usage
(spec-title-extraction) is billed separately as the operator
chooses to use it.

---

## Total set cost forecast

$0.50 – $1.50 across all five sessions (verification only). AI
fallback in S5 is operator-driven and not part of this forecast.

---

## Next-set recommendations

If S5 surfaces consumer-repo state files that need per-repo
attention (e.g., dabbler-homehealthcare-accessdb's Lightweight
tier has unusual hand-edited shapes), a follow-on set could
batch consumer-repo migration. Probably unnecessary if the bulk
migrator's `--strategy interactive` flow handles each in turn.
