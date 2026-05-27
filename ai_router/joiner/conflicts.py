"""Writer-discipline conflict detection for ai_router.joiner.

Set 049 retired the Set 033 / Set 036 coordination-conflict detectors
(engine-mismatch, bare-touch, stale-checkout-touch) along with the
rest of the H3 + H4 coordination layer (D1 + D2 in the audit). Each
of those detectors depended on the orchestrator block's
``lastActivityAt`` / ``checkedOutAt`` timestamps or the implicit
"engine claims the workspace" semantic, neither of which survives
the rip-out.

What remains is the writer-bypass detector (D3 in the audit verdict),
decoupled from the coordination framing: ``session-state.json``'s
mtime should be bracketed by a ``session-events.jsonl`` entry within
the standard tolerance, regardless of which orchestrator wrote the
file. A miss surfaces an out-of-band write that the canonical writers
did not perform — a discipline check that is engine-independent and
useful even when there is no coordination model in play.

The detector reads ``session-state.json`` + the sibling
``session-events.jsonl``; it does NOT write. Per Set 033 H1/H2 the
joiner remains observation-only.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from ai_router.joiner import parsers
from ai_router.joiner.parsers import (
    SessionStateView,
    scan_session_states,
)
from ai_router.joiner.schema import parse_iso

# Set 049: ConflictKind narrowed to just ``writer-bypass``. The three
# retired coordination kinds (engine-mismatch / bare-touch /
# stale-checkout-touch) are no longer emitted by the joiner; downstream
# consumers (HarvestService.parseConflicts in the extension) drop
# unknown kinds silently so historical journal entries keep round-
# tripping cleanly.
ConflictKind = Literal["writer-bypass"]

Severity = Literal["high", "medium", "low"]


DEFAULT_WRITER_BYPASS_EVENT_TOLERANCE_NS = 2_000_000_000  # ±2 seconds


@dataclass(frozen=True)
class ConflictReport:
    kind: ConflictKind
    severity: Severity
    detected_at: datetime
    set_slug: Optional[str]
    state_file: str
    workspace_cwd_canonical: str
    evidence: dict
    raw_refs: list[dict] = field(default_factory=list)
    note: str = ""

    def to_json_dict(self) -> dict:
        payload = asdict(self)
        payload["detected_at"] = self.detected_at.isoformat()
        return payload


# ---------------------------------------------------------------------------
# Writer-bypass — out-of-band writes the canonical writers did not perform.
# ---------------------------------------------------------------------------


def detect_writer_bypass(
    state: SessionStateView,
    *,
    detected_at: Optional[datetime] = None,
    event_tolerance_ns: int = DEFAULT_WRITER_BYPASS_EVENT_TOLERANCE_NS,
) -> list[ConflictReport]:
    """Surface writer-bypass reports for one state file.

    A bypass is suspected when ``session-state.json``'s mtime is not
    bracketed by a corresponding ``session-events.jsonl`` entry
    within ``event_tolerance_ns``. The canonical writers
    (``register_session_start`` / ``_flip_state_to_closed`` and their
    TS mirrors) append an event in the same transaction as the
    state-file write; a divergence indicates the snapshot was touched
    out-of-band.

    Set 049: this is the only conflict mode the joiner still emits.
    The framing was decoupled from the coordination layer it was
    originally spec'd alongside — the predicate is purely a writer-
    discipline check (state-file mtime vs. events ledger entries),
    engine-independent, and useful even with no holder model.
    """
    when = detected_at or datetime.now(timezone.utc)
    try:
        state_mtime_ns = state.state_file.stat().st_mtime_ns
    except OSError:
        return []
    events_path = state.state_file.with_name("session-events.jsonl")
    if not events_path.exists():
        # No events ledger at all — bypass is the wrong frame; the set
        # may be too old to have one yet. Skip rather than false-positive.
        return []
    nearest_event_ns: Optional[int] = None
    nearest_delta_ns: Optional[int] = None
    try:
        with open(events_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_str = rec.get("ts") or rec.get("timestamp")
                if not ts_str:
                    continue
                try:
                    ts = parse_iso(ts_str)
                except ValueError:
                    continue
                evt_ns = int(ts.timestamp() * 1_000_000_000)
                delta = abs(evt_ns - state_mtime_ns)
                if nearest_delta_ns is None or delta < nearest_delta_ns:
                    nearest_delta_ns = delta
                    nearest_event_ns = evt_ns
    except OSError:
        return []

    if nearest_delta_ns is None:
        # Empty ledger — same caveat as missing ledger; skip.
        return []
    if nearest_delta_ns <= event_tolerance_ns:
        return []
    return [
        ConflictReport(
            kind="writer-bypass",
            severity="high",
            detected_at=when,
            set_slug=state.set_slug,
            state_file=str(state.state_file),
            workspace_cwd_canonical=parsers.canonicalize_cwd(str(state.workspace_root)),
            evidence={
                "state_mtime_ns": state_mtime_ns,
                "nearest_event_ts_ns": nearest_event_ns,
                "delta_seconds": round(nearest_delta_ns / 1_000_000_000, 3),
                "content_hash": None,
            },
            raw_refs=[
                {"file": str(state.state_file), "field": "mtime"},
                {"file": str(events_path), "field": "nearest-event"},
            ],
            note=(
                f"state-file mtime is {nearest_delta_ns / 1_000_000_000:.1f}s "
                f"from the nearest events-ledger entry; canonical writers "
                f"bracket within ±2s"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Top-level entry point: scan_conflicts().
# ---------------------------------------------------------------------------


def scan_conflicts(
    set_slug: Optional[str] = None,
    *,
    workspace_root: Optional[Path] = None,
    detected_at: Optional[datetime] = None,
) -> list[ConflictReport]:
    """Scan all known state files and emit writer-bypass conflict reports.

    Args:
        set_slug: optionally restrict to one session set.
        workspace_root: defaults to ``Path.cwd()``; the joiner walks
            ``<root>/docs/session-sets/*/session-state.json`` from
            there.
        detected_at: pin the joiner-run timestamp (for deterministic
            tests).

    Set 049: the ``claude_root`` / ``copilot_root`` / ``engine_mismatch_window``
    / ``staleness_threshold`` parameters are gone with the retired
    engine-mismatch + stale-checkout-touch detectors. Callers that
    passed those kwargs need to update to the writer-bypass-only
    signature.
    """
    root = workspace_root or Path.cwd()
    reports: list[ConflictReport] = []
    for state in scan_session_states(root):
        if set_slug and state.set_slug != set_slug:
            continue
        reports.extend(
            detect_writer_bypass(state, detected_at=detected_at)
        )
    return reports
