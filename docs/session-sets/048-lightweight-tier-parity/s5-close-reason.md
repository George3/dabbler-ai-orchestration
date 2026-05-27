# Set 048 Session 5 — Close-out reason and verification attestation

## Close-out reason

Session 5 is the UAT + close-out session of the audit-locked
Lightweight-tier parity arc. The audit-locked spec is at
[`spec.md`](spec.md). S5 exercises the surface end-to-end, ships
the 42-item UAT checklist as the canonical artifact, bumps versions
on both registries, and — the load-bearing distinct deliverable —
fixes a Critical bug discovered during UAT execution.

### The UAT-discovered Critical bug

Running the smoke test for the route()/verify() short-circuit under
simulated pip-install `sys.path` surfaced that the `--no-router`
mode shipped in S2 was a **silent no-op** for pip-installed
consumers (the entire Lightweight target audience). Five production-
code sites used bare imports of the new Set 048 modules:

  - `ai_router/__init__.py:317` — `route()` prologue
  - `ai_router/__init__.py:617` — `verify()` prologue
  - `ai_router/start_session.py:843` — `main()` entry
  - `ai_router/close_session.py:1644` — `run()` entry
  - `ai_router/runtime_mode.py:75` — `_spec_tier()`

Those bare forms (`from runtime_mode import …`) only resolved under
the test `conftest.py`'s `sys.path` shim. Pip-installed consumers
had no such shim:

  - `route()` and `verify()` raised `ModuleNotFoundError` outright on
    every call under `DABBLER_NO_ROUTER=1`.
  - `start_session.main()` and `close_session.run()` wrapped the
    bare import in `try/except: pass`, so `--no-router` was a silent
    no-op for the entire production CLI surface. A Lightweight
    consumer running `python -m ai_router.start_session --no-router
    …` would see no error AND no effect from the flag — every
    session would proceed as full-tier with live LLM calls.

The original S2 Round-A verifier flagged this as Major #2 and the
finding was dismissed as a false positive on conftest grounds.
**That dismissal was wrong.** The dismissal rationale ("matches
existing package convention via conftest.py") was technically
accurate for the test environment but ignored that production
consumers don't have the conftest shim. S5 fixes the bug, locks the
invariant out with a static-analysis test on an `ast.walk` of
`ai_router/**/*.py`, and records the pattern lesson:
**dismissing verifier findings as false positives without
empirically reproducing them is itself a risk pattern**. The bug
shape was empirically reproducible with a 5-line script; if anyone
had run it in S2, the dismissal would not have stood.

### What ships in S5 (3 commits)

- **A** (`58a8f35`) — UAT-discovered Critical bare-import fix. All
  5 production-code sites switched to relative imports
  (`from .runtime_mode import …`). New
  `test_no_bare_imports_of_set048_modules_in_production_code`
  static-analysis guard. `conftest.py` module-aliasing block makes
  the bare-name and package-qualified imports resolve to the same
  module object (necessary because `runtime_mode` carries
  module-level cache state). `test_runtime_mode.py` caplog filter
  updated from `logger="runtime_mode"` to
  `logger="ai_router.runtime_mode"` (matches the relative-import-
  resolved `__name__`).
- **B** (`5ad1baa`) — dual version bumps + UAT checklist + doc
  walks. `pyproject.toml` 0.9.0 -> 0.10.0;
  `tools/dabbler-ai-orchestration/package.json` 0.22.0 -> 0.23.0;
  `tools/dabbler-ai-orchestration/CHANGELOG.md` prepends a
  `[0.23.0] — 2026-05-27` section; `CLAUDE.md` `Current:` rewritten
  for v0.23.0, `Previous:` walked to v0.22.0 (Set 047), v0.21.0
  entry added to the prior-version walk;
  `048-lightweight-tier-parity-uat-checklist.json` ships the 42-item
  ad-hoc UAT in the Set-045 schema (Dabbler UAT-Checklist-Editor
  compatible). `.vsix` build sanity-check succeeded — 23 files,
  881.47 KB.
- **C** (`a24ab8a`) — cross-provider verification artifacts + all 3
  Round-A findings dispositioned in-flight.

## Cross-provider verification attestation

End-of-session cross-provider verification ran via
[`run_s5_verification.py`](run_s5_verification.py):

- **Route** — `gpt-5-4` (tier 3): `pass_with_findings`, 3 findings.
  Cost: $0.1806.
- **Verify-of-verify** — skipped. No cross-provider verifier
  configured for `gpt-5-4`. The route() call already used
  `task_type="session-verification"` cross-provider routing, so the
  route response IS the Round-A verdict.

**S5 routed cost: $0.1806** of $10 NTE.
**Cumulative Set 048 spend: $0.94** (S1 $0.103 + S2 $0.147 + S3
$0.161 + S4 $0.350 + S5 $0.181 = 9.4%).

### Round-A findings dispositioned in-flight

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | Static-analysis guard narrower than docstring claimed | Major | **FIXED** in-flight — rewritten on `ast.walk` over `ai_router/**/*.py` excluding tests/; rejects both `ImportFrom` (level==0, module in set) and `Import` (alias.name in set); 9 new scanner self-tests cover bare-from, indented-from, bare-import, import-alias, relative-accept, package-absolute-accept, unrelated-accept, subpackage walk, tests-dir exclusion |
| 2 | conftest aliasing is import-order sensitive | Minor | **FIXED** in-flight — defensive `RuntimeError` if `sys.modules[<bare>]` already exists and is a different object; fail-fast beats silent split-identity bug |
| 3 | UAT checklist covered §3.x + L3-L5 but not P1 | Minor | **FIXED** in-flight — 3 new UAT items (P1 parity Identification / State-file updates / Events ledger); Feedback documents the architectural invariant |

Verification artifacts persisted at:
- [s5-verification-prompt.md](s5-verification-prompt.md)
- [s5-verification-route.md](s5-verification-route.md) — full 3-finding catalog
- [s5-verification-verify.md](s5-verification-verify.md) (skip notice)
- [s5-verification-result.json](s5-verification-result.json)

## Test counts at close

- **Python:** 1020 passed + 1 skipped (was 1010 + 1 pre-S5; +1
  static-analysis invariant test + 9 scanner self-tests + 0
  regressions).
- **TypeScript (unit):** 665 passed + 2 pre-existing failures
  unchanged from S2/S3/S4 (`configEditor-foundation` panel-
  lifecycle + `notificationsSection` rendering — both predate
  Set 048).
- `.vsix` build sanity-check (`npx vsce package
  --allow-missing-repository`) succeeded — 23 files, 881.47 KB.
  Build artifact removed locally; canonical publish path is the
  GitHub Actions workflow.

## What ships in this commit

- `docs/session-sets/048-lightweight-tier-parity/activity-log.json`
  entries 1-8 for S5.
- `docs/session-sets/048-lightweight-tier-parity/change-log.md`
  Session 5 section + Set 048 cumulative summary.
- `docs/session-sets/048-lightweight-tier-parity/disposition.json`
  with status="completed" + the close-out summary + next-set
  pointer to Set 049 (still stubbed, awaiting its own S1 audit).
- `docs/session-sets/048-lightweight-tier-parity/s5-close-reason.md`
  (this file).

## Set 048 cumulative — what shipped across 5 sessions

End-to-end parity between the Full and Lightweight tiers per the
operator-locked premises P1-P4 (carry-forward from Set 047) and the
four new operator-locked additions L1-L4 + L5. The Lightweight tier
becomes a first-class peer to Full: same writers, same Explorer UX,
same `session-state.json` lifecycle. Differences from Full are
limited to (a) no AI router runtime calls, (b) no auto-verification,
(c) copyable review prompts in lieu of routed verification, (d)
suggested-not-required UAT/E2E.

Cumulative routed spend: **$0.94 of $10 NTE (9.4%)** across 5
sessions. Set 048 closes within budget.

Verifier-catch trend across S1 -> S5 confirmed
`feedback_split_large_verification_bundles` applied in practice:
single-route verifications stay cheap and catch most issues; the
multi-pass S1 audit caught the highest-severity issue (L1 violation
in proposals); the verifier dismissed as "false positive" in S2
turned out to be a real Critical bug that S5 had to fix. Recording
this as a memory hook: **dismissing verifier findings as false
positives without empirically reproducing them is itself a risk
pattern**.

## Next-session prerequisites

Set 048 closes. Next session is the first of Set 049
(`orchestrator-coordination-removal`), still stubbed at
[`docs/session-sets/049-orchestrator-coordination-removal/`](../049-orchestrator-coordination-removal/)
and awaiting its own S1 audit pass per the standard `feedback_audit_
then_spec_for_substantial_features` discipline.

Before Set 049 starts, **Set 048's publishes must ship**:

1. **PyPI `dabbler-ai-router 0.10.0`** — push tag `v0.10.0` to
   trigger the `release.yml` workflow (OIDC trusted publishing).
2. **Marketplace `dabbler-ai-orchestration 0.23.0`** — push tag
   `vsix-v0.23.0` to trigger the `publish-vscode.yml` workflow
   (Marketplace PAT from `AZURE_VSCODE_MARKETPLACE_TOKEN`).

Both publishes are operator-initiated per
`reference_publish_via_github_actions`. The Set 047 Marketplace
0.22.0 publish that was held failed on 2026-05-26 with
`/_apis/gallery` timeouts; the Set 048 0.23.0 supersedes it
(Marketplace consumers only see the latest artifact, so no separate
retry of 0.22.0 is needed).
