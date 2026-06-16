## Verdict

- **Overall:** `NEEDS_FIX`
- **Central safety claim:** `PASS`
- **Why not green:** digest pinning is not actually implemented in the checked-in image, and footprint accounting is not lane-local on a shared Podman host.

## Checklist

| # | Status | Note |
|---|---|---|
| 1 | **PASS** | `_build_transcript()` explicitly returns `None` for `kind=="authored"`, and `_stamp_evidence_tiers()` caps matched/sole authored executions at `HYPOTHESIS`; no authored path mints `REPRODUCED` or attaches a falsifier transcript. `by_probe` is separate from `by_command` / `by_template`. |
| 2 | **PASS** | The model only supplies `probe`; `_dispatch_run_authored_probe()` wraps it via `build_probe_argv()`, and `_build_argv()` constructs the full `podman run` argv. No model field becomes a Podman flag or mount/network option. |
| 3 | **PASS** | Required cage flags are present: `--network=none`, `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`, read-only `/repo`, tmpfs `/scratch`, `--rm`, wall-clock timeout, `PYTHONPATH=/repo`, and `python -B -c ...` (not `-I` / `-E`). |
| 4 | **PASS** | Spike findings are carried correctly: cgroup caps are emitted only when enforceable, timeout does explicit `podman rm -f`, and stdout/stderr are separated so runtime warnings do not affect replay hash. |
| 5 | **FAIL** | `podman_footprint()` is not lane-local enough: containers are only prefix-matched, volumes are counted globally, and images are tracked globally by count. This cannot prove lane-owned hygiene on a shared host. |
| 6 | **PASS** | Triage is triage-only: `default_triage()` returns `None` or a block reason, has no approve branch, and runs before any container launch. |
| 7 | **PASS** | `entrypointRef`, `entrypointKind`, and `claim` are validated before cage launch; the body itself cannot be enforced by construction, which is exactly why the lane stays capped at `HYPOTHESIS`. |
| 8 | **WARN** | Functional behavior is correct: second-run replay is only a flake/rerun signal and does not raise the tier. But the rendered explanation is wrong when `replay_matched=False`. |
| 9 | **PASS** | Additivity holds: no `PodmanLaneConfig` means no `run_authored_probe`, no `probeId`, and no authored stamping path. Lane IDs stay separated. |
| 10 | **WARN** | The new doc is mostly aligned, but its digest-pin story is aspirational relative to the checked-in `Containerfile`, and its disk-hygiene claims inherit the footprint-accounting gap. |
| 11 | **WARN** | Tests cover most S4 seams, but they do not directly exercise `build_probe_argv()`’s `-B` / no `-I` / no `-E` contract, and they do not cover the shared-host attribution weakness in footprint accounting. |

## Findings

1. **Issue →** Base image is not actually digest-pinned.  
   **Location →** `ai_router/podman/Containerfile:21`  
   **Fix →** Replace `FROM python:3.11-slim` with a resolved digest form such as `FROM python@sha256:...`.

2. **Issue →** Footprint accounting cannot prove lane-local hygiene on a shared Podman host: container ownership is inferred only by a shared prefix, named volumes are counted globally, and image stability is checked via global image-count equality.  
   **Location →** `ai_router/podman_sandbox.py:277-315`; regression coverage in `ai_router/tests/test_podman_sandbox.py:239-252,318-331`  
   **Fix →** Add lane/session labels in `_build_argv()` and query by label; make volume/image checks lane-specific, or compare the configured image ref/digest instead of global counts.

3. **Issue →** `replay_matched=False` still renders text saying the second run “reproduced the same probe output.”  
   **Location →** `ai_router/pull_verifier.py:1196-1199`  
   **Fix →** Make the explanatory text conditional on the boolean value.

4. **Issue →** The suite does not directly test the `build_probe_argv()` contract, so a regression dropping `-B` or adding `-I` / `-E` would pass.  
   **Location →** `ai_router/podman_sandbox.py:516-539`; current argv coverage only hits `_build_argv()` in `ai_router/tests/test_podman_sandbox.py:59-90`  
   **Fix →** Add a unit test asserting `build_probe_argv("x") == ("python", "-B", "-c", "x")` and explicitly asserting `-I` / `-E` are absent.