# Set 063 Session 3 — close-out narrative (final session)

> **Session:** 3 of 3 (`063-getting-started-budget-and-bootstrap-retirement`)
> **Date:** 2026-06-12
> **Orchestrator:** Claude Code (`claude-fable-5`, effort high) — operator's
> choice, deviating from the ai-assignment Codex recommendation.
> **Verdict:** VERIFIED (round 2; round 1 found 3 issues, all fixed in-flight).

## What closed

- **D3 (docs disposition, consult-converged lock):** `docs/adoption-bootstrap.md`
  → URL-stable deprecation/redirect stub; **new
  `docs/budget-yaml-schema.md`** is the canonical budget.yaml contract
  (post-migration shape + provenance-cited legacy-compat table, derived
  rule marked as derived); all seven referencing docs swept; two code
  comments re-pointed (comment-only).
- **D4 (release scope):** Marketplace-only **0.31.0 → 0.32.0**
  (package.json + lock both nodes + CHANGELOG). **No PyPI bump.**
  repository-reference in pre-push wording; **publish awaits the
  operator's `vsix-v0.32.0` tag push through `require-green-test`** —
  record the run id in repository-reference post-publish.
- **UAT (pre-publish gate):** per-set ad-hoc checklist, 14/14 rows
  passed by the operator on a local candidate `.vsix` (9 walks + 5
  AI-pre-verified rows). Editor's blank `IsOtherItem` placeholders
  removed from the saved record.
- **Unplanned (operator-reported):** consumer `verificationVerdict: null`
  incident root-caused to **consumer install lag** (router 0.10.0
  installed; persistence shipped in 0.15.0; canonical 0.18.0 confirmed
  sound — this set's own S1/S2 verdicts persisted). Deliverable:
  `docs/cross-repo-router-version-lag-notice.md`. Consumer upgraded to
  0.18.0 same day; no code change.

## Verification rounds

- **R1 (gpt-5-4, $0.2496): ISSUES_FOUND** — (1) Major Correctness:
  schema-doc example comment inherited the retired doc's "ai_router uses
  budget.yaml for spend reporting" claim, contradicting its own Readers
  section → rewritten; (2) Minor Correctness: notice said "step 4" after
  a mid-session section insert renumbered the habit to step 5 → fixed;
  (3) Major Completeness: the three new files were untracked, so the R1
  `git diff --stat` evidence could not substantiate them → `git add`ed,
  evidence regenerated. Resolutions annotated in `s3-issues.json`.
- **R2 (gpt-5-4, $0.0105): VERIFIED** — narrow re-verify, no new issues.

## Costs

Routed this session **$0.2601**; set cumulative **≈ $1.0588**
(S1 $0.4983 + S2 $0.3004 + S3 $0.2601).

## Follow-up set candidates (for the operator's backlog)

1. **Runtime router-version-lag advisory** — `>=` pins never
   auto-upgrade; a lifecycle advisory needs offline/fail-open design
   (see the notice's "Why no automated guard" section).
2. **Budget-scope selector in the Getting Started form** — operator
   UAT walk-2 suggestion (total-project vs. windowed budgets);
   `budget.yaml`'s `scope` field already supports
   `per-session-set`/`per-session`; the form hard-writes `per-project`
   per the D1 lock.

## Lessons observed (for Step 9 consideration)

- **Carried-over prose is a defect class:** a canonical doc authored to
  replace a retired one inherits the old doc's claims verbatim at its
  peril — R1's Major was exactly such a sentence. Grep the new doc for
  claims of *current* behavior and re-verify each against code.
- **`git diff` evidence omits untracked files** — a verification prompt
  citing diffstat as "the whole change set" must `git add` new files
  first (or include `git status --short`).
