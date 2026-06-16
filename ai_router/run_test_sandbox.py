"""Set 068 S1 - the disposable-worktree ``run_test`` execution cage + the shared
subprocess machinery it introduces (also the new home of the ``grep`` ReDoS
isolation).

The full design contract is pinned in
``docs/session-sets/068-cadence-study-and-contract-gate/run-test-contract.md``.
This module ships three things:

1. :func:`run_subprocess_capped` - the shared primitive: run an argv (``shell=
   False``) with a **hard wall-clock timeout** (kill the process tree on
   overrun) and a **per-stream output byte cap** (over-cap output elided to a raw
   head slice, never paraphrased). Output is captured to temp files so a runaway
   command cannot blow memory before the timeout fires.
2. :func:`run_test_in_cage` - the ``run_test`` cage: create a **disposable,
   detached git worktree** from a pinned ref, run the bounded command
   in it (cwd = the throwaway checkout, so the command's ordinary in-tree writes
   are discarded with it), and tear the worktree down on **every** exit path
   (success, failed command, timeout-kill, or any exception). This is
   disposable-CWD isolation of a TRUSTED command, NOT an OS sandbox - see the
   "Scope of the isolation" note below for exactly what it does and does not
   confine.
3. :func:`isolated_regex_search` - the relocated ``grep`` ReDoS defense: a
   linear-time ``re2`` inline fast path when available, else the regex match runs
   in :mod:`ai_router.regex_worker` as a subprocess bounded by
   :func:`run_subprocess_capped`'s hard timeout. The Set 067 0.21.1 nesting-aware
   heuristic stays in :mod:`pull_verifier` as a cheap **pre-filter** only.

Deterministic-servant discipline, extended to execution: ``run_test`` returns the
**raw** exit code + captured output, never a model-summarized view.

**Scope of the isolation (read this - it is NOT an OS sandbox).** The cage runs
the configured command with ``cwd`` set to a disposable, detached worktree, so the
command's ordinary working-directory writes (build artifacts, temp files, even
commits) land in a checkout that is discarded at teardown and never touch the real
tree's working copy. It is a **disposable-CWD** isolation that relies on the
command being **operator-authored and trusted** (this set's use is the project's
OWN test command on the project's OWN pinned snapshots - Experiment B). It is
deliberately **not** an adversarial OS sandbox: there is no chroot / mount
namespace / UID restriction / env scrub / filesystem mediation, so a command that
*deliberately* writes an absolute path, follows a symlink committed into the tree,
discovers the main worktree via ``git worktree list``, or spawns a detached child
can still reach the real filesystem. Confining genuinely untrusted code is an
explicit non-goal of this bounded verification cage (a general-purpose sandbox is
a much larger surface); the threat model is accidental/incidental writes by a
trusted command, not a malicious payload. A cage that cannot be
created/torn-down reports an explicit error rather than proceeding.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Shared elision (raw head slice + ASCII marker; mirrors pull_verifier._elide,
# but operating on captured BYTES so the cap is genuinely on encoded size).
# ---------------------------------------------------------------------------

_ELISION_MARKER = "\n[... elided {n} bytes ...]\n"


def _elide_stream(head: bytes, total: int) -> Tuple[str, bool]:
    """Decode a captured stream head; append a raw elision marker if truncated.

    ``head`` is the first ``cap`` bytes read from the stream; ``total`` is the
    stream's full byte length. When ``total <= len(head)`` nothing was dropped.
    Decoding uses ``errors="ignore"`` on a truncated head so a partial trailing
    codepoint is dropped (the slice stays valid), matching
    ``pull_verifier._elide``.
    """
    if total <= len(head):
        return head.decode("utf-8", errors="replace"), False
    text = head.decode("utf-8", errors="ignore")
    dropped = total - len(text.encode("utf-8"))
    return text + _ELISION_MARKER.format(n=dropped), True


# ---------------------------------------------------------------------------
# 1. The shared capped-subprocess primitive.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CappedRun:
    """The raw outcome of one bounded subprocess run."""

    exit_code: Optional[int]  # None when the process was killed (timeout)
    stdout_text: str
    stderr_text: str
    stdout_elided: bool
    stderr_elided: bool
    stdout_bytes_total: int
    stderr_bytes_total: int
    timed_out: bool
    wall_seconds: float


def _kill_tree(proc: "subprocess.Popen") -> None:
    """Best-effort kill of the process AND its descendants.

    A test command (e.g. pytest) can spawn children; killing only the parent
    leaks them. On Windows ``taskkill /T`` walks the tree; on POSIX the process
    was started in its own session so ``killpg`` reaps the group.
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass


def run_subprocess_capped(
    argv: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    timeout_seconds: float,
    output_byte_cap: int,
    env: Optional[dict] = None,
    stdin_text: Optional[str] = None,
) -> CappedRun:
    """Run ``argv`` (``shell=False``) capped on wall-clock AND captured bytes.

    - ``shell=False`` ALWAYS: ``argv`` is a list, never a shell string, so no
      shell metacharacter interpretation is possible.
    - Hard wall-clock ``timeout_seconds``: on overrun the process tree is killed
      and ``timed_out=True`` / ``exit_code=None``.
    - Output is captured to temp files and only the first ``output_byte_cap``
      bytes of each stream are read back (elided), so a flood cannot blow memory.
    """
    t0 = time.monotonic()
    timed_out = False
    # stdout/stderr are redirected to temp files below (bounded memory); only the
    # stdin disposition and the platform process-group flag are set here.
    popen_kwargs: dict = {
        "stdin": subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
    }
    if cwd is not None:
        popen_kwargs["cwd"] = str(cwd)
    if env is not None:
        popen_kwargs["env"] = env
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    # Capture to temp files (bounded memory): redirect the pipes through files we
    # read a capped head from. We let Popen create pipes and drain them via
    # communicate(), but to bound memory for a flooding child we instead point
    # stdout/stderr at temp files.
    out_f = tempfile.TemporaryFile()
    err_f = tempfile.TemporaryFile()
    try:
        popen_kwargs["stdout"] = out_f
        popen_kwargs["stderr"] = err_f
        proc = subprocess.Popen(list(argv), **popen_kwargs)
        stdin_bytes = (
            stdin_text.encode("utf-8") if stdin_text is not None else None
        )
        try:
            proc.communicate(input=stdin_bytes, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            try:
                proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                pass
        wall = time.monotonic() - t0

        out_total = out_f.seek(0, os.SEEK_END)
        out_f.seek(0)
        out_head = out_f.read(output_byte_cap)
        err_total = err_f.seek(0, os.SEEK_END)
        err_f.seek(0)
        err_head = err_f.read(output_byte_cap)
    finally:
        out_f.close()
        err_f.close()

    stdout_text, stdout_elided = _elide_stream(out_head, out_total)
    stderr_text, stderr_elided = _elide_stream(err_head, err_total)
    exit_code = None if timed_out else proc.returncode
    return CappedRun(
        exit_code=exit_code,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        stdout_elided=stdout_elided,
        stderr_elided=stderr_elided,
        stdout_bytes_total=out_total,
        stderr_bytes_total=err_total,
        timed_out=timed_out,
        wall_seconds=wall,
    )


# ---------------------------------------------------------------------------
# 2. The run_test disposable-worktree cage.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunTestCaps:
    """Per-run bounds for the cage."""

    wall_seconds: float = 120.0
    output_byte_cap: int = 60_000


def run_test_caps_from_config(config: Optional[dict]) -> RunTestCaps:
    """Build :class:`RunTestCaps` from ``pull_verifier.run_test.caps``.

    Any field absent from the block falls back to the dataclass default, so a
    config with no ``run_test`` block yields the exact defaults (backward
    compatible). This is the consumer of the ``router-config.yaml`` caps block;
    the S3 cadence harness uses it to source the live cage's bounds from config.
    """
    pv_block = (config or {}).get("pull_verifier", {}) or {}
    caps_cfg = (pv_block.get("run_test", {}) or {}).get("caps", {}) or {}
    base = RunTestCaps()
    return RunTestCaps(
        wall_seconds=float(caps_cfg.get("wall_seconds", base.wall_seconds)),
        output_byte_cap=int(
            caps_cfg.get("output_byte_cap", base.output_byte_cap)
        ),
    )


@dataclass(frozen=True)
class RunTestResult:
    """The raw outcome of one ``run_test`` cage run (never summarized)."""

    ran: bool  # True iff the cage was created AND the command executed
    exit_code: Optional[int]  # raw command exit; None if killed (timeout)
    output: str  # combined raw stdout+stderr, capped/elided, ASCII section marks
    timed_out: bool
    wall_seconds: float
    command: Tuple[str, ...]
    worktree_created: bool
    worktree_removed: bool
    error: Optional[str]  # raw cage error (not-a-repo / bad ref / no command)

    @property
    def passed(self) -> bool:
        """True iff the command ran to a zero exit. NOT the same as ``ran``."""
        return self.ran and self.exit_code == 0

    def to_dict(self) -> dict:
        return {
            "ran": self.ran,
            "exit_code": self.exit_code,
            "passed": self.passed,
            "timed_out": self.timed_out,
            "wall_seconds": round(self.wall_seconds, 2),
            "command": list(self.command),
            "worktree_created": self.worktree_created,
            "worktree_removed": self.worktree_removed,
            "error": self.error,
            "output_chars": len(self.output),
        }

    def render(self) -> str:
        """Raw ASCII tool-result text for the agentic loop (never paraphrased)."""
        if self.error:
            return f"ERROR: run_test cage: {self.error}"
        # A teardown that did not fully complete (worktree registration or temp
        # tree survived) is a HARD failure surfaced as a leading raw ERROR, not
        # hidden in structured state - the cage-escape-is-a-hard-failure posture
        # (GPT-5.4 S1 R1, Major 2b). The ERROR prefix makes _dispatch_run_test
        # flag this as an error probe. The raw exit code + captured output are
        # STILL appended below (not dropped) so the unsafe-leak path stays
        # diagnosable (GPT-5.4 S1 R2, new Minor).
        leak_prefix = ""
        if self.ran and not self.worktree_removed:
            leak_prefix = (
                "ERROR: run_test cage: disposable worktree teardown did NOT "
                "complete (possible leak); treat this run as unsafe and "
                "investigate stranded worktrees with `git worktree list`.\n"
            )
        exit_str = "KILLED (timeout)" if self.timed_out else str(self.exit_code)
        head = (
            f"exit_code={exit_str}\n"
            f"timed_out={self.timed_out}\n"
            f"wall_seconds={round(self.wall_seconds, 2)}\n"
            f"command={' '.join(self.command)}\n"
            f"--- output ---\n"
        )
        return leak_prefix + head + self.output


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _is_git_repo(path: Path) -> bool:
    return _git(path, "rev-parse", "--git-dir").returncode == 0


def _worktree_registered(repo_root: Path, cage: Path) -> bool:
    """True iff ``cage`` is still a registered worktree of ``repo_root``.

    The leak check: after teardown, git must no longer list the cage path. A
    surviving registration is a leak (a hard failure, surfaced by the caller).
    """
    out = _git(repo_root, "worktree", "list", "--porcelain").stdout
    cage_real = cage.resolve()
    for line in out.splitlines():
        if line.startswith("worktree "):
            p = line[len("worktree "):].strip()
            try:
                if Path(p).resolve() == cage_real:
                    return True
            except OSError:  # pragma: no cover - defensive on a bad path
                continue
    return False


def _teardown(
    repo_root: Path, cage: Path, parent: Path, created: bool
) -> bool:
    """Remove the disposable worktree and its temp parent; return removed-ok.

    Best-effort and non-raising: a teardown failure is reported (return False),
    never propagated over the run's own outcome. Ordering matters for leak
    recovery (GPT-5.4 S1 R1, Major 2a): remove the worktree, then delete the temp
    tree (in case ``remove --force`` left locked files behind), and ONLY THEN
    ``git worktree prune`` - so a registration whose directory is now gone is
    cleaned up even when ``remove --force`` failed. The final
    :func:`_worktree_registered` check confirms no registration leaked.
    """
    removed = True
    if created:
        _git(repo_root, "worktree", "remove", "--force", str(cage))
        shutil.rmtree(parent, ignore_errors=True)
        # Prune AFTER the directory is gone so a failed `remove` is still
        # deregistered (a registration pointing at a missing dir is prunable).
        # `--expire now` forces immediate expiry of stale entries rather than
        # leaving a freshly-stale registration to a default age heuristic
        # (GPT-5.4 S1 R2, Major). It only ever prunes worktrees whose directory
        # is ALREADY gone, so a live worktree is never affected.
        _git(repo_root, "worktree", "prune", "--expire", "now")
        if _worktree_registered(repo_root, cage):
            removed = False  # leak: registration survived teardown
    else:
        shutil.rmtree(parent, ignore_errors=True)
    if parent.exists():
        removed = False
    return removed


def run_test_in_cage(
    repo_root,
    ref: str,
    command: Sequence[str],
    *,
    caps: Optional[RunTestCaps] = None,
    worktrees_parent=None,
) -> RunTestResult:
    """Run ``command`` in a disposable worktree of ``repo_root`` at ``ref``.

    Lifecycle: ``git worktree add --detach`` a fresh temp dir at ``ref`` ->
    run ``command`` with ``cwd`` = the throwaway worktree (so its ordinary in-tree
    writes are discarded with it) under the caps -> tear the worktree down on
    EVERY exit path (finally). This is disposable-CWD isolation of a TRUSTED
    command, NOT an OS sandbox: a command that deliberately writes an absolute
    path / follows a committed symlink / discovers the main worktree / spawns a
    detached child can still reach the real filesystem (module docstring, "Scope
    of the isolation"). The threat model is accidental writes by a trusted
    command, not a hostile payload.

    ``command`` is a resolved argv (the operator-configured test command), passed
    verbatim with ``shell=False`` - the cage never interprets a shell string.
    Returns a :class:`RunTestResult`; cage-setup failures (not a git repo, bad
    ref, empty command) come back as ``ran=False`` with a raw ``error``.
    """
    caps = caps or RunTestCaps()
    cmd = tuple(str(c) for c in (command or ()))
    repo_root = Path(repo_root).resolve()

    if not cmd:
        return RunTestResult(
            ran=False, exit_code=None, output="", timed_out=False,
            wall_seconds=0.0, command=(), worktree_created=False,
            worktree_removed=True, error="no run_test command configured",
        )
    if not _is_git_repo(repo_root):
        return RunTestResult(
            ran=False, exit_code=None, output="", timed_out=False,
            wall_seconds=0.0, command=cmd, worktree_created=False,
            worktree_removed=True,
            error=f"not a git repository: {repo_root}",
        )

    # Temp-dir creation is itself a cage-setup step: if it fails (e.g. a bad
    # worktrees_parent), convert it to a raw error result like the other setup
    # failures above, rather than letting the exception escape the contract
    # (Set 068 S6 whole-set critique, GPT-5.4, Major). Nothing was created yet,
    # so there is nothing to tear down -> worktree_removed=True (no leak).
    try:
        parent = Path(tempfile.mkdtemp(prefix="run-test-cage-", dir=worktrees_parent))
    except OSError as exc:
        return RunTestResult(
            ran=False, exit_code=None, output="", timed_out=False,
            wall_seconds=0.0, command=cmd, worktree_created=False,
            worktree_removed=True,
            error=f"run_test cage temp-dir creation failed: {exc}",
        )
    cage = parent / "wt"
    created = False
    base: RunTestResult
    try:
        add = _git(repo_root, "worktree", "add", "--detach", str(cage), ref)
        if add.returncode != 0:
            base = RunTestResult(
                ran=False, exit_code=None, output="", timed_out=False,
                wall_seconds=0.0, command=cmd, worktree_created=False,
                worktree_removed=False,
                error=f"git worktree add failed (ref {ref!r}): "
                      f"{add.stderr.strip()}",
            )
        else:
            created = True
            run = run_subprocess_capped(
                cmd,
                cwd=cage,
                timeout_seconds=caps.wall_seconds,
                output_byte_cap=caps.output_byte_cap,
            )
            base = RunTestResult(
                ran=True,
                exit_code=run.exit_code,
                output=_combine_output(run),
                timed_out=run.timed_out,
                wall_seconds=run.wall_seconds,
                command=cmd,
                worktree_created=True,
                worktree_removed=False,  # set by replace() after teardown
                error=None,
            )
    except Exception as exc:  # crash-safe: convert to an error, still tear down
        base = RunTestResult(
            ran=False, exit_code=None, output="", timed_out=False,
            wall_seconds=0.0, command=cmd, worktree_created=created,
            worktree_removed=False, error=f"run_test cage exception: {exc}",
        )
    finally:
        removed = _teardown(repo_root, cage, parent, created)
    return dataclasses.replace(base, worktree_removed=removed)


def _combine_output(run: CappedRun) -> str:
    """Raw combined stdout+stderr with ASCII section markers (never paraphrased)."""
    parts: List[str] = []
    if run.stdout_text:
        parts.append("[stdout]\n" + run.stdout_text)
    if run.stderr_text:
        parts.append("[stderr]\n" + run.stderr_text)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Relocated grep ReDoS isolation (re2 inline fast path | subprocess + kill).
# ---------------------------------------------------------------------------

# Hard wall-clock for one isolated regex evaluation. A catastrophic pattern that
# defeats the cheap pre-filter is killed at this bound instead of hanging. The
# grep itself is cheap, so a few seconds is generous; the test overrides this.
REGEX_TIMEOUT_SECONDS = 5.0
# Generous cap for the worker's match-line output; the caller (_canonical_grep)
# elides for display at 60 KB regardless.
_REGEX_OUTPUT_CAP = 8_000_000


class RegexTimeout(Exception):
    """The isolated regex evaluation exceeded its wall-clock bound (killed)."""


class RegexError(Exception):
    """The isolated regex worker failed (e.g. an invalid pattern)."""


def _try_re2(pattern: str):
    """Return a compiled linear-time engine matcher, or None if re2 is absent.

    ``re2`` (Google's RE2) guarantees linear-time matching, so ReDoS is
    impossible by construction and the search can run inline with no subprocess.
    """
    try:
        import re2  # type: ignore
    except ImportError:
        return None
    return re2.compile(pattern)


def isolated_regex_search(
    pattern: str,
    files: Sequence[Tuple[str, str]],
    *,
    timeout_seconds: Optional[float] = None,
) -> List[str]:
    """ReDoS-bounded ``grep``: return ``rel:lineno:line`` matches over ``files``.

    ``files`` is a list of already-sandbox-confined ``(rel, text)`` pairs (the
    walk + confinement stay in the caller). re2 inline when available; otherwise
    the match runs in :mod:`ai_router.regex_worker` as a subprocess with a hard
    timeout, so a catastrophic pattern is killed rather than hanging the
    orchestrator. Raises :class:`RegexTimeout` on a kill, :class:`RegexError` on
    a worker/compile failure - both surfaced by the caller as a raw ``ERROR:``.
    """
    timeout = (
        REGEX_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    )

    rx = _try_re2(pattern)
    if rx is not None:
        out: List[str] = []
        for rel, text in files:
            for i, ln in enumerate(text.splitlines(), 1):
                if rx.search(ln):
                    out.append(f"{rel}:{i}:{ln}")
        return out

    job = json.dumps(
        {
            "pattern": pattern,
            "files": [{"rel": rel, "text": text} for rel, text in files],
        }
    )
    run = run_subprocess_capped(
        [sys.executable, "-m", "ai_router.regex_worker"],
        cwd=None,
        timeout_seconds=timeout,
        output_byte_cap=_REGEX_OUTPUT_CAP,
        stdin_text=job,
    )
    if run.timed_out:
        raise RegexTimeout(
            "grep pattern timed out (ReDoS-bounded by subprocess isolation); "
            "simplify the pattern"
        )
    if run.exit_code != 0:
        raise RegexError(
            (run.stderr_text or "regex worker failed").strip()
        )
    if not run.stdout_text:
        return []
    text = run.stdout_text
    if run.stdout_elided:
        # The worker's stdout was cut mid-stream. _elide_stream appended the
        # marker AFTER a raw head slice that almost certainly ends mid-line, so
        # the head's LAST line is a corrupted partial match (GPT-5.4 S1 R1,
        # Minor 3). Take the text BEFORE the marker and drop that final partial
        # line; the earlier-attempt `lines[:-1]` only dropped the empty string
        # left by the marker's trailing newline, leaking the partial line.
        idx = text.find("\n[... elided ")
        if idx != -1:
            text = text[:idx]
        parts = text.split("\n")
        return parts[:-1] if parts else parts
    return text.split("\n")
