"""Lightweight-tier migrator: rewrite non-canonical ``session-state.json``
files into canonical v4 shape.

Set 048 Session 4 deliverable per the audit-locked spec at
``docs/session-sets/048-lightweight-tier-parity/spec.md`` §3.7.

Scope
-----

This migrator targets hand-maintained Lightweight-tier state files in
*consumer* repos — i.e. files written by an AI orchestrator or human
working at the file-edit level rather than through ``ai_router``'s
canonical writers. Consumer repos run this once during their first
post-Set-048 update; Set 048 itself does NOT ship per-consumer
migration commits.

It is intentionally *narrower* than :mod:`ai_router.migrate_v3_to_v4`:

- :mod:`migrate_v3_to_v4` operates on schema-versioned v3 files
  produced by router writers; the on-disk shape is well-defined and
  the migrator can trust that ``sessions[]`` exists and is structured.
- This migrator operates on *Lightweight-emitted shapes* — files whose
  ``schemaVersion`` may be missing, whose top-level array may be named
  ``sessionLog`` instead of ``sessions``, or whose per-session
  ``status`` may use aliases like ``"done"`` / ``"completed"``. It
  normalizes the input to a v3-shaped intermediate and then routes
  through :func:`progress.normalize_to_v4_shape` so the v4 invariants
  apply identically.

Recognized non-canonical shapes (catalogued in §3.7):

1. ``sessionLog[]`` instead of ``sessions[]`` (observed in
   ``great-psalms-scroll-font``). Each entry has the v3 per-session
   fields but the array key is wrong. Promoted by renaming.
2. Missing ``schemaVersion`` but otherwise v3-shaped (``sessions[]``
   present, per-session ``status`` set). Treated as v3 and routed
   through the v3 → v4 promotion path.
3. Per-session ``status`` using a tolerated alias (``"completed"`` /
   ``"done"``). Canonicalized via :func:`progress.canonicalize_status`
   before promotion.
4. Already canonical v4 (``schemaVersion: 4`` + ``sessions[]``).
   Skipped — idempotent.

Anything else (real v1/v2 files, files where ``sessionSetName`` is
missing, files where neither ``sessions`` nor ``sessionLog`` is a
list) is reported with a structured skip action; the migrator NEVER
silently fixes contradictions.

Backup file
-----------

Apply mode writes ``session-state.lwbak.json`` alongside the target
BEFORE writing the new file. Rollback is a single rename. The naming
is intentionally distinct from ``session-state.v3.bak.json`` (the
v3 → v4 migrator's backup) so the operator can tell which migrator
last ran on a given set.

Per-set independence: one set's failure does not block the others.
The CLI exits non-zero iff any set reported a hard error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

try:
    from progress import (  # type: ignore[import-not-found]
        SCHEMA_VERSION_V3,
        SCHEMA_VERSION_V4,
        SessionStateInvariantError,
        canonicalize_status,
        get_progress,
        normalize_to_v4_shape,
    )
except ImportError:
    from .progress import (  # type: ignore[no-redef]
        SCHEMA_VERSION_V3,
        SCHEMA_VERSION_V4,
        SessionStateInvariantError,
        canonicalize_status,
        get_progress,
        normalize_to_v4_shape,
    )

try:
    from migrate_v3_to_v4 import (  # type: ignore[import-not-found]
        build_v4_on_disk_shape,
    )
except ImportError:
    from .migrate_v3_to_v4 import (  # type: ignore[no-redef]
        build_v4_on_disk_shape,
    )


SESSION_STATE_FILENAME = "session-state.json"
BACKUP_FILENAME = "session-state.lwbak.json"

ACTION_MIGRATED = "migrated"
ACTION_SKIPPED_V4 = "skipped-v4"
ACTION_SKIPPED_PRE_V3 = "skipped-pre-v3"
ACTION_SKIPPED_NO_STATE = "skipped-no-state"
ACTION_SKIPPED_MALFORMED = "skipped-malformed"
ACTION_SKIPPED_FUTURE_SCHEMA = "skipped-future-schema"
ACTION_WOULD_VIOLATE = "would-violate"
ACTION_FAILED_BACKUP = "failed-backup"

# Recognized alias keys for the per-session array. ``sessionLog`` is
# the great-psalms-scroll-font shape; if more aliases surface in
# downstream consumer repos, add them here.
_SESSIONS_ARRAY_ALIASES = ("sessionLog",)


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of attempting to migrate one set."""

    set_dir: str
    action: str
    reason: str = ""
    before: Optional[dict] = None
    after: Optional[dict] = None
    error: Optional[str] = None
    backup_path: Optional[str] = None
    normalizations: tuple = ()

    def is_change(self) -> bool:
        return self.action == ACTION_MIGRATED

    def to_dict(self) -> dict:
        return {
            "set_dir": self.set_dir,
            "action": self.action,
            "reason": self.reason,
            "before": self.before,
            "after": self.after,
            "error": self.error,
            "backup_path": self.backup_path,
            "normalizations": list(self.normalizations),
        }


def _normalize_to_v3_intermediate(state: dict) -> tuple[dict, list[str]]:
    """Convert a Lightweight-shape dict into a v3-shaped intermediate.

    Returns ``(normalized_dict, [normalization_notes])``. Pure: does
    not mutate ``state``. The notes are short human-readable strings
    describing what was rewritten — surfaced in :class:`MigrationResult`
    so the operator sees exactly which non-canonical patterns triggered.

    The output dict carries ``schemaVersion: 3`` and a ``sessions[]``
    list with v3 per-session shape; downstream callers route it
    through :func:`progress.normalize_to_v4_shape` for the v3 → v4
    promotion. Missing fields are not invented — the existing v4
    shim is responsible for promoting / deriving the rest.
    """
    out = dict(state)
    notes: list[str] = []

    # Rename a known-alias sessions array (e.g. sessionLog -> sessions).
    if not isinstance(out.get("sessions"), list):
        for alias in _SESSIONS_ARRAY_ALIASES:
            if isinstance(out.get(alias), list):
                out["sessions"] = out.pop(alias)
                notes.append(f"renamed {alias}[] -> sessions[]")
                break

    # Canonicalize per-session status aliases ("completed" -> "complete",
    # "done" -> "complete"). The shim tolerates aliases at read time but
    # the on-disk canonical token is the ones in CANONICAL_STATUSES.
    if isinstance(out.get("sessions"), list):
        canonicalized = []
        any_changed = False
        for entry in out["sessions"]:
            if not isinstance(entry, dict):
                canonicalized.append(entry)
                continue
            raw_status = entry.get("status")
            canon = canonicalize_status(raw_status)
            if canon is not None and canon != raw_status:
                new_entry = dict(entry)
                new_entry["status"] = canon
                canonicalized.append(new_entry)
                any_changed = True
            else:
                canonicalized.append(entry)
        if any_changed:
            out["sessions"] = canonicalized
            notes.append("canonicalized per-session status aliases")

    # Stamp schemaVersion if missing but the rest of the shape looks
    # like v3 (sessions[] present). This is the most common Lightweight
    # divergence — hand-edited files often drop the schemaVersion
    # field entirely.
    if "schemaVersion" not in out and isinstance(out.get("sessions"), list):
        out["schemaVersion"] = SCHEMA_VERSION_V3
        notes.append(f"stamped missing schemaVersion: {SCHEMA_VERSION_V3}")

    # Canonicalize top-level status the same way (a Lightweight file
    # with status="done" reads correctly via the shim but the migrator
    # writes the canonical form).
    raw_top_status = out.get("status")
    canon_top = canonicalize_status(raw_top_status)
    if canon_top is not None and canon_top != raw_top_status:
        out["status"] = canon_top
        notes.append(f"canonicalized top-level status {raw_top_status!r} -> {canon_top!r}")

    return out, notes


def migrate_one_set(
    set_dir: str,
    *,
    dry_run: bool = True,
) -> MigrationResult:
    """Migrate one session-set directory's ``session-state.json`` to
    canonical v4.

    Recognizes the Lightweight-tier non-canonical shapes documented at
    the top of this module. Idempotent: a v4 file with ``sessions[]``
    is left alone. v1 / v2 files are skipped with a pointer to the
    v2 → v3 migrator. Future-schema (``schemaVersion > 4``) is refused.

    Apply mode writes ``session-state.lwbak.json`` alongside the
    target BEFORE the new file; if the backup write fails, the
    migration is aborted with :data:`ACTION_FAILED_BACKUP` and the
    original file is untouched.
    """
    state_path = os.path.join(set_dir, SESSION_STATE_FILENAME)
    backup_path = os.path.join(set_dir, BACKUP_FILENAME)

    if not os.path.isfile(state_path):
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_NO_STATE,
            reason=f"{SESSION_STATE_FILENAME} not found",
        )

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_MALFORMED,
            reason=f"failed to parse: {exc}",
            error=str(exc),
        )

    if not isinstance(state, dict):
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_MALFORMED,
            reason=f"top-level JSON is {type(state).__name__}, expected object",
        )

    raw_schema_version = state.get("schemaVersion")

    # Future-schema guard: refuse to downgrade.
    if (
        isinstance(raw_schema_version, int)
        and raw_schema_version > SCHEMA_VERSION_V4
    ):
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_FUTURE_SCHEMA,
            reason=(
                f"schemaVersion={raw_schema_version} is newer than this "
                f"migrator (v{SCHEMA_VERSION_V4}); refusing to downgrade."
            ),
            before=state,
        )

    # Already canonical v4: skip iff the on-disk shape matches what
    # this migrator would write. We test for ``sessions[]`` rather than
    # a deep diff — Lightweight users sometimes hand-edit a v4 file
    # back into a near-canonical shape, and the v4 invariants apply at
    # read time via the shim regardless.
    if (
        isinstance(raw_schema_version, int)
        and raw_schema_version >= SCHEMA_VERSION_V4
        and isinstance(state.get("sessions"), list)
    ):
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_V4,
            reason=f"already v4 (schemaVersion={raw_schema_version})",
            before=state,
            after=state,
        )

    # Pre-v3 guard: a schemaVersion of 1 or 2 (or a missing
    # schemaVersion combined with no sessions[] and no recognized
    # alias) is the v2-snapshot path — run the v2 → v3 migrator first.
    pre_v3 = (
        isinstance(raw_schema_version, int)
        and raw_schema_version < SCHEMA_VERSION_V3
    )
    if pre_v3:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_PRE_V3,
            reason=(
                f"schemaVersion={raw_schema_version} is pre-v3; run "
                "`python -m ai_router.migrate_session_state --in-place` "
                "first, then re-run this command."
            ),
            before=state,
        )

    # Normalize Lightweight divergences to a v3-shaped intermediate.
    normalized_intermediate, notes = _normalize_to_v3_intermediate(state)

    # After normalization, sessions[] must exist as a list for the v4
    # promotion to work. If not — and no recognized alias was present —
    # this is either a real pre-v3 file (missing schemaVersion + no
    # sessions array) or a malformed file we can't help.
    if not isinstance(normalized_intermediate.get("sessions"), list):
        if raw_schema_version is None:
            return MigrationResult(
                set_dir=set_dir,
                action=ACTION_SKIPPED_PRE_V3,
                reason=(
                    "no schemaVersion field and no recognized sessions[] "
                    "or sessionLog[] array; this looks like a pre-v3 "
                    "snapshot. Run "
                    "`python -m ai_router.migrate_session_state --in-place` "
                    "first, then re-run this command."
                ),
                before=state,
            )
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_MALFORMED,
            reason=(
                "schemaVersion claims v3+ but sessions[] is missing or "
                "not a list (and no recognized alias was found). "
                "Hand-repair or restore from git, then re-run."
            ),
            before=state,
        )

    spec_md_path = Path(set_dir) / "spec.md"
    try:
        normalized = normalize_to_v4_shape(
            normalized_intermediate, spec_md_path
        )
    except SessionStateInvariantError as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_WOULD_VIOLATE,
            reason=str(exc),
            before=state,
            error=str(exc),
            normalizations=tuple(notes),
        )
    except (TypeError, ValueError) as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_SKIPPED_MALFORMED,
            reason=f"normalize_to_v4_shape rejected the input: {exc}",
            before=state,
            error=str(exc),
            normalizations=tuple(notes),
        )

    # Validate the resulting v4 view against the 8 invariants before
    # we touch disk.
    try:
        get_progress(normalized)
    except SessionStateInvariantError as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_WOULD_VIOLATE,
            reason=str(exc),
            before=state,
            error=str(exc),
            normalizations=tuple(notes),
        )

    new_state = build_v4_on_disk_shape(normalized, normalized_intermediate)

    if dry_run:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_MIGRATED,
            reason="non-canonical lightweight -> v4 (dry-run; no write performed)",
            before=state,
            after=new_state,
            backup_path=None,
            normalizations=tuple(notes),
        )

    # Backup the ALREADY-PARSED `state` dict rather than re-reading the
    # on-disk file. Re-reading would race with any concurrent edit and
    # turn an otherwise-recoverable failure (JSONDecodeError on a
    # half-written file) into an unstructured exception — breaking
    # this function's "never raises on normal failure cases" contract
    # (Round-A finding 2026-05-26).
    try:
        _atomic_write_json(backup_path, state)
    except OSError as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_FAILED_BACKUP,
            reason=f"could not write backup at {backup_path}: {exc}",
            before=state,
            error=str(exc),
            normalizations=tuple(notes),
        )

    try:
        _atomic_write_json(state_path, new_state)
    except OSError as exc:
        return MigrationResult(
            set_dir=set_dir,
            action=ACTION_FAILED_BACKUP,
            reason=(
                f"backup written at {backup_path} but state-file write "
                f"failed: {exc}. Restore the backup by renaming "
                f"{BACKUP_FILENAME} back to {SESSION_STATE_FILENAME}."
            ),
            before=state,
            error=str(exc),
            backup_path=backup_path,
            normalizations=tuple(notes),
        )

    return MigrationResult(
        set_dir=set_dir,
        action=ACTION_MIGRATED,
        reason="non-canonical lightweight -> v4",
        before=state,
        after=new_state,
        backup_path=backup_path,
        normalizations=tuple(notes),
    )


def _atomic_write_json(path: str, data: dict) -> None:
    """Write ``data`` to ``path`` atomically via unique tempfile +
    ``os.replace``. Mirrors the helper in
    :mod:`ai_router.migrate_v3_to_v4`."""
    directory = os.path.dirname(path) or "."
    basename = os.path.basename(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{basename}.",
        suffix=".tmp",
        dir=directory,
    )
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _atomic_copy_json(src: str, dst: str) -> None:
    """Read *src* as JSON and write to *dst* via the atomic writer.
    Used for the ``.lwbak.json`` backup so the on-disk transition is
    "no .bak -> .bak written -> state file replaced" with no
    half-written .bak window."""
    with open(src, "r", encoding="utf-8") as f:
        raw = json.load(f)
    _atomic_write_json(dst, raw)


def discover_session_sets(scan_root: str) -> List[str]:
    """Find candidate session-set directories under ``scan_root``.

    Same shape as :mod:`ai_router.migrate_v3_to_v4` — any directory
    directly under ``scan_root`` that contains a ``session-state.json``
    is a candidate.
    """
    if not os.path.isdir(scan_root):
        return []
    out: List[str] = []
    for name in sorted(os.listdir(scan_root)):
        path = os.path.join(scan_root, name)
        if not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, SESSION_STATE_FILENAME)):
            out.append(path)
    return out


def migrate_all(
    scan_root: str,
    *,
    dry_run: bool = True,
    set_filter: Optional[Iterable[str]] = None,
) -> List[MigrationResult]:
    """Migrate every session set under ``scan_root``."""
    candidates = discover_session_sets(scan_root)
    if set_filter is not None:
        filter_set = set(set_filter)
        candidates = [
            p for p in candidates if os.path.basename(p) in filter_set
        ]
    return [migrate_one_set(set_dir, dry_run=dry_run) for set_dir in candidates]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_scan_root() -> str:
    candidate = os.path.join(os.getcwd(), "docs", "session-sets")
    return candidate if os.path.isdir(candidate) else os.getcwd()


def _print_result_line(r: MigrationResult, *, verbose: bool) -> None:
    name = os.path.basename(r.set_dir) or r.set_dir
    if r.action == ACTION_MIGRATED:
        sessions_summary = ""
        if r.after and isinstance(r.after.get("sessions"), list):
            sessions = r.after["sessions"]
            sessions_summary = f"  ({len(sessions)} session(s))"
        normalizations_summary = ""
        if r.normalizations:
            normalizations_summary = f"  [{'; '.join(r.normalizations)}]"
        print(f"  [migrated]    {name}{sessions_summary}{normalizations_summary}")
    elif r.action == ACTION_SKIPPED_V4:
        print(f"  [skip:v4]     {name}  (already v4)")
    elif r.action == ACTION_SKIPPED_PRE_V3:
        print(f"  [skip:prev3]  {name}  ({r.reason})")
    elif r.action == ACTION_SKIPPED_NO_STATE:
        print(f"  [skip:nostate]{name}  ({r.reason})")
    elif r.action == ACTION_SKIPPED_MALFORMED:
        print(f"  [skip:bad]    {name}  ({r.reason})")
    elif r.action == ACTION_SKIPPED_FUTURE_SCHEMA:
        print(f"  [skip:future] {name}  ({r.reason})")
    elif r.action == ACTION_WOULD_VIOLATE:
        print(f"  [WOULD-VIOLATE] {name}  ({r.reason})")
    elif r.action == ACTION_FAILED_BACKUP:
        if r.backup_path:
            print(
                f"  [BACKUP-FAILED:rollback-needed] {name}  ({r.reason})"
            )
        else:
            print(f"  [BACKUP-FAILED:no-bak] {name}  ({r.reason})")
    else:
        print(f"  [unknown:{r.action}] {name}  ({r.reason})")

    if verbose and r.action == ACTION_MIGRATED:
        print("    --- before (non-canonical):")
        for line in json.dumps(r.before, indent=2).splitlines():
            print(f"    {line}")
        print("    --- after (v4 canonical):")
        for line in json.dumps(r.after, indent=2).splitlines():
            print(f"    {line}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai_router.migrate_lightweight_to_canonical_v4",
        description=(
            "Migrate Lightweight-tier non-canonical session-state.json "
            "files into canonical v4 (Set 048 §3.7). Recognized "
            "divergences: sessionLog[] array name (aliased to "
            "sessions[]), missing schemaVersion on otherwise-v3 shape, "
            "and per-session/top-level status aliases. Idempotent: "
            "files already canonical v4 are skipped. v1/v2 files are "
            "skipped with instructions to run the v2 -> v3 migrator "
            "first. Default mode is dry-run; apply mode writes "
            "session-state.lwbak.json alongside each migrated file "
            "for one-cycle rollback."
        ),
    )
    parser.add_argument(
        "--scan",
        default=_default_scan_root(),
        help=(
            "Directory under which to find session sets. Default: "
            "./docs/session-sets when present, else the current directory."
        ),
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help=(
            "Write migrated state files. Default is dry-run (no writes). "
            "Apply mode writes session-state.lwbak.json alongside each "
            "migrated file so the rollback is one rename away."
        ),
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SET_NAME",
        help=(
            "Restrict migration to one or more session-set directory "
            "basenames. May be repeated."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Dump before/after JSON for each migrated set.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON results instead of human text.",
    )
    args = parser.parse_args(argv)

    scan_root = args.scan
    dry_run = not args.in_place
    set_filter = args.only or None

    results = migrate_all(scan_root, dry_run=dry_run, set_filter=set_filter)

    if not results and not args.json:
        print(f"\n  No session sets found under {scan_root!r}.")
        if set_filter:
            print(f"  (filter applied: {sorted(set(set_filter))})")
        return 0

    if not args.json:
        mode = "DRY RUN" if dry_run else "IN-PLACE"
        print(
            f"\n  Lightweight -> v4 migrator [{mode}] - scan root: {scan_root}\n"
        )
        for r in results:
            _print_result_line(r, verbose=args.verbose)

    counts = {
        "migrated": sum(1 for r in results if r.action == ACTION_MIGRATED),
        "skipped_v4": sum(1 for r in results if r.action == ACTION_SKIPPED_V4),
        "skipped_pre_v3": sum(
            1 for r in results if r.action == ACTION_SKIPPED_PRE_V3
        ),
        "skipped_no_state": sum(
            1 for r in results if r.action == ACTION_SKIPPED_NO_STATE
        ),
        "skipped_malformed": sum(
            1 for r in results if r.action == ACTION_SKIPPED_MALFORMED
        ),
        "skipped_future_schema": sum(
            1 for r in results if r.action == ACTION_SKIPPED_FUTURE_SCHEMA
        ),
        "would_violate": sum(
            1 for r in results if r.action == ACTION_WOULD_VIOLATE
        ),
        "failed_backup": sum(
            1 for r in results if r.action == ACTION_FAILED_BACKUP
        ),
        "total": len(results),
    }

    if args.json:
        print(
            json.dumps(
                {
                    "scan_root": scan_root,
                    "dry_run": dry_run,
                    "counts": counts,
                    "results": [r.to_dict() for r in results],
                },
                indent=2,
            )
        )
    else:
        print()
        print(
            f"  Summary: {counts['migrated']} migrated, "
            f"{counts['skipped_v4']} already v4, "
            f"{counts['skipped_pre_v3']} pre-v3 (run v2->v3 migrator first), "
            f"{counts['skipped_no_state']} no state file, "
            f"{counts['skipped_malformed']} malformed, "
            f"{counts['would_violate']} would-violate, "
            f"{counts['failed_backup']} backup-failed."
        )
        if dry_run and counts["migrated"]:
            print("  (dry run; rerun with --in-place to write changes)")
        if not dry_run and counts["migrated"]:
            print(
                "  (rollback: rename session-state.lwbak.json back to "
                "session-state.json to restore the pre-migration file)"
            )

    return 1 if (counts["would_violate"] or counts["failed_backup"]) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "SESSION_STATE_FILENAME",
    "BACKUP_FILENAME",
    "ACTION_MIGRATED",
    "ACTION_SKIPPED_V4",
    "ACTION_SKIPPED_PRE_V3",
    "ACTION_SKIPPED_NO_STATE",
    "ACTION_SKIPPED_MALFORMED",
    "ACTION_SKIPPED_FUTURE_SCHEMA",
    "ACTION_WOULD_VIOLATE",
    "ACTION_FAILED_BACKUP",
    "MigrationResult",
    "migrate_one_set",
    "migrate_all",
    "discover_session_sets",
    "main",
]
