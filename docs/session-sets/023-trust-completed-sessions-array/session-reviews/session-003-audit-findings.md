# Session 3 audit — events-ledger / progress-state consumers

> **Purpose:** This session is the codebase-wide audit added to Set 023
> after the Session 2 cross-provider design review surfaced the same
> third sharp edge from both providers: "other progress-readers in the
> pipeline may still consult the events ledger directly without
> considering `completedSessions[]`" (Gemini: critical; GPT: major). The
> operator chose option (B) — pause the planned reader fix (now Session
> 4) and expand Set 023's scope to include this audit.
>
> **Method:** mechanical grep sweep across Python (`ai_router/`) and
> TypeScript (`tools/dabbler-ai-orchestration/src/`) for any of the
> three search terms — `session-events.jsonl`, `closeout_succeeded`,
> `hasCloseoutEventForSession` / `read_events` — cross-referenced
> against `completedSessions`. Each candidate hit was read in
> surrounding context and classified.
>
> **Date:** 2026-05-15

---

## Classification key

- **already-correct (post-Set-022)** — consults `completedSessions[]` as
  primary, events ledger as fallback or parallel check.
- **correct-to-ignore** — the consumer's job is to read the events
  ledger as a historical / lifecycle record (debug, observability,
  lifecycle-transition machinery). Ignoring `completedSessions[]` is
  intentional and documented.
- **sharp edge — needs fix** — derives "is session N closed?" or "how
  many sessions are closed?" from the events ledger (or activity log)
  alone, would disagree with a migrated snapshot whose
  `completedSessions[]` carries operator-attested sessions the ledger
  lacks. Becomes a fix step within this session.

The Session 2 audit's sharpened invariant phrasing applies throughout:
**`completedSessions[]` is authoritative for *whether* a session is
closed; `session-events.jsonl` is authoritative for *when* each
closeout was recorded.** A consumer asking a whether-closed question
must consult the array; a consumer asking a lifecycle-timing question
correctly reads the ledger.

---

## Findings

### Python (`ai_router/`)

| Consumer | File:line | Reads | Classification | Rationale |
|---|---|---|---|---|
| `compute_effective_completed_sessions` | [session_state.py:279](../../../../ai_router/session_state.py#L279) | array → events → currentSession-1 heuristic | already-correct | Set 022 helper. Single source of truth — explicit read order prefers `completedSessions[]`. |
| `_flip_state_to_closed` | [session_state.py:355](../../../../ai_router/session_state.py#L355) | calls helper, unions with currentSession | already-correct | Set 022 writer. Maintains the array on every close. |
| `register_session_start` | [session_state.py:148](../../../../ai_router/session_state.py#L148) | calls helper to preserve array across rewrite | already-correct | Set 022 invariant: array survives session-boundary rewrites. |
| `start_session._infer_next_session` | [start_session.py:136](../../../../ai_router/start_session.py#L136) | `max(closed)+1` via helper | already-correct | Inference reads through the helper, gets array authority for free. |
| `close_session._run_repair` Case 1 | [close_session.py:743](../../../../ai_router/close_session.py#L743) | union of snapshot array ∪ ledger events | already-correct | Session 1 of this set (0.2.4) made the writer preserve hand-authored arrays. |
| `close_session._run_repair` Case 2 | [close_session.py:1062](../../../../ai_router/close_session.py#L1062) | `closeout_succeeded` ledger probe vs `state.completedSessions` | already-correct | Set 022 wiring. Detects the inverse drift shape (ledger ahead of snapshot) and flips state. |
| `close_session._is_already_closed` | [close_session.py:581](../../../../ai_router/close_session.py#L581) | events ledger only (via `current_lifecycle_state`) | correct-to-ignore (with note) | See discussion below. The docstring explicitly justifies the events-driven shape as the close-out machinery's drift-detection contract (Set 7 Session 2 design). After Session 1's writer fix, both signals always agree on post-Set-022 sets. Hand-migrated sets with array but no ledger closeout for session N fall through to the gate path (recoverable via `--repair --apply` or `--force`). Not user-visible. |
| `reconciler._evaluate_one` | [reconciler.py:223](../../../../ai_router/reconciler.py#L223) | events ledger via `current_lifecycle_state` | correct-to-ignore | Stranded-state sweep is a lifecycle-timing question (`closeout_pending` / `closeout_blocked`), not a whether-closed question. The module's docstring at line 237-248 explicitly chose this design after the Set 7 Session 2 review: an array pre-filter "would either duplicate the events check (no win) or, worse, mask drift the reconciler is meant to surface." |
| `gate_checks.check_*` (all five) | [gate_checks.py:172](../../../../ai_router/gate_checks.py#L172), [:294](../../../../ai_router/gate_checks.py#L294), [:403](../../../../ai_router/gate_checks.py#L403), [:466](../../../../ai_router/gate_checks.py#L466), [:549](../../../../ai_router/gate_checks.py#L549) | none — git status / snapshot / change-log mtime | already-correct | None of the five gate predicates read the events ledger or derive progress from it. All snapshot-based reads go through `read_session_state`, which carries `completedSessions[]` transparently. |
| `disposition.py` | [disposition.py](../../../../ai_router/disposition.py) | disposition.json only | already-correct | Doesn't touch the events ledger. The completedSessions invariant is not in scope for this module. |
| `session_events.current_lifecycle_state` | [session_events.py:321](../../../../ai_router/session_events.py#L321) | events ledger (by design) | correct-to-ignore | This IS the events-ledger lifecycle-state derivation. Its job is to read the ledger and report the most-recent session's lifecycle stage. Set 7 Session 2 explicitly documented this in the docstring as a no-op-collapse. |
| `session_events.backfill_*` | [session_events.py:578](../../../../ai_router/session_events.py#L578) | activity-log + state snapshot | correct-to-ignore | Backfill *constructs* the events ledger from history; not a progress-state derivation. |
| **`__init__.print_session_set_status`** | [__init__.py:1182](../../../../ai_router/__init__.py#L1182) | **activity-log distinct sessionNumber** | **sharp edge — fix** | **Derives `sessions_completed` from `len({entry.sessionNumber for entry in activity-log.entries})`. Activity log records IN-FLIGHT step events too, so this overcounts: a set with currentSession=2 (session 1 closed, session 2 in flight) reports `sessions_completed=2`. Set 022 Session 2 explicitly removed the same derivation from the TypeScript reader at [`fileSystem.ts:300-320`](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts) and migrated it to consult `completedSessions[]` first with events as Full-tier fallback. The Python CLI's `print_session_set_status` was left out of that migration and still uses the pre-Set-022 shape. Disagrees with the TypeScript tree view's progress display and with the spec invariant.** |

### TypeScript (`tools/dabbler-ai-orchestration/src/`)

| Consumer | File:line | Reads | Classification | Rationale |
|---|---|---|---|---|
| `readSessionSets` (sessionsCompleted derivation) | [fileSystem.ts:385](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L385) | array → events count → done+totalSessions fallback | already-correct | Set 022 Session 2 priority order. Array first; `countDistinctCloseoutSessions` as Full-tier fallback. |
| `countDistinctCloseoutSessions` | [fileSystem.ts:135](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L135) | events ledger (by design) | correct-to-ignore | The Full-tier-fallback helper. Its job is to count closeout events. |
| `hasCloseoutEventForSession` | [fileSystem.ts:95](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L95) | events ledger (by design) | correct-to-ignore | Single-purpose helper used only by `isMidSetComplete`. Its job is to answer one specific question about the ledger. |
| **`isMidSetComplete`** | [fileSystem.ts:72](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L72) | events ledger only | **sharp edge — Session 4** | **Already known.** This is the user-visible subject of Session 4 of Set 023. Documented in the Set 023 spec's Sharp edge 1; not re-counted here as a new finding. Listed for completeness. |
| `SessionSetsProvider.isCurrentSessionInFlight` | [SessionSetsProvider.ts:28](../../../../tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts#L28) | `liveSession.completedSessions[]` only | already-correct | Set 022 helper. Returns false when array is absent (safe default). |
| `SessionSetsProvider.progressText` | [SessionSetsProvider.ts:36](../../../../tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts#L36) | `sessionsCompleted` from upstream | already-correct | Renders the number `readSessionSets` already derived correctly. |
| `extension.ts` file watcher | [extension.ts:116](../../../../tools/dabbler-ai-orchestration/src/extension.ts#L116) | watches `session-events.jsonl` for change events | correct-to-ignore | Triggers refresh on ledger writes; does not derive state from the file's contents. Per Set 022 Session 2: needed so boundary writes from `start_session`/`close_session` trigger the immediate watcher debounce. |
| `SessionSetsProvider` tooltip (force-closed hint) | [SessionSetsProvider.ts:128](../../../../tools/dabbler-ai-orchestration/src/providers/SessionSetsProvider.ts#L128) | string literal mentioning `closeout_force_used` | correct-to-ignore | Diagnostic prose only; no derivation. |

---

## Discussion: `close_session._is_already_closed` (borderline classification)

The function's docstring at [`close_session.py:582`](../../../../ai_router/close_session.py#L582) explicitly justifies the events-driven shape:

> Set 7 Session 2 note: the spec lists "the close-out gate's idempotency
> check" as a reader to collapse to `read_status`. This function is the
> close-out gate's idempotency check, but it does not read coarse
> status — it derives the lifecycle state from the events ledger. The
> events ledger is intentionally authoritative here for the same reason
> the reconciler stays events-driven (Set 7 Session 2): a stale
> snapshot saying `"complete"` while the ledger still records
> `closeout_pending` is exactly the drift the close-out machinery
> exists to catch.

Under the Set 022 + Set 023 sharpened invariant ("array is authoritative
for whether-closed; ledger is authoritative for when-closed"), the
literal phrasing of "is session N closed?" is a whether-closed question
and would, in isolation, argue for the array-first pattern from Session
4's reader fix.

In practice, the post-Set-022 writer (`_flip_state_to_closed`) always
maintains both signals atomically — `completedSessions[]` and a
`closeout_succeeded` event land together on every close. The two can
disagree only via:

1. Hand-edit migration of a pre-Set-022 set (operator attestation —
   intentional; handled by `--repair --apply` after Session 1's fix).
2. A future writer bug that flips one without the other (drift the
   docstring is explicitly defensive against).

**Classification: correct-to-ignore (with note).** Rationale:

- The realistic impact of the gap (hand-migrated set, operator
  re-running `close_session` on an already-closed set) is small and
  recoverable: the operator hits the gate path and resolves via
  `--repair --apply` or `--force` — both already-documented recovery
  affordances.
- Not user-visible (the tree-view bucket flip is Session 4's territory;
  the CLI idempotency is operator-affordance only).
- The existing repair regression tests
  (`test_repair_detects_mixed_mode_drift`, `test_close_session_session4`)
  explicitly depend on the events-based derivation.
- Defaulting to the lowest-engagement classification per the operator's
  standing preference ("default to lowest-engagement bucket; require
  positive evidence to escalate" — there is no concrete user-observed
  bug here, only an invariant-purity argument).

If a future incident surfaces operator confusion from this gap, the fix
is small and mirrors Session 4's pattern (consult
`currentSession in completedSessions[]` first as an alternative
authoritative signal; fall back to the existing events-ledger check).
Documented here so future maintainers see the decision.

---

## Sharp edge to fix in this session

**`__init__.print_session_set_status`** ([__init__.py:1180-1186](../../../../ai_router/__init__.py#L1180-L1186)):

Current code derives `sessions_completed` from
`len({e["sessionNumber"] for e in activity_log["entries"]})`. This is
the pre-Set-022 shape that the TypeScript reader migrated away from at
Set 022 Session 2 (the corresponding TS comment at
[`fileSystem.ts:300-308`](../../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts#L300-L308) is explicit:
"Activity log is a step log, not a count source. Set 022 Session 2
removed the unique-`sessionNumber` count derivation that used to live
here").

Failure mode: a Full-tier set with currentSession=2 (session 1 closed,
session 2 in flight) has activity-log entries for both session numbers
1 and 2. The current code reports `sessions_completed=2`, disagreeing
with the extension's tree view (which correctly reports
`sessions_completed=1` via `completedSessions[]`).

**Fix:** route through `compute_effective_completed_sessions`. The
helper already implements the correct priority order
(array → events → currentSession-1 heuristic with warning) and is the
single source of truth Set 022 established. `sessions_completed` becomes
`len(compute_effective_completed_sessions(path))`.

**Test:** new regression in `ai_router/tests/test_print_session_set_status.py`
(or sibling) — a fixture with activity-log entries for sessions 1 and
2, `completedSessions: [1]` in snapshot, asserts the printed line shows
`1/N` not `2/N`.

**Release:** PyPI `dabbler-ai-router` 0.2.5 via the existing tag-driven
workflow. No TypeScript sharp edges found, so the v0.13.13 release in
Session 4 carries only the reader fix.

---

## Result

- **Sharp edges resolved by this audit (Python):** 1 — the Python CLI
  status reporter (`print_session_set_status`). Fixed within this
  session; shipped as `ai_router 0.2.5`.
- **Sharp edges deferred to Session 4 (TypeScript):** 1 — the
  `isMidSetComplete` reader. Already in scope; bundled into v0.13.13.
- **Sharp edges flagged but consciously left unfixed:** 1 —
  `close_session._is_already_closed`. Documented above. No user-visible
  impact; existing recovery paths cover the gap.
- **Already-correct consumers verified:** 11 (5 gate predicates + 6
  Python helpers/writers + 5 TypeScript paths).
- **Correct-to-ignore consumers verified:** 7 (reconciler, lifecycle
  derivation, events-ledger I/O helpers, backfill, watcher,
  `_is_already_closed`, the tooltip-prose mention).

The system-wide audit raised by both providers in Session 2 is now
**performed and documented on disk**, with the following resolution
shape:

- One newly-surfaced Python sharp edge (`print_session_set_status`):
  **fixed within this session**, shipping as `ai_router 0.2.5`.
- The known TypeScript sharp edge (`isMidSetComplete`): **remains open
  in Session 4's planned scope**, shipping as part of extension
  v0.13.13. Carried forward, not eliminated by this session.
- One borderline path (`close_session._is_already_closed`):
  **intentionally deferred** with the rationale documented above.
  Operator-affordance only; no user-visible impact.

The systemic concern Session 2 named is therefore reduced (no
*newly-surfaced* sharp edges remain unresolved after this session) but
not fully eliminated until Session 4 ships the reader fix. Both
remaining items are tracked: Session 4 is on the active worklist for
this set; the borderline case is documented above for re-evaluation if
a real incident surfaces it.
