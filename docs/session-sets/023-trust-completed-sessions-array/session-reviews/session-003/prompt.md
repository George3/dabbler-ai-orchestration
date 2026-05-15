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
