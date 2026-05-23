"""Per-chat session identifier helper — Set 036 Session 2.

Companion to :mod:`ai_router.start_session`. The Set 036 audit
(`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`) locked
Q1's verdict that there is **no env var** that any of the four
first-class orchestrators (Claude Code, Codex CLI, Gemini Code Assist,
GitHub Copilot) populates with a stable per-chat identifier. Claude
Code carries the identity in its ``SessionStart`` hook payload's
``session_id`` field, which the
``tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js``
hook shim forwards to ``start_session --chat-session-id <value>``.

For every other orchestrator the operator runs this CLI once per chat
session, captures the printed UUID v4, and either:

  - exports it as ``CHAT_SESSION_ID`` in the shell that the
    orchestrator inherits (the ``--export`` flow does this in one
    eval-able line), or
  - pastes it explicitly into a ``start_session --chat-session-id
    <value>`` command (for ad-hoc / Lightweight-tier flows).

CLI shape::

    python -m ai_router.new_chat_id [--export] [--shell SHELL]

Behavior:

  - **Plain mode** (no ``--export``): print the UUID on stdout. One
    line, no trailing prose, no eval syntax. Stdout is the contract;
    stderr is reserved for warnings/diagnostics.
  - **Export mode** (``--export``): print a shell-eval-able line that
    exports ``CHAT_SESSION_ID`` for the detected (or specified) shell.
    Operator pipes the output through their shell's eval primitive
    (``eval "$(...)"`` on bash, ``Invoke-Expression`` on PowerShell,
    ``... | source`` on fish).
  - **Idempotent within a shell session.** If ``$CHAT_SESSION_ID``
    is already set to a non-empty value, the CLI emits that value
    rather than minting a fresh one. The Set 036 H4 composite
    identity then keeps the orchestrator block stable across
    re-runs of ``start_session`` from the same chat.
  - **Shell selection.** ``--shell {bash,powershell,fish}`` is
    explicit. When omitted, the CLI auto-detects:

      - Windows (``os.name == "nt"``) → ``powershell``.
      - Unix-like with ``$SHELL`` ending in ``bash`` / ``zsh`` →
        ``bash`` (zsh accepts the bash ``export`` syntax).
      - Unix-like with ``$SHELL`` ending in ``fish`` → ``fish``.
      - Unix-like with ``$SHELL`` ending in ``pwsh`` →
        ``powershell``.
      - Unix-like with ``$SHELL`` unset / unrecognized →
        ``EXIT_SHELL_DETECT_FAILED`` (1) with a stderr hint.

    Detection is consulted only in export mode; plain mode prints
    the UUID with no shell context.

Exit codes:

  - ``0`` — success (UUID printed, or eval-line printed).
  - ``1`` — ``--export`` was supplied without ``--shell`` and
    detection failed (R3: bash / PowerShell / fish are the initial
    supported set; operators on other shells either pass
    ``--shell`` or fall back to ``export CHAT_SESSION_ID=...``
    manually).
  - ``2`` — usage error (argparse).

Future shells (nu, tcsh, etc.) plug in via the
``_EXPORT_FORMATTERS`` registry without touching the rest of the
module.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Callable, Optional

CHAT_SESSION_ID_ENV_VAR = "CHAT_SESSION_ID"

EXIT_OK = 0
EXIT_SHELL_DETECT_FAILED = 1
EXIT_USAGE = 2

# Shell-flavor canonical names. Aliases collapse to these tokens in
# :func:`_detect_shell` so the formatter registry stays small.
SHELL_BASH = "bash"
SHELL_POWERSHELL = "powershell"
SHELL_FISH = "fish"

SUPPORTED_SHELLS = (SHELL_BASH, SHELL_POWERSHELL, SHELL_FISH)


def _format_bash(value: str) -> str:
    # Single-quote the value to suppress any shell expansion. UUID v4
    # output never contains a single quote, but the formatter is
    # written defensively so future shell-supplied values stay safe.
    safe = value.replace("'", "'\\''")
    return f"export {CHAT_SESSION_ID_ENV_VAR}='{safe}'"


def _format_powershell(value: str) -> str:
    # Single-quoted PowerShell literal — no expansion, no
    # interpolation. Embedded single quotes double up per
    # PowerShell quoting rules.
    safe = value.replace("'", "''")
    return f"$env:{CHAT_SESSION_ID_ENV_VAR} = '{safe}'"


def _format_fish(value: str) -> str:
    # `set -gx` exports for child processes and persists across the
    # fish session. UUID has no fish metacharacters, but we
    # backslash-escape single quotes for the same defensive reason
    # as the bash formatter.
    safe = value.replace("'", "\\'")
    return f"set -gx {CHAT_SESSION_ID_ENV_VAR} '{safe}'"


_EXPORT_FORMATTERS: dict[str, Callable[[str], str]] = {
    SHELL_BASH: _format_bash,
    SHELL_POWERSHELL: _format_powershell,
    SHELL_FISH: _format_fish,
}


def _detect_shell() -> Optional[str]:
    """Best-effort shell detection. Returns canonical name or None.

    ``$SHELL`` is consulted first on every platform — a Git-Bash /
    MSYS / WSL operator on Windows who sets ``SHELL=/usr/bin/bash``
    deliberately wants bash routing, not PowerShell. Only when
    ``$SHELL`` is unset or carries an unrecognized basename does the
    Windows branch fall back to ``powershell`` (the platform default
    that the wizard / Marketplace materials presume). Unix-like
    platforms with the same unset-or-unrecognized state return
    None so the caller can prompt the operator for an explicit
    ``--shell``.

    Basename mapping: bash / sh / zsh → bash (zsh and most modern sh
    accept the ``export NAME='value'`` syntax bash emits); fish →
    fish; pwsh / powershell → powershell. Aliases collapse to the
    canonical name in the :data:`_EXPORT_FORMATTERS` registry.
    """
    raw = os.environ.get("SHELL")
    if raw:
        base = os.path.basename(raw).lower()
        if base in {"bash", "sh", "zsh"}:
            return SHELL_BASH
        if base == "fish":
            return SHELL_FISH
        if base in {"pwsh", "powershell"}:
            return SHELL_POWERSHELL
        # Unrecognized basename — fall through to the platform-
        # default branch rather than returning None outright, so a
        # Windows operator with $SHELL=/usr/bin/nu still gets
        # PowerShell as the documented default.
    if os.name == "nt":
        return SHELL_POWERSHELL
    return None


def _resolve_chat_session_id() -> str:
    """Return the existing CHAT_SESSION_ID value, or mint a fresh UUID v4.

    Idempotency contract: a non-empty ``$CHAT_SESSION_ID`` always
    wins so repeated invocations of ``new_chat_id`` from the same
    shell session re-emit the same identifier. The H4 composite
    identity check in ``start_session`` then treats the second and
    Nth invocations as same-holder re-attaches rather than refusing
    them as conflicting check-outs.

    An empty-string env value is treated as "not set" — the writer
    contract in :func:`ai_router.start_session._resolve_chat_session_id`
    collapses empty strings to None so the on-disk identity never
    carries an empty marker. The minting branch here mirrors that.
    """
    existing = os.environ.get(CHAT_SESSION_ID_ENV_VAR)
    if isinstance(existing, str) and existing:
        return existing
    return str(uuid.uuid4())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="new_chat_id",
        description=(
            "Mint or echo a per-chat session identifier for Set 036's "
            "chatSessionId-refined check-out identity. Prints the UUID "
            "directly by default, or a shell-eval-able export line with "
            "--export. Idempotent: if $CHAT_SESSION_ID is already set "
            "in the calling environment, that value is emitted instead "
            "of a fresh UUID. Supported shells (auto-detected from "
            "$SHELL on Unix, PowerShell on Windows): bash, powershell, "
            "fish. Operators on other shells should pass --shell "
            "explicitly or set CHAT_SESSION_ID manually."
        ),
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help=(
            "Emit a shell-eval-able export line that sets "
            "CHAT_SESSION_ID in the caller's shell. Pipe through "
            "`eval \"$(...)\"` (bash), `Invoke-Expression` "
            "(PowerShell), or `... | source` (fish)."
        ),
    )
    parser.add_argument(
        "--shell",
        choices=list(SUPPORTED_SHELLS),
        default=None,
        help=(
            "Explicit shell-syntax selection for --export. Defaults to "
            "auto-detect from $SHELL (Unix) or `powershell` (Windows). "
            "Required for --export when auto-detect fails."
        ),
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the CLI. Returns the process exit code.

    Split from :func:`main` so tests can drive the namespace
    directly and inspect captured stdout/stderr without going
    through argparse's error-on-exit path.
    """
    value = _resolve_chat_session_id()

    if not args.export:
        # Plain mode: write only the UUID. Tests assert that stdout
        # is exactly the UUID + newline so downstream tooling can
        # capture it with `$(python -m ai_router.new_chat_id)`.
        print(value)
        return EXIT_OK

    shell = args.shell or _detect_shell()
    if shell is None:
        print(
            "new_chat_id: --export was supplied but the shell flavor "
            "could not be auto-detected. Pass --shell "
            f"{{{'|'.join(SUPPORTED_SHELLS)}}} explicitly, or set "
            f"{CHAT_SESSION_ID_ENV_VAR} manually with your shell's "
            "native export syntax.",
            file=sys.stderr,
        )
        return EXIT_SHELL_DETECT_FAILED

    formatter = _EXPORT_FORMATTERS.get(shell)
    if formatter is None:
        # Defensive: argparse choices keep this branch unreachable
        # in normal use, but a programmatic caller passing an
        # unsupported shell value should get a clear error rather
        # than a KeyError.
        print(
            f"new_chat_id: unsupported shell {shell!r}; expected one "
            f"of {SUPPORTED_SHELLS}.",
            file=sys.stderr,
        )
        return EXIT_SHELL_DETECT_FAILED

    print(formatter(value))
    return EXIT_OK


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
