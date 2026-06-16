"""Set 069 S4 -- cross-provider session verification (Step 6, gated -> REQUIRED).

S4 ships the Podman model-authored-probe lane (proposal rung b): a NET-NEW module
(podman_sandbox.py) + a graduated Containerfile + wiring a run_authored_probe tool
into the shared adapter (pull_verifier.py) + threading a PodmanLaneConfig through
the producer (pull_critique.py) + a router-config caps block + docs. routed_gate
confirms REQUIRED (blast-radius + breadth + build-ci-config). Orchestrator is
Anthropic/opus; the verifier routes to a different provider.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

# Filled from the green full-suite run at this commit (baseline 1820 + 1 skip;
# this session adds 37 tests = 33 passing + 4 real-podman skips).
NEW_TESTS = 37
TOTAL_PASS = 1853

FILES = [
    "ai_router/podman_sandbox.py",
    "ai_router/podman/Containerfile",
    "ai_router/pull_verifier.py",
    "ai_router/pull_critique.py",
    "ai_router/router-config.yaml",
    "ai_router/docs/pull-verifier.md",
    "ai_router/tests/test_podman_sandbox.py",
    "ai_router/tests/test_pull_verifier.py",
    "ai_router/tests/test_pull_critique.py",
]
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--", *FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

# The net-new cage module + the graduated Containerfile, read directly so the
# verifier sees them cleanly (the diff is the whole file anyway for net-new).
SANDBOX = (REPO / "ai_router/podman_sandbox.py").read_text(encoding="utf-8")
CONTAINERFILE = (REPO / "ai_router/podman/Containerfile").read_text(encoding="utf-8")
EVIDENCE = (REPO / "ai_router/evidence_protocol.py").read_text(encoding="utf-8")
SPIKE = (REPO / "docs/proposals/2026-06-16-pull-architecture-capabilities/"
         "podman-spike/spike-result.json").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 4 of 6 of Set 069
(automated pull-critique capabilities) in the dabbler-ai-orchestration repo.
Return the structured verdict.

=== CONVENTIONS / BASELINE (read first; do NOT re-flag the agreed baseline) ===
- Suite baseline BEFORE this session: 1820 passed, 1 skipped (1 pre-existing,
  tracked). This session ADDS {NEW_TESTS} tests; the full ai_router pytest suite
  is GREEN at this commit ({TOTAL_PASS} passed, 5 skipped). The 4 NEW skips are
  the REAL-PODMAN cage-mechanics regressions (network/read-only/teardown/disk-
  footprint): they require a real podman + a built image, so they run on Linux CI
  / WSL and SKIP on the Windows host where this suite ran (podman lives in WSL2).
  That is BY DESIGN, not a gap. You are verifying CODE + DOCS, not re-running the
  suite.
- RELEASE CONTRACT: NO release this session. The ai_router PyPI release is
  Session 6; the version is intentionally unchanged. NO Marketplace / extension
  change (spec non-goal: no UI surface this whole set).
- SPIKE GATE: the Podman feasibility spike is GREEN (spike-result.json INCLUDED
  below: 6/6 acceptance criteria, podman 4.9.3), so S4 PROCEEDS with the full
  lane (NOT the NO-GO path). The spike's three findings are carried into S4 (see
  item 4). Do NOT re-run or re-verify the spike; verify only that S4 graduates it
  correctly and carries the findings.
- BY-DESIGN SCOPE (Session 4 = "Podman model-authored-probe lane -- rung b").
  IN scope: (a) graduate the spike harness into ai_router/podman_sandbox.py (a
  digest-pinned, no-secrets image; the `podman run` cage with --network=none,
  read-only /repo mount, tmpfs scratch, --cap-drop=ALL, caps, crash-safe
  teardown; a tiny typed tool surface); (b) wire it as the AUTONOMOUS,
  SEVERITY-GATED run_authored_probe lane in pull_verifier.pull_route with a
  TRIAGE-ONLY safety check (may reject/escalate, NEVER approve); (c) evidence
  flows through the S1 protocol; (d) thread a PodmanLaneConfig + --podman-lane
  CLI through the producer + a router-config caps block; (e) carry the spike's
  three findings + add the disk-footprint regression.
  DEFERRED (do NOT flag as gaps): the ceiling->floor ratchet + measured
  replacement gate (S5); the PyPI release + dogfood + synthesis-doc update (S6).
  The metered end-to-end agentic loop is NOT unit-tested (only the seams are);
  the REAL container runs are exercised only by the skipif-guarded real-podman
  tests (not on the Windows host). That is by design.
- ADDITIVITY IS A HARD REQUIREMENT: with NO PodmanLaneConfig the loop + producer
  + verdict schema must be byte-for-byte the prior behavior (no run_authored_probe
  tool offered, no probeId field, no authored evidence stamping). Confirm this.

=== THE CENTRAL DESIGN CLAIM TO CHECK (the safety property of this lane) ===
This is the ONE lane where the model AUTHORS the probe body (Python), so it runs
ONLY inside a real Podman container -- the container is the SECURITY BOUNDARY, not
the floor. Because a model-authored probe is NOT a trusted operator
command/template, it can NEVER mint REPRODUCED: the S1 validate_transcript
requires a commandId XOR templateId (never model-authored argv), so an authored
finding is CAPPED at HYPOTHESIS (a flagged, container-backed suspicion a human
verifies). Promotion to the floor is the S5 human-gated ratchet. Verify this cap
holds on EVERY path -- there must be NO way for an autonomous model-authored
probe to reach REPRODUCED or even ASSERTED-with-falsifier-transcript.

=== WHAT TO VERIFY (cite file:line for any finding) ===

1. THE HYPOTHESIS CAP IS AIRTIGHT. In pull_verifier: _build_transcript returns
   None for kind=="authored"; _stamp_evidence_tiers stamps HYPOTHESIS for a
   finding that (a) cites a probeId matching an authored execution, OR (b) is a
   REPRODUCED claim whose sole/matched execution is authored. Confirm there is NO
   path where an authored execution yields evidence_tier==REPRODUCED or an
   attached falsifier transcript. Confirm an authored probeId NEVER cross-binds a
   command/template lane (by_probe is lane-keyed) and vice-versa.

2. THE MODEL AUTHORS ONLY THE PROBE BODY -- NEVER A podman FLAG. In
   podman_sandbox.build_probe_argv + _build_argv + run_probe_in_container: the
   model's input is confined to the `python -B -c <body>` body; the full `podman
   run` argv (all containment flags) is harness-built. Is there ANY path where a
   model-supplied value becomes a podman flag or a mount/network option?

3. CONTAINMENT FLAGS ARE ALL PRESENT + CORRECT. --network=none, --read-only,
   --cap-drop=ALL, --security-opt=no-new-privileges, the repo bind-mounted
   read-only at /repo, tmpfs /scratch as the only writable place, --rm, the hard
   wall-clock timeout. PYTHONPATH=/repo lets the probe import the code under
   review (meta-oracle) WITHOUT -I/-E (which would drop PYTHONPATH) -- confirm -B
   is used, not -I/-E. Is read-only + --network=none + cap-drop genuinely the
   boundary for untrusted model-authored code, given the resource caps may be
   unenforced (item 4.1)?

4. THE THREE SPIKE FINDINGS ARE CARRIED (spec S4 step 3):
   4.1 cgroup-v1 ignores --memory/--pids-limit/--cpus. cgroup_caps_enforceable()
       detects v2 and _build_argv emits the resource caps ONLY when enforceable;
       on v1 they are omitted (not emitted-and-ignored). Confirm the wall-clock
       cap is the load-bearing bound when caps are unenforced, and that this is a
       DoS-hardening gap, not a containment hole.
   4.2 timeout teardown ~10s in rootless WSL: on timeout the --rm container is
       FORCE-REMOVED by name (explicit `podman rm -f`), and the result reports
       wall_seconds. Confirm the force-remove is REQUIRED (a killed `podman run`
       client can leave the container alive), not redundant.
   4.3 separate probe output from podman runtime warnings: stdout (probe_output,
       the replay-hashed bytes) vs stderr (runtime_diagnostics, NOT hashed).
       Confirm a runtime warning on stderr cannot perturb the replay-match.

5. DISK-FOOTPRINT HYGIENE (operator hard requirement). podman_footprint() counts
   leftover containers (prefix-filtered to THIS lane), named volumes, images;
   the regression asserts 0 containers + 0 volumes + unchanged image count after
   N probes. The image is reused, never rebuilt per probe (build_image is a
   one-time helper). Confirm the prefix filter cannot miscount a co-tenant's
   container, and that tmpfs scratch means no named volumes.

6. THE TRIAGE CHECK IS TRIAGE-ONLY (never approve). default_triage returns None
   (PROCEED) or a raw reason (BLOCK); it can reject (empty body / missing claim /
   no ai_router reference = meta-oracle) or ESCALATE (network/subprocess = a
   rung-c escape), but has NO approve branch. Confirm a triage rejection happens
   BEFORE any container spin-up, and that the absence of a block = proceed
   BECAUSE the container is the boundary (not because triage approved).

7. THE META-ORACLE DISCIPLINE. run_authored_probe requires entrypointRef +
   entrypointKind in PUBLIC_ENTRYPOINT_KINDS (agent_harness rejected) + a claim,
   validated BEFORE the cage. The probe is told to drive a REAL public entrypoint
   and print a deterministic PROBE_RESULT line + exit 1/0/2. Since the body is
   model-authored, this CANNOT be enforced by construction (unlike templates) --
   confirm that is exactly WHY the tier caps at HYPOTHESIS and the human stays the
   meta-oracle defense (a deliberate S4 non-goal to retire the manual run).

8. THE "PRISTINE REPLAY" FOR THIS LANE. On a reproduced probe, the dispatch runs
   a SECOND container and sets replay_matched = (both reproduced AND output
   hashes match). Confirm this is a re-runnability / flake signal surfaced to the
   agent + human, and that it does NOT elevate the tier (still HYPOTHESIS).

9. ADDITIVITY / BACKWARD COMPATIBILITY. With podman_lane_config=None: the
   run_authored_probe tool is NOT offered; the verdict schema has NO probeId
   field; the exec_lane / stamping path is reached only when a lane is active.
   Confirm the no-lane offered tools + verdict schema are byte-for-byte the prior
   (S3) shape, and that mixing the authored lane with run_test / probe-template
   lanes keeps each id bound to its own lane.

10. DOC ACCURACY (ai_router/docs/pull-verifier.md "What Set 069 S4 added"). Does
    it match the code EXACTLY (the cage flags, the 3 findings, the
    never-REPRODUCED cap, the triage-only check, the disk hygiene, the CLI flags,
    the skip-on-Windows test posture)? Any claim of CURRENT behavior the code
    does not back (L-064-8)? Any overclaim of S4 vs S5-S6?

11. TEST ADEQUACY. Do the new tests actually exercise the named behaviors -- the
    HYPOTHESIS cap (REPRODUCED-claim-with-probeId -> HYPOTHESIS; sole-authored ->
    HYPOTHESIS; _build_transcript None), the argv containment flags, the cgroup
    gating (caps emitted iff enforceable), the timeout force-remove, the
    stdout/stderr separation, the teardown-leak hard error, the triage branches,
    the footprint prefix-filter, the additivity (no-lane unchanged), the producer
    threading -- or do any pass WITHOUT exercising the behavior they name? Are the
    real-podman regressions correctly skipif-guarded (no false green)?

=== docs/proposals/.../podman-spike/spike-result.json (GREEN; for reference) ===
{SPIKE}

=== ai_router/podman_sandbox.py (NET-NEW this session; full content) ===
{SANDBOX}

=== ai_router/podman/Containerfile (NET-NEW this session) ===
{CONTAINERFILE}

=== ai_router/evidence_protocol.py (Session 1, VERIFIED; included for reference) ===
{EVIDENCE}

=== STAGED DIFF (pull_verifier.py, pull_critique.py, router-config.yaml, doc, tests) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=85,
        session_set=str(HERE),
        session_number=4,
    )
    out = HERE / "s4-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
