"""Set 069 S6 -- cross-provider session verification (Step 6, gated -> REQUIRED).

S6 is the FINAL session: synthesis docs + version bump + CHANGELOG + change-log +
PyPI release + dogfood + close. NO new product code (the capability code shipped
+ was verified in S1-S5). This verification checks the DOCS describe the as-built
code faithfully (L-064-8: a synthesis/replacement doc inherits stale claims at its
peril), that versions/claims are internally consistent (L-065-1: every echo), and
that the release contract is correct. routed_gate confirms REQUIRED (blast-radius
+ multi-module + breadth + build-config, 7 files). Orchestrator is Anthropic/opus;
the verifier routes to a different provider.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ai_router import route  # noqa: E402

TOTAL_PASS = 1953

DOC_FILES = [
    "ai_router/CHANGELOG.md",
    "ai_router/__init__.py",
    "ai_router/docs/pull-verifier.md",
    "docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md",
    "docs/verification-surface-strategy.md",
    "pyproject.toml",
    "docs/session-sets/069-automated-pull-critique-capabilities/change-log.md",
]
DIFF = subprocess.run(
    ["git", "diff", "--cached", "--", *DOC_FILES],
    cwd=str(REPO), capture_output=True, text=True,
).stdout

PROMPT = f"""\
You are the cross-provider session verifier for Session 6 of 6 (the FINAL
session) of Set 069 (automated pull-critique capabilities) in the
dabbler-ai-orchestration repo. Return the structured verdict.

=== CONVENTIONS / BASELINE (read first; do NOT re-flag the agreed baseline) ===
- The full ai_router pytest suite is GREEN at this commit ({TOTAL_PASS} passed, 5
  skipped). The 5 skips are the S4 real-podman cage regressions, which require a
  real podman + built image and skip on the Windows host BY DESIGN (they run on
  Linux CI / WSL). Do NOT flag the skips as a defect.
- THIS SESSION SHIPS NO NEW PRODUCT CODE. The capability code (evidence_protocol,
  the pull_critique execution lanes + get_diff, probe_templates, podman_sandbox,
  floor_ratchet, replacement_gate) all shipped AND was cross-provider VERIFIED in
  Sessions 1-5. You are NOT re-reviewing that code. The ONLY non-doc change is the
  version bump (0.22.1 -> 0.23.0 in __init__.py + pyproject.toml).
- RELEASE CONTRACT: ai_router is released to PyPI THIS session as 0.23.0 (a MINOR
  bump -- the set added net-new features, all additive/back-compat). NO Marketplace
  / extension change (spec non-goal: no UI surface this whole set).
- SCOPE OF THIS REVIEW (doc-synthesis session): the deliverables are the synthesis
  doc updates, the CHANGELOG 0.23.0 entry, the per-set change-log.md, the proposal
  status flip to BUILT, and the version bump. Your job is to confirm the PROSE
  describes the as-built code FAITHFULLY and is internally consistent -- NOT to
  find new code bugs (there is no new code).

=== GROUND TRUTH (the as-built behavior the docs must match; from the S1-S5
VERIFIED dispositions -- treat as authoritative) ===
- S1 evidence_protocol.py: tiers REPRODUCED / ASSERTED / HYPOTHESIS, default
  ASSERTED (additive). The ORCHESTRATOR applies the tag, never the agent.
  REPRODUCED requires a transcript with a trusted commandId XOR templateId (never
  model-authored argv), pristine-replay hash match, public-entrypoint meta-oracle.
  Set 066 validator enforces it (ARTIFACT_INVALID_EVIDENCE).
- S2: pull_critique gained trigger-only run_test execution (operator-authored
  command ids only, resolved via RunTestConfig.resolve_id) + a get_diff tool (raw
  unified diff, dispatched to git outside the byte-equality guard) + blast-radius-
  budgeted caps (budget_caps_for_paths: req/adv/none = 1.0/0.6/0.4x + floors).
  Additive: no config => byte-for-byte the read-only Set 067/068 loop.
- S3: probe_templates.py -- operator-authored versioned harnesses, model supplies
  only TYPED args; validate_template_args never raises. Seed library
  BUILTIN_PROBE_TEMPLATES drives ai_router's own public entrypoints. The dogfood
  found + fixed a LATENT UnicodeError-class bug in 4 readers of
  path_aware_critique.py (L-069-1).
- S4: podman_sandbox.py -- the model-authored-probe lane, GATED on a GREEN spike
  (6/6 acceptance criteria, podman 4.9.3). Container is the boundary
  (--network=none, read-only repo, tmpfs scratch, --cap-drop=ALL, crash-safe
  teardown, lane-labeled disk hygiene). Autonomous + severity-gated; AI safety
  check is TRIAGE-ONLY (reject/escalate, NEVER approve). CENTRAL SAFETY PROPERTY:
  a model-authored probe can NEVER mint REPRODUCED -> _build_transcript returns
  None for an authored execution, the finding is CAPPED AT HYPOTHESIS; only the S5
  ratchet promotes it.
- S5: floor_ratchet.py -- candidate falsifier (candidate-falsifiers.json) NEVER
  auto-merged; six mechanical gates + human-signoff to ADMIT; rubber-stamp guard.
  replacement_gate.py -- pre-registered seeded+holdout benchmark; verdict DERIVED
  not hand-asserted; underpowered forces meets=False; the MANUAL RUN IS NEVER
  RETIRED (strongest recommendation = reduce manual to a periodic backstop).
- Current version BEFORE this session: 0.22.1. After: 0.23.0. (0.22.0 shipped
  WITHOUT the Set 068 whole-set-critique fixes -- those rode in 0.22.1, an
  immutable-PyPI patch.)

=== THE CHECKS ===

A. FAITHFULNESS (L-064-8 -- the load-bearing check). Every claim of CURRENT
   behavior in the new prose (verification-surface-strategy.md S6, pull-verifier.md
   S5 section, the CHANGELOG 0.23.0 entry, the change-log.md, the proposal status
   header) must match the GROUND TRUTH above. Flag ANY overclaim or stale-inherited
   claim, especially:
   A.1 Does any doc say a model-authored Podman probe can mint REPRODUCED? It must
       NOT -- it caps at HYPOTHESIS. Confirm every mention is correct.
   A.2 Does any doc say the manual run is RETIRED / will be retired? It must NOT --
       never retired; the strongest move is reduce-to-periodic-backstop.
   A.3 Does any doc say the AI safety check can APPROVE? It must NOT -- triage-only
       (reject/escalate).
   A.4 Is the Podman spike described as GREEN (6/6, podman 4.9.3)? Confirm no doc
       describes the lane as pending/ungated or the spike as not-yet-run.
   A.5 Are the "additive / no behavioral change absent config" claims accurate?

B. VERSION + RELEASE CONSISTENCY (L-065-1 -- every echo).
   B.1 __init__.py __version__ and pyproject.toml version must BOTH be 0.23.0 and
       agree. (Set 068 S6 dogfood caught a version drift -- confirm none here.)
   B.2 The CHANGELOG 0.23.0 entry exists, is dated 2026-06-16, sits ABOVE 0.22.1,
       and its [Unreleased] section is empty/clean. Is 0.23.0 a defensible MINOR
       bump (additive features, no breaking change)?
   B.3 Do all docs that name the release version say 0.23.0 (not 0.22.x or 0.21.x)?
       Any stale version echo?

C. INTERNAL CONSISTENCY across the doc set. The strategy doc S6 section, the
   pull-verifier.md sections, the change-log.md, the CHANGELOG, and the proposal
   status must not contradict each other (module names, session->feature mapping,
   the spike outcome, the HYPOTHESIS-cap rule). Flag any contradiction.

D. COMPLETENESS. Does the change-log.md cover all six sessions with the correct
   per-session deliverable? Does the strategy doc S6 section + pull-verifier.md
   together describe ALL of S1-S5's shipped surface (evidence protocol; trusted-
   exec + get_diff; probe templates; podman lane; ratchet; replacement gate)? Name
   anything material that is missing or misattributed to the wrong session.

E. ACCURACY OF CROSS-REFERENCES. The new docs add relative links (proposal <->
   strategy doc <-> pull-verifier.md). Do the section names referenced actually
   exist (e.g. strategy-doc "Set 069 -- the execution-backed evidence layer")? Flag
   a dangling section reference or a wrong relative path you can detect from the
   diff.

F. ASCII / ENCODING. The docs are utf-8 files (arrows etc. are fine in .md). The
   CLI-output convention (ASCII-only) does NOT apply to doc prose. Do not flag
   utf-8 glyphs in markdown.

Return: verdict (VERIFIED or ISSUES_FOUND), a one-line summary, and -- for each
issue -- severity (Critical/Major/Minor), the file, the quoted offending claim,
and the correction. If clean, say so plainly; do not invent issues.

=== STAGED DIFF (all doc + version + changelog changes this session) ===
{DIFF}
"""


def main():
    r = route(
        PROMPT,
        task_type="session-verification",
        complexity_hint=70,
        session_set=str(HERE),
        session_number=6,
    )
    out = HERE / "s6-verification.md"
    out.write_text(r.content, encoding="utf-8")
    print(f"Wrote {out} ({len(r.content)} chars)")
    print(json.dumps({"model_used": getattr(r, "model_used", None),
                      "cost_usd": round(getattr(r, "cost_usd", 0.0) or 0.0, 6)},
                     indent=2))


if __name__ == "__main__":
    main()
