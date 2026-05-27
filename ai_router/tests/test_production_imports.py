"""Code-review-time invariant: production code must not bare-import Set 048 modules.

Set 048 S5 UAT discovered that ``ai_router/__init__.py``,
``ai_router/start_session.py``, ``ai_router/close_session.py``, and
``ai_router/runtime_mode.py`` used bare imports of the new Set 048
modules (``from runtime_mode import …``, ``from spec_config import …``).
Those bare forms only resolve under the test ``conftest.py`` ``sys.path``
shim — pip-installed package consumers (the Lightweight target audience)
have no such shim, so the imports raised ``ModuleNotFoundError``. The
``route()`` / ``verify()`` call sites blew up outright; the
``start_session.main()`` / ``close_session.run()`` sites silently
swallowed the error in ``try/except``, so ``--no-router`` was a no-op
across the entire production CLI surface.

The original S2 Round-A verifier flagged this as Major #2 and the
finding was dismissed as a false positive on conftest grounds; that
dismissal was wrong. This test exists so the dismissal cannot recur.

The fix: production code uses relative imports (``from .runtime_mode
import …``). Tests retain the bare form for convention; conftest
remains responsible for the test-only ``sys.path`` shim.
"""

import re
from pathlib import Path

AI_ROUTER_DIR = Path(__file__).resolve().parent.parent
SET_048_MODULES = (
    "runtime_mode",
    "spec_config",
    "suggestion_disposition",
    "migrate_lightweight_to_canonical_v4",
)


def test_no_bare_imports_of_set048_modules_in_production_code():
    bad: list[tuple[str, int, str]] = []
    for py_file in AI_ROUTER_DIR.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for mod in SET_048_MODULES:
                # Match `from <mod> import` at start of line (with optional
                # leading whitespace for inside-function imports). Reject
                # the bare form; allow `from .<mod>` and `from ai_router.<mod>`.
                if re.match(rf"^[ \t]*from {re.escape(mod)} import\b", line):
                    bad.append((py_file.name, lineno, line.strip()))

    assert not bad, (
        "Production code in ai_router/ has bare imports of Set 048 modules. "
        "These work under the test conftest's sys.path shim but raise "
        "ModuleNotFoundError under pip-install (the Lightweight consumer "
        "target). Use `from .<module> import …` (relative) or "
        "`from ai_router.<module> import …` (absolute) instead.\n"
        f"Offenders:\n  " + "\n  ".join(f"{fn}:{ln}  {src}" for fn, ln, src in bad)
    )
