"""Fresh close-out turn — orchestrator-driven Step 8 router.

After a session's work-doing turn writes ``disposition.json`` with
``status: "completed"`` AND verification has terminated, the
orchestrator wrapper calls :func:`route_fresh_close_out_turn` to
trigger close-out. The hook routes a fresh turn via
:func:`ai_router.route` with ``task_type="session-close-out"``. The
routed agent reads ``ai_router/docs/close-out.md`` and runs
``python -m ai_router.close_session``. The fresh turn exists so the
close-out agent encounters the close-out instructions at the moment
they are needed (the workflow doc's Step 8 was collapsed; the detail
lives in close-out.md, and the prompt for this task type explicitly
references it).

Set 026 Session 1 removed the queue-mediated daemon path. The hook
is now single-mode: route a fresh turn, return the route result, let
the routed agent invoke close_session.

The hook is **non-fatal**. A close-out turn that crashes (provider
outage, transient lock contention) leaves the session in
``closeout_pending`` / ``closeout_blocked``, where the reconciler from
:mod:`ai_router.reconciler` picks it up on the next sweep.

What this module is NOT
-----------------------
This module does not own *when* the hook fires. The decision to invoke
``route_fresh_close_out_turn`` lives in the orchestrator's wrapper /
session-driver code, which examines disposition.json and the lifecycle
state. The hook just executes the right action.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from disposition import (  # type: ignore[import-not-found]
        Disposition,
        read_disposition,
    )
except ImportError:
    from .disposition import (  # type: ignore[no-redef]
        Disposition,
        read_disposition,
    )


SESSION_CLOSE_OUT_TASK_TYPE = "session-close-out"

# The prompt sent to the routed close-out agent. Deliberately short:
# the agent's job is to commit/push/run-the-CLI/notify in the right
# order, not to reason about the gate semantics. Embedding the whole
# close-out.md into the prompt would defeat the doc-collapse work
# from Set 6 Session 1; the pointer is what keeps the single source
# of truth.
_CLOSE_OUT_TURN_CONTENT = (
    "Run end-of-session close-out for the session set at "
    "{session_set_dir}.\n\n"
    "Steps:\n"
    "1. Read ai_router/docs/close-out.md (the canonical close-out "
    "reference) for the procedure, expected outputs, ownership "
    "contract (Section 1), and remediation.\n"
    "2. Stage, commit, and push the session's work BEFORE invoking "
    "close_session. The gate's check_pushed_to_remote will fail "
    "closed if the push has not landed, so this step is a "
    "precondition rather than something close_session does itself. "
    "Use a descriptive commit message that names the session set "
    "and session number.\n"
    "3. Invoke `python -m ai_router.close_session "
    "--session-set-dir {session_set_dir}` and capture its exit code, "
    "result string, and gate-result list.\n"
    "4. If the gate fails on a transient signal (lock contention), "
    "do not retry — report the result. The reconciler will sweep "
    "the session set on the next startup.\n"
    "5. If the gate fails on a hard signal (uncommitted files, push "
    "rejected, missing nextOrchestrator), surface the remediation "
    "string verbatim so the human can address it. Do not fire the "
    "session-complete notification when the gate has failed.\n"
    "6. ONLY when close_session returns result=='succeeded' and exit "
    "code 0, fire the session-complete notification by calling "
    "`ai_router.notifications.send_session_complete_notification(...)` "
    "(or running it via the venv Python). Notification failure is "
    "non-fatal — log and continue; the session work is preserved in "
    "git regardless.\n\n"
    "Return a one-paragraph summary: what close_session reported, "
    "which gates passed/failed, whether the session reached `closed` "
    "lifecycle state, and whether the notification was sent."
)


_logger = logging.getLogger("ai_router.close_out")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)
_logger.setLevel(logging.INFO)
_logger.propagate = False


CLOSE_OUT_RESULTS = (
    "skipped_disposition_missing",
    "skipped_disposition_not_completed",
    "routed",
    "route_failed",
)


@dataclass
class FreshCloseOutResult:
    """Outcome of one ``route_fresh_close_out_turn`` invocation.

    The hook never raises; failures of the routed turn surface as a
    populated ``error`` plus a ``*_failed`` result string.
    ``route_result`` is populated when the route() call returned.
    """

    result: str
    session_set_dir: str
    messages: List[str] = field(default_factory=list)
    route_result: Optional[Any] = None
    error: Optional[str] = None


def _disposition_says_completed(
    disposition: Optional[Disposition],
) -> bool:
    """Pre-flight check: only fire close-out for completed sessions.

    A session that ends in ``failed`` or ``requires_review`` is not
    eligible for close-out — those land on the human's desk via the
    Step 7 path, not the close-out gate.
    """
    return disposition is not None and disposition.status == "completed"


def route_fresh_close_out_turn(
    session_set_dir: str,
    *,
    route_fn: Optional[Callable[..., Any]] = None,
) -> FreshCloseOutResult:
    """Fresh close-out turn.

    Reads ``disposition.json``, then routes a fresh turn to the
    close-out agent. Returns a :class:`FreshCloseOutResult` describing
    what happened. Never raises — every failure path populates
    ``result`` and ``error`` instead.

    Injection point:

    * ``route_fn`` — defaults to :func:`ai_router.route`. Tests inject
      a fake to avoid real API calls.
    """
    out = FreshCloseOutResult(
        result="",
        session_set_dir=session_set_dir,
    )

    disposition = read_disposition(session_set_dir)
    if disposition is None:
        out.result = "skipped_disposition_missing"
        out.messages.append(
            f"disposition.json not found in {session_set_dir}; "
            "close-out routing skipped"
        )
        return out

    if not _disposition_says_completed(disposition):
        out.result = "skipped_disposition_not_completed"
        out.messages.append(
            f"disposition.status={disposition.status!r}; "
            "close-out routing only fires for status=='completed'"
        )
        return out

    # Importing ai_router lazily avoids a circular import at module
    # load time (ai_router/__init__.py imports from this module
    # transitively via the public API).
    if route_fn is None:
        try:
            from . import route as _route  # type: ignore[no-redef]
        except ImportError:
            import importlib
            ai_router_mod = importlib.import_module("ai_router")
            _route = ai_router_mod.route
        route_fn = _route

    prompt = _CLOSE_OUT_TURN_CONTENT.format(
        session_set_dir=session_set_dir
    )
    try:
        rr = route_fn(
            content=prompt,
            task_type=SESSION_CLOSE_OUT_TASK_TYPE,
            session_set=session_set_dir,
        )
    except Exception as exc:  # noqa: BLE001 — never raise from the hook
        out.result = "route_failed"
        out.error = f"{type(exc).__name__}: {exc}"
        out.messages.append(
            "route_fn raised; reconciler will retry on next startup"
        )
        return out

    out.route_result = rr
    out.result = "routed"
    out.messages.append(
        "fresh close-out turn routed; the routed agent is "
        "responsible for invoking close_session"
    )
    return out


# ---------------------------------------------------------------------------
# CLI — exposed so operators can manually trigger the hook for debugging.
# Production wiring calls ``route_fresh_close_out_turn`` from Python.
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m ai_router.close_out",
        description=(
            "Manually fire the fresh close-out hook for one session "
            "set. Used for debugging the orchestrator-side wiring; "
            "production calls invoke route_fresh_close_out_turn "
            "directly from Python."
        ),
    )
    p.add_argument(
        "--session-set-dir",
        required=True,
        help="Path to the session-set directory.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    out = route_fresh_close_out_turn(args.session_set_dir)
    print(f"result: {out.result}")
    if out.error:
        print(f"error: {out.error}")
    for msg in out.messages:
        print(f"  - {msg}")
    return 1 if out.error else 0


__all__ = [
    "CLOSE_OUT_RESULTS",
    "FreshCloseOutResult",
    "SESSION_CLOSE_OUT_TASK_TYPE",
    "route_fresh_close_out_turn",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
