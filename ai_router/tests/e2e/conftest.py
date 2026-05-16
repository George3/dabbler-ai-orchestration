"""Pytest config for the e2e harness.

The e2e harness drives the real ``start_session`` / ``close_session``
CLIs against tmpdir-scoped fixture session sets and asserts on the
resulting on-disk state. Tests under this directory carry the ``e2e``
marker so they can be filtered on/off independently of the unit
suite (``pytest -m "not e2e"`` for fast pre-commit; ``pytest -m e2e``
for the full harness pass).

The parent ``ai_router/tests/conftest.py`` already adds ``ai_router/``
to ``sys.path`` so submodules import by bare filename. This file
extends that to put the e2e directory itself on the path too, so
tests can ``from fixtures import ...`` the same way unit tests do
``from disposition import ...``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pytest

E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))


@pytest.fixture(autouse=True)
def _scrub_force_close_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure ``AI_ROUTER_ALLOW_FORCE_CLOSE_OUT`` is unset in every test.

    The harness sets the variable explicitly only for tests that
    exercise the ``--force`` path; otherwise an operator-level value
    in the dev shell could leak in and mask a real gate failure.
    """
    monkeypatch.delenv("AI_ROUTER_ALLOW_FORCE_CLOSE_OUT", raising=False)
    yield
