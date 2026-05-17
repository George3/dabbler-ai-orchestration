# Migrating `session-state.json` from v2 to v3 — consumer dry-run guide

> **Audience:** Operators of any consumer repo using
> `dabbler-ai-router` (`dabbler-platform`, `dabbler-access-harvester`,
> `dabbler-homehealthcare-accessdb`, and any future consumer) who want
> to preview what the v3 migrator will do to their `session-state.json`
> files before installing the next `dabbler-ai-router` release.
>
> **Status:** Set 030 Session 4 ships the bulk migrator
> ([`ai_router/migrate_session_state.py`](../ai_router/migrate_session_state.py))
> and runs it against this repo's 29 v2 state files. The PyPI +
> Marketplace publish moves to Session 5 (per spec D14) so operators
> upgrading the extension never see broken state on v2 files. This
> doc is the bridge: read it once before you upgrade.

## What the migrator does

`python -m ai_router.migrate_session_state` walks
`docs/session-sets/*/session-state.json` under a scan root and rewrites
each v2 file into the v3 dual-write shape:

1. Adds `schemaVersion: 3`.
2. Adds the canonical `sessions[]` array (the v3 ledger), one entry per
   session with `{ number, title, status }`.
3. Recomputes the legacy triple — `currentSession`, `totalSessions`,
   `completedSessions` — from `sessions[]` so the file is dual-write
   (v3 ledger + legacy fields both present). The legacy triple is
   never independently maintained any more; it's a derivation output.
4. Preserves every other top-level field the operator added (start /
   close timestamps, orchestrator block, verification verdict, etc.).

The migrator is **idempotent**: re-running it on a v3 file produces no
changes (the file is reported as `[skip:v3]`). Set 030 itself was
born v3 and is skipped by the in-repo migration.

## What the migrator does NOT do

- **Does not drop legacy field emission.** Per spec D5, Set 030 is the
  dual-write set. Future writers continue to emit both `sessions[]` and
  the legacy triple. A separate future set will flip "stop writing
  legacy" once all consumer repos have confirmed they read v3.
- **Does not touch other files.** `activity-log.json`, `change-log.md`,
  `disposition.json`, the events ledger — none are read or written.
- **Does not call AI services.** The default `--strategy regex`
  extracts session titles from `spec.md` headings via deterministic
  regex; zero router cost. The `--strategy ai` flag is reserved for
  Session 5's in-extension migration UX and currently raises
  `NotImplementedError` if invoked from the CLI.
- **Does not modify CANCELLED.md sets' marker.** The marker file is
  the operator-visible signal for cancellation; the migrator preserves
  the on-disk `status` field as-is (which may be `cancelled`,
  `not-started`, or any other value the operator wrote — the
  extension's tree provider treats CANCELLED.md as authoritative
  regardless).

## Running a dry-run

From the root of a consumer repo's checkout:

```bash
# Default: dry-run against docs/session-sets, regex titles
python -m ai_router.migrate_session_state --scan docs/session-sets

# Verbose: dump before/after JSON per set
python -m ai_router.migrate_session_state --scan docs/session-sets --verbose

# Machine-readable summary (for scripts / CI)
python -m ai_router.migrate_session_state --scan docs/session-sets --json

# Interactive: prompt per set (regex / generic / skip / quit)
python -m ai_router.migrate_session_state --scan docs/session-sets --strategy interactive

# Single set
python -m ai_router.migrate_session_state --only 003-my-feature --scan docs/session-sets
```

Output looks like:

```
  Bulk migrator [DRY RUN] — scan root: docs/session-sets
  Strategy: regex

  [migrated]    001-forms-detail-uat  (4 complete, 0 in-progress, 0 not-started)
  [migrated]    002-forms-browse-uat  (4 complete, 0 in-progress, 0 not-started)
  ...
  [skip:v3]     030-new-feature  (already v3)

  Summary: 5 migrated, 1 already v3, 0 skipped by operator, 0 no state file, 0 malformed, 0 would-violate.
  (dry run; rerun with --in-place to write changes)
```

If `--json` is passed, the same information arrives as a structured
payload with `counts`, `results[]`, and `before` / `after` dicts per
set. CI hooks can assert `counts.would_violate == 0` before allowing
the upgrade.

## Applying the migration

After the dry-run looks correct:

```bash
python -m ai_router.migrate_session_state --scan docs/session-sets --in-place
```

Each file is rewritten atomically (tempfile + `os.replace`) so a
partial-write can never corrupt state. Commit the migration as its own
git commit so it can be diffed and reviewed without touching unrelated
work:

```bash
git add docs/session-sets/*/session-state.json
git commit -m "Migrate session-state.json files from v2 to v3 (dual-write)"
```

## Rolling back

Every migrated file is plain JSON. To roll back:

```bash
git diff HEAD~1 -- docs/session-sets/  # see what changed
git checkout HEAD~1 -- docs/session-sets/  # revert all migrated files
```

Or per-file:

```bash
git checkout HEAD~1 -- docs/session-sets/003-my-feature/session-state.json
```

There is no in-memory state to invalidate, no migration log to undo,
no schema version to roll back inside any process — just JSON files.

## Inference rules the migrator applies

The migrator is **inferential**, not strict: it operates on existing v2
files where the operator has already decided the set's semantics, and
it has access to stronger combined signals than the read-time
`synthesize_v3_from_v2()` helper. The rules:

| v2 input | v3 output |
|---|---|
| `status: complete` + `lifecycleState: closed` | All `sessions[].status` → `complete` (force-promote-all, even if `completedSessions[]` is missing). |
| `status: complete` + `currentSession >= totalSessions` | Same as above. |
| `status: in-progress` + valid `currentSession` int | That session → `in-progress`; sessions listed in `completedSessions[]` → `complete`; rest → `not-started`. |
| `status: in-progress` + `currentSession: null` + `completedSessions: [N, ...]` | Between-sessions state. Listed sessions → `complete`; rest → `not-started`. |
| `status: not-started` | All sessions → `not-started`. |
| `status: cancelled` | Top-level `status` preserved. Sessions reflect actual completion from `completedSessions[]`. |
| `currentSession: True` / `1.0` / non-int | Filtered out at the strict-int boundary. The migrator does not silently escalate sessions based on `bool`-promoted integers. |
| `status: "completed"` or `"done"` | Canonicalized to `"complete"`. |
| Spec.md heading exists for session N | Heading text is the title. |
| Spec.md heading missing or malformed | Title falls back to `"Session N"`. |
| `--strategy generic` | All titles are `"Session N"` regardless of spec.md. |

If the inferred v3 shape would violate any of the [8 v3
invariants](session-state-schema.md), the set is reported as
`[WOULD-VIOLATE]` and the on-disk file is left untouched (even with
`--in-place`). The CLI exits with code 1 so CI hooks can catch it.

## Lightweight-tier hand-edit ergonomics

The dabbler-homehealthcare-accessdb repo runs the **Lightweight tier**,
where the orchestrator (or operator) maintains `session-state.json` by
hand — there is no router writer. The v3 shape is designed so each
session transition requires one session-level field flip:

```jsonc
// Starting a session: change ONE session-level field
{
  "sessions": [
    { "number": 1, "title": "...", "status": "in-progress" }, //  <-- not-started -> in-progress
    { "number": 2, "title": "...", "status": "not-started" }
  ]
}

// Closing a session: change ONE session-level field
{
  "sessions": [
    { "number": 1, "title": "...", "status": "complete" },    //  <-- in-progress -> complete
    { "number": 2, "title": "...", "status": "not-started" }
  ]
}
```

The set-level fields (`status`, `lifecycleState`) only flip at the
boundaries — first session start (not-started → in-progress) and last
session close (in-progress → complete). Between sessions, the
session-level flip is the only required change.

The legacy triple (`currentSession`, `completedSessions`,
`totalSessions`) is **optional** for Lightweight-tier hand edits — the
v3 reader derives every summary value from `sessions[]`. Keeping the
triple in sync makes the file easier to diff but isn't required for
correctness; the dual-write set's writers maintain it automatically
once a Full-tier writer touches the file.

For a worked end-to-end walkthrough (every step + validated through
`get_progress()`), see
[`docs/session-sets/030-session-state-v3-sessions-ledger/verification-output/lightweight-ergonomics-demo.txt`](session-sets/030-session-state-v3-sessions-ledger/verification-output/lightweight-ergonomics-demo.txt).

## When to migrate

You can migrate at any time before the GA release of
`dabbler-ai-router 0.4.0` / `dabbler-ai-orchestration 0.14.0` (Set 030
Session 5). After the GA release:

- **If you've already migrated:** nothing changes for you. Your state
  files are already v3.
- **If you haven't migrated yet:** the VS Code extension's
  activation-time scanner (Session 5 deliverable) will flag any v2
  files in the Session Set Explorer with a `(needs migration)` badge,
  and the right-click context menu offers a "Migrate to v3 schema"
  action that runs this same migrator on a single set. You can keep
  using v2 files indefinitely if you wish — the extension's read path
  is permanently v2-tolerant — but you'll see the badge.

The CLI is faster for bulk migration; the in-extension UX is more
discoverable for a single set the operator forgot.

## Set ordering note (per spec D15)

There is no ordering dependency between Set 029 (or any in-flight
work) and Set 030. If your repo has a v2 state file that was created
after the migrator's bulk run but before you install the new release,
the lazy migrator catches it on extension activation.

## Pre-RC smoke test (Set 030 Session 4)

This repo (`dabbler-ai-orchestration`) shipped the migrator in Set 030
Session 4 and used it to migrate all 29 of its own v2 state files in a
single in-place run. The summary:

```
Summary: 29 migrated, 1 already v3, 0 skipped by operator,
         0 no state file, 0 malformed, 0 would-violate.
```

All 29 migrated files round-trip through `read_progress()` cleanly.
The `currentSession: 3 → null` change on closed sets is the correct v3
derived value — after close, no session is in-progress, so the legacy
field becomes `null`. This matches what Session 2's
`_flip_state_to_closed` writer would emit on a freshly-closed v3 set.

## Reporting issues

If the dry-run shows a set marked `[WOULD-VIOLATE]` and you can't tell
from the error message why, capture the full `--verbose --json` output
for that set and open an issue against this repo with the redacted
state file content attached. Include your repo's tier (Full or
Lightweight).

## Cross-references

- Schema reference: [`docs/session-state-schema.md`](session-state-schema.md)
- v2-vs-v3 narrative: [`docs/session-state-schema-example.md`](session-state-schema-example.md)
- Spec: [`docs/session-sets/030-session-state-v3-sessions-ledger/spec.md`](session-sets/030-session-state-v3-sessions-ledger/spec.md)
- Proposal: [`docs/proposals/2026-05-17-session-state-sessions-ledger-v3.md`](proposals/2026-05-17-session-state-sessions-ledger-v3.md)
