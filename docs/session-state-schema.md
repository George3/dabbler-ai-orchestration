# session-state.json schema — `docs/session-sets/<slug>/session-state.json`

The machine-readable lifecycle file for every session set. The Session
Set Explorer extension, `ai_router`'s `close_session`, the cancel /
restore commands, and the cost dashboard all read it; on Full tier
`ai_router` writes it, on Lightweight tier the human (or AI orchestrator)
maintains it by hand.

The schema is **strict where machines parse**: a fixed field set with
canonical string values for `status` and `lifecycleState`. Field-name
drift or status-value drift causes silent display bugs in the
extension — the ctelr-spec 1/2 + 2/3 episode (2026-05-12) was a
hand-written file with `status: "completed"` (past participle) instead
of `"complete"`, which displayed as N−1/N until the count derivation
was canonicalized in extension v0.13.10.

## When this applies

Every directory under `docs/session-sets/<slug>/` that contains a
`spec.md`. The state file sits next to `spec.md`, `activity-log.json`,
and `change-log.md`. A directory with a spec but no state file is
lazy-synthesized on first read by `ensureSessionStateFile` (mirrored in
`ai_router/session_state.py` and `tools/.../utils/sessionState.ts`),
which infers the initial status from current file presence.

The schema applies to all four Dabbler consumer repos and to any new
repo adopted through the bootstrap prompt.

## Required fields

A conforming `session-state.json` is a JSON object with these fields:

```json
{
  "schemaVersion": 2,
  "sessionSetName": "<slug matching the directory name>",
  "currentSession": <int | null>,
  "totalSessions": <int | null>,
  "status": "not-started" | "in-progress" | "complete" | "cancelled",
  "lifecycleState": "closed" | "work_in_progress" | null,
  "startedAt": "<ISO 8601 timestamp | null>",
  "completedAt": "<ISO 8601 timestamp | null>",
  "verificationVerdict": "VERIFIED" | null,
  "orchestrator": { "engine": "...", "provider": "...", "model": "...", "effort": "..." } | null
}
```

### Field-by-field

| Field | Type | Purpose |
|---|---|---|
| `schemaVersion` | int (currently `2`) | Schema gate; bump when breaking. |
| `sessionSetName` | string | Must equal the parent directory's basename. |
| `currentSession` | int or null | 1-indexed; `null` only when status is `"not-started"`. |
| `totalSessions` | int or null | Planned session count. May be `null` if uncertain; the extension also reads `totalSessions` from spec.md's yaml block. |
| `status` | enum (see below) | Canonical lifecycle state. **Drives Done/Active bucketing and count derivation in the extension.** |
| `lifecycleState` | enum or null | Coarser-grained machine-readable lifecycle (close-out's view). |
| `startedAt` | ISO 8601 or null | First session start time. |
| `completedAt` | ISO 8601 or null | Final session completion time. |
| `verificationVerdict` | `"VERIFIED"` or null | Set by `close_session` after all gates pass. |
| `orchestrator` | object or null | Engine / provider / model that ran the set. Null for fully-hand-driven Lightweight runs. |

## Status — the canonical string

Exactly one of four values:

- `"not-started"` — no work yet; `currentSession` should be `null`.
- `"in-progress"` — at least one session has begun and not all are complete.
- `"complete"` — all sessions completed; close-out has run (or, on Lightweight, the human has confirmed).
- `"cancelled"` — set was cancelled mid-flight. See `## Cancel / restore` below.

**Aliases tolerated on read, never written:** the extension's `readStatus()`
and `ai_router.session_state` both canonicalize `"completed"` and `"done"`
to `"complete"` at the read boundary (`STATUS_ALIASES` in
`tools/dabbler-ai-orchestration/src/utils/sessionState.ts`). The
canonicalization keeps legacy files functional but **all new writes must
emit the canonical token**. Drift to `"completed"` or `"done"` is a bug
in the writer, not a valid alternate spelling.

## lifecycleState — the coarse machine view

Exactly one of:

- `null` — set is `not-started`; nothing to track.
- `"work_in_progress"` — at least one session has begun; the set is still
  live for close-out and queue routing.
- `"closed"` — final close-out has run. Pairs with `status: "complete"`
  or `status: "cancelled"` (via cancel-flow markers).

`lifecycleState: "done"`, `"active"`, `"finished"`, or any other value
is **not** canonical. The extension's bucketing uses `status` first
(via the alias map) and `lifecycleState` only as a tiebreaker; a mismatch
won't crash the UI but it surfaces in events-ledger audits and may
confuse other consumers.

## Optional fields

### `completedSessions: number[]` (recommended on Lightweight tier)

Array of 1-indexed session numbers that have been completed. Schema v2's
authoritative signal for the "X done out of N" display.

When present, the extension uses `completedSessions.length` directly. When
absent, it falls back to deriving from `status` (`"complete"` → all done)
or `currentSession − 1` (assumes the latest session is in flight). On
Lightweight tier — where there's no `ai_router` writer — including this
array eliminates the off-by-one ambiguity.

```json
{ ..., "completedSessions": [1, 2, 3] }
```

### `forceClosed: boolean`

Set by `close_session --force` to record that gates were bypassed.
Observability only; doesn't change UI behavior.

### `orchestrator.effort`

Optional `"low"`, `"medium"`, or `"high"` hint carried through to the
provider.

## Cancel / restore

Cancellation is tracked by **file presence** (`CANCELLED.md` /
`RESTORED.md`), not by a `status: "cancelled"` field alone. The
extension's bucketing rule (per Set 008's spec) is filename-first:
`CANCELLED.md` present → tree state is Cancelled regardless of
`status`. The `cancelLifecycle` helpers in `ai_router` and the
extension keep `status` in lockstep with the markdown markers so the
two signals don't diverge; manual edits resolve via the file-presence
path.

## Lazy synthesis (file-absent branch)

A folder with `spec.md` but no `session-state.json` triggers
`ensureSessionStateFile`, which infers a starting shape from current
file presence:

| Files present | Inferred `status` | Inferred `lifecycleState` |
|---|---|---|
| `change-log.md` | `"complete"` | `"closed"` |
| `activity-log.json` (no change-log) | `"in-progress"` | `"work_in_progress"` |
| Neither | `"not-started"` | `null` |

Both the TS and Python writers must produce structurally identical
content — concurrent synthesis under a race resolves last-rename-wins
without confusion.

## Tier expectations

- **Full tier** (`Workflow: Full` in the spec frontmatter): `ai_router`
  writes the state file on every session boundary. `completedSessions`
  is currently optional but planned; until then, `ai_router` flips
  `status` to `"complete"` after the final session and the extension
  uses the `state === "done"` derivation.
- **Lightweight tier** (`Workflow: Lightweight`): no router writes. The
  human or AI orchestrator maintains the file by hand on each session
  boundary. **Include `completedSessions` explicitly** — it removes
  the off-by-one risk and is the only authoritative count signal under
  hand-maintenance.

## Worked examples

### Lightweight tier, all sessions complete

```json
{
  "schemaVersion": 2,
  "sessionSetName": "002-extraction-pipeline",
  "currentSession": 3,
  "totalSessions": 3,
  "status": "complete",
  "lifecycleState": "closed",
  "startedAt": "2026-05-12",
  "completedAt": "2026-05-12",
  "verificationVerdict": null,
  "orchestrator": null,
  "completedSessions": [1, 2, 3]
}
```

### Full tier, mid-set

```json
{
  "schemaVersion": 2,
  "sessionSetName": "021-developer-approachability",
  "currentSession": 2,
  "totalSessions": 4,
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
  }
}
```

### Not started

```json
{
  "schemaVersion": 2,
  "sessionSetName": "022-next-up",
  "currentSession": null,
  "totalSessions": 3,
  "status": "not-started",
  "lifecycleState": null,
  "startedAt": null,
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": null
}
```

## Parser cheat-sheet (for AI orchestrators and tooling)

Reading the canonical state of a folder:

1. Parse `session-state.json` as a JSON object.
2. Read `status`; canonicalize via the alias map (`"completed"` →
   `"complete"`, `"done"` → `"complete"`).
3. Read `completedSessions` if present; that's the authoritative count.
4. Else if canonical `status === "complete"`, count = `totalSessions`.
5. Else fall back to `currentSession − 1`. This is an estimate; emit
   `completedSessions` to avoid it.

Bucketing in the Session Sets Explorer:

- `CANCELLED.md` present → Cancelled (filename wins).
- Else canonical `status === "complete"` and not mid-set → Done.
- Else canonical `status === "in-progress"` → Active.
- Else → Not Started.

## Migration

For consumer repos carrying pre-Set-7 drift:

1. Rewrite `status: "completed"` → `"complete"` and `status: "done"` →
   `"complete"`.
2. Rewrite `lifecycleState: "done"` / `"active"` / `"finished"` to the
   canonical `"closed"` (for terminal states) or `"work_in_progress"`
   (for live ones).
3. On Lightweight tier, add `completedSessions: [1, 2, ...]` listing
   every session that has completed.
4. Leave timestamps and other observability fields alone unless
   demonstrably wrong.

The extension tolerates the unmigrated state files via the read-boundary
alias map (since v0.13.10), so this migration can be done at leisure
without breaking the UI. Migrate to keep the files self-describing for
non-extension readers and to remove the off-by-one estimation.
