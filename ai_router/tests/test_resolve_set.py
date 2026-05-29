"""Tests for the number->slug resolver (Set 050 Session 4, Feature 2).

Covers verdict Q8 (match / collision / no-match), Q11 (next number +
zero-pad width rule), the bare-number detection used by start_session's
``--session-set-dir`` integration, and the standalone CLI.
"""

from __future__ import annotations

import json
import os

import pytest

try:  # test convention: bare import; production: relative fallback
    import resolve_set as rs  # type: ignore[import-not-found]
except ImportError:
    from ai_router import resolve_set as rs  # type: ignore[no-redef]


def _mkset(root, name):
    os.makedirs(os.path.join(root, name), exist_ok=True)


# --- numeric_prefix ----------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("050-schema-drift", 50),
        ("047-state-file-v4", 47),
        ("7-bar", 7),
        ("001-first", 1),
        ("harvester-cli-distribution", None),
        ("050", None),  # no trailing hyphen -> not a slug prefix
        ("_archived", None),
        ("v4-something", None),
    ],
)
def test_numeric_prefix(name, expected):
    assert rs.numeric_prefix(name) == expected


# --- resolve_slug: match -----------------------------------------------------


def test_resolve_exact_match(tmp_path):
    root = str(tmp_path)
    _mkset(root, "047-foo")
    _mkset(root, "050-schema-drift")
    _mkset(root, "harvester-cli")  # unnumbered, ignored
    assert rs.resolve_slug(root, 50) == "050-schema-drift"
    assert rs.resolve_slug(root, 47) == "047-foo"


def test_resolve_leading_zeros_normalized(tmp_path):
    root = str(tmp_path)
    _mkset(root, "050-schema-drift")
    # 50, 050, 0050 all resolve to the same set
    assert rs.resolve_slug(root, 50) == "050-schema-drift"
    assert rs.resolve_set(root, 50) == os.path.join(root, "050-schema-drift")


# --- resolve_slug: no-match --------------------------------------------------


def test_resolve_no_match_lists_available(tmp_path):
    root = str(tmp_path)
    _mkset(root, "047-foo")
    _mkset(root, "050-bar")
    with pytest.raises(rs.SetNotFoundError) as exc:
        rs.resolve_slug(root, 99)
    msg = str(exc.value)
    assert "99" in msg
    assert "47" in msg and "50" in msg  # available numbers listed
    assert "--next" in msg
    # No fuzzy "nearest" suggestion.
    assert "nearest" not in msg.lower()


def test_resolve_no_match_empty_repo(tmp_path):
    root = str(tmp_path)
    _mkset(root, "harvester-cli")  # only unnumbered dirs
    with pytest.raises(rs.SetNotFoundError) as exc:
        rs.resolve_slug(root, 1)
    assert "(none)" in str(exc.value)


# --- resolve_slug: collision -------------------------------------------------


def test_resolve_collision_names_both(tmp_path):
    root = str(tmp_path)
    _mkset(root, "050-schema-drift")
    _mkset(root, "050-other-thing")
    with pytest.raises(rs.SetCollisionError) as exc:
        rs.resolve_slug(root, 50)
    msg = str(exc.value)
    assert "050-schema-drift" in msg
    assert "050-other-thing" in msg


# --- index / available -------------------------------------------------------


def test_index_and_available(tmp_path):
    root = str(tmp_path)
    _mkset(root, "001-a")
    _mkset(root, "047-b")
    _mkset(root, "050-c")
    _mkset(root, "_archived")  # skipped
    _mkset(root, "bare-name")  # skipped (no prefix)
    assert rs.available_prefixes(root) == [1, 47, 50]
    idx = rs.index_by_prefix(root)
    assert idx[47] == ["047-b"]


# --- next_session_set_number (Q11) -------------------------------------------


def test_next_number_empty_repo(tmp_path):
    root = str(tmp_path)
    nxt, padded = rs.next_session_set_number(root)
    assert nxt == 1
    assert padded == "001"  # width floor of 3


def test_next_number_three_digit_repo(tmp_path):
    root = str(tmp_path)
    _mkset(root, "047-a")
    _mkset(root, "050-b")
    nxt, padded = rs.next_session_set_number(root)
    assert nxt == 51
    assert padded == "051"


def test_next_number_width_grows_with_widest(tmp_path):
    root = str(tmp_path)
    _mkset(root, "050-b")
    _mkset(root, "1000-big")  # 4-digit prefix widens the field
    nxt, padded = rs.next_session_set_number(root)
    assert nxt == 1001
    assert padded == "1001"


def test_next_number_pads_to_widest_even_when_next_is_short(tmp_path):
    root = str(tmp_path)
    # widest existing is 4 digits, but the gap-free max is 0123 -> next 124
    _mkset(root, "0123-x")
    _mkset(root, "0099-y")
    nxt, padded = rs.next_session_set_number(root)
    assert nxt == 124
    assert padded == "0124"  # zero-padded to width 4


def test_next_number_ignores_unnumbered(tmp_path):
    root = str(tmp_path)
    _mkset(root, "harvester-cli")
    _mkset(root, "vba-symbol-db")
    nxt, padded = rs.next_session_set_number(root)
    assert nxt == 1
    assert padded == "001"


# --- bare-number detection (start_session integration) -----------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("50", True),
        ("050", True),
        ("0", True),
        ("050-schema-drift", False),
        ("docs/session-sets/050-x", False),
        ("", False),
        ("abc", False),
    ],
)
def test_looks_like_bare_number(value, expected):
    assert rs.looks_like_bare_number(value) is expected


def test_resolve_session_set_dir_passes_path_through(tmp_path):
    # A path value is returned verbatim (pre-Set-050 contract preserved).
    p = "docs/session-sets/050-x"
    assert rs.resolve_session_set_dir(p, scan_root=str(tmp_path)) == p


def test_resolve_session_set_dir_resolves_number(tmp_path):
    root = str(tmp_path)
    _mkset(root, "050-schema-drift")
    out = rs.resolve_session_set_dir("50", scan_root=root)
    assert out == os.path.join(root, "050-schema-drift")


# --- CLI ---------------------------------------------------------------------


def test_cli_resolve_prints_slug(tmp_path, capsys):
    root = str(tmp_path)
    _mkset(root, "050-schema-drift")
    rc = rs.main(["50", "--scan", root])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "050-schema-drift"


def test_cli_resolve_json(tmp_path, capsys):
    root = str(tmp_path)
    _mkset(root, "050-schema-drift")
    rc = rs.main(["50", "--scan", root, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == "050-schema-drift"
    assert payload["number"] == 50


def test_cli_next(tmp_path, capsys):
    root = str(tmp_path)
    _mkset(root, "050-b")
    rc = rs.main(["--next", "--scan", root])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "051"


def test_cli_collision_exit_code(tmp_path, capsys):
    root = str(tmp_path)
    _mkset(root, "050-a")
    _mkset(root, "050-b")
    rc = rs.main(["50", "--scan", root])
    assert rc == 3
    assert "ambiguous" in capsys.readouterr().err


def test_cli_no_match_exit_code(tmp_path, capsys):
    root = str(tmp_path)
    _mkset(root, "050-a")
    rc = rs.main(["99", "--scan", root])
    assert rc == 4
    assert "Available numbers" in capsys.readouterr().err


def test_cli_missing_scan_root(tmp_path, capsys):
    missing = os.path.join(str(tmp_path), "nope")
    rc = rs.main(["50", "--scan", missing])
    assert rc == 2
