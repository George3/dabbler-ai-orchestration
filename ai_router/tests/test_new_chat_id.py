"""Set 036 Session 2 — ``ai_router.new_chat_id`` CLI tests.

Covers the four behavior groups enumerated in
``docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/spec.md``
Session 2 Step 1:

(a) plain mode prints a fresh UUID v4 (one line, no shell syntax)
(b) ``--export`` emits a shell-eval-able line; ``--shell`` selects
    the syntax explicitly (bash, powershell, fish); auto-detect
    picks PowerShell on Windows and parses ``$SHELL`` on Unix
(c) idempotency — a pre-existing non-empty ``$CHAT_SESSION_ID``
    short-circuits the UUID mint so plain and export modes both
    re-emit the existing value
(d) failure mode — ``--export`` with no ``--shell`` and an
    undetectable shell environment exits ``EXIT_SHELL_DETECT_FAILED``
    with a stderr hint pointing at ``--shell`` and the env-var
    fallback

Tests drive the public ``main(argv)`` entrypoint and capture stdout /
stderr via ``capsys`` so coverage matches what an operator's shell
sees. A small handful of cases exercise the helper functions directly
where the public surface would have to mock the environment too
heavily to be readable.
"""

from __future__ import annotations

import os
import re
import uuid

import pytest

import new_chat_id
from new_chat_id import (
    CHAT_SESSION_ID_ENV_VAR,
    EXIT_OK,
    EXIT_SHELL_DETECT_FAILED,
    SHELL_BASH,
    SHELL_FISH,
    SHELL_POWERSHELL,
    SUPPORTED_SHELLS,
    main,
)


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Clear CHAT_SESSION_ID + $SHELL before every test.

    Each test opts in to whatever env shape it needs by re-setting
    these values. The autouse fixture prevents leakage from the
    invoking developer's shell into the test process.
    """
    monkeypatch.delenv(CHAT_SESSION_ID_ENV_VAR, raising=False)
    monkeypatch.delenv("SHELL", raising=False)


# ---------------------------------------------------------------------------
# (a) plain mode prints a fresh UUID v4
# ---------------------------------------------------------------------------


def test_plain_mode_prints_uuid_v4(capsys):
    rc = main([])
    out, err = capsys.readouterr()
    assert rc == EXIT_OK
    assert err == ""
    # One line, no shell syntax.
    lines = out.splitlines()
    assert len(lines) == 1
    assert UUID_RE.match(lines[0])
    # Round-trip through uuid.UUID to confirm version-4 framing
    # (the regex enforces the framing already; the constructor
    # catches any future regex-loosening regression).
    parsed = uuid.UUID(lines[0])
    assert parsed.version == 4


def test_plain_mode_emits_different_uuids_across_calls(capsys):
    rc1 = main([])
    out1, _ = capsys.readouterr()
    rc2 = main([])
    out2, _ = capsys.readouterr()
    assert rc1 == EXIT_OK and rc2 == EXIT_OK
    assert out1.strip() != out2.strip()


# ---------------------------------------------------------------------------
# (b) --export emits shell-eval-able lines; --shell selects flavor
# ---------------------------------------------------------------------------


def test_export_bash_prints_export_line(capsys):
    rc = main(["--export", "--shell", SHELL_BASH])
    out, err = capsys.readouterr()
    assert rc == EXIT_OK
    assert err == ""
    line = out.strip()
    # `export NAME='<uuid>'` with single quotes per the bash
    # formatter contract.
    match = re.match(
        rf"^export {CHAT_SESSION_ID_ENV_VAR}='([0-9a-f-]{{36}})'$",
        line,
    )
    assert match, f"unexpected bash export shape: {line!r}"
    assert UUID_RE.match(match.group(1))


def test_export_powershell_prints_env_assignment(capsys):
    rc = main(["--export", "--shell", SHELL_POWERSHELL])
    out, err = capsys.readouterr()
    assert rc == EXIT_OK
    assert err == ""
    line = out.strip()
    # `$env:NAME = '<uuid>'` with single quotes (no interpolation).
    match = re.match(
        rf"^\$env:{CHAT_SESSION_ID_ENV_VAR} = '([0-9a-f-]{{36}})'$",
        line,
    )
    assert match, f"unexpected PowerShell export shape: {line!r}"
    assert UUID_RE.match(match.group(1))


def test_export_fish_prints_set_gx(capsys):
    rc = main(["--export", "--shell", SHELL_FISH])
    out, err = capsys.readouterr()
    assert rc == EXIT_OK
    assert err == ""
    line = out.strip()
    match = re.match(
        rf"^set -gx {CHAT_SESSION_ID_ENV_VAR} '([0-9a-f-]{{36}})'$",
        line,
    )
    assert match, f"unexpected fish export shape: {line!r}"
    assert UUID_RE.match(match.group(1))


def test_export_auto_detect_picks_powershell_on_windows(
    capsys, monkeypatch,
):
    monkeypatch.setattr(new_chat_id.os, "name", "nt")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"$env:{CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_honors_shell_env_on_windows(
    capsys, monkeypatch,
):
    # Round A Major fix: a Git-Bash / MSYS / WSL operator on Windows
    # with $SHELL set to a bash path expects bash export syntax, not
    # PowerShell. The detector now consults $SHELL before falling
    # back to the Windows default.
    monkeypatch.setattr(new_chat_id.os, "name", "nt")
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"export {CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_honors_fish_shell_env_on_windows(
    capsys, monkeypatch,
):
    monkeypatch.setattr(new_chat_id.os, "name", "nt")
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"set -gx {CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_falls_back_to_powershell_on_windows_when_shell_unrecognized(
    capsys, monkeypatch,
):
    # Unrecognized $SHELL (e.g., nu) on Windows still gets the
    # PowerShell fallback — the platform default takes over only
    # when $SHELL gives no usable signal.
    monkeypatch.setattr(new_chat_id.os, "name", "nt")
    monkeypatch.setenv("SHELL", "/usr/bin/nu")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"$env:{CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_parses_shell_env_bash(capsys, monkeypatch):
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/bin/bash")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"export {CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_parses_shell_env_zsh_as_bash(
    capsys, monkeypatch,
):
    # zsh accepts the bash `export NAME='value'` syntax, so the
    # detector collapses it to bash. The contract is documented in
    # _detect_shell's docstring.
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"export {CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_parses_shell_env_fish(capsys, monkeypatch):
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/usr/local/bin/fish")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"set -gx {CHAT_SESSION_ID_ENV_VAR}")


def test_export_auto_detect_parses_shell_env_pwsh_as_powershell(
    capsys, monkeypatch,
):
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/usr/bin/pwsh")
    rc = main(["--export"])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.startswith(f"$env:{CHAT_SESSION_ID_ENV_VAR}")


# ---------------------------------------------------------------------------
# (c) idempotency: existing $CHAT_SESSION_ID short-circuits the mint
# ---------------------------------------------------------------------------


def test_plain_mode_echoes_existing_chat_session_id(capsys, monkeypatch):
    existing = "11111111-2222-4333-8444-555555555555"
    monkeypatch.setenv(CHAT_SESSION_ID_ENV_VAR, existing)
    rc = main([])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.strip() == existing


def test_export_mode_echoes_existing_chat_session_id(capsys, monkeypatch):
    existing = "11111111-2222-4333-8444-555555555555"
    monkeypatch.setenv(CHAT_SESSION_ID_ENV_VAR, existing)
    rc = main(["--export", "--shell", SHELL_BASH])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    assert out.strip() == f"export {CHAT_SESSION_ID_ENV_VAR}='{existing}'"


def test_empty_env_value_does_not_short_circuit(capsys, monkeypatch):
    # An empty string env value is "not really set" — the writer-side
    # contract in start_session._resolve_chat_session_id collapses
    # empty strings to None, and this helper mirrors that so the
    # on-disk identity never carries an empty-string marker.
    monkeypatch.setenv(CHAT_SESSION_ID_ENV_VAR, "")
    rc = main([])
    out, _ = capsys.readouterr()
    assert rc == EXIT_OK
    line = out.strip()
    # A fresh UUID was minted because the empty env value was
    # treated as unset.
    assert UUID_RE.match(line)


# ---------------------------------------------------------------------------
# (d) failure mode: --export with no --shell and undetectable shell
# ---------------------------------------------------------------------------


def test_export_fails_when_shell_unknown(capsys, monkeypatch):
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    # SHELL is cleared by the autouse fixture; no --shell supplied;
    # os.name is posix so the Windows short-circuit doesn't fire.
    rc = main(["--export"])
    out, err = capsys.readouterr()
    assert rc == EXIT_SHELL_DETECT_FAILED
    assert out == ""
    assert "--shell" in err
    assert CHAT_SESSION_ID_ENV_VAR in err
    # The error names every supported shell so the operator knows
    # what to pass — protects against drift if SUPPORTED_SHELLS
    # expands later.
    for shell in SUPPORTED_SHELLS:
        assert shell in err


def test_export_fails_when_shell_basename_unrecognized(capsys, monkeypatch):
    monkeypatch.setattr(new_chat_id.os, "name", "posix")
    monkeypatch.setenv("SHELL", "/usr/bin/nu")  # nushell, not in scope per R3
    rc = main(["--export"])
    out, err = capsys.readouterr()
    assert rc == EXIT_SHELL_DETECT_FAILED
    assert out == ""
    assert "--shell" in err


# ---------------------------------------------------------------------------
# Helper-level coverage (regression seams)
# ---------------------------------------------------------------------------


def test_format_bash_single_quotes_uuid_safely():
    line = new_chat_id._format_bash("abc-123")
    assert line == f"export {CHAT_SESSION_ID_ENV_VAR}='abc-123'"


def test_format_powershell_single_quotes_uuid_safely():
    line = new_chat_id._format_powershell("abc-123")
    assert line == f"$env:{CHAT_SESSION_ID_ENV_VAR} = 'abc-123'"


def test_format_fish_single_quotes_uuid_safely():
    line = new_chat_id._format_fish("abc-123")
    assert line == f"set -gx {CHAT_SESSION_ID_ENV_VAR} 'abc-123'"


def test_format_bash_escapes_embedded_single_quote():
    # UUID v4 output never contains a single quote, but the
    # formatter is defensive — exercise the escape path so a future
    # caller passing arbitrary values doesn't open an injection
    # window.
    line = new_chat_id._format_bash("ab'cd")
    assert line == f"export {CHAT_SESSION_ID_ENV_VAR}='ab'\\''cd'"


def test_format_powershell_escapes_embedded_single_quote():
    line = new_chat_id._format_powershell("ab'cd")
    assert line == f"$env:{CHAT_SESSION_ID_ENV_VAR} = 'ab''cd'"


def test_format_fish_escapes_embedded_single_quote():
    # Round A Minor fix: bash and PowerShell escape branches were
    # exercised; the fish branch was not. Lock the contract so a
    # future refactor of _format_fish can't silently change the
    # escape rule.
    line = new_chat_id._format_fish("ab'cd")
    assert line == f"set -gx {CHAT_SESSION_ID_ENV_VAR} 'ab\\'cd'"


def test_resolve_chat_session_id_returns_existing(monkeypatch):
    monkeypatch.setenv(CHAT_SESSION_ID_ENV_VAR, "preset-value")
    assert new_chat_id._resolve_chat_session_id() == "preset-value"


def test_resolve_chat_session_id_mints_fresh_when_unset():
    value = new_chat_id._resolve_chat_session_id()
    assert UUID_RE.match(value)
