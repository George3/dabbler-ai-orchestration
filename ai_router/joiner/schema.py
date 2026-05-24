"""Canonical Harvest Record schema for ai_router.joiner.

Derived from joiner-spec.md §5. The dataclasses defined here are
what producers (S3 wrapper, S3 Copilot parser, S4 Claude parser,
S4 narration marker emitter) MUST emit and what consumers
(Explorer in S5, audit tools, conflict detector) MUST consume.

This module also holds the canonicalization helpers shared across
the joiner package and the ``harvest()`` entry point which assembles
the joined event stream from currently-available producers.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

EventType = Literal[
    "launch",
    "session_start",
    "turn",
    "tool_call",
    "marker",
    "usage",
    "session_end",
]

Source = Literal["wrapper", "claude-native", "copilot-native", "narration"]

Engine = Literal["claude", "copilot", "codex", "gemini"]

BindingState = Literal["bound", "unbound", "ambiguous"]


# ---------------------------------------------------------------------------
# Canonicalization helpers (shared across joiner modules).
# ---------------------------------------------------------------------------


def canonicalize_cwd(cwd: str) -> str:
    """Normalize a workspace cwd into the joiner's comparison form.

    Rules: forward-slashed, lowercased, no trailing slash. Case-
    insensitive on Windows; harmless on POSIX (lowercasing already-
    lowercase paths). See joiner-spec.md §3.4.
    """
    if not cwd:
        return ""
    return cwd.replace("\\", "/").rstrip("/").lower()


def normalize_engine(engine: str) -> str:
    """Strip ``-code`` / ``-cli`` suffixes and lowercase.

    The state file may carry ``claude-code`` while the native log
    carries ``claude``; the join must compare on the base engine.
    """
    if not engine:
        return ""
    base = engine.lower()
    for suffix in ("-code", "-cli"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp into a tz-aware UTC datetime.

    Tolerates trailing ``Z`` (Python <3.11 lacks native support).
    """
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    parsed = datetime.fromisoformat(ts)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Canonical Harvest Record (joiner-spec.md §5).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarvestRecord:
    ts: datetime
    event_type: EventType
    source: Source
    engine: Engine
    workspace_cwd: str
    workspace_cwd_canonical: str
    raw_ref: dict = field(default_factory=dict)

    provider: Optional[str] = None
    model: Optional[str] = None
    conv_id: Optional[str] = None

    set_slug: Optional[str] = None
    session_number: Optional[int] = None

    binding_state: Optional[BindingState] = None
    bound_candidates: Optional[list[str]] = None

    effort: Optional[str] = None
    tool: Optional[str] = None
    tool_args_summary: Optional[dict] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None

    def to_json_dict(self) -> dict:
        """Serialize to a JSON-safe dict (datetimes → ISO strings)."""
        payload = asdict(self)
        payload["ts"] = self.ts.isoformat()
        return payload


# ---------------------------------------------------------------------------
# ``harvest()`` public entry point.
# ---------------------------------------------------------------------------


DEFAULT_BIND_WINDOW = timedelta(seconds=30)


def harvest(
    workspace_cwd: Optional[str] = None,
    since: Optional[datetime] = None,
    *,
    claude_root: Optional[Path] = None,
    copilot_root: Optional[Path] = None,
    launch_log: Optional[Path] = None,
    bind_window: timedelta = DEFAULT_BIND_WINDOW,
) -> Iterable[HarvestRecord]:
    """Yield the joined Harvest Record stream from current producers.

    Applies the joiner-spec.md §4 positive-case join algorithm:
    each wrapper-launch record is matched to candidate native
    sessions by engine + canonicalized cwd + ``bind_window``
    timestamp delta. The result is emitted as a ``launch`` record
    with ``binding_state ∈ {"bound", "unbound", "ambiguous"}``;
    bound native sessions are emitted as a single ``session_start``
    record (carrying the bound conv_id back to the launch).

    Native sessions that no launch claimed (free-running) are
    emitted as their own ``session_start`` records with no
    ``binding_state`` set — these are the bypass-channel data
    points the Q1 self-observation supplements.

    Args:
        workspace_cwd: optionally restrict to one workspace.
        since: optionally restrict to events after this timestamp.
        claude_root / copilot_root: parser-root overrides (testing).
        launch_log: override the wrapper launch log path.
        bind_window: launch ↔ native-session timestamp tolerance.

    Yields:
        ``HarvestRecord`` instances in chronological order.
    """
    # Local imports avoid a circular package-init dependency.
    from ai_router.joiner import parsers

    cwd_filter = canonicalize_cwd(workspace_cwd) if workspace_cwd else None
    natives = list(
        parsers.scan_native_sessions(
            claude_root=claude_root,
            copilot_root=copilot_root,
        )
    )
    launches = list(parsers.scan_launch_log(launch_log))

    records: list[HarvestRecord] = []
    bound_native_ids: set[tuple[str, str]] = set()

    for launch in launches:
        candidates = [
            ns for ns in natives
            if ns.engine == launch.engine
            and ns.cwd_canonical == launch.workspace_cwd_canonical
            and abs(ns.first_event_ts - launch.launch_ts) <= bind_window
        ]
        if cwd_filter and launch.workspace_cwd_canonical != cwd_filter:
            continue
        if since and launch.launch_ts < since:
            continue
        if len(candidates) == 0:
            binding_state: BindingState = "unbound"
            conv_id: Optional[str] = None
            bound_candidates: Optional[list[str]] = None
        elif len(candidates) == 1:
            binding_state = "bound"
            conv_id = candidates[0].conv_id
            bound_candidates = None
            bound_native_ids.add((candidates[0].engine, candidates[0].conv_id))
        else:
            binding_state = "ambiguous"
            conv_id = None
            bound_candidates = [c.conv_id for c in candidates]
        records.append(
            HarvestRecord(
                ts=launch.launch_ts,
                event_type="launch",
                source="wrapper",
                engine=launch.engine,  # type: ignore[arg-type]
                workspace_cwd=launch.workspace_cwd,
                workspace_cwd_canonical=launch.workspace_cwd_canonical,
                set_slug=launch.set_slug,
                session_number=launch.session_number,
                conv_id=conv_id,
                provider=launch.provider,
                model=launch.model,
                effort=launch.effort,
                binding_state=binding_state,
                bound_candidates=bound_candidates,
                raw_ref=launch.raw_ref,
            )
        )

    for native in natives:
        if cwd_filter and native.cwd_canonical != cwd_filter:
            continue
        if since and native.first_event_ts < since:
            continue
        records.append(
            HarvestRecord(
                ts=native.first_event_ts,
                event_type="session_start",
                source=f"{native.engine}-native",  # type: ignore[arg-type]
                engine=native.engine,  # type: ignore[arg-type]
                workspace_cwd=native.cwd_canonical,
                workspace_cwd_canonical=native.cwd_canonical,
                conv_id=native.conv_id,
                raw_ref={"file": native.source_file, "field": "first-event"},
            )
        )

    records.sort(key=lambda r: r.ts)
    yield from records


def serialize_records(records: Iterable[HarvestRecord]) -> str:
    """JSON-encode an iterable of records into a list payload."""
    return json.dumps([r.to_json_dict() for r in records], indent=2)
