# Session 3 verification — Set 023, audit + Python sharp-edge fix

You are verifying Session 3 of Set 023: a codebase-wide audit of
events-ledger / progress-state consumers, plus a Python-side fix to
the one sharp edge the audit surfaced. The audit was added to Set 023
after the Session 2 cross-provider design review surfaced a third
sharp edge from both providers (Gemini: critical; GPT: major): "other
progress-readers in the pipeline may still consult the events ledger
directly without considering `completedSessions[]`."

## What Session 3 had to do

1. Mechanical grep sweep across `ai_router/` (Python) and
   `tools/dabbler-ai-orchestration/src/` (TypeScript) for any code path
   that derives "is session N closed?" or "how many sessions are
   closed?" from `session-events.jsonl`, `closeout_succeeded` events,
   or related signals.
2. Classify each candidate consumer as:
   - **already-correct (post-Set-022)** — consults `completedSessions[]`
     first.
   - **correct-to-ignore** — consumer's job IS to read the ledger
     (debug, observability, lifecycle-transition machinery).
   - **sharp edge — needs fix** — derives progress from the ledger
     alone, disagrees with a migrated snapshot whose array is more
     complete than the ledger.
3. Document findings in
   `session-reviews/session-003-audit-findings.md`.
4. Fix any sharp edges found. Ship Python fixes as `ai_router 0.2.5`.

## Set 022 / Set 023 invariant (sharpened in Session 2)

`completedSessions[]` is authoritative for **whether** a session is
closed; `session-events.jsonl` is authoritative for **when** each
closeout was recorded. The reader-side guard fix planned for Session 4
makes the array an alternative authoritative signal for
`isMidSetComplete`; the writer-side fix shipped in Session 1
(`ai_router 0.2.4`) makes the repair preserve operator-attested
arrays.

## What was found

Eighteen consumers were classified. Tabulated in
`session-reviews/session-003-audit-findings.md` (find it in the same
folder you'll be reviewing). Summary:

- 11 already-correct (5 gate predicates + Set 022 helpers + TS reader
  paths)
- 7 correct-to-ignore (reconciler stranded-state sweep, lifecycle
  derivation, events-ledger I/O helpers, backfill, watcher,
  `close_session._is_already_closed`, tooltip prose)
- **1 sharp edge fixed in this session (Python):**
  `ai_router.print_session_set_status`
- 1 known sharp edge already in Session 4's scope (TypeScript
  `isMidSetComplete`); listed for completeness, not re-counted.

The borderline case is `close_session._is_already_closed` — the
close-out CLI's idempotency check. The docstring explicitly justifies
its events-driven shape (Set 7 Session 2 design decision); realistic
impact is small (operator-affordance only, not user-visible); existing
recovery paths cover the gap. Classified as **correct-to-ignore (with
note)** and documented in audit-findings.md for future re-evaluation.

## The Python sharp edge fixed in Session 3

`ai_router/__init__.py`'s `print_session_set_status` (the CLI status
reporter for `python -m ai_router.report` / equivalent) derived
`sessions_completed` from `len({entry.sessionNumber for entry in
activity_log["entries"]})`. This is the **pre-Set-022 derivation that
the TypeScript reader migrated away from at Set 022 Session 2**
(`fileSystem.ts` carries an explicit comment: "Activity log is a step
log, not a count source. Set 022 Session 2 removed the unique-
`sessionNumber` count derivation that used to live here").

### Failure shape

A Full-tier set in the in-flight window — currentSession=2, session 1
closed, session 2 in flight — has activity-log entries for both
session numbers 1 and 2 (because the activity log records every step
inside every session, including the in-flight one). The pre-Set-022
shape counts both, reports `2/N` complete. The Set 022 invariant
(`completedSessions[]` is authoritative) and the TypeScript reader
both report `1/N`.

The Python CLI status reporter was left out of the Set 022 Session 2
migration. The TypeScript and Python views of the same on-disk state
silently disagreed.

### The fix

Replace `len({entry.sessionNumber for entry in entries})` with
`len(compute_effective_completed_sessions(path))`. The helper is the
single source of truth Set 022 established and applies the correct
priority order (array → events → currentSession-1 heuristic with
warning).

#### The full diff applied

```python
# In ai_router/__init__.py, inside print_session_set_status's per-set loop:

# Before (pre-Set-022 derivation, mirrors what TS removed at Set 022 S2):
#
#   sessions_completed = 0
#   ...
#   if os.path.isfile(activity_path):
#       try:
#           with open(activity_path, "r", encoding="utf-8") as f:
#               data = json.load(f)
#           total_sessions = data.get("totalSessions")
#           entries = data.get("entries", [])
#           if entries:
#               last_touched = max(...)
#               sessions_completed = len({
#                   e["sessionNumber"] for e in entries
#                   if e.get("sessionNumber") is not None
#               })
#       except Exception:
#           pass

# After (audit-driven fix in Session 3):

from .session_state import read_status, compute_effective_completed_sessions
# (the second import is the new one)

# ... per-set loop ...
sessions_completed = len(compute_effective_completed_sessions(path))
total_sessions: Optional[int] = None
last_touched: Optional[str] = None

# Activity log still consulted for two non-count signals:
# totalSessions (lives at the top level) and the per-step
# dateTime for the ``last touched`` display.
if os.path.isfile(activity_path):
    try:
        with open(activity_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_sessions = data.get("totalSessions")
        entries = data.get("entries", [])
        if entries:
            last_touched = max(
                (e.get("dateTime", "") for e in entries),
                default=None,
            )
    except Exception:
        pass
```

The block now mirrors the TypeScript reader's structure: array via
the helper is authoritative for the count; activity log is for
non-count signals only (totalSessions top-level field, per-step
timestamp for `last touched`).

#### Tests added

`ai_router/tests/test_print_session_set_status_completed_count.py`
contains three regression tests:

1. **`test_in_flight_session_does_not_inflate_count`** — Activity log
   has entries for sessions 1 and 2 (session 2 in flight),
   `completedSessions: [1]`, totalSessions: 4. Asserts the rendered
   table shows `1/4` and does NOT show `2/4`. This is the failure
   shape above.

2. **`test_legacy_set_without_array_falls_back_via_helper`** — A
   pre-Set-022 set with no `completedSessions[]` and no events
   ledger. The helper's last-resort `currentSession - 1` heuristic
   kicks in. currentSession=3 → sessions_completed=2, rendered as
   `2/5`. Verifies the helper's fallback chain still works.

3. **`test_done_set_uses_array_length`** — A done set with
   `completedSessions: [1,2,3,4]`, totalSessions: 4, but
   activity-log entries for sessions 1-5 (a stray rolled-back
   attempt). Asserts the count is 4 (array length, what we want),
   not 5 (activity-log distinct, the pre-fix behavior). Done sets
   render as N/N via the existing render rule; the assertion is
   about which N.

All 719 tests pass (was 716; +3 from the new file).

## What you are verifying

Read these on disk before answering:

1. `docs/session-sets/023-trust-completed-sessions-array/session-reviews/session-003-audit-findings.md` — the full audit findings table with classifications and citations.
2. `ai_router/__init__.py:1125-1200` — the modified `print_session_set_status` function.
3. `ai_router/tests/test_print_session_set_status_completed_count.py` — the three regression tests.

Answer the following in your verification verdict:

### Verification checklist

1. **Audit coverage.** Did the audit miss any obvious events-ledger
   consumer that should have been classified? Specifically, did it
   miss anything in: `ai_router/queue_db.py`, `ai_router/queue_verification.py`,
   `ai_router/session_log.py`, `ai_router/session_lifecycle.py`,
   `ai_router/orchestrator_role.py`, `ai_router/verifier_role.py`,
   `ai_router/close_out.py`, `ai_router/role_status.py`,
   `ai_router/heartbeat_status.py`, `ai_router/cost_report.py`,
   `ai_router/queue_status.py`, `ai_router/metrics.py`, OR any
   TypeScript file under `tools/dabbler-ai-orchestration/src/` other
   than the four named (extension.ts, fileSystem.ts,
   SessionSetsProvider.ts, and SessionSetsProvider tests)? You should
   only flag this if you can name a specific file + reason that the
   grep pattern would have caught it and the audit overlooked it.

2. **Sharp-edge classification soundness.**
   (a) Is the classification of `print_session_set_status` as a sharp
       edge correct? Are the failure-shape, fix shape, and test
       coverage adequate?
   (b) Is the classification of `close_session._is_already_closed`
       as correct-to-ignore (with note) defensible? Or is this
       actually a sharp edge that should have been fixed in this
       session?
   (c) Is the classification of `reconciler._evaluate_one` as
       correct-to-ignore defensible? The reconciler's job is to find
       stranded sets — does it have any whether-closed-derivation
       responsibility that the audit missed?

3. **Fix correctness.**
   (a) Does the new code correctly delegate count derivation to
       `compute_effective_completed_sessions`?
   (b) Does the helper's last-resort `currentSession - 1` heuristic
       (which emits a WARNING to stderr) introduce any
       previously-unintended log noise in the CLI's output path?
   (c) Are the three regression tests sufficient, or is there a
       specific shape the tests do not cover that the operator would
       hit in practice?

4. **Coverage of the Session 2 audit's third sharp edge concern.**
   The audit-findings document claims the systemic concern raised by
   both providers in Session 2 is "resolved on disk." Is that claim
   accurate, or is there a residual gap?

5. **Any other concerns.** Open-ended.

### Output format

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {
      "category": "audit-coverage" | "classification" | "fix-correctness" | "test-coverage" | "scope" | "other",
      "severity": "Critical" | "Major" | "Minor",
      "description": "...",
      "recommended_fix": "...",
      "citation": "file:line if applicable"
    }
  ],
  "rationale": "one-paragraph summary of how you reached the verdict"
}
```

Severity guidance: **Critical** = a sharp edge the audit missed that
would cause user-visible drift; **Major** = the fix is incorrect or
incomplete; **Minor** = doc / phrasing issue that doesn't change
behavior or invalidate the audit.


---

## Inlined: session-003-audit-findings.md

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

The system-wide concern raised by both providers in Session 2 is now
**resolved on disk**. One Python sharp edge surfaced and fixed; the
TypeScript sharp edge is Session 4's planned scope; the borderline
case (`_is_already_closed`) is documented for future re-evaluation if
a real incident surfaces it.


---

## Inlined: the modified print_session_set_status function

```python
def print_session_set_status(base_dir: str = "docs/session-sets") -> None:
    """Print a status table of every session set under *base_dir*.

    State is read from each set's ``session-state.json`` via
    :func:`read_status` (Set 7 invariant: every folder has one, lazy-synth
    fallback for any that slipped through backfill). The presence of a
    ``CANCELLED.md`` marker (Set 8) takes precedence over the status
    field — a partially-completed set the operator has cancelled
    renders as cancelled, not whatever its prior status was. Sets are
    grouped in the table by state (in-progress first, then not-started,
    then done, then cancelled), and within each group sorted by most
    recently touched.
    """
    from .session_state import read_status, compute_effective_completed_sessions
    from .session_lifecycle import is_cancelled

    if not os.path.isdir(base_dir):
        print(f"(no session-sets directory at {base_dir})")
        return

    in_progress: list[dict] = []
    not_started: list[dict] = []
    done: list[dict] = []
    cancelled: list[dict] = []

    for name in sorted(os.listdir(base_dir)):
        path = os.path.join(base_dir, name)
        if not os.path.isdir(path):
            continue
        spec_path = os.path.join(path, "spec.md")
        if not os.path.isfile(spec_path):
            continue

        activity_path = os.path.join(path, "activity-log.json")
        state_path = os.path.join(path, SESSION_STATE_FILENAME)

        # Set 023 Session 3 audit: authoritative count comes from
        # ``compute_effective_completed_sessions``, which Set 022 made
        # the single source of truth (array → events ledger → legacy
        # ``currentSession - 1`` heuristic with warning). The pre-Set-022
        # shape that lived here — ``len({entry.sessionNumber for entry
        # in activity_log.entries})`` — was the same derivation Set 022
        # Session 2 explicitly removed from the TypeScript reader
        # (``fileSystem.ts`` near readSessionSets, "Activity log is a
        # step log, not a count source"). Activity-log entries record
        # in-flight step events too, so the old shape overcounted by 1
        # whenever a session was open — a Full-tier set with
        # currentSession=2 (session 1 closed, session 2 in flight)
        # reported ``2/N`` here while the extension correctly reported
        # ``1/N``. The Python CLI status reporter was left out of the
        # Set 022 migration; this brings it into agreement with the
        # extension and the canonical invariant.
        sessions_completed = len(compute_effective_completed_sessions(path))
        total_sessions: Optional[int] = None
        last_touched: Optional[str] = None

        # Activity log still consulted for two non-count signals:
        # totalSessions (lives at the top level) and the per-step
        # dateTime for the ``last touched`` display, which is more
        # granular than the state-file's session-boundary timestamps
        # while a session is mid-flight.
        if os.path.isfile(activity_path):
            try:
                with open(activity_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                total_sessions = data.get("totalSessions")
                entries = data.get("entries", [])
                if entries:
                    last_touched = max(
                        (e.get("dateTime", "") for e in entries),
                        default=None,
                    )
            except Exception:
                pass

        if os.path.isfile(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                if total_sessions is None:
                    total_sessions = state_data.get("totalSessions")
                state_touched = state_data.get("completedAt") or state_data.get("startedAt")
                if state_touched and (not last_touched or state_touched > last_touched):
                    last_touched = state_touched
            except Exception:
                pass

        # CANCELLED.md presence beats every other state signal — a
        # partially-completed set the operator has cancelled renders as
        # cancelled, not whatever its prior status was. The marker file
        # is checked first so we do not have to teach `read_status` the
        # cancelled state (which Set 7 already does, but the on-disk
        # status field may still be in-progress / complete on
        # legacy-shape state files that pre-date Set 8's writers).
        if is_cancelled(path):
            state = "cancelled"
        else:
            # Single source of truth for non-cancelled state: read_status.
            # The "done" display label maps from the canonical "complete"
            # status. A "cancelled" status that is NOT backed by a
            # CANCELLED.md (e.g., a manually-edited state file) falls
            # through to "not-started" — operators relying on the marker
            # file alone get the same rendering whether they edited the
            # status field or not.
            status = read_status(path)
            if status == "complete":
                state = "done"
            elif status == "in-progress":
                state = "in-progress"
            else:
                state = "not-started"

        record = {
            "name": name,
            "completed": sessions_completed,
            "total": total_sessions,
            "last_touched": last_touched or "",
            "state": state,
        }

        if state == "done":
            done.append(record)
        elif state == "in-progress":
            in_progress.append(record)
        elif state == "cancelled":
            cancelled.append(record)
        else:
            not_started.append(record)

    in_progress.sort(key=lambda r: r["last_touched"], reverse=True)
    done.sort(key=lambda r: r["last_touched"], reverse=True)
    not_started.sort(key=lambda r: r["name"])
    # Cancelled sets sink to the bottom; within the group, most recently
    # touched first (mirrors the in-progress / done convention).
    cancelled.sort(key=lambda r: r["last_touched"], reverse=True)

    # ASCII-only glyphs — Windows cp1252 consoles cannot print emoji and
    # crash mid-line, losing the rest of the report (see lessons-learned
    # "Persist Routed Output To Disk Before Any Display Or Logging Side
    # Effects" for the original failure shape).
    rows = (
        [("[~]", r) for r in in_progress]
        + [("[ ]", r) for r in not_started]
        + [("[x]", r) for r in done]
        + [("[!]", r) for r in cancelled]
    )

    if not rows:
        print(f"(no session sets under {base_dir})")
        return

    name_width = max(len(r[1]["name"]) for r in rows)
    name_width = max(name_width, len("Session Set"))

    print()
    print("=" * (name_width + 32))
    print("SESSION-SET STATUS")
    print("=" * (name_width + 32))
    print(f"{'St':3}  {'Session Set':<{name_width}}  {'Progress':>10}  Touched")
    print(f"{'-' * 3}  {'-' * name_width}  {'-' * 10}  {'-' * 10}")
    for icon, r in rows:
        if r["state"] == "done":
            # Done sets show actual sessions run as both sides of the fraction.
            # total_sessions is a planning estimate; it may exceed completed
            # when optional buffer sessions are not needed.
            progress = f"{r['completed']}/{r['completed']}" if r["completed"] > 0 else "-"
        elif r["total"] not in (None, 0):
            progress = f"{r['completed']}/{r['total']}"
        elif r["completed"] > 0:
            progress = f"{r['completed']} done"
        else:
            progress = "-"
        touched = r["last_touched"][:10] if r["last_touched"] else "-"
        print(f"{icon}  {r['name']:<{name_width}}  {progress:>10}  {touched}")
    print("=" * (name_width + 32))
    legend = (
        f"  [~] in-progress: {len(in_progress)}    "
        f"[ ] not-started: {len(not_started)}    "
        f"[x] done: {len(done)}"
    )
    if cancelled:
        # The cancelled column only appears when at least one cancelled
        # set is present, mirroring the spec's tree-view rule for the
        # extension's Cancelled group ("only renders when ≥ 1 is
        # present"). Keeps the legend clean for the common case.
        legend += f"    [!] cancelled: {len(cancelled)}"
    print(legend)
    print("=" * (name_width + 32) + "\n")



```

---

## Inlined: the three new regression tests

```python
"""Set 023 Session 3 regression: ``print_session_set_status`` count
derivation must consult ``completedSessions[]`` (via the canonical
``compute_effective_completed_sessions`` helper), not the pre-Set-022
activity-log distinct-sessionNumber shape.

Failure shape the test pins:

A Full-tier set in the in-flight window — currentSession=2, session 1
closed, session 2 in flight — has activity-log entries for both
sessions 1 and 2. The pre-Set-022 derivation
``len({entry.sessionNumber for entry in entries})`` counts the
in-flight session 2 as completed, reporting 2/N. The Set 022 invariant
(``completedSessions[]`` is authoritative) and the TypeScript reader
both report 1/N. This test asserts the Python CLI agrees.

Mirror of the migration Set 022 Session 2 applied to the TypeScript
``readSessionSets``: "Activity log is a step log, not a count source."
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_ai_router():
    """Load ``ai_router`` from its package directory via importlib."""
    init = REPO_ROOT / "ai_router" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "ai_router_for_print_count_test",
        str(init),
        submodule_search_locations=[str(init.parent)],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ai_router_for_print_count_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ar():
    return _load_ai_router()


def _capture(ar, base_dir: Path) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        ar.print_session_set_status(str(base_dir))
    return buf.getvalue()


def test_in_flight_session_does_not_inflate_count(ar, tmp_path: Path) -> None:
    """A set with currentSession=2 (session 1 closed, session 2 in
    flight) reports 1/4 — not 2/4. The activity-log records both
    session numbers as having steps, but only session 1 is in
    ``completedSessions[]``.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "in-flight-shape"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 4,
            "entries": [
                {"dateTime": "2026-05-15T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-15T08:30:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-15T09:00:00-04:00", "sessionNumber": 2},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "in-progress",
            "currentSession": 2,
            "totalSessions": 4,
            "completedSessions": [1],
            "startedAt": "2026-05-15T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    assert "1/4" in out, out
    assert "2/4" not in out, out


def test_legacy_set_without_array_falls_back_via_helper(
    ar, tmp_path: Path
) -> None:
    """A pre-Set-022 set with no ``completedSessions[]`` and no events
    ledger falls through ``compute_effective_completed_sessions``'s
    last-resort ``currentSession - 1`` heuristic. currentSession=3 →
    sessions_completed=2, rendered as 2/5.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "legacy-no-array"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 5,
            "entries": [
                {"dateTime": "2026-05-10T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-11T08:00:00-04:00", "sessionNumber": 2},
                {"dateTime": "2026-05-12T08:00:00-04:00", "sessionNumber": 3},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "in-progress",
            "currentSession": 3,
            "totalSessions": 5,
            "startedAt": "2026-05-10T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    # Helper fallback: sessions_completed = currentSession - 1 = 2.
    assert "2/5" in out, out


def test_done_set_uses_array_length(ar, tmp_path: Path) -> None:
    """A done set with completedSessions=[1,2,3,4] renders 4/4, not
    whatever the activity-log entry count happens to be.
    """
    base = tmp_path / "session-sets"
    set_dir = base / "shipped"
    set_dir.mkdir(parents=True)
    (set_dir / "spec.md").write_text("# stub\n", encoding="utf-8")
    (set_dir / "change-log.md").write_text("# Changes\n", encoding="utf-8")
    (set_dir / "activity-log.json").write_text(
        json.dumps({
            "totalSessions": 4,
            # Deliberately includes a stray entry for session 5 (e.g.,
            # an abandoned attempt that got rolled back). The count
            # must not include it because session 5 is not in
            # ``completedSessions[]``.
            "entries": [
                {"dateTime": "2026-05-01T08:00:00-04:00", "sessionNumber": 1},
                {"dateTime": "2026-05-02T08:00:00-04:00", "sessionNumber": 2},
                {"dateTime": "2026-05-03T08:00:00-04:00", "sessionNumber": 3},
                {"dateTime": "2026-05-04T08:00:00-04:00", "sessionNumber": 4},
                {"dateTime": "2026-05-05T08:00:00-04:00", "sessionNumber": 5},
            ],
        }),
        encoding="utf-8",
    )
    (set_dir / "session-state.json").write_text(
        json.dumps({
            "schemaVersion": 2,
            "status": "complete",
            "currentSession": 4,
            "totalSessions": 4,
            "completedSessions": [1, 2, 3, 4],
            "startedAt": "2026-05-01T08:00:00-04:00",
            "completedAt": "2026-05-04T08:00:00-04:00",
        }),
        encoding="utf-8",
    )
    out = _capture(ar, base)
    # Done sets render as N/N (the existing render rule); the count
    # must be 4 (array length), not 5 (activity-log distinct sessions).
    assert "4/4" in out, out
    assert "5/5" not in out, out

```
