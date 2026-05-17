# Proposal: session-state v3 `sessions` ledger

**Date:** 2026-05-17  
**Status:** Draft, reviewed by Gemini Pro  
**Audience:** Dabbler AI orchestration maintainers and consumer-repo agents  
**Scope:** `docs/session-sets/<slug>/session-state.json`, `ai_router`, and the
Session Set Explorer extension

---

## Problem

`session-state.json` currently carries three progress fields that must remain
consistent with each other:

- `currentSession`
- `totalSessions`
- `completedSessions`

The intended invariant is documented, but the shape is still fragile because
the fields can drift independently. In particular, `currentSession` has carried
two subtly different meanings:

- the session currently in flight
- the most recently closed session

That ambiguity forces readers to combine `currentSession`, `completedSessions`,
`status`, and sometimes `session-events.jsonl` to answer basic questions like
"what session is active?" and "what session should run next?"

The goal is to make progress state a single-source-of-truth ledger and derive
all summary values from it.

---

## Proposed schema

Introduce schema v3 with a required `sessions` array:

```json
{
  "schemaVersion": 3,
  "sessionSetName": "example-session-set",
  "status": "in-progress",
  "lifecycleState": "work_in_progress",
  "startedAt": "2026-05-17T09:30:00-04:00",
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": {
    "engine": "codex",
    "provider": "openai",
    "model": "gpt-5.4",
    "effort": "high"
  },
  "sessions": [
    {
      "number": 1,
      "title": "HHC Inventory + Add a Client Package Draft + Tests",
      "status": "complete"
    },
    {
      "number": 2,
      "title": "Peer Review + Generalization Findings + Handoff + Close",
      "status": "in-progress"
    },
    {
      "number": 3,
      "title": "Some Other Session",
      "status": "not-started"
    }
  ]
}
```

### Why an array

Use an array of structured records instead of an object keyed by session title.

Session titles are human-facing and may change during planning. Object keys also
make ordering and numeric parsing more awkward. An array keeps ordering natural,
keeps session number as data, and leaves room for future per-session fields
without changing the top-level contract.

### Session status values

Each `sessions[]` entry uses one of:

- `"not-started"` — this session has not begun.
- `"in-progress"` — this session is currently active.
- `"complete"` — this session has closed successfully. (Revised from
  proposal's original `"done"` per operator's terminology lock 2026-05-17;
  see Revisions footer.)
- `"cancelled"` — optional future value if per-session cancellation is needed.

For v3, set-level cancellation remains controlled by the existing
`CANCELLED.md` / `RESTORED.md` mechanism.

---

## Derived values

Readers must derive the old summary concepts from `sessions`:

```text
totalSessions = sessions.length
completedSessions = sessions where status == "complete", mapped to number
currentSession = the single session where status == "in-progress", else null
nextSession = first session where status == "not-started", else null
```

This means the valid between-sessions state is explicit:

```json
"sessions": [
  { "number": 1, "title": "Session 1", "status": "complete" },
  { "number": 2, "title": "Session 2", "status": "not-started" }
]
```

There is no active `currentSession` in this state. The set is live, but no
session is in flight. The next session is derived as session 2.

---

## Invariants

Writers and readers should enforce these rules:

1. `sessions` is required and non-empty for any set with a known plan.
2. `sessions[].number` values are positive integers, unique, and sorted
   ascending.
3. At most one session may have `status: "in-progress"`.
4. A session may not be `"complete"` if an earlier session is `"not-started"` or
   `"in-progress"`, unless a future schema explicitly supports skipped
   sessions.
5. Top-level `status: "not-started"` requires every session to be
   `"not-started"`.
6. Top-level `status: "in-progress"` allows either exactly one in-progress
   session or a between-sessions state with at least one complete session and at
   least one not-started session.
7. Top-level `status: "complete"` requires every session to be `"complete"`.
8. `lifecycleState: "closed"` pairs with top-level `status: "complete"` or
   `"cancelled"` only.

When these rules fail, tools should fail loud with an actionable error instead
of trying to infer intent from contradictory state.

---

## Writer behavior

### Session start

`register_session_start(session_number=N)` should:

1. Ensure `sessions` exists, backfilling it from `spec.md` if needed.
2. Validate no other session is already `"in-progress"`.
3. Set session `N` to `"in-progress"`.
4. Leave prior sessions as `"complete"`.
5. Leave later sessions as `"not-started"`.
6. Set top-level `status` to `"in-progress"` and `lifecycleState` to
   `"work_in_progress"`.

If another session is already `"in-progress"`, the writer must fail loudly with
an actionable error. It must not force-close, overwrite, or silently advance the
previous session. Recovery belongs in explicit repair tooling, not in normal
session-start behavior.

### Session close

`close_session` / `mark_session_complete` should:

1. Validate session `N` is currently `"in-progress"` or already `"complete"` under
   an idempotent retry.
2. Set session `N` to `"complete"`.
3. If all sessions are `"complete"` and `change-log.md` is present, set top-level
   `status` to `"complete"` and `lifecycleState` to `"closed"`.
4. Otherwise leave top-level `status` as `"in-progress"` and
   `lifecycleState` as `"work_in_progress"` to represent the between-sessions
   state.

---

## Migration path

### Phase 1: read-compatible v3 support

Add parser helpers that return a normalized progress view:

```text
get_progress(state) -> {
  sessions,
  totalSessions,
  completedSessions,
  currentSession,
  nextSession,
  isBetweenSessions
}
```

For v3 files, derive all values from `sessions`.

For v2 files, synthesize `sessions` from:

1. session headings in `spec.md` for numbers and titles
2. `completedSessions[]` for `"complete"`
3. `currentSession` not in `completedSessions[]` for `"in-progress"`
4. all remaining sessions as `"not-started"`

The scaffolding path should write the planned `sessions` list directly into
`session-state.json` when the session set is created. `spec.md` remains the
source for regeneration and repair, but common readers should not need to parse
Markdown just to render current progress.

### Phase 2: dual-write

Update Full-tier writers to emit both:

- canonical v3 `sessions`
- legacy `currentSession`, `totalSessions`, and `completedSessions`

Legacy fields should be generated from `sessions`, never independently
maintained. This preserves compatibility for consumer repos and older VSIX
installs while eliminating writer-side ambiguity.

### Phase 3: reader migration

Move `ai_router`, close-out gates, repair logic, and the Session Set Explorer
to the normalized progress helper. No reader should directly interpret
`currentSession`, `totalSessions`, or `completedSessions` once this phase is
complete.

### Phase 4: stop writing legacy fields

After all active consumers have shipped v3 readers, stop writing the legacy
summary fields in new `session-state.json` files. Keep tolerant read support
for old files indefinitely.

---

## Compatibility notes

The events ledger remains authoritative for audit history: when a close-out
happened, which gate emitted it, and what repair path ran. The `sessions`
ledger is the consumer-readable lifecycle snapshot: what session is active,
what is complete, and what comes next.

This proposal does not remove `status`, `lifecycleState`, timestamps,
`verificationVerdict`, `orchestrator`, `forceClosed`, or cancellation marker
files. It only replaces the progress triple with a single structured progress
ledger.

Session titles are copied from `spec.md` for display convenience. If a title is
edited later in `spec.md`, progress semantics do not change because `number`
and `status` are authoritative. A future repair or reconciliation command may
refresh copied titles from `spec.md`; until then, title drift is cosmetic.

---

## Open questions and current recommendations

1. **Per-session metadata:** defer. Keep v3 focused on the progress ledger.
   `startedAt`, `completedAt`, `verificationVerdict`, and `orchestrator` can
   remain top-level until a later schema revision needs per-session history.
2. **Planned session source:** write the planned list directly into
   `session-state.json` at scaffold time. Use `spec.md` for regeneration and
   repair, not as a required read path for every UI refresh.
3. **Skipped sessions:** do not support a `"skipped"` status in v3. Keep the
   invariant strictly sequential; if a planned session is removed, update
   `spec.md` and reconcile the `sessions` list.

---

## Review feedback

Gemini Pro reviewed this proposal on 2026-05-17 and gave a strong approve. The
review specifically endorsed the array-of-records shape, the explicit
between-sessions state, and the phased migration path. It also asked for two
clarifications now incorporated here:

- normal writers fail loudly if a second session is started while another is
  still `"in-progress"`
- session-title drift between `spec.md` and `session-state.json` is cosmetic
  and can be handled by future reconciliation tooling

---

## Recommendation

Adopt `sessions` as the schema v3 progress ledger, using an array of structured
records. Treat `currentSession`, `totalSessions`, and `completedSessions` as
derived compatibility fields during migration, then retire them from new writes
once all readers have moved to the normalized progress helper.

This keeps the operational model simple:

- one source of truth for progress
- one derived answer for the current session
- one explicit between-sessions state
- no off-by-one inference from `currentSession`

---

## Revisions

### 2026-05-17 — operator terminology lock + GPT-5.4 implementation review

The operator locked terminology unification on `"complete"` at both
session and set level (rather than the proposal's original session-level
`"done"`). This proposal doc has been globally updated from `"done"` to
`"complete"` to match. Rationale: aligns with the existing canonical
Dabbler convention (`"complete"` at the set level), unifies the Session
Set Explorer's user-visible label (also migrating from "Done" to
"Complete"), and eliminates a class of ctelr-spec-style drift bugs.

After the spec (`docs/session-sets/030-session-state-v3-sessions-ledger/spec.md`)
was drafted from this proposal, GPT-5.4 reviewed the resulting session
plan and produced five revisions, all accepted by the operator:

1. **No publish in Session 4.** Moved final PyPI + Marketplace publish
   from Session 4 to Session 5 (after the in-extension migration UX
   ships), so operators upgrading the extension never see broken state
   on v2 files. Session 4 ships a release-candidate VSIX for internal
   smoke only.
2. **Keep dual-write as the operational steady state.** Set 030 does
   NOT drop legacy field emission. Writers emit BOTH `sessions[]` and
   the legacy fields indefinitely; a future set may flip
   "stop writing legacy" gated on consumer-repo v3-reader confirmation.
3. **Resolve terminology drift with the proposal.** (This Revisions
   entry is the proposal-side fix.)
4. **Narrow the "no direct legacy reads" lint rule.** Rephrased as:
   "No application reader may read legacy fields except through approved
   compatibility helpers." Carve-outs for `progress.py` / `progress.ts`,
   the migrator, tests, and v2 compat code are explicit.
5. **Register `spec-title-extraction` routing config in Session 1.**
   Session 5's AI-fallback depends on this task type being registered;
   landing it in Session 1 (alongside the schema work) removes a
   dependency risk.

The spec captures all five revisions as decisions D2 (proposal alignment
note), D4 (revised phase mapping), D5 (dual-write steady state), D13
(narrowed lint rule), D14 (final publish gate), D15 (Set 029 ordering),
and D16 (Lightweight ergonomics dry-run before publish).
