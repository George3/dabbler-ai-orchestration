# session-state.json schema — `docs/session-sets/<slug>/session-state.json`

The machine-readable lifecycle file for every session set. The Session
Set Explorer extension, `ai_router`'s `close_session`, the cancel /
restore commands, and the cost dashboard all read it; on Full tier
`ai_router` writes it, on Lightweight tier the human (or AI
orchestrator) maintains it by hand.

The schema is **strict where machines parse**: a fixed field set with
canonical string values for `status` and `lifecycleState`. Field-name
drift or status-value drift causes silent display bugs in the
extension — the ctelr-spec 1/2 + 2/3 episode (2026-05-12) was a
hand-written file with `status: "completed"` (past participle) instead
of `"complete"`, which displayed as N−1/N until the count derivation
was canonicalized in extension v0.13.10.

## v3 is canonical; v2 read support is permanent

Set 030 (proposal at
`docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`)
replaced the v2 progress triple (`currentSession` /
`totalSessions` / `completedSessions`) with a single canonical
`sessions[]` ledger. **New writes always use v3.** v2 files keep
working: the read-time synthesizer at
[`ai_router/progress.py`](../ai_router/progress.py) normalizes v2 to
a v3 view on the fly, and tolerant v2 read support is permanent.

Dual-write of legacy fields is the operational steady state through
this set (per Set 030 D5): Full-tier writers emit BOTH `sessions[]`
and the legacy triple, so consumer repos pinned to older versions of
the extension or the router keep working through the migration. A
future set may flip "stop writing legacy" once every consumer has
confirmed v3-reader support.

## When this applies

Every directory under `docs/session-sets/<slug>/` that contains a
`spec.md`. The state file sits next to `spec.md`, `activity-log.json`,
and `change-log.md`. A directory with a spec but no state file is
lazy-synthesized on first read (`ensureSessionStateFile` in the
extension; `ensure_state_file` in the router), which infers the
initial status from current file presence and writes a v3 skeleton.

The schema applies to all four Dabbler consumer repos and to any new
repo adopted through the bootstrap prompt.

---

## Reader contract — every reader uses `get_progress()`

There is exactly one reader path:

- **Python:** `from ai_router.progress import get_progress`
  (or, when reading a v2 file: `synthesize_v3_from_v2(state, spec_md_path)`
  first, then `get_progress(state)`).
- **TypeScript (extension):** `import { getProgress } from "../utils/progress";`
  (with `synthesizeV3FromV2(state, specMdPath)` for v2 inputs).

The helper returns a `ProgressView` with every derived field already
populated. Readers **MUST NOT** directly interpret `currentSession`,
`totalSessions`, or `completedSessions` — those fields are legacy
compatibility surface and the writer derives them from `sessions[]`.
Direct reads risk re-introducing the off-by-one and drift bugs that
motivated v3.

Set 030 Session 3 ships a lint rule that fails CI on any direct
legacy-field read inside application code (`ai_router/` and the
extension's `src/`), with explicit carve-outs for `progress.py` /
`progress.ts` themselves, the migrator, tests, and v2 compat code.

---

## v3 schema shape

A conforming v3 `session-state.json` is a JSON object with these
fields:

```json
{
  "schemaVersion": 3,
  "sessionSetName": "<slug matching the directory name>",
  "status": "not-started" | "in-progress" | "complete" | "cancelled",
  "lifecycleState": "work_in_progress" | "closed" | null,
  "startedAt": "<ISO 8601 timestamp | null>",
  "completedAt": "<ISO 8601 timestamp | null>",
  "verificationVerdict": "VERIFIED" | null,
  "orchestrator": { "engine": "...", "provider": "...", "model": "...", "effort": "..." } | null,
  "sessions": [
    { "number": 1, "title": "Schema doc + helper", "status": "complete" },
    { "number": 2, "title": "Writers + scaffolding", "status": "in-progress" },
    { "number": 3, "title": "Reader migration",     "status": "not-started" }
  ]
}
```

### Field-by-field

| Field | Type | Purpose |
|---|---|---|
| `schemaVersion` | int (currently `3`) | Schema gate; bump when breaking. |
| `sessionSetName` | string | Must equal the parent directory's basename. |
| `status` | enum (see below) | Canonical top-level lifecycle state. Drives Done/Active bucketing in the extension. |
| `lifecycleState` | enum or null | Coarser-grained machine-readable lifecycle (close-out's view). |
| `startedAt` | ISO 8601 or null | First session start time. |
| `completedAt` | ISO 8601 or null | Final session completion time. |
| `verificationVerdict` | `"VERIFIED"` or null | Set by `close_session` after all gates pass. |
| `orchestrator` | object or null | Engine / provider / model / effort that ran the set. Null for hand-driven Lightweight runs. |
| `sessions` | array of objects | The canonical progress ledger. See below. |

### `sessions[]` — the canonical progress ledger

Each entry is an object with three required fields:

| Field | Type | Purpose |
|---|---|---|
| `number` | positive int | 1-indexed session number. Unique within the array, sorted ascending. |
| `title` | string | Display title, copied from `spec.md`'s `### Session K of N: <title>` heading. Cosmetic — drift between `spec.md` and the state file is benign. |
| `status` | enum (see below) | Per-session lifecycle state. |

`number` and `status` are authoritative for progress semantics; `title`
exists so consumers don't have to re-parse `spec.md` for every UI
refresh. A future repair command may refresh stale titles from
`spec.md`; until then, title drift is cosmetic (per the Set 030
Gemini-approved clarification).

### Dual-write legacy fields (Set 030 steady state)

Through this set and indefinitely after, Full-tier writers also emit
the legacy progress triple, derived from `sessions[]`:

```json
{
  ...,
  "currentSession": 2,
  "totalSessions": 3,
  "completedSessions": [1]
}
```

These three fields are **observability only** in v3 — they exist so
older readers (consumer repos still on a pre-v3 extension, ad-hoc
scripts, the cost dashboard's legacy paths) keep working. They are
never the source of truth; if the dual-write parity test ever flags a
disagreement between `sessions[]` and the legacy triple, the bug is
on the writer side and the legacy values must be regenerated from
`sessions[]`.

---

## Status — the canonical glossary

### Top-level `status`

Exactly one of four values; same vocabulary as the per-session
ledger:

- `"not-started"` — no session has begun.
- `"in-progress"` — at least one session has begun and not all are
  complete. **Includes the between-sessions state** (one session
  closed, the next not yet started).
- `"complete"` — every session in `sessions[]` is `"complete"`.
- `"cancelled"` — set was cancelled mid-flight. Filename
  (`CANCELLED.md`) is the primary marker; `status: "cancelled"`
  follows.

**Aliases tolerated on read, never written:** the canonicalizer in
both helpers maps `"completed"` and `"done"` to `"complete"`. The
canonicalization keeps legacy files functional but **all new writes
must emit the canonical token**. Drift to `"completed"` or `"done"`
is a bug in the writer, not a valid alternate spelling.

> **Terminology note (Set 030):** the Session Set Explorer's display
> label has been unified from "Done" to "Complete" everywhere it
> appears (rendered tree labels, viewsWelcome text, README
> screenshots). The JSON canonical token and the display label now
> match: one word, one mental model. The legacy "Done" string only
> survives as an internal bucketing type alias
> (`SessionState = "done" | ...`) and the read-time alias map.

### Per-session `sessions[].status`

Three accepted values today:

- `"not-started"` — this session has not begun.
- `"in-progress"` — this session is currently active. **At most one
  session may be in this state at a time** (invariant rule 3).
- `"complete"` — this session has closed successfully.

**Not accepted:** `"cancelled"` at the session level is reserved
for a future schema. Set 030 only exercises set-level cancellation
(`CANCELLED.md` filename marker plus top-level
`status: "cancelled"`). Validators raise
`SessionStateInvariantError(rule=2)` if a session entry uses it.

### `lifecycleState` — the coarse machine view

Exactly one of:

- `null` — set is `not-started`; nothing to track.
- `"work_in_progress"` — at least one session has begun; the set is
  still live for close-out and queue routing.
- `"closed"` — final close-out has run. Pairs with
  `status: "complete"` or `status: "cancelled"` only (invariant rule
  8).

---

## Derived values — the `get_progress()` view

`get_progress(state)` returns:

```text
sessions            = state.sessions
totalSessions       = sessions.length
completedSessions   = [s.number for s in sessions if s.status == "complete"]
currentSession      = the single session where s.status == "in-progress", else null
nextSession         = first session where s.status == "not-started", else null
isBetweenSessions   = currentSession is null
                      AND completedSessions is non-empty
                      AND nextSession is not null
```

The `isBetweenSessions` predicate is what the extension's tree view
uses to distinguish a fresh-start row from a "set is live but no
session is active right now" row, and to decide whether to render the
"session N in flight" annotation.

---

## Invariants — the 8 v3 rules

Writers and readers enforce these rules; violations raise
`SessionStateInvariantError` (Python) /
`SessionStateInvariantError` (TypeScript) with the violated rule
number and an actionable message. **Fail loud, never silently
recover.** Recovery lives in explicit repair tooling
(`close_session --repair`, future `migrate_session_state`); the
normal writers and the read-side validator never paper over a
violation.

1. **`sessions` is required and non-empty** for any set with a
   known plan.
2. **`sessions[].number` values are positive integers, unique, and
   contiguous starting at 1** (per spec decision D12: skipped
   sessions are not supported; the invariant is *strict sequential*,
   so `[1, 3]` is rejected, not just `[2, 1]`). Each entry's
   `status` must be one of `"not-started"`, `"in-progress"`, or
   `"complete"` — **session-level `"cancelled"` is reserved for a
   future schema** and rejected today.
3. **At most one session may have `status: "in-progress"`.**
4. **No session may be `"complete"` if an earlier session is
   `"not-started"` or `"in-progress"`.** Complete sessions form a
   contiguous prefix.
5. **Top-level `status: "not-started"`** requires every session to
   be `"not-started"`.
6. **Top-level `status: "in-progress"`** allows either exactly one
   in-progress session OR a between-sessions state (≥1 complete, ≥1
   not-started, 0 in-progress).
7. **Top-level `status: "complete"`** requires every session to be
   `"complete"`. The synthesizer is intentionally non-papering: a
   v2 file with `status: "complete"` but an incomplete
   `completedSessions[]` ledger is surfaced as a rule-7 violation
   rather than coerced into a "consistent" shape.
8. **`lifecycleState: "closed"`** pairs with top-level
   `status: "complete"` or `"cancelled"` only. This rule fires even
   when top-level `status` is absent — a state with
   `lifecycleState: "closed"` and missing `status` is internally
   inconsistent regardless.

> **Shape-vs-invariant errors.** Unknown top-level `status` values
> (typos, future tokens) raise `SessionStateInvariantError(rule=2)`
> as a structural/enum error, not rule 5/6/7 specifically — those
> rules are about consistency between top-level and per-session
> states, not about the top-level vocabulary itself.

---

## Lightweight tier — one-field-flip worked example

The Lightweight tier maintains `session-state.json` by hand. The v3
shape is deliberately optimized so each session transition is a
**single-field edit** to one `sessions[]` entry, plus an optional
top-level `status` flip on the first/last transition.

Starting state (fresh set, 3 sessions planned):

```json
{
  "schemaVersion": 3,
  "sessionSetName": "002-extraction-pipeline",
  "status": "not-started",
  "lifecycleState": null,
  "startedAt": null,
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": null,
  "sessions": [
    { "number": 1, "title": "Discover sources", "status": "not-started" },
    { "number": 2, "title": "Extract + normalize", "status": "not-started" },
    { "number": 3, "title": "Load + verify", "status": "not-started" }
  ]
}
```

### Start session 1

- Flip `sessions[0].status`: `"not-started"` → `"in-progress"`
- Flip top-level `status`: `"not-started"` → `"in-progress"`
- Flip `lifecycleState`: `null` → `"work_in_progress"`
- Set `startedAt` to today's ISO timestamp

(The top-level flips happen only on the first session's start.)

### Close session 1

- Flip `sessions[0].status`: `"in-progress"` → `"complete"`

That's it. No other edits required. The top-level `status` stays
`"in-progress"` because session 2 has not started yet — this is the
canonical between-sessions state.

### Start session 2

- Flip `sessions[1].status`: `"not-started"` → `"in-progress"`

One edit.

### Close session 2

- Flip `sessions[1].status`: `"in-progress"` → `"complete"`

One edit.

### Start + close session 3 (final)

- Start: flip `sessions[2].status`: `"not-started"` →
  `"in-progress"`
- Close: flip `sessions[2].status`: `"in-progress"` → `"complete"`
- Final-close additional flips: top-level `status` →
  `"complete"`, `lifecycleState` → `"closed"`, set `completedAt` to
  today's ISO timestamp.

The Set 030 D10 ergonomic test (Session 4) replays this exact
sequence against a real `dabbler-homehealthcare-accessdb` state file
to confirm the one-field-flip property holds end-to-end before the GA
release.

---

## Worked examples (v3)

### Not-started

```json
{
  "schemaVersion": 3,
  "sessionSetName": "022-next-up",
  "status": "not-started",
  "lifecycleState": null,
  "startedAt": null,
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": null,
  "sessions": [
    { "number": 1, "title": "Plan",   "status": "not-started" },
    { "number": 2, "title": "Build",  "status": "not-started" },
    { "number": 3, "title": "Verify", "status": "not-started" }
  ]
}
```

`get_progress()` returns
`currentSession=None`, `nextSession=1`, `isBetweenSessions=False`.

### Mid-set, session 2 in flight

```json
{
  "schemaVersion": 3,
  "sessionSetName": "021-developer-approachability",
  "status": "in-progress",
  "lifecycleState": "work_in_progress",
  "startedAt": "2026-05-11T14:30:00-04:00",
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": {
    "engine": "claude-code",
    "provider": "anthropic",
    "model": "claude-opus-4-7",
    "effort": "normal"
  },
  "sessions": [
    { "number": 1, "title": "Pull together quick-start",       "status": "complete" },
    { "number": 2, "title": "Wire the wizard into onboarding", "status": "in-progress" },
    { "number": 3, "title": "Marketplace launch checklist",    "status": "not-started" },
    { "number": 4, "title": "Final round of dogfood feedback", "status": "not-started" }
  ]
}
```

`get_progress()` returns `currentSession=2`, `nextSession=3`,
`completedSessions=[1]`, `isBetweenSessions=False`. The extension's
tree view renders this as `1/4 · session 2 in flight`.

### Between sessions

Session 1 has closed; session 2 has not yet started. Top-level status
is still `in-progress` (the set is live), but no session is in
flight.

```json
{
  "schemaVersion": 3,
  "sessionSetName": "030-session-state-v3-sessions-ledger",
  "status": "in-progress",
  "lifecycleState": "work_in_progress",
  "startedAt": "2026-05-17T05:00:00-04:00",
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": { "engine": "claude", "provider": "anthropic", "model": "claude-opus-4-7", "effort": "high" },
  "sessions": [
    { "number": 1, "title": "Schema doc + get_progress() helper + v2-read synthesizer", "status": "complete" },
    { "number": 2, "title": "Dual-write writers + scaffolding",                          "status": "not-started" },
    { "number": 3, "title": "Reader migration + Explorer label",                         "status": "not-started" },
    { "number": 4, "title": "Bulk migrator + in-repo migration + RC build",              "status": "not-started" },
    { "number": 5, "title": "Migration UX + loading state + final release",              "status": "not-started" }
  ]
}
```

`get_progress()` returns `currentSession=None`, `nextSession=2`,
`completedSessions=[1]`, `isBetweenSessions=True`. The extension's
tree view renders this as `1/5` plain (no in-flight annotation).

### Complete

```json
{
  "schemaVersion": 3,
  "sessionSetName": "021-developer-approachability",
  "status": "complete",
  "lifecycleState": "closed",
  "startedAt": "2026-05-11T14:30:00-04:00",
  "completedAt": "2026-05-13T18:45:00-04:00",
  "verificationVerdict": "VERIFIED",
  "orchestrator": {
    "engine": "claude-code",
    "provider": "anthropic",
    "model": "claude-opus-4-7",
    "effort": "normal"
  },
  "sessions": [
    { "number": 1, "title": "Pull together quick-start",       "status": "complete" },
    { "number": 2, "title": "Wire the wizard into onboarding", "status": "complete" },
    { "number": 3, "title": "Marketplace launch checklist",    "status": "complete" },
    { "number": 4, "title": "Final round of dogfood feedback", "status": "complete" }
  ]
}
```

---

## Cancel / restore

Cancellation is tracked by **file presence** (`CANCELLED.md` /
`RESTORED.md`), not by `status: "cancelled"` alone. The extension's
bucketing rule is filename-first: `CANCELLED.md` present → tree
state is Cancelled regardless of `status`. The `cancelLifecycle`
helpers keep `status` in lockstep with the markdown markers so the
two signals don't diverge; manual edits resolve via the file-presence
path.

Per-session cancellation is reserved for a future schema. v3 readers
tolerate `"cancelled"` in `sessions[]` but no v3 writer emits it.

---

## Lazy synthesis (file-absent branch)

A folder with `spec.md` but no `session-state.json` triggers
`ensureSessionStateFile` (extension) / `ensure_state_file` (router),
which infers a starting shape from current file presence:

| Files present | Inferred `status` | Inferred `lifecycleState` |
|---|---|---|
| `change-log.md` | `"complete"` | `"closed"` |
| `activity-log.json` (no change-log) | `"in-progress"` | `"work_in_progress"` |
| Neither | `"not-started"` | `null` |

Both writers also seed `sessions[]` by parsing `spec.md` headings
(`### Session K of N: <title>`); when the spec has no headings, they
fall back to generic `"Session N"` titles up to the planned count.

---

## Tier expectations

- **Full tier** (`Workflow: Full` in the spec frontmatter): `ai_router`
  writes the state file on every session boundary.
  - `start_session`: validates no other session is in-progress
    (invariant rule 3), flips `sessions[N-1].status` to
    `"in-progress"`, sets top-level `status` and `lifecycleState`
    accordingly, sets `startedAt` if previously null. Always backfills
    `sessions[]` from `spec.md` if absent.
  - `close_session`: validates `sessions[N-1].status` is
    `"in-progress"` (or already `"complete"` under idempotent
    retry), flips it to `"complete"`, then re-derives top-level
    status (rule 6/7) and lifecycleState (rule 8). Final close also
    sets `completedAt` and `verificationVerdict`.
- **Lightweight tier** (`Workflow: Lightweight`): no router writes.
  The human or AI orchestrator maintains the file by hand on each
  session boundary using the one-field-flip recipe above. **Always
  include and maintain `sessions[]`** — it is the only authoritative
  progress signal under hand-maintenance.

---

## Reading a v2 file (compat path)

Before v3 reaches every consumer repo, readers will still encounter
v2 files in the wild. The compat path is:

1. Read the file as JSON. Check `schemaVersion`.
2. If `schemaVersion == 3`: pass directly to `get_progress(state)`.
3. If `schemaVersion == 2` (or missing): call
   `synthesize_v3_from_v2(state, spec_md_path)` first. The
   synthesizer returns a NEW dict (does not mutate the input) with
   `sessions[]` derived from `completedSessions[]`, `currentSession`,
   and `spec.md` titles. Pass the result to `get_progress()`.
4. The Session 5 bulk migrator (`python -m
   ai_router.migrate_session_state`) is the eventual one-shot path
   for converting v2 files in place. Until then, the read-side
   synthesizer is the daily-driver path.

### v2 → v3 default-to-not-started rule

The synthesizer follows the project's
`feedback_default_not_started_evidence_to_escalate` rule: every
session defaults to `"not-started"` and is only escalated when
concrete evidence is present:

- A session escalates to `"complete"` **only** if its number is
  present in v2's `completedSessions[]` as a strict positive integer
  (not `true`, not `1.0`).
- A session escalates to `"in-progress"` **only** if it equals v2's
  `currentSession` AND the top-level status is `"in-progress"` AND
  the session is not already complete.
- All other sessions stay `"not-started"`.

This biases conservatively: a hand-edited v2 file with ambiguous
fields reads as less progressed than it might be, which the operator
can fix by hand, rather than reading as more progressed and silently
producing wrong "X/N" counts.

**The synthesizer does not "fix" contradictions.** A v2 file with
top-level `status: "complete"` but an incomplete
`completedSessions[]` is reported faithfully: the named-complete
sessions are `"complete"`, the rest are `"not-started"`, and the
contradiction surfaces as a rule-7 violation on the next
`get_progress()` call. Per the "fail loud, never silently recover"
rule, the operator (or a repair tool) is responsible for resolving
the inconsistency before the file becomes readable. Earlier drafts
of the synthesizer force-promoted every session to complete in this
case; that papered over real human errors and was removed.

---

## Migration recipe (one-time, for legacy v1/v2 files)

The bulk migrator in Set 030 Session 4 will run this recipe
automatically on every state file under `docs/session-sets/`. For
ad-hoc hand-migration of a single file:

1. Run `synthesize_v3_from_v2()` on the existing state with the set's
   `spec.md` path. The returned dict is the v3 shape.
2. Inspect the synthesized `sessions[]` titles. Edit any that the
   regex got wrong (titles drift on hand-rewritten specs).
3. Bump `schemaVersion` to `3`.
4. Remove the legacy progress triple — or leave them in place if the
   file will be read by an old reader; the dual-write contract treats
   the triple as compat surface and ignores it on the source-of-truth
   path.
5. Write the file back. The next `start_session` /
   `close_session` invocation will rewrite the dual-write shape and
   normalize anything that drifted further.

Lifecycle-state and status-token migration recipes are unchanged from
v2:

- Rewrite `status: "completed"` → `"complete"` and
  `status: "done"` → `"complete"`.
- Rewrite `lifecycleState: "done"` / `"active"` / `"finished"` to
  the canonical `"closed"` (terminal) or `"work_in_progress"`
  (live).

---

## Bucketing in the Session Sets Explorer (v3)

The extension's tree view buckets each row from `get_progress()` plus
filename signals:

- `CANCELLED.md` present → **Cancelled** (filename wins).
- Else top-level `status === "complete"` and `isBetweenSessions ===
  false` → **Complete** (the user-visible label that was "Done"
  through v0.13.x).
- Else top-level `status === "in-progress"` → **Active**.
- Else → **Not Started**.

The "not mid-set" guard (`isMidSetComplete` in
`tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`) consults
the same `sessions[]` ledger as `get_progress()`; v3 makes the guard
trivial since "every session complete" is directly readable. The
legacy `completedSessions[]` + events-ledger fallback paths described
in earlier versions of this doc are still tolerated for reading old
files but are not exercised by v3 writers.

---

## Drift check

The v3 example file at `docs/session-state-schema-example.json` is
the canonical reference. A future drift check (Session 4 of Set 030
or later) will regenerate it from the live schema constants and
fail-loud when the documented example and the live writer
disagree. Until then, keep them in sync by hand when either changes.
