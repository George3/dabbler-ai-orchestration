# Set 047 Session 5 — Writer-flip phase part 2 (TS) + Explorer prerequisites — Cross-Provider Verification

## What you're verifying

Set 047 Session 5 of the v4 state-file schema migration. This session:

1. Flipped all four TypeScript writer surfaces (`synthesizeNotStartedState`,
   `ensureSessionStateFile`, `cancelSessionSet`, `restoreSessionSet`) to
   emit canonical v4 on-disk shape — the TS mirror of S4's Python flip.
2. Landed the new `spec.md` `prerequisites` field schema (spec §3.3):
   `[{slug, condition: "complete"}]`.
3. Added a `blockedByPrereqs: boolean` derived property on the in-memory
   `SessionSet` record in `readSessionSets`.
4. Added a `[BLOCKED BY PREREQS]` badge in the Session Set Explorer
   `descriptionFor()` renderer (suppressed on terminal-state rows).
5. Authored a Layer-3 Playwright spec for the badge rendering and a
   UAT checklist for the user-visible Explorer surface.

Scope-locked spec: `docs/session-sets/047-state-file-schema-v4-audit/spec.md`
§3.1 (v4 schema shape), §3.3 (prerequisites + blocked-on-prereqs), §4
row for Session 5.

## What you're NOT verifying

- The Session-2 shim itself (`normalizeToV4Shape`) — already verified
  in S2.
- The Session-3 migrator (`migrateOneSetV4`) — already verified in S3.
- The S4 Python writer flip — already verified in S4. (S5's Python
  parity-mirror tests touch this minimally; only call out if the TS
  flip materially diverges from the Python on-disk contract.)

## Critical contracts to verify

### V4 on-disk shape (spec §3.1) — TS writers must mirror Python

The four TS writer surfaces flipped in S5 must emit v4 shape matching
the Python writers' output (S4). Specifically:

**Preserved top-level keys (in canonical order):**
- `schemaVersion: 4`
- `sessionSetName: string`
- `status: "not-started" | "in-progress" | "complete" | "cancelled"`
- `sessions: SessionRecord[]` (per-session ledger, when a plan is known)

**Optional passthroughs (when present in source):**
- `preCancelStatus`
- `forceClosed`

**Dropped top-level keys (re-derived at read time by the shim):**
- `lifecycleState`
- `currentSession`
- `totalSessions`
- `completedSessions`
- `startedAt`
- `completedAt`
- `orchestrator`
- `verificationVerdict`

**Per-session metadata (each `sessions[]` entry):**
- `number: int`
- `title: string`
- `status: "not-started" | "in-progress" | "complete" | "cancelled"`
- `startedAt: ISO8601 | null`
- `completedAt: ISO8601 | null`
- `orchestrator: {engine, provider, model, effort, chatSessionId} | null`
- `verificationVerdict: "VERIFIED" | "ISSUES_FOUND" | null`

### Plan-less carve-out (mirrors Python S4 verifier Critical 3)

When the input state file has NO `sessions[]` array (the documented
plan-less case where a set was registered before its spec.md was
authored), cancel/restore must:
1. Preserve the absence of `sessions[]` on output.
2. Carry `orchestrator` and `startedAt` at the top level as the
   documented plan-less passthrough.

Writing `sessions: []` would convert a "plan unknown" file into a
"zero-session" file — a semantic shift that would mis-trip invariant
checks downstream.

### Headings fallback for totalSessions (mirrors Python S4 verifier Critical 2)

When the spec has no `Session Set Configuration` totalSessions but DOES
have `### Session N: title` headings, `readTotalSessionsFromSpec`
should pick up the headings and emit a sessions[] array. A headings-
only spec is a legitimate plan signal (e.g., audit proposals authored
before the configuration block lands).

### Prerequisites + blockedByPrereqs (spec §3.3)

- `parsePrerequisites(specPath)` returns `null` when the field is
  absent, `[]` when explicitly `prerequisites: []`, and the parsed
  list otherwise. Tolerant of operator typos: entries missing `slug`
  or with unknown `condition` are dropped.
- `readSessionSets` cross-references each set's `prerequisites`
  against the target set's `state` and sets
  `blockedByPrereqs: boolean`. ANY unsatisfied prereq blocks the row.
  An unknown target slug keeps the row blocked (typo / missing-set
  must not silently unblock).
- `blockedByPrereqsBadge(set)` returns `[BLOCKED BY PREREQS]` only
  on non-terminal rows; suppressed on complete / cancelled rows.

## Specific things to look hard at

1. **TS writers byte-for-byte parity with Python S4 on the v4 contract.**
   The Python mirror is at `ai_router/session_lifecycle._to_v4_on_disk_shape`
   and `ai_router/session_state._not_started_payload` /
   `_backfill_payload`. The TS implementations are in
   `tools/dabbler-ai-orchestration/src/utils/sessionState.ts`
   (`notStartedPayload`, `backfillPayload`) and
   `tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`
   (`toV4OnDiskShape`).

2. **The cancel/restore plan-less carve-out detection logic** —
   `isPlanless = !inputHasSessions && (!Array.isArray(normalizedSessions)
   || normalizedSessions.length === 0)` — must match the Python
   pattern. If the input has `sessions: []` (zero-session, NOT
   plan-less), the carve-out should NOT trigger, and the writer should
   emit `sessions: []` on disk.

3. **`parsePrerequisites` parser robustness.** The parser is a
   lightweight regex pattern (not a full YAML parser) — does it handle
   reasonable variations like `condition` omitted (defaults to
   "complete"), entries in arbitrary order within a block, comments
   in the spec, etc.? Look for any prompt-injection-style input that
   could mis-parse.

4. **The `blockedByPrereqs` cross-reference pass timing.** It runs
   AFTER the main per-set loop in `readSessionSets`. Confirm the
   `setsByName` map is populated before any iteration consumes it
   (i.e., the resolution direction works for forward references —
   a depending set that was constructed earlier than its prereq
   target should still resolve correctly).

5. **The Explorer badge suppression on terminal-state rows.** Verify
   `blockedByPrereqsBadge` returns `""` when `set.state` is `"complete"`
   or `"cancelled"`, regardless of `set.blockedByPrereqs`. The
   `contextValueFor()` function also gates `blocked-by-prereqs` on
   non-terminal state, so the right-click menu surface stays
   consistent with the visual badge.

6. **Test coverage gaps.** I added 11 new tests (5 v4 writers + 5
   prerequisites + 6 badge) and updated 3 fileSystem.ts lazy-synth
   tests + 1 cancelLifecycle.ts parity test. Are there v4-contract
   scenarios or prereq-edge cases I missed that should have explicit
   tests?

## Verdict format

Reply with:

- **One-line verdict:** `VERIFIED` or `ISSUES_FOUND`.
- **Critical / Important / Nice-to-have** sections with specific
  file:line citations. Critical = a contract violation that would
  surface a bug on real workspaces. Important = a deviation from
  parity / spec that an operator would notice. Nice-to-have = code
  quality / consistency improvements that don't affect correctness.

Per memory `feedback_dont_hide_behind_out_of_scope`, I will apply all
Critical + Important + Nice-to-have items in-flight rather than
deferring them to a future session — call them out clearly so I can
address them before close-out.
