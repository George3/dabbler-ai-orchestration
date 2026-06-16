"""Set 069 S4 - the Podman model-authored-probe cage (graduated from the spike).

The proposal's CRUX-1 hard line is: **model-authored code runs only inside a real
container**. Set 069 S1-S3 gave the automated pull-critic three execution lanes
that never run model-authored code - it may only *trigger* an operator-authored
``run_test`` command, read ``get_diff``, or *parameterize* an operator-authored
probe template. This module adds the one lane where the model **authors** the
probe body: rung (b) of the proposal ladder
(``docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md`` sec 3),
**autonomous + severity-gated**, with the **container as the boundary** (so no
human approval for (b) itself; only a probe that must *escape* the container is
rung (c), human-gated).

This is :mod:`ai_router.run_test_sandbox`'s sibling: the isolation mechanism is
``podman run`` instead of ``git worktree add``. It graduated into ``ai_router/``
only after the **GREEN** Podman feasibility spike
(``docs/proposals/2026-06-16-pull-architecture-capabilities/podman-spike/``,
6/6 acceptance criteria, podman 4.9.3). The spike harness (``podman_cage.py``)
proved the mechanics; this module hardens them for production and carries the
spike's three recorded findings.

Containment flags (the whole point - the cage, NOT the floor, is what makes
running model-authored code safe; proposal sec 3.5 / spec Standards):

    --network=none              no network at all (egress denied)
    --read-only                 read-only container rootfs
    -v <repo>:/repo:ro          the repo snapshot mounted READ-ONLY
    --tmpfs /scratch:rw         the only writable place (RAM-backed, ephemeral)
    --cap-drop=ALL              drop every Linux capability
    --security-opt=no-new-privileges
    --memory / --pids-limit / --cpus   resource caps (cgroup-v2 only; see below)
    --rm                        auto-remove on exit (teardown)

The three spike findings, carried here (spec S4 step 3):

1. **Rootless cgroups-v1 ignores ``--memory`` / ``--pids-limit`` / ``--cpus``.**
   The spike box ran rootless on cgroups-v1, where podman warns *"Resource limits
   are not supported and ignored on cgroups V1 rootless systems"* and the caps are
   NOT enforced. The effective bound there is the **wall-clock timeout** (which
   works) + ``--network=none`` + the read-only FS. So this harness **detects the
   cgroup version** (:func:`cgroup_caps_enforceable`) and emits the resource-cap
   flags **only when they will actually be enforced** (cgroup v2). On v1-rootless
   it omits them (so the run is not polluted by the ignore-warning) and leans on
   the wall-clock cap, which the spike proved kills a hung probe. Production fix
   to *restore* the caps: enable cgroup v2 + controller delegation (an environment
   change, not a code change) - and this harness then uses them automatically.

2. **Timeout teardown is slow in rootless WSL (~10 s).** A steady-state probe is
   ~1.5 s, but force-removing a *timed-out* live container added ~10 s. So the
   default ``wall_seconds`` is kept conservative and the timeout path is the rare
   one; :class:`PodmanResult` reports ``wall_seconds`` so a caller can see the cost.

3. **Separate the probe's output from podman's runtime warnings.** The spike's raw
   capture (correct, but) mixed podman's own warning into the probe's stderr. For
   clean, deterministic evidence this harness captures **stdout and stderr
   separately**: the probe's contracted ``PROBE_RESULT:`` line goes to **stdout**
   (``probe_output`` - the bytes hashed for the pristine-replay falsifier match),
   while podman's runtime diagnostics land on **stderr** (``runtime_diagnostics`` -
   shown to the model but NEVER part of the replay hash, so a runtime warning can
   never make two honest runs mismatch).

**Scope of the isolation.** Unlike the ``run_test`` cage (disposable-CWD isolation
of a *trusted* command, explicitly NOT an OS sandbox), this lane IS an OS-level
container sandbox, because it runs **untrusted, model-authored** code. The
container is the security boundary. What the container does NOT fix (proposal sec
3.5, kept as disciplines elsewhere): **probe-correctness / the meta-oracle** - a
perfectly contained probe can still "prove" a non-bug, so a container-confirmed
finding must drive a **real public entrypoint** and the autonomous lane's tier is
capped below REPRODUCED (the human-gated S5 ratchet promotes it). That tiering is
``pull_verifier``'s job; this module only runs the cage and returns raw truth.

Cross-platform: shells out to the ``podman`` CLI through the shared
:func:`ai_router.run_test_sandbox.run_subprocess_capped` primitive (process-tree
kill, temp-file capture, byte caps), so it runs on Windows (via the WSL2-backed
podman) and on Linux CI alike. ``shell=False`` always; the model never authors a
``podman`` flag - it supplies only the probe body.
"""

from __future__ import annotations

import dataclasses
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:  # package vs bare-import (mirrors the rest of ai_router)
    from .run_test_sandbox import run_subprocess_capped
except ImportError:  # pragma: no cover - test/bare context
    from run_test_sandbox import run_subprocess_capped  # type: ignore


# The probe's standardized exit-code contract (aligned with
# ai_router.probe_templates so both execution lanes speak one convention):
#   exit 1 -> reproduced (the entrypoint raised / the defect is real)
#   exit 0 -> robust     (the entrypoint handled the input gracefully)
#   exit 2 -> probe error (the probe could not perform its check)
PROBE_REPRODUCED_EXIT = 1
PROBE_ROBUST_EXIT = 0
PROBE_ERROR_EXIT = 2
PROBE_RESULT_PREFIX = "PROBE_RESULT: "

# Every container this cage creates is named with this prefix AND carries the
# lane LABEL below, so the disk-footprint check can find any leak attributable to
# THIS lane without touching a co-tenant's containers/volumes (proposal sec 3.2:
# never prune blindly). The label is the authoritative lane-ownership signal on a
# SHARED host (a prefix is only a convention; a label is queryable + can't collide
# with another tool's naming), so the footprint queries filter by it (GPT-5.4 S4
# verification, finding 2).
CONTAINER_NAME_PREFIX = "pull-probe-"
LANE_LABEL = "pull-probe-lane"

# The operator-authored image. The default tag is for the spike / local dev /
# CI; production passes a digest-pinned ref (``name@sha256:...``) instead.
DEFAULT_IMAGE_TAG = "pull-probe:local"
# The graduated Containerfile dir (ai_router/podman/), so build_image() and the
# CI build step can find it without a hard-coded path.
CONTAINERFILE_DIR = Path(__file__).resolve().parent / "podman"


# ---------------------------------------------------------------------------
# Image identity (digest-pinned, no-secrets - proposal sec 3.2 / 3.5).
# ---------------------------------------------------------------------------


def image_is_digest_pinned(image: str) -> bool:
    """True iff ``image`` is pinned by digest (``name@sha256:...``), not a tag.

    Production REQUIRES a digest pin: the image is built/pulled once and the model
    never touches it, so a digest makes the cage reproducible and tamper-evident
    (proposal sec 3.2). A bare tag (``pull-probe:local``) is allowed only for the
    spike / local dev; the producer warns when an un-pinned image is used.
    """
    return isinstance(image, str) and "@sha256:" in image


def build_image(
    tag: str, containerfile_dir, *, timeout_seconds: float = 600.0
) -> Tuple[bool, str]:
    """Build the cage image ONCE from an operator-authored Containerfile dir.

    Returns ``(ok, raw_output)``. Built once and reused across all probes - NEVER
    rebuilt per probe (per-build layer churn is the Docker bloat failure mode the
    operator called out; proposal sec 3.2). CI builds it at the start of a run; a
    dev box builds it once. ``shell=False``; the build is a fixed argv.
    """
    run = run_subprocess_capped(
        ["podman", "build", "-t", tag, "-f",
         str(Path(containerfile_dir) / "Containerfile"), str(containerfile_dir)],
        timeout_seconds=timeout_seconds,
        output_byte_cap=200_000,
    )
    out = (run.stdout_text + "\n" + run.stderr_text).strip()
    return (run.exit_code == 0), out


# ---------------------------------------------------------------------------
# Cage caps + cgroup detection (spike finding 1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PodmanCaps:
    """Per-probe bounds for the Podman cage.

    ``wall_seconds`` is the load-bearing bound on a rootless-cgroups-v1 host (the
    spike's environment), where the resource caps below are ignored (finding 1).
    ``enforce_resource_caps`` tri-states the ``--memory`` / ``--pids-limit`` /
    ``--cpus`` flags: ``None`` (default) auto-detects via
    :func:`cgroup_caps_enforceable` and emits them only when cgroup v2 will honor
    them; ``True`` / ``False`` force the decision (tests pin it so they never shell
    out to ``podman info``).
    """

    wall_seconds: float = 30.0
    output_byte_cap: int = 60_000
    memory: str = "512m"
    pids_limit: int = 256
    cpus: str = "2"
    enforce_resource_caps: Optional[bool] = None


def podman_caps_from_config(config: Optional[dict]) -> PodmanCaps:
    """Build :class:`PodmanCaps` from ``pull_verifier.podman.caps`` (omit-absent).

    Any field absent from the block falls back to the dataclass default, so a
    config with no ``podman`` block yields the exact defaults (backward
    compatible). Mirrors :func:`ai_router.run_test_sandbox.run_test_caps_from_config`.
    ``enforce_resource_caps`` stays ``None`` (auto-detect the cgroup version)
    unless the config pins a boolean.
    """
    pv_block = (config or {}).get("pull_verifier", {}) or {}
    caps_cfg = (pv_block.get("podman", {}) or {}).get("caps", {}) or {}
    base = PodmanCaps()
    enforce = caps_cfg.get("enforce_resource_caps", None)
    return PodmanCaps(
        wall_seconds=float(caps_cfg.get("wall_seconds", base.wall_seconds)),
        output_byte_cap=int(caps_cfg.get("output_byte_cap", base.output_byte_cap)),
        memory=str(caps_cfg.get("memory", base.memory)),
        pids_limit=int(caps_cfg.get("pids_limit", base.pids_limit)),
        cpus=str(caps_cfg.get("cpus", base.cpus)),
        enforce_resource_caps=(
            bool(enforce) if isinstance(enforce, bool) else None
        ),
    )


def cgroup_caps_enforceable() -> bool:
    """True iff ``--memory`` / ``--pids-limit`` / ``--cpus`` will be ENFORCED here.

    Spike finding 1: on a rootless **cgroups-v1** host podman *ignores* the
    resource caps (and warns), so emitting them just pollutes the run. They are
    honored only on **cgroup v2** (with controller delegation, which rootless
    systemd provides). Detect the host cgroup version via ``podman info``; default
    to ``False`` (the conservative spike reality) if podman is unavailable or the
    query fails - so a missing/odd environment leans on the wall-clock cap rather
    than emitting flags that may be silently ignored.
    """
    try:
        r = subprocess.run(
            ["podman", "info", "--format", "{{.Host.CgroupsVersion}}"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.strip() == "v2"


def podman_available() -> Optional[str]:
    """Return the ``podman`` client version string, or None if podman is unusable.

    Used to skip the real-podman tests on a host without it (the Windows pytest
    run; podman lives in WSL2) and to record the version in the lane's provenance.
    """
    try:
        r = subprocess.run(
            ["podman", "version", "--format", "{{.Client.Version}}"],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _container_exists(name: str) -> bool:
    try:
        r = subprocess.run(
            ["podman", "ps", "-a", "--filter", f"name=^{name}$",
             "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=30,
        )
        return name in r.stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Disk-footprint hygiene (operator hard requirement; spec Standards + S4 test).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PodmanFootprint:
    """A LANE-LOCAL snapshot of the cage's disk footprint (proposal sec 3.2).

    Every count is scoped to THIS lane (by the :data:`LANE_LABEL`), so the check
    is sound on a SHARED Podman host where co-tenants own their own
    containers/volumes/images (GPT-5.4 S4 verification, finding 2):

    - ``containers`` - leftover containers carrying the lane label (must be 0;
      every probe is ``--rm`` + force-removed on timeout);
    - ``volumes`` - named volumes carrying the lane label (must be 0; the cage
      uses tmpfs, so it NEVER creates a named volume - a non-zero count is a real
      leak, and a co-tenant's unlabeled volume is correctly NOT counted);
    - ``image_present`` - whether the configured cage image exists (so probes can
      run); the lane NEVER builds an image at runtime (only the one-time
      :func:`build_image`), so there is no per-probe image to count - the relevant
      assertion is "the reused image is present", not a fragile global count.

    ``error`` is a raw podman error, else None.
    """

    containers: int
    volumes: int
    image_present: bool
    error: Optional[str] = None


def podman_footprint(
    *, image: str = "", label: str = LANE_LABEL
) -> PodmanFootprint:
    """Measure the LANE-LOCAL disk footprint (containers / volumes / image).

    The operator's hard requirement is **no growing footprint**: after a probe
    run there must be 0 leftover lane containers and 0 lane named volumes, and the
    reused image must still be present (the cage never accretes a per-probe
    image). Every query filters by ``label`` so a co-tenant on the same host is
    never miscounted. Read-only; runs ``podman`` list queries, never a prune.
    """
    try:
        cont = subprocess.run(
            ["podman", "ps", "-a", "--filter", f"label={label}",
             "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=30,
        )
        vol = subprocess.run(
            ["podman", "volume", "ls", "--filter", f"label={label}",
             "--format", "{{.Name}}"],
            capture_output=True, text=True, timeout=30,
        )
        present = True
        if image:
            chk = subprocess.run(
                ["podman", "image", "exists", image],
                capture_output=True, text=True, timeout=30,
            )
            present = chk.returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        return PodmanFootprint(
            containers=0, volumes=0, image_present=False, error=str(exc)
        )
    if cont.returncode != 0 or vol.returncode != 0:
        return PodmanFootprint(
            containers=0, volumes=0, image_present=False,
            error=(cont.stderr or vol.stderr or "podman list failed").strip(),
        )
    containers = [n for n in cont.stdout.split() if n]
    volumes = [v for v in vol.stdout.split() if v]
    return PodmanFootprint(
        containers=len(containers), volumes=len(volumes), image_present=present
    )


# ---------------------------------------------------------------------------
# The cage run + its raw result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PodmanResult:
    """The raw outcome of one model-authored probe run in the Podman cage.

    Deterministic-servant discipline, extended to container execution: this is the
    **raw** exit code + captured output, never a model-summarized view.
    ``probe_output`` (stdout) and ``runtime_diagnostics`` (stderr) are kept
    SEPARATE (spike finding 3) so the probe's own deterministic output is the
    replay-hashed evidence and podman's runtime warnings cannot perturb the hash.
    """

    ran: bool  # True iff podman launched AND the probe executed (exit or timeout)
    exit_code: Optional[int]  # raw probe exit; None if killed (timeout)
    timed_out: bool
    probe_output: str  # stdout: the probe's OWN output (the replay-hashed bytes)
    runtime_diagnostics: str  # stderr: podman runtime warnings (NOT replay-hashed)
    wall_seconds: float
    container_removed: bool  # True iff no container with our name survives
    image: str
    image_digest_pinned: bool
    resource_caps_enforced: bool  # whether --memory/--pids/--cpus were emitted
    argv: Tuple[str, ...]  # the full podman argv actually run (provenance)
    error: Optional[str] = None  # raw setup/teardown error, else None

    @property
    def reproduced(self) -> bool:
        """True iff the probe ran cleanly to the REPRODUCED exit code (1)."""
        return (
            self.ran
            and self.error is None
            and self.container_removed
            and self.exit_code == PROBE_REPRODUCED_EXIT
        )

    def to_dict(self) -> dict:
        return {
            "ran": self.ran,
            "exit_code": self.exit_code,
            "reproduced": self.reproduced,
            "timed_out": self.timed_out,
            "wall_seconds": round(self.wall_seconds, 2),
            "container_removed": self.container_removed,
            "image": self.image,
            "image_digest_pinned": self.image_digest_pinned,
            "resource_caps_enforced": self.resource_caps_enforced,
            "probe_output_chars": len(self.probe_output),
            "error": self.error,
        }

    def render(self) -> str:
        """Raw ASCII tool-result text for the agentic loop (never paraphrased).

        A teardown that did not complete (a surviving container) is a HARD failure
        surfaced as a leading raw ERROR - the container-escape-is-a-hard-failure
        posture (mirrors run_test_sandbox.RunTestResult.render). The raw exit code +
        captured output are STILL appended so the unsafe path stays diagnosable.
        """
        if self.error and not self.ran:
            return f"ERROR: podman cage: {self.error}"
        leak_prefix = ""
        if self.ran and not self.container_removed:
            leak_prefix = (
                "ERROR: podman cage: container teardown did NOT complete "
                "(possible leak); treat this run as unsafe and investigate "
                "stranded containers with `podman ps -a`.\n"
            )
        elif self.error:
            # A teardown-path error (e.g. force-remove failed) with the container
            # gone is still surfaced, but not as an unsafe leak.
            leak_prefix = f"NOTE: podman cage: {self.error}\n"
        exit_str = "KILLED (timeout)" if self.timed_out else str(self.exit_code)
        head = (
            f"exit_code={exit_str}\n"
            f"timed_out={self.timed_out}\n"
            f"wall_seconds={round(self.wall_seconds, 2)}\n"
            f"image={self.image} (digest_pinned={self.image_digest_pinned})\n"
            f"resource_caps_enforced={self.resource_caps_enforced}\n"
            "--- probe output (stdout) ---\n"
            f"{self.probe_output}\n"
            "--- runtime diagnostics (stderr; not part of the replay hash) ---\n"
            f"{self.runtime_diagnostics}"
        )
        return leak_prefix + head


def _build_argv(
    image: str,
    probe_argv: Sequence[str],
    *,
    repo_root: Path,
    name: str,
    caps: PodmanCaps,
    enforce_caps: bool,
) -> List[str]:
    """Assemble the locked-down ``podman run`` argv (the model touches NONE of it)."""
    argv: List[str] = [
        "podman", "run", "--rm", "--name", name,
        # The lane-ownership label (queryable; the authoritative signal the
        # footprint check filters by on a shared host - GPT-5.4 S4 finding 2).
        "--label", f"{LANE_LABEL}=1",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
    ]
    if enforce_caps:
        # Emitted ONLY when cgroup v2 will honor them (spike finding 1); on
        # rootless cgroups-v1 they are ignored + warned, so we omit them there.
        argv += [
            f"--memory={caps.memory}",
            f"--pids-limit={caps.pids_limit}",
            f"--cpus={caps.cpus}",
        ]
    argv += [
        "--tmpfs", "/scratch:rw,size=64m,mode=1777",
        "-v", f"{repo_root}:/repo:ro",
        "-w", "/scratch",
        # The code under review is importable as ``ai_router.*`` from the
        # read-only mount, so a model probe can drive a REAL public entrypoint
        # (the meta-oracle discipline) without authoring import plumbing.
        "--env", "PYTHONPATH=/repo",
        image,
        *[str(a) for a in probe_argv],
    ]
    return argv


def run_probe_in_container(
    image: str,
    probe_argv: Sequence[str],
    *,
    repo_root,
    caps: Optional[PodmanCaps] = None,
) -> PodmanResult:
    """Run ``probe_argv`` inside a locked-down, disposable Podman container.

    The model authors only ``probe_argv`` (in practice ``["python", "-c",
    <body>]``); this function builds the full ``podman run`` argv. Lifecycle: run
    the bounded subprocess (process-tree kill + separate stdout/stderr capture +
    byte caps via :func:`run_subprocess_capped`) -> on a wall-clock timeout the
    ``--rm`` container is **force-removed by name** (crash-safe teardown, spike
    finding 2's ~10 s path) -> confirm no container with our name survives. Returns
    a :class:`PodmanResult`; a podman-unavailable / launch failure comes back as
    ``ran=False`` with a raw ``error`` (never an exception).
    """
    caps = caps or PodmanCaps()
    repo_root = Path(repo_root).resolve()
    name = f"{CONTAINER_NAME_PREFIX}{uuid.uuid4().hex[:12]}"

    if caps.enforce_resource_caps is None:
        enforce_caps = cgroup_caps_enforceable()
    else:
        enforce_caps = caps.enforce_resource_caps

    argv = _build_argv(
        image, probe_argv, repo_root=repo_root, name=name, caps=caps,
        enforce_caps=enforce_caps,
    )

    setup_err: Optional[str] = None
    try:
        run = run_subprocess_capped(
            argv,
            timeout_seconds=caps.wall_seconds,
            output_byte_cap=caps.output_byte_cap,
        )
    except (OSError, ValueError) as exc:  # podman binary absent / bad argv
        return PodmanResult(
            ran=False, exit_code=None, timed_out=False, probe_output="",
            runtime_diagnostics="", wall_seconds=0.0, container_removed=True,
            image=image, image_digest_pinned=image_is_digest_pinned(image),
            resource_caps_enforced=enforce_caps, argv=tuple(argv),
            error=f"podman run failed to launch: {exc}",
        )

    if run.timed_out:
        # Crash-safe teardown: the timed-out container is force-removed by name
        # (the ~10 s rootless-WSL path; spike finding 2). run_subprocess_capped
        # already killed the `podman run` client process tree on the host, but the
        # container itself can outlive a killed client, so the explicit rm is
        # required, not redundant.
        try:
            subprocess.run(
                ["podman", "rm", "-f", name],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            setup_err = f"force-remove after timeout failed: {exc}"

    removed = not _container_exists(name)
    return PodmanResult(
        ran=True,
        exit_code=run.exit_code,
        timed_out=run.timed_out,
        # stdout = the probe's own output (replay-hashed); stderr = runtime
        # diagnostics (NOT replay-hashed). Spike finding 3.
        probe_output=run.stdout_text,
        runtime_diagnostics=run.stderr_text,
        wall_seconds=run.wall_seconds,
        container_removed=removed,
        image=image,
        image_digest_pinned=image_is_digest_pinned(image),
        resource_caps_enforced=enforce_caps,
        argv=tuple(argv),
        error=setup_err,
    )


def build_probe_argv(probe_body: str) -> Tuple[str, ...]:
    """The trusted argv wrapper around a model-authored probe BODY.

    The model authors only ``probe_body`` (a Python source string that imports the
    code under review from ``/repo`` and drives a real public entrypoint, printing
    a deterministic ``PROBE_RESULT:`` line and exiting per the 1/0/2 contract).
    The harness wraps it as ``python -c <body>`` - the model never authors a
    ``podman`` flag or the interpreter invocation. ``-B`` keeps the read-only
    container from trying to write ``__pycache__``; ``PYTHONPATH=/repo`` (set on
    the podman argv, NOT here) is what makes ``import ai_router`` resolve to the
    code under review, so the interpreter is deliberately NOT run isolated
    (``-I``/``-E`` would drop ``PYTHONPATH`` and the probe could not import it).
    """
    return ("python", "-B", "-c", probe_body)
