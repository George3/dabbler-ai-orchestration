"""Decision-review queue reader.

The decision-review queue is a JSONL file at
``<session-set>/decision-review-queue.jsonl`` that the orchestrator
consults when planning the next session. Entries come from two
surfaces, both shipped by Set 026 Session 6:

1. The ``dabbler.flagDecisionForReview`` VS Code command — operator
   types a reason; one JSON line is appended.
2. The ``dabbler.scanAnnotationsForActiveSet`` VS Code command — the
   workspace is walked for ``@dabbler:outsource-review("reason")``
   annotations in source code; new annotations are appended.

The queue is an *append-only ledger of intent*, not a state machine.
The orchestrator reads it at session start, surfaces the entries in
its initial planning checklist, and then ``clear_queue`` drops the
file (entries that remained relevant after planning are typically
addressed in-session and re-flagged afterward if needed).

This module is the Python read/clear surface. The append surface
lives in the VS Code extension (TypeScript) — see
``tools/dabbler-ai-orchestration/src/commands/flagDecisionForReview.ts``
and ``src/commands/scanAnnotationsForActiveSet.ts``.

Per-entry shape
---------------

Each line is a JSON object. The fields the writers produce:

- ``ts``: ISO 8601 timestamp the entry was created.
- ``reason``: operator-supplied or annotation-extracted text.
- ``source``: ``"command"`` or ``"annotation"``.
- ``file``: workspace-relative file path (POSIX separators) for
  annotation entries; ``null`` for command entries.
- ``line``: 1-based line number for annotation entries; ``null`` for
  command entries.

This module does NOT validate the per-entry shape. The schema is
intentionally open so future surfaces can attach additional context
(test IDs, linked issues, etc.) without bumping the format. Callers
that care about specific fields should look them up defensively
(``entry.get("reason", "")``) rather than positional-unpacking.

Malformed lines
---------------

A line that fails ``json.loads`` is skipped with a logged warning,
mirroring the same defensive shape ``session_events.read_events``
uses. The append-only ledger contract means a partial write that
left a half-line on disk shouldn't break the whole read; callers
just see one fewer entry than was attempted.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Union

PathLike = Union[str, Path]

DECISION_REVIEW_QUEUE_FILENAME = "decision-review-queue.jsonl"


_logger = logging.getLogger("ai_router.decision_review_queue")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.propagate = False


def queue_path(session_set_dir: PathLike) -> Path:
    """Return the absolute path to a session set's queue file.

    Does not check whether the file exists; ``read_queue`` and
    ``clear_queue`` are tolerant of the missing-file case.
    """
    return Path(session_set_dir) / DECISION_REVIEW_QUEUE_FILENAME


def read_queue(session_set_dir: PathLike) -> List[Dict[str, Any]]:
    """Read all entries from ``<session_set_dir>/decision-review-queue.jsonl``.

    Returns an empty list if the file does not exist or contains no
    parseable lines. Malformed lines are skipped with a logged
    warning; one bad line does not poison the rest of the read.

    The returned list preserves on-disk order — callers that want to
    sort by ``ts`` or group by ``source`` do so themselves.
    """
    path = queue_path(session_set_dir)
    if not path.is_file():
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _logger.warning(
            "decision-review queue read failed at %s: %s — returning empty list",
            path,
            exc,
        )
        return []

    out: List[Dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            _logger.warning(
                "decision-review queue %s line %d: skipping malformed JSON (%s)",
                path,
                line_no,
                exc.msg,
            )
            continue
        if not isinstance(obj, dict):
            _logger.warning(
                "decision-review queue %s line %d: expected object, got %s — skipping",
                path,
                line_no,
                type(obj).__name__,
            )
            continue
        out.append(obj)
    return out


def clear_queue(session_set_dir: PathLike) -> int:
    """Drop the queue file. Returns the number of entries that were in
    it (0 if the file was absent or unparseable).

    Idempotent: calling on an already-cleared (or never-existed) queue
    is a no-op and returns 0. The return value lets the orchestrator
    log how many entries were consumed, without forcing the caller to
    read first and then clear.

    The implementation reads-then-unlinks rather than truncates, so a
    crash mid-call leaves either the original file fully intact or
    fully absent — no half-truncated state.
    """
    path = queue_path(session_set_dir)
    if not path.is_file():
        return 0

    # Count before delete so the return value is honest even if the
    # unlink races with another writer.
    entries = read_queue(session_set_dir)
    try:
        os.unlink(path)
    except FileNotFoundError:
        # Concurrent clear — fine.
        return len(entries)
    except OSError as exc:
        _logger.warning(
            "decision-review queue clear failed at %s: %s — leaving file in place",
            path,
            exc,
        )
        return 0
    return len(entries)
