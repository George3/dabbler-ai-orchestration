"""CI guard: CURRENT_SCHEMA_VERSION in claude-session-start-invoker.js ==
SESSION_STATE_SCHEMA_VERSION in ai_router — Set 050 Session 3.

The pure-JS hot-path drift scan in the SessionStart hook reads a bundled
constant rather than importing ai_router (a Python router may be absent
in consumer repos with a stale pin). This test is the mechanical lock that
prevents the JS constant from drifting away from the Python canonical value.

Pinning rule: when SESSION_STATE_SCHEMA_VERSION is bumped, this test will
fail until CURRENT_SCHEMA_VERSION in the invoker is updated to match. That
failure is the intended signal — bump both together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    from ai_router.session_state import SCHEMA_VERSION as PY_SCHEMA_VERSION
except ImportError:
    from session_state import SCHEMA_VERSION as PY_SCHEMA_VERSION  # type: ignore[import-not-found]


# Path relative to this file: ../../tools/dabbler-ai-orchestration/scripts/
_INVOKER_PATH = (
    Path(__file__).parent.parent.parent
    / "tools"
    / "dabbler-ai-orchestration"
    / "scripts"
    / "claude-session-start-invoker.js"
)


def _read_invoker_constant() -> int:
    """Extract CURRENT_SCHEMA_VERSION = <int> from the invoker JS file."""
    if not _INVOKER_PATH.exists():
        pytest.skip(f"Invoker not found at {_INVOKER_PATH} — skipping constant guard")
    text = _INVOKER_PATH.read_text(encoding="utf-8")
    match = re.search(r"^\s*const\s+CURRENT_SCHEMA_VERSION\s*=\s*(\d+)\s*;", text, re.MULTILINE)
    if not match:
        raise AssertionError(
            f"Could not find 'const CURRENT_SCHEMA_VERSION = <int>;' in {_INVOKER_PATH}. "
            "The constant may have been renamed or removed."
        )
    return int(match.group(1))


def test_invoker_constant_matches_python_schema_version() -> None:
    """CURRENT_SCHEMA_VERSION in claude-session-start-invoker.js must equal
    ai_router's SESSION_STATE_SCHEMA_VERSION. Bump both together when the
    schema is bumped."""
    js_version = _read_invoker_constant()
    assert js_version == PY_SCHEMA_VERSION, (
        f"CURRENT_SCHEMA_VERSION in claude-session-start-invoker.js ({js_version}) "
        f"!= ai_router SESSION_STATE_SCHEMA_VERSION ({PY_SCHEMA_VERSION}). "
        "Bump the JS constant to match the Python value, or vice versa."
    )
