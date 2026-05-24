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
from datetime import datetime, timezone
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


def harvest(
    workspace_cwd: Optional[str] = None,
    since: Optional[datetime] = None,
) -> Iterable[HarvestRecord]:
    """Yield the joined Harvest Record stream from current producers.

    S2 skeleton: produces the records the parsers can surface today
    (native-log first-event records). The wrapper launch records
    join in once S3 ships ``dabbler-launch``; until then the
    ``binding_state`` field is None on emitted records (they are
    surfaced as ``session_start`` events from the native side
    only).

    Args:
        workspace_cwd: optionally restrict to one workspace.
        since: optionally restrict to events after this timestamp.

    Yields:
        ``HarvestRecord`` instances in chronological order.
    """
    # Local import to avoid a circular import at package init time.
    from ai_router.joiner import parsers

    cwd_filter = canonicalize_cwd(workspace_cwd) if workspace_cwd else None
    records: list[HarvestRecord] = []

    for native in parsers.scan_native_sessions():
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
