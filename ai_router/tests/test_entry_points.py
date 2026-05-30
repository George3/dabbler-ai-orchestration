"""Guard every declared console-script entry point against breakage.

Set 051 retired the ``backfill_session_state`` entry point, which had
pointed at ``ai_router.backfill_session_state:main`` — a module that has
lived under the unpackaged ``ai_router/scripts/`` dir since Set 021, so
the installed console script never resolved and nobody noticed for ~30
session sets.

This test parses ``[project.scripts]`` straight from ``pyproject.toml``
and imports each target, asserting the named callable exists. A future
entry point that points at a missing module / attribute fails here rather
than silently shipping a dead console script.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - project requires 3.10+, CI runs 3.11
    tomllib = None


def _repo_root() -> Path:
    # ai_router/tests/test_entry_points.py -> repo root is two parents up.
    return Path(__file__).resolve().parents[2]


def _load_entry_points() -> dict:
    pyproject = _repo_root() / "pyproject.toml"
    if tomllib is None:
        pytest.skip("tomllib unavailable (Python < 3.11)")
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("scripts", {})


def test_pyproject_declares_console_scripts():
    eps = _load_entry_points()
    assert eps, "no [project.scripts] declared in pyproject.toml"
    assert "start_session" in eps
    assert "close_session" in eps


def test_retired_backfill_entry_point_absent():
    """The long-broken backfill entry point must stay retired (Set 051)."""
    eps = _load_entry_points()
    assert "backfill_session_state" not in eps


def test_every_entry_point_target_imports():
    """Each ``module:attr`` target imports and the attribute is callable."""
    eps = _load_entry_points()
    failures = []
    for name, target in eps.items():
        module_path, _, attr = target.partition(":")
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:  # noqa: BLE001 - report which target broke
            failures.append(f"{name}={target!r}: import failed: {exc!r}")
            continue
        if not attr:
            failures.append(f"{name}={target!r}: missing ':attr' suffix")
            continue
        fn = getattr(module, attr, None)
        if fn is None:
            failures.append(f"{name}={target!r}: module has no attribute {attr!r}")
        elif not callable(fn):
            failures.append(f"{name}={target!r}: {attr!r} is not callable")
    assert not failures, "broken console-script entry points:\n" + "\n".join(failures)
