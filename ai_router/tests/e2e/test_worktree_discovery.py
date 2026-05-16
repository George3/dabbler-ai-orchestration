"""Python-side worktree listing picks up both primary and sibling worktrees.

Creates a fixture that mirrors the canonical "sibling-worktrees-folder"
layout (Set 016):

    <tmp>/repo/                     ← primary working tree
    <tmp>/repo-worktrees/
        feature-x/                  ← canonical linked worktree

Then calls ``worktree.enumerate_worktrees(primary_root)`` — the
production helper used by the extension's tree provider and the
``python -m ai_router.worktree list`` command — and asserts that:

* Both worktrees are returned.
* The primary is classified ``"main"`` and its path matches.
* The sibling is classified ``"canonical"``, has slug ``"feature-x"``,
  and has ``branch_matches_convention == True`` (branch
  ``session-set/feature-x`` matches the expected naming convention).

A second test verifies that session-set directories planted in the
sibling worktree are discoverable by walking the ``enumerate_worktrees``
output — the pattern the Session Set Explorer uses to collect sets
across all worktrees.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import (  # type: ignore[import-not-found]
    make_session_set,
    make_sibling_worktree,
)


pytestmark = pytest.mark.e2e


def test_sibling_worktree_classified_as_canonical(tmp_path: Path) -> None:
    """enumerate_worktrees returns and correctly classifies a sibling worktree."""
    from worktree import enumerate_worktrees  # type: ignore[import-not-found]

    handle = make_session_set(tmp_path, slug="harness-wt-main", total_sessions=2)
    wt_path = make_sibling_worktree(handle, "feature-x")

    all_wt = enumerate_worktrees(handle.repo_root)

    assert len(all_wt) == 2, (
        f"expected 2 worktrees (main + sibling); "
        f"got {[(str(w.path), w.classification) for w in all_wt]!r}"
    )

    # Primary worktree assertions.
    main_wts = [w for w in all_wt if w.is_main]
    assert len(main_wts) == 1
    assert main_wts[0].path.resolve() == handle.repo_root.resolve()
    assert main_wts[0].classification == "main"

    # Sibling worktree assertions.
    sibling_wts = [w for w in all_wt if not w.is_main]
    assert len(sibling_wts) == 1
    sibling = sibling_wts[0]
    assert sibling.path.resolve() == wt_path.resolve(), (
        f"sibling path mismatch: expected {wt_path!r}, got {sibling.path!r}"
    )
    assert sibling.classification == "canonical", (
        f"expected classification='canonical'; got {sibling.classification!r} "
        f"(issues: {sibling.issues!r})"
    )
    assert sibling.slug == "feature-x", (
        f"expected slug='feature-x'; got {sibling.slug!r}"
    )
    assert sibling.branch_matches_convention, (
        f"branch should match 'session-set/feature-x'; "
        f"got branch={sibling.branch!r}"
    )


def test_session_sets_in_sibling_worktree_discoverable(tmp_path: Path) -> None:
    """Session sets planted in a sibling worktree are found by walking enumerate_worktrees."""
    from worktree import enumerate_worktrees  # type: ignore[import-not-found]

    handle = make_session_set(tmp_path, slug="harness-wt-a", total_sessions=2)
    wt_path = make_sibling_worktree(handle, "feature-y")

    # Plant a session-set directory in the sibling worktree (simulates an
    # orchestrator having called ``start_session`` in a linked worktree).
    sibling_set_dir = wt_path / "docs" / "session-sets" / "harness-wt-b"
    sibling_set_dir.mkdir(parents=True, exist_ok=True)

    all_wt = enumerate_worktrees(handle.repo_root)

    # Walk all worktrees and collect every docs/session-sets/<slug> directory.
    discovered_slugs: set[str] = set()
    for wt in all_wt:
        ss_root = wt.path / "docs" / "session-sets"
        if ss_root.is_dir():
            for entry in ss_root.iterdir():
                if entry.is_dir():
                    discovered_slugs.add(entry.name)

    assert "harness-wt-a" in discovered_slugs, (
        f"primary repo's session set not found; discovered={discovered_slugs!r}"
    )
    assert "harness-wt-b" in discovered_slugs, (
        f"sibling worktree's session set not found; discovered={discovered_slugs!r}"
    )
