# Proposal — CI-Agnostic, AI-Agnostic Schema-Drift Enforcement (Set 053 S1)

**Date:** 2026-05-29
**Author:** Claude Opus 4.8 (orchestrator)
**Status:** draft for cross-provider devil's-advocate consensus
**Spec:** [`../../session-sets/053-ci-agnostic-schema-drift-enforcement/spec.md`](../../session-sets/053-ci-agnostic-schema-drift-enforcement/spec.md)

## Problem recap

Set 050 shipped schema-drift **detection** (`check_migrations` CLI + a
pure-JS scan) but wired the only **automatic trigger** into a Claude Code
`SessionStart` hook. Most staff use **GitHub Copilot** (no executable
session-start hook — only instruction files); consumer repos may host on
**Azure DevOps**, not GitHub. So Copilot users get zero automatic
protection and the enforcement cannot be GitHub-specific.

## S1 inventory findings (empirical, this session)

These reshape several dispositions, so they lead:

1. **Writer-path hardening is ALREADY DONE.** Every Python writer
   (`register_session_start`, `_flip_state_to_closed`,
   `_not_started_payload`, `_backfill_payload`) stamps `schemaVersion`
   from the constant `SCHEMA_VERSION` (= `SCHEMA_VERSION_V4 = 4`,
   `progress.py:42`). Every TS writer (`synthesizeNotStartedState`,
   `ensureSessionStateFile`, `cancelSessionSet`, `restoreSessionSet`,
   `migrateOneSetV4`, `migrateOneSet`) stamps from the shared
   `progress.ts` constants. **No writer uses a bare literal or
   passes a stale value through.** → Writer-path hardening is not
   net-new protection; it collapses to a *convention test* pinning the
   already-correct behavior.
2. **The real residual failure vector is HAND-AUTHORING** — an
   orchestrator or human writing `session-state.json` directly without
   going through any writer (exactly the harvester incident). This
   bypasses every writer unconditionally. Only a **post-write check**
   (CI / git hook) can see it. → CI is the centerpiece; writer-hardening
   is necessary-already-satisfied, not the strategic core.
3. **`check_migrations` has no git/changed-files awareness** — it scans
   `docs/session-sets/*/session-state.json` repo-wide and reports
   drift/ahead/unreadable, exiting non-zero. A "changed-files only" mode
   is net-new and (per Gemini) brittle.
4. **AGENTS.md advisory vehicle** is `ai_router/narration.py`
   `_AGENTS_TEMPLATE` (+ `_CLAUDE_TEMPLATE`); the
   `regenerateNarrationTemplates` command shells to
   `python -m ai_router.narration --kind agents`. But it writes **per-set
   `narration-templates/` artifacts**, not the repo-root `AGENTS.md` /
   `.github/copilot-instructions.md` an agent actually reads — a
   distribution gap to close.
5. **Reader shim fails loud** on structural violations
   (`normalize_to_v4_shape` raises `SessionStateInvariantError`/`TypeError`),
   but is **permissive on the version *number*** — it does not validate
   that content conforms to the declared `schemaVersion` (Q10).

## Recommended dispositions (to be challenged)

### Q1/Q8 — Centerpiece & layer priority
**Recommend:** **CI gate is the centerpiece** (only source-agnostic,
non-bypassable catch — sees hand-edits). Ship four layers in priority
order: (1) CI required-check, (2) git pre-commit hook, (3) AGENTS.md /
copilot-instructions advisory, (4) writer-path **convention test**
(pins the already-done hardening; near-zero cost). Writer hardening is
*not* the centerpiece — the inventory shows it's already satisfied and
can't see the real vector.

### Q2 — Hook installation & bypass
**Recommend:** ship a committed `core.hooksPath` hooks dir + a one-line
enable step (`git config core.hooksPath .githooks`) in the setup script
and the extension's existing install command. Accept `--no-verify` is
bypassable — that's *why* CI is mandatory and the hook is "early
feedback," not the guarantee. Add a **pre-push** hook too (catches
tooling/bot commits that skip pre-commit).

### Q3 — CI wrapper packaging
**Recommend:** one canonical cross-platform script
(`scripts/check-schema.ps1` + `.sh`, or a `python -m ai_router.check_migrations`
call) that each CI just invokes, PLUS thin committed templates:
`azure-pipelines-schema-check.yml` and a GitHub Actions snippet, PLUS a
generic "run this, fail on non-zero" recipe. Logic stays in the CLI; the
YAML is a 5-line wrapper.

### Q4 — Writer-path audit scope
**Recommend:** **CLOSED by the inventory** — all writers already stamp
from the constant. Deliverable shrinks to a static-analysis/convention
test asserting no writer emits a `schemaVersion` literal, mirroring the
Set 050 invoker-constant CI guard.

### Q5 — AGENTS.md wording & distribution
**Recommend:** add a one-line advisory to `_AGENTS_TEMPLATE` and
`_CLAUDE_TEMPLATE` in `narration.py`: "Never hand-edit `schemaVersion`;
run `python -m ai_router.check_migrations` and the migrator chain." AND
close the distribution gap: emit/append to repo-root `AGENTS.md` +
`.github/copilot-instructions.md` (not just per-set artifacts) — exact
mechanism a Q for S2. Explicitly the weakest layer.

### Q6 — "Required-for-merge" guidance
**Recommend:** document + recommend protected-branch enforcement, with
the **manual** out-of-band steps spelled out: Azure DevOps **Branch
Policies → Build validation** ≡ GitHub **required status check**. We
provide the failing check; the repo admin wires the policy.

### Q7 — Repo-wide vs changed-files (+ brittleness)
**Recommend:** **repo-wide scan, but only fail on NEW drift** — reconcile
with Set 050's "old schema is acceptable" non-goal via a committed
**baseline allowlist** (`schema-drift-baseline.json` listing the sets
intentionally left on an old schema). CI fails if a set is sub-current
AND not in the baseline. This sidesteps the brittle git-diff approach
entirely (Gemini's strongest objection) while honoring the non-goal. A
new sub-current write isn't in the baseline → fails; pre-existing
intentional-old sets are listed → pass.

### Q9 — `--fix` / fixer for DX
**Recommend:** add `check_migrations --fix` that runs the existing
three-migrator chain (`.bak`-backed) on the offending sets. This is
**operator-invoked, reversible** — it does NOT violate Set 050's "no
*silent* auto-migration" non-goal (the gate never auto-runs it; the dev
chooses). Improves the CI-failure DX Gemini flagged.

### Q10 — Reader-shim resilience & content validation
**Recommend:** add an optional `check_migrations --validate-content` that
checks the JSON conforms to its declared `schemaVersion` (not just the
number), surfacing "stated v4 but missing sessions[]" drift the version
check misses. Scope the reader-shim test matrix as an S2 task. Keep
default behavior unchanged (number compare) to stay fast.

### Q11 — Challenge "old schema acceptable" vs one-time sweep
**Recommend:** **KEEP the non-goal** (operator-locked in Set 050). The
baseline-allowlist (Q7) gives us new-drift enforcement without forcing a
sweep, so the brittleness argument for a forced sweep weakens. Differentiation
of valid-old vs newly-mis-authored = baseline membership, not git-diff.

### Q12 — Escape hatch for intentional older schema
**Recommend:** the Q7 baseline allowlist **is** the escape hatch —
adding a set to it is the explicit, reviewed opt-out. No separate
mechanism.

### Q13 — Azure DevOps wrapper specifics
**Recommend:** the ADO template must (a) include explicit Python-setup +
`pip install dabbler-ai-router` steps, (b) emit
`##vso[task.logissue type=error;]...` so failures surface on the PR
overview, (c) document the manual Branch-Policy build-validation enable
step. No target-branch diffing needed — the baseline approach (Q7) makes
the check branch-independent.

## Net scope after dispositions (for S2/S3 lock)

- **S2:** CI check enhancements (`--fix`, baseline-allowlist mode,
  optional `--validate-content`); committed CI templates (Azure + GitHub
  + generic) + cross-platform wrapper script; git pre-commit + pre-push
  hooks + `core.hooksPath` installer; writer-convention test; AGENTS.md /
  copilot-instructions advisory in `narration.py` + repo-root
  distribution.
- **S3:** consumer rollout doc (Azure + GitHub paths), workflow-doc
  multi-trigger update, version bumps, close-out.

## Key tension for the panel

The inventory **demotes writer-hardening** (already done) and **elevates
the baseline-allowlist** as the mechanism that lets CI enforce new drift
without the brittle git-diff OR a forced migration sweep. Is the baseline
allowlist the right call, or does it add a maintenance burden (every
intentional-old set must be listed) worse than git-diff or a one-time
sweep? That's the load-bearing question for consensus.
