"""CLI entry point for ai_router.joiner.

Invocation:

    python -m ai_router.joiner --conflicts [--set-slug <slug>] [--json]
    python -m ai_router.joiner --coverage [--json]
    python -m ai_router.joiner --harvest [--workspace <cwd>] [--json]

The Set 045 Explorer integration (S5) shells out to this CLI on
each ``SessionSetsProvider`` refresh and parses the JSON-encoded
result. Per joiner-spec.md §8, this is the only IPC surface the
Explorer needs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_router.joiner.conflicts import scan_conflicts
from ai_router.joiner.coverage import coverage
from ai_router.joiner.schema import harvest


def _emit_json(payload) -> None:
    print(json.dumps(payload, indent=2))


def _emit_conflicts(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace) if args.workspace else None
    reports = scan_conflicts(
        set_slug=args.set_slug,
        workspace_root=workspace,
    )
    payload = [r.to_json_dict() for r in reports]
    if args.json:
        _emit_json(payload)
    else:
        if not reports:
            print("No conflicts detected.")
        else:
            for r in reports:
                print(f"[{r.severity.upper()}] {r.kind}  {r.set_slug or '?'}")
                print(f"  {r.note}")
                print()
    return 0


def _emit_coverage(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace) if args.workspace else None
    summaries = coverage(workspace_root=workspace)
    payload = [s.to_json_dict() for s in summaries]
    if args.json:
        _emit_json(payload)
    else:
        for s in summaries:
            badges = []
            if s.wrapper_launched:
                badges.append("wrapper")
            if s.native_log_bound:
                badges.append("native")
            if s.narration_present:
                badges.append("narration")
            if s.bypass_inferred:
                badges.append("bypass")
            print(f"{s.set_slug}: {' '.join(badges) or '(no signal)'}")
    return 0


def _emit_harvest(args: argparse.Namespace) -> int:
    records = list(harvest(workspace_cwd=args.workspace_cwd))
    payload = [r.to_json_dict() for r in records]
    if args.json:
        _emit_json(payload)
    else:
        for r in records:
            print(f"{r.ts.isoformat()}  {r.engine}  {r.event_type}  {r.conv_id or '-'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_router.joiner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--conflicts", action="store_true", help="Emit conflict reports")
    mode.add_argument("--coverage", action="store_true", help="Emit per-set coverage summaries")
    mode.add_argument("--harvest", action="store_true", help="Emit joined Harvest Record stream")
    parser.add_argument("--set-slug", help="Restrict to a specific session set (conflicts only)")
    parser.add_argument("--workspace", help="Workspace root (defaults to cwd) — used by --conflicts / --coverage")
    parser.add_argument("--workspace-cwd", help="Filter harvest stream to one workspace (canonical-compared)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable text")
    args = parser.parse_args(argv)

    if args.conflicts:
        return _emit_conflicts(args)
    if args.coverage:
        return _emit_coverage(args)
    if args.harvest:
        return _emit_harvest(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
