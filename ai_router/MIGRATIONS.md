# Session-state schema migrations

`session-state.json` has evolved through four schema versions. The
current version this package writes and reads is **v4** (see
`SESSION_STATE_SCHEMA_VERSION` in `progress.py` / the bundled JS
constant). Readers tolerate older shapes transparently via
`normalize_to_v4_shape`, so **migrating on disk is optional** — "old
schema is acceptable" (Set 050). You only need these tools when you want
to *rewrite* old files to the current shape (e.g. before an audit, or to
silence the lifecycle drift advisory).

## The migrators are version-specific and must run in sequence

There is deliberately **no single auto-upgrade command**. Each migrator
handles exactly one transition, and the module names encode the
direction:

| Tool | Transition | Notes |
|---|---|---|
| `python -m ai_router.migrate_session_state` | **v2 → v3** | The oldest step. (Historic name predates the version-in-name convention; it is the v2→v3 migrator.) |
| `python -m ai_router.migrate_v3_to_v4` | **v3 → v4** | |
| `python -m ai_router.migrate_lightweight_to_canonical_v4` | Lightweight shape → **v4** | For Lightweight-tier files (`sessionLog[]`, status aliases, missing `schemaVersion`); normalizes straight to canonical v4. |
| `python -m ai_router.migrate_router_config` | `router-config.yaml` schema bump | Config file, **not** session state. Comment-preserving (needs `ruamel.yaml`; `pip install dabbler-ai-router[migration]`). |

### Upgrading a genuine v2 file to v4 takes **two** steps, in order

This is the non-obvious part (empirically confirmed in Set 050 S2): a
file with `schemaVersion: 2` is **skipped by `migrate_v3_to_v4`** (it only
accepts v3 input), so you must run the v2→v3 step first:

```bash
# 1. v2 -> v3
python -m ai_router.migrate_session_state --in-place docs/session-sets/<slug>/session-state.json
# 2. v3 -> v4
python -m ai_router.migrate_v3_to_v4 --in-place docs/session-sets/<slug>/session-state.json
```

A v3 file needs only step 2. A Lightweight file uses
`migrate_lightweight_to_canonical_v4` instead (it goes straight to v4).
Each migrator writes a `.bak` (`migrate_v3_to_v4`) / equivalent backup and
is idempotent on already-current files.

### Bulk upgrade

The VS Code extension's **"Upgrade older session sets"** title-bar action
(Set 050) runs the correct three-migrator chain
(`migrate_session_state` → `migrate_lightweight_to_canonical_v4` →
`migrate_v3_to_v4`, each `--in-place`) across every sub-current set at
once. `python -m ai_router.check_migrations --verbose` reports which sets
are sub-current without changing anything.

## Why not a single `migrate --from vN --to vM` front door?

Considered and rejected in the Set 051 audit (cross-provider consensus):
a unified engine would invent downgrade / partial-path semantics nobody
needs and add a new public CLI surface to maintain, all to wrap a
short, well-documented sequence. The per-step entry points + this
document are the supported interface.
