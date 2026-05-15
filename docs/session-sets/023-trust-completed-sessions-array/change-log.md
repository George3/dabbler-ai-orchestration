# Set 023: trust-completed-sessions-array — Change Log

**Sessions:** 4 of 4 completed (2026-05-15)
**Orchestrator:** Anthropic / Claude Opus 4.7 (1M context) — all four sessions
**Cumulative routed cost (verification + audit):** ~$0.78 — Session 1
verification $0.10, Session 2 audit + verification ~$0.30 (gpt-5-4 and
gemini-pro design routes plus session-verification), Session 3
verification $0.147, Session 4 verification $0.235.

---

## What Set 023 delivers

Set 022 declared `completedSessions[]` to be the authoritative
whether-closed signal on both tiers. Set 023 closes the two sharp
edges Set 022's migration surfaced — one in the ai_router writer,
one in the extension reader — plus the audit-driven third sharp
edge a cross-provider design review surfaced mid-set. After this set
ships, a migrated pre-Set-022 set whose operator hand-adds
`completedSessions: [1..N]` to its snapshot displays as N/N Done in
the Session Set Explorer without any other intervention, and
`close_session --repair --apply` preserves operator-attested arrays
verbatim while still healing the events ledger.

The four drift cases enumerated in `ai_router/docs/close-out.md` § 5
remain. The v0.13.11 defensive guards remain as recovery
defense-in-depth. This set adds the **trust-the-array** layer: every
whether-closed reader on every tier now consults
`completedSessions[]` as a primary or alternative authoritative
signal, with the events ledger reserved for its proper role —
recording *when* each closeout occurred.

### Session 1 — ai_router writer: union-not-overwrite (released as ai_router 0.2.4)

`close_session._run_repair` Case 1's apply path used to overwrite
`completedSessions[]` with the events-ledger reconstruction after
appending synthetic closeout events — regressing a hand-migrated
snapshot from `[1, 2, 3, 4]` to `[3, 4]` whenever the ledger had only
recorded a later session's closeout (Set 004 on this repo hit this
on 2026-05-15). Session 1's fix replaces the overwrite with a
**monotone-up union**: the merged value is `sorted(set(snapshot) |
set(ledger) | {currentSession})`. Four apply outcomes are now
distinguished in the `messages` line — backfilled / merged /
normalized / preserved — so the operator sees at a glance what the
repair did (or didn't do).

The merge is idempotent under repeated `--repair --apply`: a clean
shape produces no further snapshot writes. Tests in
`test_repair_detects_mixed_mode_drift.py` cover the preserve path,
the union path, the normalized-typo path, and the no-op idempotency
path.

### Session 2 — Cross-provider design-alignment audit (doc-only)

Before the reader-side fix shipped, the design was reviewed by both
GPT 5.4 and Gemini Pro on the same prompt. Both providers concurred
with the Set 022 hand-migration approach, the writer-side union, and
the reader-side array-before-ledger ordering. Both raised the same
**third sharp edge** independently (Gemini: critical; GPT: major):
other progress-readers in the pipeline may still consult the events
ledger directly without considering `completedSessions[]`. The
operator chose option (B): pause the reader fix and expand Set 023's
scope to include a system-wide audit (Session 3 added mid-set). Both
providers also surfaced refinements that landed in Session 4
implementation: an observability warn when the array overrides a
missing ledger closeout (GPT on Q(c)), the sharpened authoritative
phrasing distinguishing whether-closed from when-closed (both on
Q(e)), and audit-driven test fixtures F5/F6/F7. See
`session-reviews/session-002-audit/audit-summary.md` for the
combined verdict and the resolution shape per question.

### Session 3 — System-wide audit of events-ledger consumers (released as ai_router 0.2.5)

A mechanical grep sweep across `ai_router/` (Python) and
`tools/dabbler-ai-orchestration/src/` (TypeScript) cross-referenced
every `session-events.jsonl` / `closeout_succeeded` /
`hasCloseoutEventForSession` / `read_events` reference against
`completedSessions` references. Eighteen consumers classified:

- **11 already-correct** (5 close-out gate predicates + 6 Python
  helpers/writers + 5 TypeScript reader/provider paths).
- **7 correct-to-ignore** (reconciler stranded-state sweep, lifecycle
  derivation, events-ledger I/O helpers, backfill,
  `close_session._is_already_closed` with a documented note, the
  extension's file watcher, the force-closed tooltip prose).
- **1 newly-surfaced sharp edge fixed in-session:**
  `ai_router.__init__.print_session_set_status` used the
  pre-Set-022 activity-log `len({sessionNumber})` derivation — the
  same shape Set 022 Session 2 removed from the TypeScript reader.
  Fix: replaced with
  `len(compute_effective_completed_sessions(path))` (the Set 022
  single source of truth). Tests: four regression fixtures
  including an events-ledger fallback fixture added per the round-1
  verifier finding. Shipped as `ai_router 0.2.5` via the
  tag-driven release flow.
- **1 known sharp edge deferred to Session 4** (`isMidSetComplete`).

The audit document is on disk at
`session-reviews/session-003-audit-findings.md` and includes a
classification key, per-consumer rationale with `file:line` citations,
the borderline-classification discussion for
`close_session._is_already_closed`, and the result summary. The
systemic concern raised in Session 2 is formally documented and
closed for the codebase as of Session 3 (modulo the Session 4 fix).

### Session 4 — Extension reader fix (released as extension v0.13.13)

`isMidSetComplete` (in
`tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`) now
consults `completedSessions[]` as an alternative authoritative
whether-closed signal before falling through to the events-ledger
check. The ordering is `currentSession < totalSessions` early-return
→ array check → ledger check → return false. When the array
satisfies the guard but the events ledger lacks the corresponding
`closeout_succeeded` event, a one-line `console.warn` of the form
`[session-set <slug>] completedSessions[] overrides missing ledger
closeout for session N` surfaces the drift; the override is correct,
the warn is observability only.

**Tests** in `fileSystem.test.ts` — new suite `fileSystem —
isMidSetComplete (Set 023 Session 4)` with the seven spec-driven
fixtures (F1: array satisfies + no ledger; F2: array disagrees +
ledger disagrees → mid-set; F3/F4: legacy no-array paths preserved
unchanged; F5: non-array `completedSessions` shapes fall through
safely; F6: stray out-of-range entries don't accidentally satisfy
`.includes`; F7: only `currentSession` matters, non-final
disagreement irrelevant) plus a migration-shape bonus that asserts
the observability warn fires exactly once with the expected slug +
session number, plus three round-1-verifier-driven coverage
additions (the `currentSession < totalSessions` early-return path;
no-warn assertions on the three non-override shapes; the ambiguous
array-misses + no-ledger-file shape).

**Docs:** `docs/session-state-schema.md` "Parser cheat-sheet"
bucketing section now documents the array-before-ledger ordering and
the sharpened invariant phrasing. `ai_router/docs/close-out.md` § 5
drift case 1 gains an attestation note: `completedSessions[]` is
operator-attested for migrated sets and tool-maintained for sets
that ran the close-out gate.

**Smoke-test against Set 006** confirms the fix: `completedSessions:
[1, 2, 3]` satisfies the guard at `currentSession === 3`, so even
if the synthetic session-3 closeout event were absent from the
ledger, the set would still be bucketed as Done.

### Release artifacts

- **PyPI** `dabbler-ai-router 0.2.4` (Session 1 — repair union).
- **PyPI** `dabbler-ai-router 0.2.5` (Session 3 — CLI status reader
  trust the array).
- **VS Code Marketplace**
  `DarndestDabbler.dabbler-ai-orchestration v0.13.13` (Session 4 —
  `isMidSetComplete` consults the array + observability warn +
  sharpened docs).

### Deferred (post-Set-023 candidates)

Surfaced by the Session 4 verifier round 1 and intentionally not
addressed in this set:

- **Tri-state helper for `hasCloseoutEventForSession`** so unreadable
  ledgers are distinguishable from "no closeout event present" — a
  cross-cutting change touching every caller (also the existing
  mid-set drift path in `readSessionSets`).
- **`console.warn` dedupe / rate-limiting** if Explorer refresh
  produces real-world noise. None observed yet.
- **Upstream range validation** of `currentSession` /
  `totalSessions` numeric shapes — owned by `readSessionSets` and
  `compute_effective_completed_sessions`, not the reader guard.
- **`close_session._is_already_closed`** array-first refinement
  (Session 3 deferred borderline classification). Operator-affordance
  only; no user-visible impact. Documented in
  `session-reviews/session-003-audit-findings.md` for re-evaluation
  if a real incident surfaces it.
- **Out-of-range entry clamp** in the Session 1 union (Session 2
  audit risk note). A typo like `completedSessions: [1, 2, 99]` with
  `totalSessions: 4` survives a repair pass today; Session 4 fixture
  F6 documents that the reader is robust to the writer-side gap, but
  the writer itself does not clamp.

These five items can queue as a follow-on micro-set if any of them
trip a real incident.

---

## Success criteria — final accounting

| Criterion | Status |
|---|---|
| Migrated set hand-adding `completedSessions: [1..N]` displays as N/N Done with no other intervention | **Met** (Session 4) |
| `--repair --apply` preserves a complete hand-authored array while still healing the ledger | **Met** (Session 1) |
| Repeated `--repair --apply` on a clean set is idempotent (no further snapshot writes) | **Met** (Session 1) |
| Full repair test suite + extension `fileSystem.test.ts` suite pass on new and existing fixtures | **Met** |
| The two named sharp edges Set 022 surfaced are resolved | **Met** (Sessions 1 + 4) |
| The third sharp edge surfaced by both providers in Session 2 is closed on disk | **Met** (Session 3 audit + Session 3 fix + Session 4 reader fix) |
| v0.13.11 defensive guards remain in place as recovery defense-in-depth | **Met** (legacy paths preserved in `isMidSetComplete`) |
