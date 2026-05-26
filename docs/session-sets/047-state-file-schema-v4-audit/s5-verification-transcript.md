**ISSUES_FOUND**

## Critical
- None.

## Important
- **Issue** → `parsePrerequisites()` treats a present-but-unparseable `condition:` line as if the field were omitted, so it silently defaults to `"complete"` instead of dropping the entry. That violates spec §3.3’s “unknown condition entries are dropped” contract and can produce a false `[BLOCKED BY PREREQS]` badge. It also drops otherwise-valid entries when `slug:` carries an inline comment.  
  **Location** → `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts:221-264`  
  **Fix** → Parse each list item line-by-line, strip trailing YAML comments from scalar values before matching, and distinguish:
  - no `condition` key present → default to `"complete"`
  - `condition: complete` → keep
  - `condition` key present but invalid/unrecognized → drop  
  Add regressions for:
  - `condition: started # note`
  - `condition: complete # note`
  - `slug: 046-prereq # note`

- **Issue** → `blockedByPrereqs` is derived inside `readSessionSets(root)` before `readAllSessionSets()` merges roots/worktrees, so the merged Explorer view can keep a row blocked even when its prerequisite resolves to a complete set from another discovered root.  
  **Location** → `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts:616-644`, `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts:662-677`  
  **Fix** → Recompute `blockedByPrereqs` after the merged slug map is built in `readAllSessionSets()`, or move prerequisite resolution to the merged-read layer and keep `readSessionSets(root)` as a raw per-root scan.

## Nice-to-have
- **Issue** → The spec-called-out zero-session/non-plan-less branch is implemented, but not explicitly pinned by tests. Current coverage exercises absent `sessions[]` carve-out, not the distinct `sessions: []` case.  
  **Location** → `tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts:327-345`  
  **Fix** → Add cancel/restore tests with raw input `{ ..., sessions: [] }` and assert output still contains `sessions: []` rather than dropping the key.

- **Issue** → Layer-3 UI coverage does not verify terminal-row suppression of `[BLOCKED BY PREREQS]`; only the pure unit predicate covers it today.  
  **Location** → `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts:90-120`, `tools/dabbler-ai-orchestration/src/test/playwright/blocked-by-prereqs.spec.ts:113-184`  
  **Fix** → Add a Playwright fixture where `blockedByPrereqs === true` but the dependent row is `complete`/`cancelled`, and assert the badge is not rendered.