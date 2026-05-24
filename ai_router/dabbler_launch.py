"""``dabbler-launch`` — observability wrapper that spawns an AI CLI subprocess
and records a canonical launch record before the spawn.

Set 045 / Session 3 deliverable. The wrapper is the writer-side
producer for the dual-primary log-harvest architecture
(Set 044 proposal v1, locked by consensus audit). The record it
writes is consumed by ``ai_router.joiner`` for deterministic
correlation against per-backend native logs.

Headless mode only (Set 044 commitment 4 — interactive
TTY-passthrough on Windows is permanently out of v1 scope). The
wrapper passes stdin/stdout/stderr through unchanged so the spawned
AI CLI behaves identically to a direct invocation.

Per joiner-spec.md §5, the wrapper emits a canonical
``HarvestRecord``-shaped JSON line with ``event_type="launch"``,
``source="wrapper"``. The line is APPENDED to
``~/.dabbler/launch-log.jsonl`` (configurable via
``--launch-log``). The append happens **before** the subprocess
spawn so a failed spawn still leaves the record on disk for the
joiner to surface as an unbound launch.

Invocation:

    python -m ai_router.dabbler_launch --engine claude --workspace-cwd .
        --set-slug 045-log-harvest-implementation --session-number 3
        --effort high -- claude code

Everything after ``--`` is the AI CLI's argv. The wrapper preserves
exit code and signals.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from ai_router.joiner.schema import canonicalize_cwd


KNOWN_ENGINES = {"claude", "copilot", "codex", "gemini"}


@dataclass(frozen=True)
class LaunchInputs:
    engine: str
    workspace_cwd: str
    set_slug: Optional[str]
    session_number: Optional[int]
    effort: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    launch_log: Path
    child_argv: list[str]


def default_launch_log() -> Path:
    """Return the operator-default launch-log path."""
    return Path(os.path.expanduser("~")) / ".dabbler" / "launch-log.jsonl"


def build_record(
    *,
    inputs: LaunchInputs,
    launch_id: str,
    when: Optional[datetime] = None,
) -> dict:
    """Build the canonical ``HarvestRecord``-shaped launch record.

    The record matches joiner-spec.md §5.1 field-for-field. Fields
    not meaningful for a wrapper-launch event (``conv_id``,
    ``binding_state``, ``tool``, etc.) are emitted as ``null`` so
    that JSON consumers can parse with a fixed schema.
    """
    ts = when or datetime.now(timezone.utc)
    cwd_canon = canonicalize_cwd(inputs.workspace_cwd)
    return {
        "ts": ts.isoformat(),
        "event_type": "launch",
        "source": "wrapper",
        "engine": inputs.engine,
        "provider": inputs.provider,
        "model": inputs.model,
        "conv_id": None,
        "workspace_cwd": inputs.workspace_cwd,
        "workspace_cwd_canonical": cwd_canon,
        "set_slug": inputs.set_slug,
        "session_number": inputs.session_number,
        "binding_state": None,
        "bound_candidates": None,
        "effort": inputs.effort,
        "tool": None,
        "tool_args_summary": None,
        "tokens_in": None,
        "tokens_out": None,
        "raw_ref": {"launch_id": launch_id},
    }


def append_launch_record(launch_log: Path, record: dict) -> None:
    """Append one JSON-encoded record to the launch log.

    Creates the parent directory if it does not exist. The write is
    flush+fsync-best-effort: a single line append is atomic on
    POSIX/Windows for typical AI-launch frequencies (≪ 1 / second),
    so a stronger lock is not required.
    """
    launch_log.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(launch_log, "a", encoding="utf-8") as f:
        f.write(line)


def spawn_child(child_argv: list[str], cwd: str) -> int:
    """Spawn the AI CLI subprocess and return its exit code.

    stdin/stdout/stderr are inherited unchanged (headless-passthrough
    only — Set 044 commitment 4). The wrapper waits for the child to
    exit and surfaces its return code.
    """
    if not child_argv:
        return 0
    completed = subprocess.run(child_argv, cwd=cwd, check=False)
    return completed.returncode


def run_launch(
    inputs: LaunchInputs,
    *,
    when: Optional[datetime] = None,
    spawn: bool = True,
) -> tuple[str, int]:
    """Write the launch record and (optionally) spawn the child.

    Returns ``(launch_id, exit_code)``. When ``spawn=False`` (used by
    Layer-2 tests that exercise the record-writing side only), the
    exit code is always 0.
    """
    launch_id = str(uuid.uuid4())
    record = build_record(inputs=inputs, launch_id=launch_id, when=when)
    append_launch_record(inputs.launch_log, record)
    exit_code = spawn_child(inputs.child_argv, inputs.workspace_cwd) if spawn else 0
    return launch_id, exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ai_router.dabbler_launch",
        description=(
            "Observability wrapper for AI CLI launches. Writes a "
            "canonical launch record to ~/.dabbler/launch-log.jsonl "
            "and spawns the AI CLI subprocess in headless mode."
        ),
    )
    parser.add_argument(
        "--engine",
        required=True,
        help="AI engine identifier: claude | copilot | codex | gemini",
    )
    parser.add_argument(
        "--workspace-cwd",
        required=True,
        help="Workspace cwd the AI CLI will run inside (correlates to native log)",
    )
    parser.add_argument(
        "--set-slug",
        default=None,
        help="Optional session-set slug (e.g. '045-log-harvest-implementation')",
    )
    parser.add_argument(
        "--session-number",
        type=int,
        default=None,
        help="Optional session number within the set",
    )
    parser.add_argument(
        "--effort",
        default=None,
        help="Effort level the AI was invoked with: low | medium | high | etc.",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider tag (e.g. anthropic | github | openai | google)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model identifier (e.g. claude-opus-4-7)",
    )
    parser.add_argument(
        "--launch-log",
        type=Path,
        default=None,
        help="Override the launch-log path (defaults to ~/.dabbler/launch-log.jsonl)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the launch record but do NOT spawn the AI subprocess",
    )
    parser.add_argument(
        "child_argv",
        nargs=argparse.REMAINDER,
        help="The AI CLI argv (preceded by '--' on the command line)",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> tuple[LaunchInputs, bool]:
    """Parse argv into LaunchInputs and a dry-run flag."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.engine not in KNOWN_ENGINES:
        parser.error(
            f"--engine must be one of {sorted(KNOWN_ENGINES)}; got {args.engine!r}"
        )

    child_argv = list(args.child_argv or [])
    if child_argv and child_argv[0] == "--":
        child_argv = child_argv[1:]
    if not child_argv and not args.dry_run:
        parser.error(
            "no child argv supplied; pass the AI CLI command after '--' or use --dry-run"
        )

    inputs = LaunchInputs(
        engine=args.engine,
        workspace_cwd=args.workspace_cwd,
        set_slug=args.set_slug,
        session_number=args.session_number,
        effort=args.effort,
        provider=args.provider,
        model=args.model,
        launch_log=args.launch_log or default_launch_log(),
        child_argv=child_argv,
    )
    return inputs, args.dry_run


def main(argv: Optional[Sequence[str]] = None) -> int:
    inputs, dry_run = parse_args(argv)
    launch_id, exit_code = run_launch(inputs, spawn=not dry_run)
    if dry_run:
        print(f"launch-id: {launch_id}")
        print(f"launch-log: {inputs.launch_log}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
