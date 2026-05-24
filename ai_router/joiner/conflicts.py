"""Conflict detection for ai_router.joiner.

Implements the three conflict modes specified in joiner-spec.md §3:

- Mode A: engine-mismatch (high severity)
- Mode B: bare-touch / stale-checkout-touch (medium severity)
- Mode C: writer-bypass session-state write (high severity)

The detector reads session-state.json + native logs + (eventually)
the events-ledger; it does NOT write. Per Set 033 H1/H2, the joiner
is observation-only.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Literal, Optional

from ai_router.joiner import parsers
from ai_router.joiner.parsers import (
    NativeSession,
    SessionStateView,
    scan_native_sessions,
    scan_session_states,
)
from ai_router.joiner.schema import normalize_engine, parse_iso

ConflictKind = Literal[
    "engine-mismatch",
    "bare-touch",
    "stale-checkout-touch",
    "writer-bypass",
]

Severity = Literal["high", "medium", "low"]


DEFAULT_ENGINE_MISMATCH_WINDOW = timedelta(minutes=5)
DEFAULT_STALENESS_THRESHOLD = timedelta(hours=2)
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
# Mode A — engine-mismatch.
# ---------------------------------------------------------------------------


def detect_engine_mismatch(
    state: SessionStateView,
    native_sessions: Iterable[NativeSession],
    *,
    window: timedelta = DEFAULT_ENGINE_MISMATCH_WINDOW,
    detected_at: Optional[datetime] = None,
) -> list[ConflictReport]:
    """Surface engine-mismatch reports for one state-file view."""
    if state.orchestrator_engine is None or state.last_activity is None:
        return []
    state_engine_norm = normalize_engine(state.orchestrator_engine)
    state_cwd_canon = parsers.canonicalize_cwd(str(state.workspace_root))
    when = detected_at or datetime.now(timezone.utc)
    reports: list[ConflictReport] = []
    for ns in native_sessions:
        if ns.cwd_canonical != state_cwd_canon:
            continue
        delta = abs(ns.first_event_ts - state.last_activity)
        if delta > window:
            continue
        if normalize_engine(ns.engine) == state_engine_norm:
            continue
        reports.append(
            ConflictReport(
                kind="engine-mismatch",
                severity="high",
                detected_at=when,
                set_slug=state.set_slug,
                state_file=str(state.state_file),
                workspace_cwd_canonical=state_cwd_canon,
                evidence={
                    "state_engine": state.orchestrator_engine,
                    "native_engine": ns.engine,
                    "native_conv_id": ns.conv_id,
                    "delta_seconds": round(delta.total_seconds(), 1),
                },
                raw_refs=[
                    {"file": str(state.state_file), "field": "orchestrator.engine"},
                    {"file": ns.source_file, "field": "first-event"},
                ],
                note=(
                    f"state-file claims {state.orchestrator_engine} but "
                    f"{ns.engine} session {ns.conv_id} is active in the "
                    f"same workspace within {delta.total_seconds():.0f}s"
                ),
            )
        )
    return reports


# ---------------------------------------------------------------------------
# Mode B — bare-touch / stale-checkout-touch.
# ---------------------------------------------------------------------------


def detect_bare_or_stale_touch(
    state: SessionStateView,
    native_sessions: Iterable[NativeSession],
    *,
    staleness_threshold: timedelta = DEFAULT_STALENESS_THRESHOLD,
    detected_at: Optional[datetime] = None,
) -> list[ConflictReport]:
    """Surface bare-touch or stale-checkout-touch reports for one state.

    Mode B fires when an AI is active in the workspace housing this
    session set but no fresh checkout claim is in place.
    """
    when = detected_at or datetime.now(timezone.utc)
    state_cwd_canon = parsers.canonicalize_cwd(str(state.workspace_root))
    reports: list[ConflictReport] = []

    if state.orchestrator_engine is None:
        # Bare-touch — no checkout block at all.
        for ns in native_sessions:
            # Touch must be strictly inside the workspace boundary.
            if not _touches_workspace(ns.cwd_canonical, state_cwd_canon):
                continue
            reports.append(
                ConflictReport(
                    kind="bare-touch",
                    severity="medium",
                    detected_at=when,
                    set_slug=state.set_slug,
                    state_file=str(state.state_file),
                    workspace_cwd_canonical=state_cwd_canon,
                    evidence={
                        "native_engine": ns.engine,
                        "native_conv_id": ns.conv_id,
                        "checkout_age_seconds": None,
                        "first_event_ts": ns.first_event_ts.isoformat(),
                    },
                    raw_refs=[
                        {"file": str(state.state_file), "field": "orchestrator"},
                        {"file": ns.source_file, "field": "first-event"},
                    ],
                    note=(
                        f"no checkout but {ns.engine} session {ns.conv_id} "
                        f"active in workspace housing set {state.set_slug}"
                    ),
                )
            )
        return reports

    # Stale-checkout-touch — checkout exists but is ancient.
    if state.last_activity is None:
        return reports
    age = when - state.last_activity
    if age <= staleness_threshold:
        return reports
    for ns in native_sessions:
        if not _touches_workspace(ns.cwd_canonical, state_cwd_canon):
            continue
        if ns.first_event_ts <= state.last_activity + staleness_threshold:
            continue
        reports.append(
            ConflictReport(
                kind="stale-checkout-touch",
                severity="medium",
                detected_at=when,
                set_slug=state.set_slug,
                state_file=str(state.state_file),
                workspace_cwd_canonical=state_cwd_canon,
                evidence={
                    "native_engine": ns.engine,
                    "native_conv_id": ns.conv_id,
                    "checkout_age_seconds": round(age.total_seconds(), 1),
                    "first_event_ts": ns.first_event_ts.isoformat(),
                },
                raw_refs=[
                    {"file": str(state.state_file), "field": "orchestrator.lastActivityAt"},
                    {"file": ns.source_file, "field": "first-event"},
                ],
                note=(
                    f"checkout {age.total_seconds() / 3600:.1f}h stale; "
                    f"{ns.engine} session {ns.conv_id} touching workspace anyway"
                ),
            )
        )
    return reports


def _touches_workspace(native_cwd_canon: str, workspace_canon: str) -> bool:
    """Return True if the native session's cwd is inside the workspace."""
    if not native_cwd_canon or not workspace_canon:
        return False
    if native_cwd_canon == workspace_canon:
        return True
    return native_cwd_canon.startswith(workspace_canon + "/")


# ---------------------------------------------------------------------------
# Mode C — writer-bypass.
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
    within ``event_tolerance_ns``. The canonical writers append an
    event in the same transaction as the state-file write.
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
    claude_root: Optional[Path] = None,
    copilot_root: Optional[Path] = None,
    detected_at: Optional[datetime] = None,
    engine_mismatch_window: timedelta = DEFAULT_ENGINE_MISMATCH_WINDOW,
    staleness_threshold: timedelta = DEFAULT_STALENESS_THRESHOLD,
) -> list[ConflictReport]:
    """Scan all known state files and emit conflict reports.

    Args:
        set_slug: optionally restrict to one session set.
        workspace_root: defaults to ``Path.cwd()``; the joiner walks
            ``<root>/docs/session-sets/*/session-state.json`` from
            there.
        claude_root / copilot_root: override default operator-home
            scanner roots (used in tests + when scanning a remote
            machine's logs).
        detected_at: pin the joiner-run timestamp (for deterministic
            tests).
    """
    root = workspace_root or Path.cwd()
    natives = list(scan_native_sessions(claude_root=claude_root, copilot_root=copilot_root))
    reports: list[ConflictReport] = []
    for state in scan_session_states(root):
        if set_slug and state.set_slug != set_slug:
            continue
        reports.extend(
            detect_engine_mismatch(
                state,
                natives,
                window=engine_mismatch_window,
                detected_at=detected_at,
            )
        )
        reports.extend(
            detect_bare_or_stale_touch(
                state,
                natives,
                staleness_threshold=staleness_threshold,
                detected_at=detected_at,
            )
        )
        reports.extend(
            detect_writer_bypass(state, detected_at=detected_at)
        )
    return reports
