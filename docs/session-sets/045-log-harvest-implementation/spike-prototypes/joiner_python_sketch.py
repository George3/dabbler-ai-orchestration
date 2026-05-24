"""Q4 spike — joiner sketch in Python (sibling to ai_router/).

Set 045 / Session 1 spike. Throwaway sketch — kept for reference.

Demonstrates the simplest meaningful conflict scenario:
**orchestrator-engine mismatch**.

Scenario: `session-state.json` says the active orchestrator is
Claude, but a Copilot native log shows tool_use of `Edit` against
the same state file. The two AIs are stepping on each other; the
Explorer should warn.

This sketch reuses ``correlation_prototype.scan_claude_logs`` and
``scan_copilot_logs`` to surface native-session records, then joins
them against the on-disk ``session-state.json`` for a chosen
session set.

Run:
    python joiner_python_sketch.py
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Reuse the correlation-prototype scrapers.
sys.path.insert(0, str(Path(__file__).parent))
from correlation_prototype import (  # noqa: E402
    NativeSession,
    scan_claude_logs,
    scan_copilot_logs,
    canonicalize_cwd,
    _parse_iso,
)


@dataclass
class ConflictReport:
    kind: str                     # 'engine-mismatch' | 'no-checkout-but-touch' | 'writer-bypass'
    set_slug: str
    state_file: str
    state_orchestrator_engine: str | None
    native_engine: str
    native_conv_id: str
    native_source: str
    notes: str


def load_state(state_path: Path) -> dict | None:
    if not state_path.exists():
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def detect_engine_mismatch(
    state_file: Path,
    natives: list[NativeSession],
    workspace_cwd_canonical: str,
    window: timedelta = timedelta(hours=1),
) -> list[ConflictReport]:
    """For one session set, surface conflict reports.

    Compares the checked-out orchestrator engine against any native
    session active in the same workspace within ``window`` of the
    state file's ``orchestrator.lastActivityAt``.
    """
    state = load_state(state_file)
    if state is None:
        return []
    orch = state.get("orchestrator") or {}
    state_engine = orch.get("engine")
    if not state_engine:
        return []  # no checkout — separate conflict mode not in this sketch
    last_activity_str = orch.get("lastActivityAt") or state.get("startedAt")
    if not last_activity_str:
        return []
    try:
        last_activity = _parse_iso(last_activity_str)
    except ValueError:
        return []
    set_slug = state.get("sessionSetName") or state_file.parent.name

    conflicts: list[ConflictReport] = []
    for ns in natives:
        if ns.cwd_canonical != workspace_cwd_canonical:
            continue
        delta = abs(ns.first_event_ts - last_activity)
        if delta > window:
            continue
        if ns.engine.lower() == state_engine.lower():
            continue  # same engine; no conflict
        # Strip "-code" / "-cli" suffixes if present for the compare.
        state_engine_norm = state_engine.lower().split("-")[0]
        if ns.engine.lower() == state_engine_norm:
            continue
        conflicts.append(
            ConflictReport(
                kind="engine-mismatch",
                set_slug=set_slug,
                state_file=str(state_file),
                state_orchestrator_engine=state_engine,
                native_engine=ns.engine,
                native_conv_id=ns.conv_id,
                native_source=ns.source_file,
                notes=f"native session within {delta.total_seconds():.0f}s of last checkout activity",
            )
        )
    return conflicts


def demo() -> dict:
    import os

    t0 = time.perf_counter()
    home = Path(os.path.expanduser("~"))
    natives = list(scan_claude_logs(home / ".claude" / "projects")) + list(
        scan_copilot_logs(home / ".copilot" / "session-state")
    )
    t_scan = time.perf_counter() - t0

    # Synthesize a deliberate conflict: pretend this very repo's
    # current state file (045) is checked out by Copilot, then look
    # for Claude sessions in the same workspace within the last hour.
    repo_root = Path(__file__).resolve().parents[4]
    state_file = repo_root / "docs" / "session-sets" / "045-log-harvest-implementation" / "session-state.json"
    workspace_cwd_canonical = canonicalize_cwd(str(repo_root))

    # Read the real state, patch it in memory, write to a temp file.
    real_state = load_state(state_file) or {}
    patched = dict(real_state)
    patched_orch = dict((real_state.get("orchestrator") or {}))
    patched_orch["engine"] = "copilot"  # the deliberate mismatch
    patched["orchestrator"] = patched_orch
    tmp_path = Path(__file__).parent / "synthetic_conflict_state.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(patched, f, indent=2)

    t1 = time.perf_counter()
    conflicts = detect_engine_mismatch(
        state_file=tmp_path,
        natives=natives,
        workspace_cwd_canonical=workspace_cwd_canonical,
    )
    t_detect = time.perf_counter() - t1

    # Control case: real state (claude-code) should produce 0 conflicts
    # for the same workspace.
    t2 = time.perf_counter()
    real_conflicts = detect_engine_mismatch(
        state_file=state_file,
        natives=natives,
        workspace_cwd_canonical=workspace_cwd_canonical,
    )
    t_control = time.perf_counter() - t2

    return {
        "language": "python",
        "n_native_sessions_scanned": len(natives),
        "scan_seconds": round(t_scan, 4),
        "detect_seconds_synthetic_conflict": round(t_detect, 4),
        "detect_seconds_control": round(t_control, 4),
        "synthetic_conflicts_found": [c.__dict__ for c in conflicts],
        "control_conflicts_found": [c.__dict__ for c in real_conflicts],
    }


if __name__ == "__main__":
    report = demo()
    out_path = Path(__file__).parent / "joiner_python_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {out_path}")
    print(f"Scanned: {report['n_native_sessions_scanned']} native sessions in {report['scan_seconds']}s")
    print(f"Synthetic conflicts: {len(report['synthetic_conflicts_found'])}")
    print(f"Control conflicts: {len(report['control_conflicts_found'])}")
