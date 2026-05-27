# Set 048 Session 4 cross-provider verification request

## Context

Set 048 Session 4 ships the four "closing" deliverables of the
Lightweight-tier parity arc: per-consumer migrator CLI, the
external-verification command, three review-criteria template
files, the Get Started wizard tier-branch, and the four doc
revisions plus the cross-repo notice. The audit-locked spec is
at `docs/session-sets/048-lightweight-tier-parity/spec.md`
§3.7 (migrator), §3.8 (external-verification command), §3.9
(review-criteria storage), and §4 row for Session 4 (doc
revisions + wizard tier-branch).

Operator-locked premises in scope:
- **P1.** Lightweight orchestrators MUST follow the SAME process
  as Full for model/effort/session-set/session identification
  and state-file updates.
- **P3.** Lightweight differs from Full ONLY in: no router
  runtime calls; no auto-verification; copyable review prompts;
  suggested-not-required UAT/E2E.
- **P4.** Lightweight users must not be required to hand-edit
  state files (migrator addresses this).
- **L1.** Copyable prompts MUST reference file paths, NOT embed
  contents. The §3.9 review-criteria carve-out is the documented
  exception (operator-authored meta-instructions).

## What I'm asking you to verify

1. **Correctness** — Does the migrator's `_normalize_to_v3_intermediate`
   handle the four documented divergences (sessionLog[] alias, missing
   schemaVersion, top-level status alias, per-session status alias)
   in the right order, without mutating the input dict?
2. **Refusal correctness** — Does the migrator correctly refuse
   pre-v3 and future-schema inputs, and gracefully handle missing /
   malformed state files without raising?
3. **Backup atomicity** — `.lwbak.json` is written BEFORE the
   new state file (mirroring `.v3.bak.json` in `migrate_v3_to_v4`).
   On state-file-write failure with backup landed, the result
   includes `backup_path` so the operator knows where to recover.
4. **External-verification UX** — When the file is missing, the
   command creates an empty file (no templated header per §3.8)
   and opens it. EEXIST races fall through gracefully.
5. **Review-criteria templates** — Each file's comment header
   tells the operator how to edit and what happens if they
   delete the file. Sample bullets are repo-relevant.
6. **Wizard tier-branch** — The radio-group + data-tier toggle
   logic correctly hides full-only content under Lightweight and
   vice versa. Default is Full to preserve existing behavior.
7. **Doc consistency** — The five doc revisions and the new
   cross-repo notice describe the SAME mental model (P1 + P3
   + L1 + tri-state + migrator + agent-capability requirement)
   without contradicting each other. Pay particular attention
   to whether the workflow doc Step 6 Lightweight subsection
   and the schema doc Tier-expectations bullet agree on the
   `--no-router` short-circuit semantics.
8. **Spec compliance** — Are the four §3.x specs (§3.7 migrator,
   §3.8 external-verification command, §3.9 review-criteria,
   §4 wizard) implemented as specified? Flag any silent gaps
   or scope drift.

Please return findings as a JSON object matching
`ai_router/prompt-templates/verification.md` schema.

---

## File: ai_router/migrate_lightweight_to_canonical_v4.py

```python
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

    try:
        _atomic_copy_json(state_path, backup_path)
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
            f"\n  Lightweight -> v4 migrator [{mode}] — scan root: {scan_root}\n"
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

```

---

## File: tools/dabbler-ai-orchestration/src/commands/externalVerification.ts

```typescript
import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { SessionSet } from "../types";
import { readAllSessionSets } from "../utils/fileSystem";

interface SetItem extends vscode.TreeItem {
  set: SessionSet;
}

const FILE_NAME = "external-verification.md";

async function pickSet(sets: SessionSet[]): Promise<SessionSet | undefined> {
  if (sets.length === 0) {
    vscode.window.showInformationMessage(
      "No session sets found in this workspace."
    );
    return undefined;
  }
  if (sets.length === 1) return sets[0];
  const picked = await vscode.window.showQuickPick(
    sets.map((s) => ({
      label: s.name,
      description: s.state,
      detail: s.dir,
      set: s,
    })),
    {
      placeHolder: "Pick a session set to open external-verification.md for",
    }
  );
  return picked?.set;
}

async function openOrCreate(set: SessionSet): Promise<void> {
  const filePath = path.join(set.dir, FILE_NAME);
  // Per §3.8 the file is intentionally free-form — no templated
  // header. Create-if-missing with an empty file so the editor opens
  // on an untouched canvas.
  if (!fs.existsSync(filePath)) {
    try {
      fs.writeFileSync(filePath, "", { encoding: "utf-8", flag: "wx" });
    } catch (err) {
      // EEXIST is a benign race (another process / a parallel save
      // already created it); fall through to open. Any other error is
      // surface-worthy so the operator can fix permissions etc.
      const e = err as NodeJS.ErrnoException;
      if (e?.code !== "EEXIST") {
        vscode.window.showErrorMessage(
          `Could not create ${FILE_NAME} in ${set.name}: ${e?.message ?? String(err)}`
        );
        return;
      }
    }
  }
  await vscode.commands.executeCommand(
    "vscode.open",
    vscode.Uri.file(filePath)
  );
}

export function registerExternalVerificationCommand(
  context: vscode.ExtensionContext
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.openExternalVerificationDoc",
      async (item?: SetItem) => {
        // Item-shape invocation (right-click context, programmatic
        // callers passing a TreeItem) takes the bound set directly.
        if (item?.set) {
          await openOrCreate(item.set);
          return;
        }
        // Command Palette invocation: enumerate workspace sets and
        // pick. The picker is skipped when there's only one set so
        // the common single-set case is one click.
        const sets = readAllSessionSets();
        const picked = await pickSet(sets);
        if (picked) {
          await openOrCreate(picked);
        }
      }
    )
  );
}

```

---

## File: docs/review-criteria/spec.md

```markdown
<!--
  Repo-specific review criteria for session-set SPECS.

  This file is read by the Dabbler extension's `Copy: Spec-review
  prompt` command and embedded into the clipboard payload under
  "Operator review criteria (from docs/review-criteria/spec.md)".

  - Edit the bullets below to teach reviewers what THIS repo cares
    about most when scoping a session set.
  - Keep it short (≤ ~30 lines). The prompt is meant to be paste-
    able into any AI chat with file access.
  - Delete this file to fall back to the extension's default English
    spec-review instructions.
-->

When reviewing a session-set spec, weight the following:

- **Scope realism.** Can each session realistically be completed by a
  single orchestrator in one sitting (1–4 hours of focused work)?
  Flag any session whose stated deliverables span more than three
  loosely-coupled subsystems.
- **Verifiability.** Does the spec name concrete artifacts that prove
  completion (file paths, command outputs, test counts)? Vague "ship
  X" with no measurable signal is a yellow flag.
- **Prerequisites + non-goals.** Are the cross-set dependencies
  explicit, and are out-of-scope items called out so the orchestrator
  doesn't drift?
- **Audit-lock discipline.** If the set claims to implement a prior
  audit's verdict, the §2 "operator-locked premises" should match the
  audit doc exactly. Cite the verdict path.
- **Backwards compatibility surfaces.** Any change to shared schemas,
  CLIs, or extension command IDs must spell out the back-compat plan.
- **Repo conventions.** Defer to `CLAUDE.md` at the repo root for any
  rule the spec doesn't explicitly override.

```

---

## File: docs/review-criteria/session.md

```markdown
<!--
  Repo-specific review criteria for the MOST RECENT SESSION's
  accomplishments.

  This file is read by the Dabbler extension's `Copy: Session-
  accomplishments review prompt` command and embedded into the
  clipboard payload under "Operator review criteria (from
  docs/review-criteria/session.md)".

  - Edit the bullets below to teach reviewers what THIS repo cares
    about most when judging a finished session.
  - Keep it short (≤ ~30 lines).
  - Delete this file to fall back to the extension's default English
    session-review instructions.
-->

When reviewing a finished session, weight the following:

- **Spec alignment.** Compare the session's commits and activity-log
  entries against the spec's promised deliverables for THIS session
  number. Flag scope creep (commits unrelated to the stated goal) and
  missing deliverables.
- **Activity-log honesty.** Each entry should correspond to a real
  artifact (commit hash, file change, command invocation). Entries
  that summarize work without naming concrete outputs are weak audit
  trail.
- **Round-A in-flight fixes.** If the session ran a cross-provider
  verification, were Round-A findings addressed in-flight rather
  than deferred? Per `feedback_dont_hide_behind_out_of_scope`, small
  fixes belong in the same session.
- **Test coverage.** New or behavior-changing code should ship with
  at least unit-test coverage. Note any new code paths without a
  matching test.
- **Documentation drift.** If the session changed a public interface
  (CLI flag, command ID, schema field), the relevant doc file must
  be updated in the same session.
- **Budget discipline.** Cumulative routed spend should be reported
  in the session's close-out notes (per
  `feedback_budget_question_scope`).

```

## File: docs/review-criteria/set.md

(Similar shape to session.md — review-criteria header + 6-bullet
checklist focused on whole-set-level review concerns: scope-vs-delivery,
memory carry-forward, version-bump correctness, set-level Round-A
discipline, cross-repo notice, cumulative budget. Reviewable at
docs/review-criteria/set.md in the worktree.)

---

## Wizard tier-branch (Commit D)

`tools/dabbler-ai-orchestration/webview/wizard.html` gained:

1. A new `<h2>Choose adoption tier</h2>` section above
   `<h2>Prerequisites</h2>` containing two radio buttons
   `name="tier" value="full"|"lightweight"`, with `value="full"`
   checked by default. The labels describe each tier's
   prerequisites + spend implications in 1-2 sentences.
2. Existing prerequisites + the cost-reality callout gained
   `data-tier="full"` attributes. A new Lightweight
   prerequisite (path-aware review agent) and a new no-API-
   spend callout gained `data-tier="lightweight"`.
3. The `Configure AI Router` and `Show cost dashboard` buttons
   gained `data-tier="full"`. `Troubleshoot` was left untagged
   (applies to both tiers).
4. JS handler `applyTierVisibility(tier)` toggles `.hidden`
   class on every `[data-tier]` element based on the active
   radio. Runs once on script-load + on every radio change.
5. CSS: `.hidden { display: none !important; }` plus tier-
   toggle styling (border + accent-color on the active radio).
6. The existing `pricingLink` click handler is now guarded by
   `if (pricing)` because the link lives inside the cost-
   reality callout which can be hidden.

---

## package.json delta

`tools/dabbler-ai-orchestration/package.json` gains one new
command entry under `contributes.commands`:

```json
{
  "command": "dabbler.openExternalVerificationDoc",
  "title": "Open External Verification Document",
  "category": "Dabbler"
}
```

No other contribute-section changes. The command is Command-
Palette-only (not added to the right-click QuickPick).

---

## extension.ts delta

One new import + one new `safeRegister` invocation:

```typescript
import { registerExternalVerificationCommand } from "./commands/externalVerification";
// ...later in activate():
  safeRegister("registerExternalVerificationCommand", () =>
    registerExternalVerificationCommand(context),
  );
```

The new import shifted the watcher pattern's
`createFileSystemWatcher(pattern)` line from 149 to 150;
the watcher-inventory pinned line was bumped accordingly.

---

## Doc revisions (Commit E)

Five doc changes shipped:

1. `docs/session-state-schema.md` § Tier expectations: the
   Lightweight bullet was rewritten from "router writers don't
   operate, hand-edit only" to the actual Set 048 model — 
   router writers DO operate under `--no-router` mode; lazy LLM-
   SDK imports keep credentials out of the Lightweight path;
   verification short-circuits to manual attestation; the
   external-verification.md soft gate fires when missing;
   hand-maintained Lightweight files are still supported and
   the new `migrate_lightweight_to_canonical_v4` CLI handles
   non-canonical drift.
2. `docs/ai-led-session-workflow.md` Step 6 gained a
   `#### Lightweight tier — copyable review prompts replace
   routed verification` subsection: 5-step flow covering when
   the orchestrator triggers the copy-prompt commands, the
   path-aware-agent requirement, the external-verification.md
   paste-back convention, the close_session soft gate, and the
   review-criteria file convention.
3. `docs/planning/session-set-authoring-guide.md`:
   - Session Set Configuration block example gains `tier: full`
     and updates the requiresUAT/E2E comments to show the
     `true | false | "suggested"` tri-state.
   - Field semantics bullets added for `tier: "full"`,
     `tier: "lightweight"`, `requiresUAT: "suggested"`,
     `requiresE2E: "suggested"` — the suggested values
     explicitly document the upfront-positive-confirmation
     prompt mechanism that replaces the audit's originally-
     proposed triple-redundancy reminder.
   - Defaults section updated: `tier: full` joins the implicit
     defaults when the configuration block is omitted.
4. `docs/adoption-bootstrap.md` closing pointers for Lightweight
   tier rewritten to describe Set 048's actual deliverables:
   copyable prompts via the four `dabbler.copy*Prompt` commands;
   external-verification.md paste-back via the new command;
   optional `docs/review-criteria/*.md` files; hand-maintained
   state files via the new Lightweight migrator; upgrade-to-Full
   path stays.
5. `docs/cross-repo-lightweight-notice.md` is a NEW file
   following the established `cross-repo-checkout-notice.md` /
   `cross-repo-harvest-notice.md` pattern. It's a one-time copy
   source for consumer-repo CLAUDE.md authors. Documents the
   --no-router activation knobs, the copyable-prompt + paste-
   back flow, the agent-capability requirement, the optional
   review-criteria files, the per-consumer migrator one-time
   recipe, and the Get Started panel tier-branch.

---

## Test counts at close

- Python: 1009 passed + 1 pre-existing skip (no Python
  failures introduced; 16 new tests for the Lightweight
  migrator under `ai_router/tests/test_migrate_lightweight_to_canonical_v4.py`).
- TypeScript (unit): 665 passed + 2 pre-existing failures
  unchanged from S2/S3 (configEditor-foundation +
  notificationsSection). No new TS tests in S4 — the
  external-verification command is a thin wrapper over
  `vscode.commands.executeCommand`, `vscode.window.showQuickPick`,
  and `fs.writeFileSync` with no testable pure-function seam.
