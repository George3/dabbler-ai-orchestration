# Set 047 Session 5 — Close-out reason

## Scope shipped (per spec §4 row for Session 5)

Writer-flip phase part 2: the TypeScript mirror of S4's Python writer
flip plus the new user-visible Explorer surface (`prerequisites` field
schema + `blockedByPrereqs` derivation + `[BLOCKED BY PREREQS]`
badge).

### TS writers flipped to v4

1. **`synthesizeNotStartedState` / `notStartedPayload`**
   (`tools/dabbler-ai-orchestration/src/utils/sessionState.ts`)
   - Emits `schemaVersion: 4`, top-level `status` +
     `sessions[]` only (when a plan is known).
   - Drops `currentSession`, `totalSessions`, `completedSessions`,
     `startedAt`, `completedAt`, `verificationVerdict`,
     `orchestrator`, `lifecycleState` from the top level — mirrors
     the Python `_not_started_payload` S4 contract byte-for-byte on
     the v4 shape.
   - Each `sessions[]` entry carries the per-session metadata fields
     (startedAt / completedAt / orchestrator / verificationVerdict)
     defaulted to null.
   - `readTotalSessionsFromSpec` falls back on `### Session N`
     headings when the Session Set Configuration block has no
     numeric `totalSessions` — mirrors Python S4 verifier Critical 2.
   - Plan-less carve-out preserved: when no total is resolvable
     (no config block + no headings), emit a v4 file with no
     `sessions[]` so the next legitimate write can materialize it.

2. **`ensureSessionStateFile` / `backfillPayload`**
   (`tools/dabbler-ai-orchestration/src/utils/sessionState.ts`)
   - Change-log branch promotes all sessions to `complete` and
     leaves per-session `completedAt` at null (the change-log mtime
     is a set-level heuristic, not a per-session boundary —
     matches Python parity).
   - Activity-log branch promotes session 1 to `in-progress` and
     writes the earliest activity-log timestamp onto
     `sessions[0].startedAt` (per-session, NOT top-level).
   - Both branches fall through to the not-started shape when the
     spec lacks a known plan (rule-1 guard).

3. **`cancelSessionSet` + `restoreSessionSet`**
   (`tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`)
   - Re-emit canonical v4 shape on every write via the new helper
     `toV4OnDiskShape`, which projects any v1/v2/v3/v4 input through
     the `normalizeToV4Shape` shim and trims to the v4 contract.
   - Plan-less carve-out (`sessions[]` absent, top-level
     `orchestrator` + `startedAt` passthrough) is preserved across
     cancel→restore — mirrors Python S4 verifier Critical 3.
   - Passthrough keys (`preCancelStatus`, `forceClosed`) preserved.

### Explorer prerequisites surface (spec §3.3)

- **`SessionSetPrerequisite` type** added to `src/types.ts`:
  `{slug: string, condition: "complete"}`. The enum is one value
  today but kept as a string field so a future spec can extend it.
- **`SessionSet.prerequisites: SessionSetPrerequisite[] | null`** —
  parsed from spec.md's Session Set Configuration block. `null`
  when absent, `[]` when `prerequisites: []` is explicit.
- **`SessionSet.blockedByPrereqs: boolean`** — derived by
  `readSessionSets` / `readAllSessionSets` cross-referencing each
  set's prereqs against the target set's `state`. ANY unsatisfied
  prereq blocks the row. An unknown target slug (typo / missing
  set) keeps the row blocked so a typo doesn't silently unblock.
- **`parsePrerequisites(specPath)`** — lightweight regex parser
  (no YAML lib dependency). Strips inline YAML comments from
  scalar values; tolerant of operator typos (drops entries
  missing `slug` or with unknown `condition`).
- **`blockedByPrereqsBadge(set)`** — returns
  `[BLOCKED BY PREREQS]` only on non-terminal rows; suppressed on
  `complete` / `cancelled` rows (once a set is closed, its
  dependency status is no longer actionable).
- **`contextValueFor(set)`** — gates `blocked-by-prereqs` on
  non-terminal state so the right-click menu surface stays
  consistent with the visual badge.

### In-flight verifier fixes (Round-A ISSUES_FOUND, 0 Critical)

Cross-provider verification ran one round against gpt-5-4 tier 3
($0.4717) and returned ISSUES_FOUND with 0 Critical + 2 Important +
2 Nice-to-have items; all 4 addressed in-flight per memory
`feedback_dont_hide_behind_out_of_scope`:

1. **Important 1 — `parsePrerequisites` condition handling.**
   Previously a present-but-unparseable `condition:` line silently
   defaulted to `"complete"` instead of dropping the entry, violating
   spec §3.3's drop-unknown contract. Also dropped otherwise-valid
   entries when `slug:` carried an inline comment. Fix:
   - Strip trailing YAML `# comment` from scalar values before
     matching.
   - Distinguish "no `condition` key present" (default to
     `"complete"`) from "key present but invalid" (drop).
   - Added 2 regression tests pinning each branch.

2. **Important 2 — `blockedByPrereqs` cross-reference belongs at
   the merged-read layer.** Previously the derivation ran inside
   `readSessionSets(root)` so the merged Explorer view in
   `readAllSessionSets()` could keep a row blocked when its prereq
   resolved to a complete set from another discovered root /
   worktree. Fix:
   - Factored the cross-reference into `deriveBlockedByPrereqs(sets)`
     helper.
   - Per-root call inside `readSessionSets` preserved (single-root
     callers still get the right answer + tests don't need to mock
     `discoverRoots`).
   - Added a second invocation at the merged-list boundary in
     `readAllSessionSets` so cross-root resolution works.

3. **Nice-to-have 1 — explicit `sessions: []` carve-out test.**
   The plan-less carve-out applies only to ABSENT `sessions`;
   explicit `sessions: []` (zero-session) must round-trip
   unchanged. Added one regression test on the cancel path.

4. **Nice-to-have 2 — Layer-3 terminal-row badge suppression.**
   The unit predicate test covered this; the Playwright spec did
   not. Added a 4th scenario: dependant is `complete` on disk,
   prereq target stays not-started — badge must be absent.

### New tests

- `tools/dabbler-ai-orchestration/src/test/suite/sessionStateV4Writers.test.ts`
  — 13 tests covering the four TS writer surfaces' v4 emission,
  plan-less carve-out, explicit empty-sessions handling, and
  cancel→restore round-trip.
- `tools/dabbler-ai-orchestration/src/test/suite/prerequisites.test.ts`
  — 12 tests covering `parsePrerequisites` (5 baseline + 2
  verifier-fix regressions), the cross-reference pass in
  `readSessionSets` (5 scenarios), and the
  `blockedByPrereqsBadge` predicate (3 scenarios).
- `tools/dabbler-ai-orchestration/src/test/playwright/blocked-by-prereqs.spec.ts`
  — 4 Layer-3 scenarios (blocked / unblocked / terminal-row
  suppression / no-prereqs-field).
- Updated 4 existing baseline tests to assert v4 shape:
  `cancelLifecycle.test.ts` (writer-parity test → v4 cancel shape),
  `fileSystem.test.ts` (3 lazy-synth tests).

### UAT checklist

- `docs/session-sets/047-state-file-schema-v4-audit/047-state-file-schema-v4-audit-uat-checklist.json`
  — 13 items covering the prerequisites badge surface (6 items),
  TS writer v4 emission (5 items), and mixed v3/v4 reader
  compatibility (2 items). Schema dual-keyed for the UAT Editor
  app + the Dabbler extension's pending-count parser.

## Final test posture

- Python: 896 passed, 1 skipped (pre-existing), 0 failed.
- TS unit: 623 passed (+3 verifier-fix regressions over the pre-fix
  baseline of 620), 2 pre-existing baseline failures unchanged
  (`configEditor-foundation` ViewColumn stub + `notificationsSection`
  disabled-button assertion, both last-touched in Set 026 — unrelated
  to v4 work).

## Cumulative routed cost

- S1 audit: $0.10851
- S2 reader-first phase + 2 verification rounds: $0.48351
- S3 migrator phase + 1 verification round: $0.28820
- S4 writer-flip phase 1 + 1 verification round: $0.45704
- S5 writer-flip phase 2 + 1 verification round: **$0.47171**
- **Cumulative S1+S2+S3+S4+S5: $1.80897 of $10 NTE (18.1%)**

Plenty of headroom for S6 (schema-doc + authoring-guide revision +
close-out + publish).

## Manual-verify attestation

Per memory `feedback_auto_verify_dont_hide`: cross-provider routed
verification ran successfully against gpt-5-4 tier 3 with a single
ISSUES_FOUND verdict; all 4 verifier items were addressed in-flight
before close-out. The Round-A verdict confirmed 0 Critical items,
which is a step up from S4's 3 Critical / 1 Important / 3
Nice-to-have — reflects the more focused scope of S5 (TS mirror of
an already-verified Python flip, plus the new UX surface authored
under the spec-locked §3.3 contract).

I have manually verified:
- All TS unit tests pass except for the 2 pre-existing baseline
  failures (no S5 regressions).
- All Python tests still pass (the S5 changes are TS-side; no
  Python edits beyond the S4 baseline).
- `tsc --noEmit` compiles cleanly.
- The four user-visible deliverables from spec §4 row 5 are
  shipped: TS writers emit v4, `blockedByPrereqs` derivation
  lands, `prerequisites` field schema is parsed, badge renders in
  the Explorer description.
- Layer-3 Playwright spec authored (4 scenarios) and UAT checklist
  authored (13 items). Per memory
  `project_ci_linux_macos_playwright_launch_timeouts` the
  Playwright suite has pre-existing Linux/macOS infra issues; the
  spec runs locally on Windows.
