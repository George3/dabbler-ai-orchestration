# Session 4 verification prompt — Set 023 reader fix (extension v0.13.13)

## Context

Set 023 Session 4 ships the extension-side fix that closes Sharp Edge
1 from the Set 023 spec: `isMidSetComplete` previously treated the
`session-events.jsonl` ledger as the *only* authoritative
"session N is closed" signal. After Set 022 declared
`completedSessions[]` to be authoritative for whether-closed,
`isMidSetComplete` was the last reader on either tier that hadn't
caught up. A migrated pre-Set-022 set whose operator hand-added
`completedSessions: [1..N]` to the snapshot would still be
downgraded to In Progress in the Session Set Explorer unless the
operator also ran `close_session --repair --apply` to synthesize the
missing final-session ledger event.

The Session 2 cross-provider design audit (GPT 5.4 + Gemini Pro,
both reviewed the design before the writer fix shipped) confirmed
the array-before-ledger ordering and added two refinements that
landed in this implementation:

1. **Observability warn** when the array overrides a missing ledger
   closeout (GPT 5.4 caveat on Question (c)).
2. **Sharpened authoritative phrasing** in the schema doc and
   close-out doc to distinguish whether-closed (array) from
   when-closed (ledger), so future maintainers do not read "both
   are authoritative" as "must agree" (both providers on Question (e)).

Session 3 (system-wide audit) found one Python sharp edge
(`print_session_set_status` — shipped as `ai_router 0.2.5`) and
documented one borderline path (`close_session._is_already_closed`)
that was intentionally deferred. No additional TypeScript sharp
edges were surfaced, so this v0.13.13 release carries only the
reader fix plus its audit-driven test fixtures.

## What changed in this session

1. **`tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`**
   `isMidSetComplete` consults `completedSessions[]` before the
   events-ledger check. When the array satisfies the guard but the
   ledger does not, a one-line `console.warn` surfaces the drift.
   The legacy ledger-only path is preserved for sets without the
   array. The docstring is rewritten to reflect the new
   two-authoritative-signals contract.

2. **`tools/dabbler-ai-orchestration/src/test/suite/fileSystem.test.ts`**
   New suite `fileSystem — isMidSetComplete (Set 023 Session 4)`
   with fixtures F1–F7 plus a migration-shape bonus fixture. F5
   covers `null` / non-array `completedSessions` values (Gemini on
   (e)). F6 covers a stray out-of-range entry (`[1, 2, 99]` —
   audit-driven, both providers on (b) and (e)). F7 documents that
   only `currentSession` is checked; non-final disagreement is
   irrelevant (GPT on (e)).

3. **`docs/session-state-schema.md`** "Parser cheat-sheet" /
   bucketing section now documents the array-before-ledger ordering
   and the sharpened invariant phrasing.

4. **`ai_router/docs/close-out.md`** § 5 drift case 1 gains an
   attestation note: `completedSessions[]` is **operator-attested**
   for migrated sets and **tool-maintained** for sets that ran the
   close-out gate (GPT on (a)).

5. **Version bump** to extension v0.13.13:
   `tools/dabbler-ai-orchestration/package.json`,
   `tools/dabbler-ai-orchestration/package-lock.json`,
   `tools/dabbler-ai-orchestration/CHANGELOG.md`, `CLAUDE.md`.

## Verification questions

Answer in JSON with one key per question. Be specific; cite line
numbers where possible.

1. **Correctness of `isMidSetComplete`.** Does the new ordering
   (currentSession < totalSessions → array check → ledger check)
   match the spec's pseudo-code in `spec.md` § Architecture? Is the
   `Array.isArray` + `.includes(currentSession)` guard correct
   defensive shape against non-array `completedSessions` values?

2. **Observability warn placement.** The warn fires *inside* the
   array-satisfies-guard branch, only when the ledger exists and
   lacks the corresponding closeout. Is this the right moment to
   warn (not too eager, not silenced)? Any concern about warn
   spamming on repeated reads of the same set?

3. **Test coverage.** Do fixtures F1–F7 cover the spec's enumerated
   shapes plus the audit-driven cases? Any missing shape (e.g., the
   `currentSession < totalSessions` early-return path; the
   array-present-but-ledger-absent migration shape)?

4. **Doc edits.** Does the schema doc + close-out doc language hold
   up the sharpened invariant ("array is authoritative for
   whether-closed; ledger is authoritative for when-closed") clearly
   enough that a future maintainer would not "fix" the guard to
   require both signals to agree?

5. **Backward compatibility.** A set carrying `completedSessions[]`
   but stale/incorrect entries would now be classified as Done where
   it would have been In Progress under v0.13.12. The spec's Risks
   section calls this the intended migration story; do you agree, or
   does the change create a regression class we missed?

6. **Anything else (open).** Sharp edges, security concerns, naming,
   error handling, edge cases the test fixtures don't cover.
