"""Q2 spike — deterministic wrapper-to-native-log correlation prototype.

Set 045 / Session 1 spike. Throwaway code — kept under
spike-prototypes/ for reference, not promoted to shipping surface.

Hypothesis
----------
A `dabbler-launch` wrapper record carrying
``(launch_ts, workspace_cwd, target_backend)`` can be 1:1 joined to
the AI's native log records via:

    Claude:  ~/.claude/projects/<workspace-slug>/<conv_id>.jsonl
             — first 'user' event carries (sessionId, timestamp, cwd).
    Copilot: ~/.copilot/session-state/<conv_id>/events.jsonl
             — first record is type=session.start with
               (sessionId, startTime, data.context.cwd).

Join keys: ``(workspace_cwd matches)`` AND
``(first_native_event_ts within +/- window of launch_ts)``.

This prototype exercises the join against real on-disk logs to
demonstrate the binding is deterministic at a tight window (default
30 s). Outputs a JSON report; no side effects.

Run:
    python correlation_prototype.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Path normalization — Claude's project-dir slug encodes cwd. Copilot stores
# cwd as a free-form string in data.context.cwd. Both need a canonical
# comparison form (case-insensitive on Windows, forward-slashed, no trailing
# slash) so the join key is stable across path conventions.
# ---------------------------------------------------------------------------


def canonicalize_cwd(cwd: str) -> str:
    if not cwd:
        return ""
    # Normalize separators and case for Windows; resolve to absolute if possible.
    normalized = cwd.replace("\\", "/").rstrip("/").lower()
    return normalized


def claude_slug_to_cwd(slug: str) -> str:
    # Claude's project-dir slug format on Windows: "C--tmp-foo-bar"
    # (drive letter + "--" + path-with-dashes). Reverse to a path-like
    # string for canonical comparison. This is a heuristic: dashes in
    # the original path become indistinguishable from path separators,
    # so a path like ``c:/foo-bar`` slugs to ``c--foo-bar`` and
    # canonicalizes to ``c/foo/bar`` — the join compares against the
    # canonical form of the native cwd, not the slug, so this is a
    # fallback only when the JSONL's own cwd field is missing.
    if len(slug) >= 4 and slug[1:3] == "--":
        drive = slug[0]
        rest = slug[3:].replace("-", "/")
        return canonicalize_cwd(f"{drive}:/{rest}")
    return canonicalize_cwd(slug)


# ---------------------------------------------------------------------------
# Native-log scrapers — return the minimal tuple needed for the join.
# ---------------------------------------------------------------------------


@dataclass
class NativeSession:
    engine: str                 # 'claude' | 'copilot'
    conv_id: str                # native sessionId
    first_event_ts: datetime    # earliest signal we can pin
    cwd_canonical: str
    source_file: str
    cwd_source: str             # 'jsonl-field' | 'slug-fallback' | 'context'


def _parse_iso(ts: str) -> datetime:
    # Tolerate trailing 'Z' (Python <3.11 needs explicit timezone).
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def scan_claude_logs(root: Path) -> Iterable[NativeSession]:
    if not root.exists():
        return
    for workspace_dir in root.iterdir():
        if not workspace_dir.is_dir():
            continue
        slug_cwd = claude_slug_to_cwd(workspace_dir.name)
        for jsonl_path in workspace_dir.glob("*.jsonl"):
            conv_id = jsonl_path.stem
            first_ts: datetime | None = None
            cwd_field: str | None = None
            try:
                with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        ts_str = rec.get("timestamp")
                        if ts_str and first_ts is None:
                            try:
                                first_ts = _parse_iso(ts_str)
                            except ValueError:
                                pass
                        if not cwd_field:
                            c = rec.get("cwd")
                            if c:
                                cwd_field = c
                        if first_ts and cwd_field:
                            break
            except OSError:
                continue
            if first_ts is None:
                continue
            if cwd_field:
                cwd_canon = canonicalize_cwd(cwd_field)
                cwd_source = "jsonl-field"
            else:
                cwd_canon = slug_cwd
                cwd_source = "slug-fallback"
            yield NativeSession(
                engine="claude",
                conv_id=conv_id,
                first_event_ts=first_ts,
                cwd_canonical=cwd_canon,
                source_file=str(jsonl_path),
                cwd_source=cwd_source,
            )


def scan_copilot_logs(root: Path) -> Iterable[NativeSession]:
    if not root.exists():
        return
    for session_dir in root.iterdir():
        if not session_dir.is_dir():
            continue
        events = session_dir / "events.jsonl"
        if not events.exists():
            continue
        try:
            with open(events, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline().strip()
                if not first_line:
                    continue
                try:
                    rec = json.loads(first_line)
                except json.JSONDecodeError:
                    continue
        except OSError:
            continue
        if rec.get("type") != "session.start":
            continue
        data = rec.get("data", {})
        conv_id = data.get("sessionId") or session_dir.name
        start_ts = data.get("startTime") or rec.get("timestamp")
        if not start_ts:
            continue
        try:
            first_ts = _parse_iso(start_ts)
        except ValueError:
            continue
        cwd = data.get("context", {}).get("cwd")
        yield NativeSession(
            engine="copilot",
            conv_id=conv_id,
            first_event_ts=first_ts,
            cwd_canonical=canonicalize_cwd(cwd) if cwd else "",
            source_file=str(events),
            cwd_source="context",
        )


# ---------------------------------------------------------------------------
# Synthetic launch record + join logic.
# ---------------------------------------------------------------------------


@dataclass
class LaunchRecord:
    """What `dabbler-launch` would write before spawning the AI subprocess."""

    launch_ts: datetime
    workspace_cwd: str
    set_slug: str
    session_number: int
    effort: str
    target_backend: str         # 'claude' | 'copilot'
    launch_id: str              # uuid the wrapper generates; carried for audit only

    def workspace_canonical(self) -> str:
        return canonicalize_cwd(self.workspace_cwd)


@dataclass
class JoinResult:
    launch: LaunchRecord
    candidates: list[NativeSession]   # candidates within window
    bound: NativeSession | None       # 1:1 binding (only if len(candidates)==1)
    ambiguity: str | None             # 'no-match' | 'multi-match' | None


def join(
    launch: LaunchRecord,
    natives: list[NativeSession],
    window: timedelta = timedelta(seconds=30),
) -> JoinResult:
    cwd_canon = launch.workspace_canonical()
    candidates: list[NativeSession] = []
    for ns in natives:
        if ns.engine != launch.target_backend:
            continue
        if ns.cwd_canonical != cwd_canon:
            continue
        delta = abs(ns.first_event_ts - launch.launch_ts)
        if delta <= window:
            candidates.append(ns)
    if not candidates:
        return JoinResult(launch=launch, candidates=[], bound=None, ambiguity="no-match")
    if len(candidates) > 1:
        return JoinResult(launch=launch, candidates=candidates, bound=None, ambiguity="multi-match")
    return JoinResult(launch=launch, candidates=candidates, bound=candidates[0], ambiguity=None)


# ---------------------------------------------------------------------------
# Demo: synthesize launch records that should bind to known on-disk
# sessions, then exercise the join at multiple window sizes.
# ---------------------------------------------------------------------------


def demo() -> dict:
    home = Path(os.path.expanduser("~"))
    claude_root = home / ".claude" / "projects"
    copilot_root = home / ".copilot" / "session-state"

    natives = list(scan_claude_logs(claude_root)) + list(scan_copilot_logs(copilot_root))

    # Pick a recent known Claude session as our positive-case target.
    # Sort by first_event_ts desc; pick the first claude session whose cwd
    # contains 'dabbler-ai-orchestration'.
    claude_target: NativeSession | None = None
    for ns in sorted(natives, key=lambda x: x.first_event_ts, reverse=True):
        if ns.engine == "claude" and "dabbler-ai-orchestration" in ns.cwd_canonical:
            claude_target = ns
            break

    # And a Copilot session from the synthetic-set.
    copilot_target: NativeSession | None = None
    for ns in sorted(natives, key=lambda x: x.first_event_ts):
        if ns.engine == "copilot" and "synthetic-set" in ns.cwd_canonical:
            copilot_target = ns
            break

    results: list[dict] = []

    def add(label: str, jr: JoinResult) -> None:
        results.append(
            {
                "label": label,
                "launch_ts": jr.launch.launch_ts.isoformat(),
                "target_backend": jr.launch.target_backend,
                "workspace_canonical": jr.launch.workspace_canonical(),
                "ambiguity": jr.ambiguity,
                "n_candidates": len(jr.candidates),
                "bound_conv_id": jr.bound.conv_id if jr.bound else None,
                "bound_source_file": jr.bound.source_file if jr.bound else None,
            }
        )

    # Positive case A: launch record 5 s before claude_target's first event
    # — should bind 1:1 at 30 s window.
    if claude_target:
        offset_seconds = 5
        launch_a = LaunchRecord(
            launch_ts=claude_target.first_event_ts - timedelta(seconds=offset_seconds),
            workspace_cwd=claude_target.cwd_canonical,
            set_slug="045-log-harvest-implementation",
            session_number=1,
            effort="high",
            target_backend="claude",
            launch_id="demo-positive-claude",
        )
        add("positive-claude-30s", join(launch_a, natives, timedelta(seconds=30)))
        add("positive-claude-5s", join(launch_a, natives, timedelta(seconds=5)))
        add("positive-claude-2s", join(launch_a, natives, timedelta(seconds=2)))

    # Positive case B: copilot, same idea.
    if copilot_target:
        launch_b = LaunchRecord(
            launch_ts=copilot_target.first_event_ts - timedelta(seconds=5),
            workspace_cwd=copilot_target.cwd_canonical,
            set_slug="045-log-harvest-implementation",
            session_number=1,
            effort="high",
            target_backend="copilot",
            launch_id="demo-positive-copilot",
        )
        add("positive-copilot-30s", join(launch_b, natives, timedelta(seconds=30)))

    # Negative case A: launch 10 minutes off — should produce no-match.
    if claude_target:
        launch_c = LaunchRecord(
            launch_ts=claude_target.first_event_ts - timedelta(minutes=10),
            workspace_cwd=claude_target.cwd_canonical,
            set_slug="045-log-harvest-implementation",
            session_number=1,
            effort="high",
            target_backend="claude",
            launch_id="demo-negative-far",
        )
        add("negative-far-30s", join(launch_c, natives, timedelta(seconds=30)))

    # Negative case B: wrong cwd — should produce no-match even if time matches.
    if claude_target:
        launch_d = LaunchRecord(
            launch_ts=claude_target.first_event_ts - timedelta(seconds=5),
            workspace_cwd="C:/nonexistent/path",
            set_slug="045-log-harvest-implementation",
            session_number=1,
            effort="high",
            target_backend="claude",
            launch_id="demo-negative-wrong-cwd",
        )
        add("negative-wrong-cwd", join(launch_d, natives, timedelta(seconds=30)))

    # Ambiguity probe: enlarge window to 1 hour and re-run claude — likely picks up
    # bracketed sessions in the same workspace.
    if claude_target:
        launch_e = LaunchRecord(
            launch_ts=claude_target.first_event_ts - timedelta(seconds=5),
            workspace_cwd=claude_target.cwd_canonical,
            set_slug="045-log-harvest-implementation",
            session_number=1,
            effort="high",
            target_backend="claude",
            launch_id="demo-ambiguity-1h",
        )
        add("ambiguity-claude-1h", join(launch_e, natives, timedelta(hours=1)))

    return {
        "scanned": {
            "claude_sessions": sum(1 for n in natives if n.engine == "claude"),
            "copilot_sessions": sum(1 for n in natives if n.engine == "copilot"),
        },
        "targets": {
            "claude": claude_target.conv_id if claude_target else None,
            "claude_first_event_ts": claude_target.first_event_ts.isoformat() if claude_target else None,
            "claude_cwd": claude_target.cwd_canonical if claude_target else None,
            "copilot": copilot_target.conv_id if copilot_target else None,
            "copilot_first_event_ts": copilot_target.first_event_ts.isoformat() if copilot_target else None,
            "copilot_cwd": copilot_target.cwd_canonical if copilot_target else None,
        },
        "results": results,
    }


if __name__ == "__main__":
    report = demo()
    out_path = Path(__file__).parent / "correlation_prototype_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {out_path}")
    print(f"Scanned: {report['scanned']}")
    print(f"Results: {len(report['results'])} join scenarios")
