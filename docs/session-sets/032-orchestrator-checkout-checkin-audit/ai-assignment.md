# Set 032 — AI Assignment

> **Status:** Authored at end of Session 1 (2026-05-19) by Claude
> Opus 4.7 (1M context) as the close-out next-orchestrator pointer
> required by the `check_next_orchestrator_present` gate. Captures
> the locked verdicts that drive Session 2's spec-drafting work.

---

## Session 1 of 2: Audit resolution (CLOSED 2026-05-19)

### Locked verdicts (all 6 resolved via cross-engine consensus)

| Item | Verdict | Cross-provider state |
|---|---|---|
| **H1** Writer authority | Router-only writes; hooks become invokers | Both engines confirmed |
| **H2** Single source of truth | `session-state.json` canonical; `.dabbler/orchestrator.json` RETIRED | Both engines confirmed |
| **H3** Hard vs. advisory | Hard coordination at write time + explicit operator override (refusal error names holder + release paths) | Both engines confirmed |
| **H4** Holder identity key | `engine + provider` composite | Gemini refined → composite; GPT permitted any stable subset; operator adjudicated 2026-05-19 |
| **OQ1** Field merge | Merge into existing `orchestrator` block; +2 nested fields (`checkedOutAt`, `lastActivityAt`) | Both engines confirmed |
| **OQ2** Events as types or aliases | Aliases — no ledger schema change | Both engines confirmed |

Full reasoning at
[`docs/proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md`](../../proposals/2026-05-19-orchestrator-tracking-architecture/proposal-addendum.md)
§9. Source response files in the same directory:
`audit-resolution-{gemini-pro,gpt-5-4,h4-gemini-pro}.txt`.

### Session 1 costs

- Audit Gemini Pro call: $0.008
- Audit GPT-5.4 call: $0.000 (429 → manual paste; pre-audit pattern repeated)
- H4 follow-up Gemini Pro: $0.004
- Round A verification: $0.013
- Round B verification: $0.019
- **Session 1 routed spend: ~$0.044** of $1.00 set NTE

---

## Session 2 of 2: Draft Set 033 implementation spec + close-out

### Recommended orchestrator

**Claude Opus 4.7 @ effort=medium.**

### Rationale

Session 2's primary deliverable is the Set 033 implementation
`spec.md` — a 6-session implementation plan that authors a spec
from the 6 locked verdicts above. The decisions are made; the work
is structured composition: translating verdicts into per-session
Steps / Creates / Touches / Ends-with / Progress-keys, then
cross-provider review for sequencing/dependency mistakes.

This is structurally similar to drafting the canonical spec
template plus cross-reading the locked addendum sections — Opus
keeps the spec's internal references coherent (per-session
dependencies, file paths, test layer references, RR identity-key
rule from H4 threading through start_session + multi-set
rendering + Playwright tests). Medium effort is right: the
verdicts close all design questions, so the work is execution-
style, not high-effort design.

A consensus-call to Gemini Pro on the drafted spec (cost capped
at $0.15 per spec) catches sequencing mistakes before Set 033
starts. GPT-5.4 manual paste only if Gemini flags must-fix items
that warrant a second opinion.

### Per-session split for Set 033 (verdict-driven)

Per the Set 032 spec's Session 2 step 2:

- **S1** state machine in `session-state.json` + `start_session`
  refactor (hard-coordination refusal + `--force` override; refusal
  error names holder + release paths per H3)
- **S2** per-set marker retirement (H2 verdict) + resolver refactor
  (`resolveActiveSet()` → `listInProgressSets()`, multi-set rendering)
  + banner removal
- **S3** UI rename (`dabbler.setOrchestrator` →
  `dabbler.checkOutOrchestrator`) + ActionRegistry update + Command
  Palette "Release Check-Out" action
- **S4** Playwright tests for multi-set rendering + check-out
  conflict scenarios
- **S5** queueing / polling feature (second orchestrator detects
  held check-out, offers poll/abort/force-override)
- **S6** cross-tier check-in on `close_session` (Lightweight + Full)
  + cross-repo CLAUDE.md notifications + workflow-doc
  within-set-sequential invariant + PyPI release

Session 2 authoring may resize the per-session split during
drafting — that's expected (the spec's Risk R2 acknowledges this).
