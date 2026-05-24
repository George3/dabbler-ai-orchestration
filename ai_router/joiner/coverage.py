"""Per-session-set coverage summaries for ai_router.joiner.

See joiner-spec.md §6. The Explorer (S5) renders per-row badges
from these summaries; the Q1 bypass-rate computation (S5) also
reads them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ai_router.joiner import parsers
from ai_router.joiner.parsers import (
    NativeSession,
    scan_launch_log,
    scan_native_sessions,
    scan_session_states,
)


@dataclass(frozen=True)
class CoverageSummary:
    set_slug: str
    workspace_cwd_canonical: str
    wrapper_launched: bool
    narration_present: bool
    native_log_bound: bool
    last_signal_ts: Optional[datetime]
    bypass_inferred: bool

    def to_json_dict(self) -> dict:
        payload = asdict(self)
        payload["last_signal_ts"] = (
            self.last_signal_ts.isoformat() if self.last_signal_ts else None
        )
        return payload


def coverage(
    *,
    workspace_root: Optional[Path] = None,
    claude_root: Optional[Path] = None,
    copilot_root: Optional[Path] = None,
    launch_log: Optional[Path] = None,
) -> list[CoverageSummary]:
    """Compute per-session-set coverage summaries.

    S2 ships the structural skeleton; the ``narration_present``
    field returns False until S4 emits ``marker`` events. The
    ``wrapper_launched`` field returns False until S3 ships
    ``dabbler-launch`` and the launch log starts accumulating
    records.
    """
    root = workspace_root or Path.cwd()
    natives = list(scan_native_sessions(claude_root=claude_root, copilot_root=copilot_root))
    launches = list(scan_launch_log(launch_log))
    summaries: list[CoverageSummary] = []
    for state in scan_session_states(root):
        workspace_canon = parsers.canonicalize_cwd(str(state.workspace_root))
        relevant_natives = [
            n for n in natives
            if n.cwd_canonical == workspace_canon
            or n.cwd_canonical.startswith(workspace_canon + "/")
        ]
        wrapper_launched = any(
            launch.set_slug == state.set_slug for launch in launches
        )
        native_log_bound = bool(relevant_natives)
        last_signal_ts = _max_ts(relevant_natives)
        summaries.append(
            CoverageSummary(
                set_slug=state.set_slug,
                workspace_cwd_canonical=workspace_canon,
                wrapper_launched=wrapper_launched,
                narration_present=False,  # S4 wires this
                native_log_bound=native_log_bound,
                last_signal_ts=last_signal_ts,
                bypass_inferred=native_log_bound and not wrapper_launched,
            )
        )
    return summaries


def _max_ts(natives: list[NativeSession]) -> Optional[datetime]:
    candidates = [
        n.last_event_ts or n.first_event_ts for n in natives
    ]
    if not candidates:
        return None
    return max(candidates)
