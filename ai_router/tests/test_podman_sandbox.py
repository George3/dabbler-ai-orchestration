"""Tests for the Set 069 S4 Podman model-authored-probe cage (podman_sandbox).

Two layers:

1. **Fake-cage / unit** (run everywhere, incl. the Windows host where podman
   lives only in WSL): argv construction (the containment flags), the cgroup-v2
   resource-cap gating (spike finding 1), result mapping, the
   stdout/stderr-separation (spike finding 3), the crash-safe timeout teardown
   (spike finding 2), the teardown-leak-is-a-hard-error render, image
   digest-pin detection, caps-from-config, and footprint parsing. These fake
   ``run_subprocess_capped`` / ``subprocess.run`` so no real podman is needed.

2. **Real-podman regression** (``@requires_podman``, skipped when podman is
   unavailable or the image is not built): the actual containment properties the
   spike proved - ``--network=none`` holds, the repo mount is read-only and
   nothing leaks, a hung probe is killed + the container torn down, AND the
   operator's disk-footprint hard requirement (run N probes -> 0 leftover
   containers + 0 named volumes + image count unchanged).

No metered API calls anywhere.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import podman_sandbox as ps  # conftest puts ai_router/ on sys.path


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _fake_capped(
    *, exit_code=0, stdout="", stderr="", timed_out=False, wall=1.0
):
    """A stand-in for run_test_sandbox.CappedRun (only the fields used here)."""
    return SimpleNamespace(
        exit_code=exit_code,
        stdout_text=stdout,
        stderr_text=stderr,
        stdout_elided=False,
        stderr_elided=False,
        timed_out=timed_out,
        wall_seconds=wall,
    )


@pytest.fixture
def no_real_podman(monkeypatch):
    """Force the harness off any real podman: no container exists, caps known."""
    monkeypatch.setattr(ps, "_container_exists", lambda name: False)
    monkeypatch.setattr(ps, "cgroup_caps_enforceable", lambda: False)


# ---------------------------------------------------------------------------
# argv construction (the containment flags + the resource-cap gating)
# ---------------------------------------------------------------------------


def test_build_argv_has_all_containment_flags():
    argv = ps._build_argv(
        "img", ("python", "-c", "x"),
        repo_root=ps.Path("."), name="pull-probe-abc",
        caps=ps.PodmanCaps(), enforce_caps=False,
    )
    s = " ".join(argv)
    assert argv[:2] == ["podman", "run"]
    assert "--rm" in argv
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
    assert "--security-opt=no-new-privileges" in argv
    assert "/scratch:rw,size=64m,mode=1777" in argv
    assert any(a.endswith(":/repo:ro") for a in argv)
    assert "PYTHONPATH=/repo" in argv
    # the model-authored probe argv is the tail (after the image)
    assert argv[-3:] == ["python", "-c", "x"]


def test_build_argv_resource_caps_gated_on_cgroup_v2():
    base = dict(repo_root=ps.Path("."), name="pull-probe-x", caps=ps.PodmanCaps())
    off = ps._build_argv("img", ("python",), enforce_caps=False, **base)
    on = ps._build_argv("img", ("python",), enforce_caps=True, **base)
    # Spike finding 1: emit --memory/--pids-limit/--cpus ONLY when enforceable.
    assert not any(a.startswith("--memory=") for a in off)
    assert not any(a.startswith("--pids-limit=") for a in off)
    assert not any(a.startswith("--cpus=") for a in off)
    assert "--memory=512m" in on
    assert "--pids-limit=256" in on
    assert "--cpus=2" in on


def test_run_probe_autodetect_omits_caps_on_v1(monkeypatch, no_real_podman):
    captured = {}

    def fake_capped(argv, **kw):
        captured["argv"] = argv
        return _fake_capped(exit_code=0, stdout="ok")

    monkeypatch.setattr(ps, "run_subprocess_capped", fake_capped)
    # enforce_resource_caps=None -> auto-detect; no_real_podman pins v1 (False).
    res = ps.run_probe_in_container(
        "img", ("python", "-c", "x"), repo_root=".",
        caps=ps.PodmanCaps(enforce_resource_caps=None),
    )
    assert res.resource_caps_enforced is False
    assert not any(a.startswith("--memory=") for a in captured["argv"])


# ---------------------------------------------------------------------------
# result mapping + stdout/stderr separation (spike finding 3)
# ---------------------------------------------------------------------------


def test_reproduced_maps_stdout_stderr_separately(monkeypatch, no_real_podman):
    monkeypatch.setattr(
        ps, "run_subprocess_capped",
        lambda argv, **kw: _fake_capped(
            exit_code=ps.PROBE_REPRODUCED_EXIT,
            stdout="PROBE_RESULT: reproduced",
            stderr="WARN: Resource limits are not supported",
        ),
    )
    res = ps.run_probe_in_container("img", ("python",), repo_root=".")
    assert res.ran and res.reproduced
    # stdout = the probe's own output (replay-hashed); stderr = runtime warnings.
    assert res.probe_output == "PROBE_RESULT: reproduced"
    assert "Resource limits" in res.runtime_diagnostics
    assert res.container_removed is True
    body = res.render()
    assert "probe output (stdout)" in body
    assert "runtime diagnostics" in body


def test_robust_probe_is_not_reproduced(monkeypatch, no_real_podman):
    monkeypatch.setattr(
        ps, "run_subprocess_capped",
        lambda argv, **kw: _fake_capped(exit_code=ps.PROBE_ROBUST_EXIT, stdout="ok"),
    )
    res = ps.run_probe_in_container("img", ("python",), repo_root=".")
    assert res.ran and not res.reproduced


def test_launch_failure_is_a_clean_error(monkeypatch):
    def boom(argv, **kw):
        raise OSError("podman not found")

    monkeypatch.setattr(ps, "run_subprocess_capped", boom)
    res = ps.run_probe_in_container("img", ("python",), repo_root=".")
    assert res.ran is False
    assert res.error and "failed to launch" in res.error
    assert res.render().startswith("ERROR: podman cage:")


# ---------------------------------------------------------------------------
# crash-safe timeout teardown (spike finding 2)
# ---------------------------------------------------------------------------


def test_timeout_force_removes_container_by_name(monkeypatch):
    monkeypatch.setattr(
        ps, "run_subprocess_capped",
        lambda argv, **kw: _fake_capped(exit_code=None, timed_out=True, wall=13.5),
    )
    rm_calls = []

    def fake_run(cmd, **kw):
        rm_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ps.subprocess, "run", fake_run)
    # the container no longer exists after the force-remove
    monkeypatch.setattr(ps, "_container_exists", lambda name: False)
    res = ps.run_probe_in_container("img", ("python",), repo_root=".")
    assert res.timed_out and res.exit_code is None
    # an explicit `podman rm -f <name>` fired (the ~10s rootless-WSL path)
    assert any(c[:3] == ["podman", "rm", "-f"] for c in rm_calls)
    assert res.container_removed is True
    assert res.error is None


def test_teardown_leak_is_a_hard_error(monkeypatch):
    monkeypatch.setattr(
        ps, "run_subprocess_capped",
        lambda argv, **kw: _fake_capped(exit_code=ps.PROBE_REPRODUCED_EXIT, stdout="x"),
    )
    # a container SURVIVES -> a leak
    monkeypatch.setattr(ps, "_container_exists", lambda name: True)
    monkeypatch.setattr(ps, "cgroup_caps_enforceable", lambda: False)
    res = ps.run_probe_in_container("img", ("python",), repo_root=".")
    assert res.container_removed is False
    assert res.reproduced is False  # a leak cannot back a reproduction
    assert res.render().startswith("ERROR: podman cage: container teardown did NOT")


# ---------------------------------------------------------------------------
# image identity + caps-from-config
# ---------------------------------------------------------------------------


def test_image_digest_pin_detection():
    assert ps.image_is_digest_pinned("pull-probe@sha256:deadbeef") is True
    assert ps.image_is_digest_pinned("pull-probe:local") is False
    assert ps.image_is_digest_pinned("") is False


def test_caps_from_config_defaults_and_override():
    assert ps.podman_caps_from_config(None) == ps.PodmanCaps()
    caps = ps.podman_caps_from_config(
        {"pull_verifier": {"podman": {"caps": {
            "wall_seconds": 5, "memory": "1g", "enforce_resource_caps": True,
        }}}}
    )
    assert caps.wall_seconds == 5.0
    assert caps.memory == "1g"
    assert caps.enforce_resource_caps is True
    # a non-bool enforce value falls back to None (auto-detect)
    caps2 = ps.podman_caps_from_config(
        {"pull_verifier": {"podman": {"caps": {"enforce_resource_caps": "yes"}}}}
    )
    assert caps2.enforce_resource_caps is None


# ---------------------------------------------------------------------------
# cgroup detection + footprint parsing (faked podman CLI)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ver,expected", [("v2", True), ("v1", False)])
def test_cgroup_caps_enforceable(monkeypatch, ver, expected):
    monkeypatch.setattr(
        ps.subprocess, "run",
        lambda cmd, **kw: SimpleNamespace(returncode=0, stdout=ver + "\n", stderr=""),
    )
    assert ps.cgroup_caps_enforceable() is expected


def test_cgroup_caps_enforceable_false_on_error(monkeypatch):
    def boom(cmd, **kw):
        raise OSError("no podman")

    monkeypatch.setattr(ps.subprocess, "run", boom)
    assert ps.cgroup_caps_enforceable() is False


def test_footprint_is_lane_local_by_label(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        # podman applies `--filter label=` server-side, so the ps/volume output
        # here is ALREADY scoped to our lane (a co-tenant's box is excluded).
        if cmd[1] == "ps":
            seen["ps_filter"] = "label=" + ps.LANE_LABEL in cmd
            return SimpleNamespace(returncode=0,
                                   stdout="pull-probe-aaa\npull-probe-bbb\n",
                                   stderr="")
        if cmd[1] == "volume":
            seen["vol_filter"] = "label=" + ps.LANE_LABEL in cmd
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd[1] == "image":  # `podman image exists <ref>`
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(cmd)

    monkeypatch.setattr(ps.subprocess, "run", fake_run)
    fp = ps.podman_footprint(image="pull-probe:local")
    # both queries filtered by the lane label (not a name prefix)
    assert seen["ps_filter"] and seen["vol_filter"]
    assert fp.containers == 2  # only the lane's own labeled containers
    assert fp.volumes == 0
    assert fp.image_present is True
    assert fp.error is None


def test_footprint_image_absent(monkeypatch):
    def fake_run(cmd, **kw):
        if cmd[1] in ("ps", "volume"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")  # image exists -> no

    monkeypatch.setattr(ps.subprocess, "run", fake_run)
    fp = ps.podman_footprint(image="missing@sha256:x")
    assert fp.image_present is False and fp.containers == 0


def test_build_probe_argv_contract():
    # The model-authored body is wrapped as `python -B -c <body>`; -I/-E are
    # deliberately ABSENT (they would drop PYTHONPATH=/repo) (GPT-5.4 S4 finding 4).
    argv = ps.build_probe_argv("import ai_router; print('x')")
    assert argv == ("python", "-B", "-c", "import ai_router; print('x')")
    assert "-I" not in argv and "-E" not in argv


def test_build_argv_carries_lane_label():
    argv = ps._build_argv(
        "img", ("python",), repo_root=ps.Path("."), name="pull-probe-x",
        caps=ps.PodmanCaps(), enforce_caps=False,
    )
    assert "--label" in argv
    assert f"{ps.LANE_LABEL}=1" in argv


# ---------------------------------------------------------------------------
# Real-podman regression (skipped without podman + a built image)
# ---------------------------------------------------------------------------

_PODMAN_VERSION = ps.podman_available()


def _image_built() -> bool:
    if not _PODMAN_VERSION:
        return False
    import subprocess
    r = subprocess.run(
        ["podman", "image", "exists", ps.DEFAULT_IMAGE_TAG],
        capture_output=True,
    )
    return r.returncode == 0


requires_podman = pytest.mark.skipif(
    not _image_built(),
    reason=(
        "real podman + the pull-probe:local image required; build it with "
        "`podman build -t pull-probe:local -f ai_router/podman/Containerfile "
        "ai_router/podman` (runs on Linux CI / WSL, skipped on the Windows host)"
    ),
)


@requires_podman
def test_real_network_is_denied(tmp_path):
    res = ps.run_probe_in_container(
        ps.DEFAULT_IMAGE_TAG,
        ("python", "-c",
         "import socket; socket.setdefaulttimeout(3); "
         "socket.create_connection(('1.1.1.1', 53))"),
        repo_root=tmp_path, caps=ps.PodmanCaps(wall_seconds=20),
    )
    assert res.ran and res.exit_code not in (0, None)  # blocked
    assert res.container_removed


@requires_podman
def test_real_repo_mount_is_read_only_and_no_leak(tmp_path):
    marker = tmp_path / "LEAK_TEST.tmp"
    res = ps.run_probe_in_container(
        ps.DEFAULT_IMAGE_TAG,
        ("python", "-c", "open('/repo/LEAK_TEST.tmp','w').write('x')"),
        repo_root=tmp_path,
    )
    assert res.exit_code not in (0, None)  # the write failed
    assert not marker.exists()  # nothing leaked to the real tree
    assert res.container_removed


@requires_podman
def test_real_timeout_kills_and_tears_down(tmp_path):
    res = ps.run_probe_in_container(
        ps.DEFAULT_IMAGE_TAG,
        ("python", "-c", "import time; time.sleep(60)"),
        repo_root=tmp_path, caps=ps.PodmanCaps(wall_seconds=3),
    )
    assert res.timed_out and res.exit_code is None
    assert res.container_removed and res.error is None


@requires_podman
def test_real_disk_footprint_stays_bounded(tmp_path):
    """Operator hard requirement: N probes leave 0 leftover containers/volumes
    and do NOT accrete a per-probe image."""
    for i in range(3):
        res = ps.run_probe_in_container(
            ps.DEFAULT_IMAGE_TAG,
            ("python", "-c", f"print('PROBE_RESULT: run {i}')"),
            repo_root=tmp_path,
        )
        assert res.ran and res.container_removed
    after = ps.podman_footprint(image=ps.DEFAULT_IMAGE_TAG)
    assert after.containers == 0  # no leftover LABELED containers from this lane
    assert after.volumes == 0  # tmpfs scratch -> no named volumes
    assert after.image_present is True  # the reused image is still there
