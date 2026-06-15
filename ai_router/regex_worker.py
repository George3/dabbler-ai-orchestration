"""Set 068 S1 - isolated regex worker for ReDoS-bounded ``grep``.

This module is run as a **subprocess** (``python -m ai_router.regex_worker``) by
:func:`ai_router.run_test_sandbox.isolated_regex_search` so a catastrophic-
backtracking pattern is killed by the parent's hard wall-clock timeout instead of
hanging the orchestrator. Python's ``re`` has no step/time bound and a regex match
holds the GIL, so a thread cannot interrupt it - a true kill requires a separate
process. The worker is the separate process.

Protocol (line-oriented, ASCII):

- **stdin**: one JSON object ``{"pattern": str, "files": [{"rel": str, "text":
  str}, ...]}``. The parent does the sandbox-confined walk + read and ships only
  already-confined ``(rel, text)`` pairs; the worker never touches the filesystem.
- **stdout**: matching lines as ``rel:lineno:line``, one per line.
- **exit code**: ``0`` on success, ``2`` on a regex-compile error (message on
  stderr), ``3`` on a malformed job.

The worker self-limits its output to ``_MAX_MATCH_LINES`` so a pathological
pattern that matches everything cannot produce unbounded output before the
timeout fires; the parent elides for display regardless.
"""

from __future__ import annotations

import json
import re
import sys
from typing import List

# Self-limit: stop after this many match lines. The parent's _elide caps the
# displayed result at 60 KB anyway; this bounds the worker's own memory/output.
_MAX_MATCH_LINES = 100_000


def search(pattern: str, files: List[dict]) -> List[str]:
    """Compile ``pattern`` and return ``rel:lineno:line`` matches over ``files``.

    Raises :class:`re.error` on an invalid pattern. Pure function so it can be
    unit-tested in-process without spawning the subprocess.
    """
    rx = re.compile(pattern)
    out: List[str] = []
    for f in files:
        rel = f.get("rel", "")
        text = f.get("text", "")
        for i, ln in enumerate(text.splitlines(), 1):
            if rx.search(ln):
                out.append(f"{rel}:{i}:{ln}")
                if len(out) >= _MAX_MATCH_LINES:
                    return out
    return out


def main(argv=None) -> int:
    raw = sys.stdin.read()
    try:
        job = json.loads(raw)
        pattern = job["pattern"]
        files = job["files"]
        if not isinstance(pattern, str) or not isinstance(files, list):
            raise ValueError("job must carry a string pattern and a files list")
    except (ValueError, TypeError, KeyError) as exc:
        sys.stderr.write(f"malformed regex job: {exc}")
        return 3
    try:
        matches = search(pattern, files)
    except re.error as exc:
        sys.stderr.write(f"regex compile error: {exc}")
        return 2
    # Write via the binary buffer so Windows text-mode does NOT translate the
    # match-line separators to "\r\n" (which would leave a stray "\r" on every
    # line the parent splits on "\n"). Match lines are joined with bare "\n".
    sys.stdout.buffer.write("\n".join(matches).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
