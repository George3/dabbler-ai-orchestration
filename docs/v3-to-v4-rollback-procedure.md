# v3 → v4 Migration: Rollback Procedure

> Set 047 Session 3 deliverable per spec §3.8. Owners of this
> procedure: any operator who ran `python -m ai_router.migrate_v3_to_v4
> --in-place` or the Session Sets view's "Migrate to v4 schema"
> right-click action and wants to revert.

## When to use this procedure

Roll back when **any** of the following are true after a v3 → v4
migration:

1. **The migrator reported a partial-write failure where the backup
   was already on disk.** Specifically:
   - The CLI line for the set reads `[BACKUP-FAILED]` AND the
     accompanying message mentions a path ending in
     `session-state.v3.bak.json` (i.e., the backup write SUCCEEDED but
     the subsequent state-file write failed). This is the only
     migrator-side disposition where the state file may have been
     partially or fully replaced; restore from `.bak` to get back to
     a known-good v3.
   - The extension's notification read "Migration of <set> failed: ..."
     and the reason text referenced `session-state.v3.bak.json` as
     the existing backup location.

   **The following dispositions do NOT require rollback:**
   - `WOULD-VIOLATE` — the migrator validated invariants in-memory
     and refused to write anything. The state file is untouched. Fix
     the input file (or use `git checkout`) and re-run.
   - `BACKUP-FAILED` where the message does NOT reference an existing
     `.bak` path — the backup write itself failed (typically
     permissions or disk-full), so the state file was never replaced.
     Fix the underlying filesystem issue and re-run.
   - `SKIPPED-*` — no write performed.

2. **Read-side regressions after the migration.** Symptoms include:
   - The Session Sets Explorer row displays an unexpected progress
     fraction (`X/?` or `0/N`) on a previously-clean set.
   - `python -m ai_router.close_session` rejects a close-out that
     should have proceeded (gate-check drift from v3 → v4 derivation).
   - The orchestrator block (`engine`, `provider`, `model`, `effort`,
     `chatSessionId`) disappears from a live in-progress row.
   - Cancellation state (`status: "cancelled"`, the `CANCELLED.md`
     marker) reads differently before vs. after the migration.

3. **You are on a `dabbler-ai-router` release earlier than the
   v3-shim version.** The reader-first shim from Set 047 Session 2
   ships in `dabbler-ai-router 0.9.0+` and the extension 0.22.0+ (the
   release that publishes this S3 work). Versions earlier than that
   cannot read v4 files; rolling back is the only path back to a
   readable state without upgrading the toolchain first.

4. **Belt-and-suspenders: any time the operator decides the
   migration's side effects are unwelcome and a clean v3 baseline is
   preferable.** The procedure is cheap and idempotent; there is no
   "you waited too long" penalty.

## What the migrator wrote

Each session-set directory under `docs/session-sets/<slug>/` that the
migrator touched in apply mode now contains:

- `session-state.json` — the new v4 shape (per-session metadata,
  dropped derived top-level fields).
- `session-state.v3.bak.json` — the previous v3 file, byte-equivalent
  in content (the migrator parses and re-emits with `indent=2` so the
  formatting is canonical, but the JSON values are preserved).

The migrator wrote the `.bak` BEFORE replacing `session-state.json`,
so if the `.bak` exists, it represents the file's content immediately
before the most-recent migration attempt.

## Procedure

Roll back **per session set**. Each set is independent; you can roll
back one and leave others on v4.

### Option A: Single set, via shell

```bash
cd docs/session-sets/<slug>/

# 1. Verify the .bak exists.
ls -l session-state.v3.bak.json

# 2. Inspect the .bak (sanity-check it looks like the pre-migration v3).
#    The schemaVersion field should be 3 and sessions[] should be present.
python -c "import json; d=json.load(open('session-state.v3.bak.json')); \
print('schemaVersion:', d.get('schemaVersion')); \
print('sessions len:', len(d.get('sessions') or []))"

# 3. Restore. On Linux/macOS:
mv session-state.v3.bak.json session-state.json
# On Windows PowerShell:
# Move-Item -Force session-state.v3.bak.json session-state.json
```

The set is now back on v3. Re-running the v4 migrator will recreate
the `.bak` and re-write v4 on the next apply.

### Option B: Single set, via VS Code

1. Open the session-set folder in VS Code's Explorer
   (`docs/session-sets/<slug>/`).
2. Right-click `session-state.json` → **Delete**.
3. Right-click `session-state.v3.bak.json` → **Rename** to
   `session-state.json`.
4. In the Session Sets view, right-click the set row → **Refresh**
   (or invoke "Dabbler: Refresh Session Sets" from the Command
   Palette).

### Option C: All sets at once, via shell

```bash
# From the repo root. Restores every set whose .bak exists.
for bak in docs/session-sets/*/session-state.v3.bak.json; do
  dir=$(dirname "$bak")
  echo "Restoring $dir"
  mv "$bak" "$dir/session-state.json"
done
```

PowerShell equivalent:

```powershell
Get-ChildItem -Path docs/session-sets -Filter session-state.v3.bak.json -Recurse |
  ForEach-Object {
    $target = Join-Path $_.Directory.FullName "session-state.json"
    Write-Host "Restoring $($_.Directory.FullName)"
    Move-Item -Force -Path $_.FullName -Destination $target
  }
```

## Validation after rollback

After restoring one or more sets, verify the rollback succeeded:

1. **Schema version.** Confirm `schemaVersion` is `3` again:
   ```bash
   python -c "import json; print(json.load(open('docs/session-sets/<slug>/session-state.json'))['schemaVersion'])"
   ```
   Expected output: `3`.

2. **Sessions array intact.** Confirm `sessions[]` is present and
   has the expected length:
   ```bash
   python -c "import json; d=json.load(open('docs/session-sets/<slug>/session-state.json')); print(len(d['sessions']))"
   ```

3. **No `.bak` left behind.** The rollback move consumed the `.bak`;
   `ls docs/session-sets/<slug>/session-state.v3.bak.json` should
   report "No such file or directory."

4. **Extension reads the set without error.** Open the Session Sets
   view; the restored row should show the expected progress fraction
   and the **(needs migration)** badge should reappear (because the
   set is back on v3 and Set 047's `needsMigration` detector flags
   canonical v3 as needing a v4 upgrade).

5. **Python CLI reads the set without error.** Run any read-side
   command that operates on the set, e.g.:
   ```bash
   python -m ai_router.close_session --session-set-dir docs/session-sets/<slug> --dry-run
   ```
   Should not raise on schema-version mismatch.

## Failure modes during rollback itself

- **The `.bak` does not exist.** Either the migrator never ran in
  apply mode on this set, or the operator already restored it once.
  Check `git log -- docs/session-sets/<slug>/session-state.json` for
  the pre-migration version and restore from git instead.
- **The `mv` / `Move-Item` fails with a permissions error.** The
  state file may be open in an editor. Close any IDE / editor tab
  that has `session-state.json` open and retry.
- **The restored `session-state.json` reads as malformed.** The
  migrator's `.bak` was written via the same atomic helper as
  `session-state.json` itself, so a half-written `.bak` is highly
  unlikely. If it occurs, fall back to `git checkout HEAD --
  docs/session-sets/<slug>/session-state.json`.

## Re-running the migration after rollback

The migration is idempotent and the `.bak` file is recreated on every
apply-mode run. To re-attempt the migration after fixing whatever
prompted the rollback, just run:

```bash
python -m ai_router.migrate_v3_to_v4 --in-place --only <slug>
```

Or in the extension, right-click the row → **Migrate to v4 schema**.

## Cross-references

- Audit-locked spec: [`docs/session-sets/047-state-file-schema-v4-audit/spec.md`](session-sets/047-state-file-schema-v4-audit/spec.md)
- Migrator Python source: [`ai_router/migrate_v3_to_v4.py`](../ai_router/migrate_v3_to_v4.py)
- Migrator TS source: [`tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts`](../tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts)
- Canonical schema reference (to be rewritten in Set 047 Session 6):
  [`docs/session-state-schema.md`](session-state-schema.md)
