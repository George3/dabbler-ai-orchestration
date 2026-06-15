"""Tests for the Set 068 S1 run_test execution cage + relocated ReDoS isolation.

Covers the load-bearing invariants from
``docs/session-sets/068-cadence-study-and-contract-gate/run-test-contract.md``:
the disposable worktree is created and ALWAYS torn down (incl. on exception); a
command that overruns is killed; output is capped/elided; a write cannot escape
the worktree (the real tree is never mutated); the result is the raw exit+output;
and a pathological regex that DEFEATS the cheap heuristic is bounded by the
subprocess isolation rather than hanging.

No metered API calls: everything here is git + local subprocess + the regex
worker. The cage subprocess is the venv's own python (``sys.executable``).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

import run_test_sandbox as rts  # conftest puts ai_router/ on sys.path
import regex_worker as rw


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path):
    """A throwaway one-commit git repo (the cage's source-of-truth ref)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def _git(*args):
        subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True
        )

    _git("init", "-q")
    _git("config", "user.email", "t@example.invalid")
    _git("config", "user.name", "Test")
    (repo / "hello.txt").write_text("hi\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")
    return repo


def _registered_worktrees(repo) -> int:
    """Count of EXTRA (non-main) worktrees git has registered for ``repo``."""
    out = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    # one "worktree <path>" line per registered worktree; main is one of them.
    return max(0, out.count("worktree ") - 1)


# ---------------------------------------------------------------------------
# run_subprocess_capped primitive
# ---------------------------------------------------------------------------


class TestRunSubprocessCapped:
    def test_exit_code_and_output_captured(self, tmp_path):
        run = rts.run_subprocess_capped(
            [sys.executable, "-c", "import sys; print('out'); sys.exit(3)"],
            cwd=tmp_path, timeout_seconds=30, output_byte_cap=60000,
        )
        assert run.exit_code == 3
        assert "out" in run.stdout_text
        assert run.timed_out is False

    def test_timeout_kills_and_reports(self, tmp_path):
        run = rts.run_subprocess_capped(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=tmp_path, timeout_seconds=1.0, output_byte_cap=60000,
        )
        assert run.timed_out is True
        assert run.exit_code is None
        assert run.wall_seconds < 20  # killed promptly, not after 30s

    def test_output_is_capped_and_elided(self, tmp_path):
        run = rts.run_subprocess_capped(
            [sys.executable, "-c", "print('x' * 5000)"],
            cwd=tmp_path, timeout_seconds=30, output_byte_cap=100,
        )
        assert run.stdout_elided is True
        assert "[... elided" in run.stdout_text
        assert run.stdout_bytes_total >= 5000

    def test_stdin_is_fed(self, tmp_path):
        run = rts.run_subprocess_capped(
            [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read().upper())"],
            cwd=tmp_path, timeout_seconds=30, output_byte_cap=60000,
            stdin_text="abc",
        )
        assert run.exit_code == 0
        assert "ABC" in run.stdout_text


# ---------------------------------------------------------------------------
# run_test_in_cage lifecycle
# ---------------------------------------------------------------------------


class TestRunTestInCage:
    def test_runs_and_tears_down(self, git_repo):
        res = rts.run_test_in_cage(
            git_repo, "HEAD", [sys.executable, "-c", "print('TEST OK')"]
        )
        assert res.ran is True
        assert res.exit_code == 0
        assert res.passed is True
        assert res.worktree_created is True
        assert res.worktree_removed is True
        assert "TEST OK" in res.output
        assert _registered_worktrees(git_repo) == 0  # cage unregistered

    def test_write_cannot_escape_real_tree_untouched(self, git_repo):
        # The command writes a RELATIVE path; it must land in the disposable
        # worktree (discarded), never in the real tree.
        res = rts.run_test_in_cage(
            git_repo, "HEAD",
            [sys.executable, "-c", "open('escaped.txt','w').write('x')"],
        )
        assert res.ran is True
        assert not (git_repo / "escaped.txt").exists()
        # real tree is clean (only the committed hello.txt)
        status = subprocess.run(
            ["git", "-C", str(git_repo), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert status.strip() == ""

    def test_timeout_killed_and_torn_down(self, git_repo):
        res = rts.run_test_in_cage(
            git_repo, "HEAD",
            [sys.executable, "-c", "import time; time.sleep(30)"],
            caps=rts.RunTestCaps(wall_seconds=1.0, output_byte_cap=60000),
        )
        assert res.timed_out is True
        assert res.exit_code is None
        assert res.passed is False
        assert res.worktree_removed is True
        assert _registered_worktrees(git_repo) == 0

    def test_output_capped(self, git_repo):
        res = rts.run_test_in_cage(
            git_repo, "HEAD",
            [sys.executable, "-c", "print('y' * 5000)"],
            caps=rts.RunTestCaps(wall_seconds=30, output_byte_cap=200),
        )
        assert "[... elided" in res.output

    def test_teardown_on_exception(self, git_repo, monkeypatch):
        # If the run phase raises, teardown MUST still fire (finally) and the
        # worktree must be unregistered - a crash never leaks a cage.
        def boom(*a, **k):
            raise RuntimeError("injected mid-run failure")

        monkeypatch.setattr(rts, "run_subprocess_capped", boom)
        res = rts.run_test_in_cage(
            git_repo, "HEAD", [sys.executable, "-c", "pass"]
        )
        assert res.ran is False
        assert "injected mid-run failure" in res.error
        assert res.worktree_removed is True
        assert _registered_worktrees(git_repo) == 0

    def test_bad_ref_is_error_not_crash(self, git_repo):
        res = rts.run_test_in_cage(
            git_repo, "no-such-ref", [sys.executable, "-c", "pass"]
        )
        assert res.ran is False
        assert res.error and "worktree add failed" in res.error
        assert _registered_worktrees(git_repo) == 0

    def test_not_a_git_repo_is_error(self, tmp_path):
        res = rts.run_test_in_cage(
            tmp_path, "HEAD", [sys.executable, "-c", "pass"]
        )
        assert res.ran is False
        assert "not a git repository" in res.error

    def test_empty_command_is_error(self, git_repo):
        res = rts.run_test_in_cage(git_repo, "HEAD", [])
        assert res.ran is False
        assert "no run_test command configured" in res.error

    def test_render_is_raw_ascii(self, git_repo):
        res = rts.run_test_in_cage(
            git_repo, "HEAD", [sys.executable, "-c", "print('hello-cage')"]
        )
        rendered = res.render()
        assert "exit_code=0" in rendered
        assert "hello-cage" in rendered
        assert rendered.isascii()

    def test_teardown_leak_is_reported_and_surfaced(self, git_repo, monkeypatch):
        # GPT-5.4 S1 R1 Major 2: a worktree registration that survives teardown
        # is a LEAK -> worktree_removed=False AND render() surfaces a hard ERROR
        # (not a silently-normal result). Simulate the surviving registration.
        monkeypatch.setattr(rts, "_worktree_registered", lambda repo, cage: True)
        res = rts.run_test_in_cage(
            git_repo, "HEAD", [sys.executable, "-c", "print('ok')"]
        )
        assert res.ran is True
        assert res.worktree_removed is False
        rendered = res.render()
        assert rendered.startswith("ERROR:")
        assert "teardown did NOT complete" in rendered
        # GPT-5.4 S1 R2 new Minor: the raw exit code + output are PRESERVED on the
        # leak path (not dropped), so the unsafe run stays diagnosable.
        assert "exit_code=0" in rendered
        assert "ok" in rendered

    def test_render_surfaces_leak_without_cage_error(self):
        # A ran=True result with worktree_removed=False renders as a leading ERROR
        # even though `error` is None (the leak IS the failure) - AND keeps the
        # raw exit/output block.
        res = rts.RunTestResult(
            ran=True, exit_code=0, output="[stdout]\ndiag-output", timed_out=False,
            wall_seconds=0.1, command=("x",), worktree_created=True,
            worktree_removed=False, error=None,
        )
        rendered = res.render()
        assert rendered.startswith("ERROR:")
        assert "exit_code=0" in rendered  # raw result preserved, not dropped
        assert "diag-output" in rendered


# ---------------------------------------------------------------------------
# Caps from config
# ---------------------------------------------------------------------------


class TestCapsFromConfig:
    def test_reads_run_test_caps(self):
        cfg = {"pull_verifier": {"run_test": {"caps": {
            "wall_seconds": 7, "output_byte_cap": 123}}}}
        caps = rts.run_test_caps_from_config(cfg)
        assert caps.wall_seconds == 7.0
        assert caps.output_byte_cap == 123

    def test_defaults_when_absent(self):
        base = rts.RunTestCaps()
        for cfg in (None, {}, {"pull_verifier": {}}):
            caps = rts.run_test_caps_from_config(cfg)
            assert caps.wall_seconds == base.wall_seconds
            assert caps.output_byte_cap == base.output_byte_cap


# ---------------------------------------------------------------------------
# Relocated grep ReDoS isolation
# ---------------------------------------------------------------------------


class TestIsolatedRegexSearch:
    def test_normal_search(self):
        files = [("a.py", "alpha\nbeta\n"), ("b.txt", "needle here\nhay\n")]
        out = rts.isolated_regex_search("needle", files)
        assert out == ["b.txt:1:needle here"]

    def test_no_matches(self):
        assert rts.isolated_regex_search("zzz", [("a", "x\n")]) == []

    def test_multi_match_lines_are_clean_no_carriage_return(self):
        # Regression: the subprocess worker must NOT leave a trailing "\r" on
        # multi-line output (Windows text-mode newline translation). Every line
        # is a clean 'rel:lineno:line' with no stray "\r".
        files = [("a.py", "hit one\nmiss\nhit two\nhit three\n")]
        out = rts.isolated_regex_search("hit", files)
        assert out == ["a.py:1:hit one", "a.py:3:hit two", "a.py:4:hit three"]
        assert all("\r" not in ln for ln in out)

    def test_catastrophic_pattern_bounded_by_isolation(self, monkeypatch):
        # (a|a)*c DEFEATS the cheap nesting-quantifier heuristic (its group body
        # has no quantifier) but backtracks catastrophically. The subprocess
        # isolation must kill it at the timeout, never hang.
        monkeypatch.setattr(rts, "REGEX_TIMEOUT_SECONDS", 1.5)
        files = [("big.txt", "a" * 64)]
        with pytest.raises(rts.RegexTimeout):
            rts.isolated_regex_search("(a|a)*c", files)

    def test_invalid_pattern_is_regex_error(self):
        with pytest.raises(rts.RegexError):
            rts.isolated_regex_search("(unclosed", [("a", "x\n")])

    def test_elided_output_drops_partial_match_line(self, monkeypatch):
        # GPT-5.4 S1 R1 Minor 3: when the worker's stdout is elided mid-line, the
        # corrupted partial trailing match line must be dropped - every returned
        # line is a COMPLETE 'rel:lineno:line' match, never a truncation.
        import re as _re

        monkeypatch.setattr(rts, "_REGEX_OUTPUT_CAP", 50)
        text = "\n".join(f"x{i}" for i in range(300))  # 300 matching lines
        out = rts.isolated_regex_search("x", [("f.txt", text)])
        assert 0 < len(out) < 300  # truncated by the tiny output cap
        for ln in out:
            assert _re.fullmatch(r"f\.txt:\d+:x\d+", ln), ln  # no partial line


class TestRegexWorker:
    def test_search_pure_function(self):
        files = [{"rel": "f.py", "text": "foo\nbar\nfoobar\n"}]
        assert rw.search("foo", files) == ["f.py:1:foo", "f.py:3:foobar"]

    def test_search_compile_error_raises(self):
        import re
        with pytest.raises(re.error):
            rw.search("(unclosed", [{"rel": "a", "text": "x"}])
