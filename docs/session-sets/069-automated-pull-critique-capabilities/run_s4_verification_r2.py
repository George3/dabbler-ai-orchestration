"""Set 069 S4 -- cross-provider verification ROUND 2 (re-verify the R1 fixes).

R1 (gpt-5-4) returned NEEDS_FIX with the CENTRAL SAFETY CLAIM = PASS and four
findings. All four are now fixed; this round re-verifies ONLY the fixes (and that
they introduced no regression), pinned to the verifier's own tier so a wording-
only short response cannot auto-escalate cross-provider (L-064-7).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

FILES = [
    "ai_router/podman_sandbox.py",
    "ai_router/podman/Containerfile",
    "ai_router/pull_verifier.py",
    "ai_router/docs/pull-verifier.md",
    "ai_router/tests/test_podman_sandbox.py",
]
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--", *FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

SANDBOX = (REPO / "ai_router/podman_sandbox.py").read_text(encoding="utf-8")

PROMPT = f"""\
You are the cross-provider session verifier for Session 4 of 6 of Set 069
(automated pull-critique capabilities). This is ROUND 2: re-verify ONLY the fixes
to your Round-1 findings. Round 1 returned NEEDS_FIX; the CENTRAL SAFETY CLAIM (a
model-authored Podman probe can never mint REPRODUCED; it caps at HYPOTHESIS) was
already PASS and is UNCHANGED. The full ai_router suite is GREEN (1856 passed / 5
skipped; the 4 skips are the real-podman regressions that skip on the Windows
host, by design). NO release this session (S6). Return the structured verdict.

Confirm each Round-1 finding is resolved (cite file:line); flag ONLY a NEW defect
introduced by a fix, not the agreed baseline.

R1 FINDING 1 -> Base image not digest-pinned / digest story aspirational.
  FIX: the digest pin is deliberately an operator/arch DEPLOY step (not hard-coded
  in a portable template); the REAL enforcement is now at RUNTIME -
  _dispatch_run_authored_probe prepends a "NOTE: cage image ... is NOT
  digest-pinned (dev/CI only)..." to the tool result whenever
  image_is_digest_pinned(image) is False, so an un-pinned production run is VISIBLE
  not silent. The Containerfile comment + the doc now state the checked-in image is
  a tag (dev/CI) and production must pin both base and runtime ref. Confirm the
  runtime NOTE fires for an un-pinned ref and the doc no longer claims pinning is
  already done. (Is making un-pinned VISIBLE-at-runtime + an operator deploy step a
  defensible resolution for a portable template, vs hard-coding an arch-specific
  digest? If you still consider a hard-coded base digest mandatory, say why.)

R1 FINDING 2 -> Footprint not lane-local on a shared host (containers by prefix,
  volumes/images global).
  FIX: every container now carries a queryable lane LABEL (LANE_LABEL =
  "pull-probe-lane", added in _build_argv); podman_footprint() now filters BOTH
  `podman ps` and `podman volume ls` by `--filter label=pull-probe-lane`, so a
  co-tenant's containers/volumes are never miscounted; the brittle global
  image-COUNT comparison is replaced by `podman image exists <configured ref>`
  (image_present) - the lane never builds an image at runtime, so the meaningful
  assertion is "the reused image is present", not a global count. Confirm the
  footprint is now genuinely lane-local and sound on a shared host.

R1 FINDING 3 -> replay_matched=False still rendered "reproduced the same output".
  FIX: the rendered text is now conditional on replay_matched (re-runnable vs
  "did NOT reproduce ... flaky / non-deterministic"). Confirm the message is
  correct for BOTH branches and the tier is still HYPOTHESIS regardless.

R1 FINDING 4 -> No direct test of build_probe_argv's -B / no -I / no -E contract.
  FIX: test_build_probe_argv_contract asserts argv == ("python","-B","-c",body)
  and that "-I"/"-E" are absent; test_build_argv_carries_lane_label asserts the
  label is on the podman argv. Confirm these tests exercise the contract.

Also confirm NO regression: the HYPOTHESIS cap, additivity (no PodmanLaneConfig =
unchanged), the triage-only check, and the spike's three carried findings are all
still intact after these edits.

=== ai_router/podman_sandbox.py (full current content) ===
{SANDBOX}

=== STAGED DIFF since R1 (podman_sandbox.py, Containerfile, pull_verifier.py, doc, tests) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=70,
        max_tier=3,
        session_set=str(HERE),
        session_number=4,
    )
    out = HERE / "s4-verification-round-2.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
