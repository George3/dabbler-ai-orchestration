"""ai_router.joiner — multi-source log joiner + conflict detector.

Set 045 Session 2 skeleton. The joiner observes wrapper launch
logs, per-backend native logs, and session-state.json files;
it produces three views:

1. Harvest Records — normalized event stream (the positive view).
2. Conflict Reports — typed discrepancies between sources.
3. Coverage Summaries — per-session-set observability badges.

See ``docs/session-sets/045-log-harvest-implementation/joiner-spec.md``
for the full design contract.

Public API:

    from ai_router.joiner import scan_conflicts, harvest, coverage

The CLI wraps the same three entry points; see ``ai_router.joiner.cli``.
"""
from __future__ import annotations

from ai_router.joiner.conflicts import ConflictReport, scan_conflicts
from ai_router.joiner.coverage import CoverageSummary, coverage
from ai_router.joiner.schema import HarvestRecord, harvest

__all__ = [
    "ConflictReport",
    "CoverageSummary",
    "HarvestRecord",
    "coverage",
    "harvest",
    "scan_conflicts",
]
