# Change Log — Set 063: Getting Started budget step + adoption-bootstrap retirement

**Status:** COMPLETE (3 of 3 sessions) — 2026-06-12.
**Release:** extension **0.32.0**, Marketplace-only (no PyPI — no Python
runtime reader of `budget.yaml`; `ai_router/` packaged surface untouched).
Local operator UAT **passed 2026-06-12** on a candidate `.vsix` build;
**publish PENDING the operator's `vsix-v0.32.0` tag push** through the
`require-green-test` gate. Record the publish run id in
`docs/repository-reference.md` once the workflow succeeds.

## Why this set existed

The 2026-06-12 README pass surfaced that the conversational
adoption-bootstrap path's welcome button had been dead UI since Set 060
(the host always ships a `gettingStarted` block, so the webview's welcome
fallback never rendered) and that the only capability the Getting Started
form lacked was the bootstrap flow's Full-tier budget dialog. Operator
decision: give the form the budget step and retire the parallel path —
one onboarding path, one set of docs, no dual-path drift.

## What shipped

### Session 1 — audit & design-lock (VERIFIED, 2 rounds)

- Empirical retirement inventory (11 extension surfaces, file:line),
  unreachability proof + the one type-level resurrection path, and the
  `budget.yaml` contract audit across writers/migrator/readers — the
  post-migration §2.4 shape the form's writer must emit.
- Cross-provider design consult (gpt-5-4 + gemini-pro): D3
  retire-with-redirects CONVERGED; D1 `$0` sub-choice SPLIT, resolved to
  the required inline radio pair (no silent default) per the workflow
  doc's operator-picks zero-budget contract; gemini dissent recorded.
- Locks D1–D4 in `s1-audit.md` §4.

### Session 2 — budget step in, bootstrap path out (VERIFIED, 2 rounds)

- **D1:** pure-TS writer `src/utils/budgetYaml.ts` emitting the audited
  post-migration shape (migrator-no-op + editor-schema-valid, both
  test-asserted); required budget/NTE input in the form's
  Build-project-structure step (Full only; Lightweight OMITS the block
  from the DOM); `$0` reveals the required
  manual-via-other-engine/skipped radio pair; scaffold-time no-clobber
  write; host boundary FAIL-CLOSED (R1 Major fix: un-narrowable riders
  are rejected, never scaffolded budgetless).
- **D2:** all 11 surfaces ripped (command, contribution, viewsWelcome,
  the whole welcome-HTML pipe, `.welcome` CSS, `scanState` context key);
  `gettingStarted` now REQUIRED on `SnapshotPayload`; Marketplace
  description reworded; watcherInventory allowlist bumped same-commit.

### Session 3 — docs sweep, UAT, release (VERIFIED, 2 rounds)

- **D3:** `docs/adoption-bootstrap.md` → URL-stable deprecation/redirect
  stub (≤0.31.0 clients fetch the raw URL at click time — no 404); new
  canonical **`docs/budget-yaml-schema.md`** (post-migration shape +
  provenance-cited legacy-compat table, derived rule marked derived);
  swept ai-led-session-workflow.md, quick-start.md (+ "Without VS Code"
  manual note), both READMEs, repository-reference.md, tier-model.md,
  and two code-comment tense fixes.
- **D4:** 0.31.0 → 0.32.0 (package.json + lock + CHANGELOG);
  repository-reference release status in pre-push wording.
- **UAT:** per-set ad-hoc checklist
  (`063-getting-started-budget-and-bootstrap-retirement-uat-checklist.json`),
  9 operator walks + 5 AI-pre-verified rows — operator passed 14/14 on
  the local build.
- **Unplanned (operator-reported):** consumer `verificationVerdict: null`
  incident root-caused to consumer install lag (router 0.10.0 installed;
  persistence shipped in 0.15.0; canonical 0.18.0 confirmed sound) →
  **`docs/cross-repo-router-version-lag-notice.md`** authored; consumer
  upgraded same day; no code change.

## Verification

Every session cross-provider verified by gpt-5-4 (2 rounds each; every
R1 finding fixed in-flight and persisted to `sN-issues.json` with
resolutions). S3's R1: a Major carried-over-prose error in the new
schema doc, a Minor stale step reference, and a Major evidence gap
(untracked files invisible to `git diff`) — all fixed, R2 VERIFIED.

## Suite baseline at set close

Python 1222 passed + 1 skipped · TS mocha 908 passing + the 2 tracked
pre-existing Set-026 failures · Playwright Layer 3 LOCAL 18 passed
(4.7 m) · drift guard OK.

## Costs

Routed: S1 $0.4983 + S2 $0.3004 + S3 $0.2601 = **≈ $1.0588** for the set.

## Follow-up set candidates

1. **Runtime router-version-lag advisory** — `>=` pins never
   auto-upgrade; consumer venvs silently age (this set's incident). Needs
   offline/fail-open design in the `start_session`/`close_session`
   lifecycle.
2. **Budget-scope selector in the Getting Started form** — operator UAT
   suggestion; `budget.yaml`'s `scope` already supports
   `per-session-set`/`per-session`; the form hard-writes `per-project`
   per the D1 lock.
