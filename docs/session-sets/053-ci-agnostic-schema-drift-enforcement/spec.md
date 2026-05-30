# CI-Agnostic, AI-Agnostic Schema-Drift Enforcement Spec

> **STUB — audit-then-spec. Not started.** This spec captures scope and
> open questions; the S1 audit (cross-provider consensus) locks the
> design before implementation.
>
> **Purpose:** Set 050 shipped a schema-drift guard, but its automatic
> trigger is a **Claude Code `SessionStart` hook** — so it protects only
> Claude Code users. Most staff use **GitHub Copilot**, which has **no
> executable session-start hook** (only instruction files). And consumer
> repos may host on **Azure DevOps**, not GitHub — so the enforcement
> cannot be GitHub-Actions-specific either. This set re-anchors the guard
> on **CI-agnostic, host-agnostic, AI-agnostic** triggers so a stale
> `schemaVersion` write is caught no matter who writes it (Copilot,
> Claude, a human), where the repo is hosted (Azure DevOps, GitHub,
> GitLab, …), and which CI runs it.
>
> **Created:** 2026-05-29
> **Session Set:** `docs/session-sets/053-ci-agnostic-schema-drift-enforcement/`
> **Prerequisite:** Set 050 (shipped — provides the `check_migrations`
> CLI + pure-JS scan this set re-triggers).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
```

> Rationale: CI wrappers, git hooks, a hook-installer command, instruction
> templates, and writer-path hardening — no browser-visible UI behavior.
> Coverage is unit tests + the existing Python/TS suites + (for any
> extension command) Layer-3 Playwright. If S1 finds the work grows a
> rendered surface, the implementing session re-evaluates a `"suggested"`
> UAT flag.

---

## Project Overview

### Motivation (operator-driven, 2026-05-29)

Set 050's guard fires from `~/.claude/settings.json` →
`claude-session-start-invoker.js`. That is the **only automatic trigger**,
and it exists **only for Claude Code**. Operator reality: *most staff use
GitHub Copilot.* Copilot has no shell-level session-start hook — its only
levers are instruction files (`.github/copilot-instructions.md`,
`AGENTS.md`), which can merely *ask* the agent to run the check. That is
exactly the unreliable "AI remembers to do it" pattern Set 050 was built
to escape. So today, **Copilot users get zero automatic drift protection.**

Second constraint (operator, 2026-05-29): consumer repos may live on
**Azure DevOps**, not GitHub. The enforcement therefore must be
**CI-agnostic** — not a bespoke GitHub Action.

### Key insight — the enforcement primitive is already agnostic

The guard is `python -m ai_router.check_migrations` — a plain CLI that
exits non-zero on drift — plus the standalone pure-JS scan. Both run
identically on Azure Pipelines, GitHub Actions, GitLab CI, a git hook, a
`make` target, or a human shell. **Only the trigger is platform-specific,
and the trigger is a few lines of wrapper.** The design discipline: keep
all logic in the CLI; ship thin per-host wrappers, never platform-bound
logic.

### Cross-provider input already on record (S1 must weigh, not assume)

Two providers were consulted at stub time (2026-05-29) and **they
disagree on the centerpiece** — S1 must resolve this, not assume it.

**GPT-5.4** ranked: (1) CI required-for-merge check as the non-bypassable
backstop; (2) git pre-commit/pre-push hook for early local feedback;
(3) `AGENTS.md` / `copilot-instructions.md` **advisory only** (rated
`insufficient_alone` — instruction files create false confidence and are
not enforceable); (4) optional pre-push hook for tooling/bot commits that
skip commit hooks; (5) **writer-path hardening** (stamp `schemaVersion`
from a code constant) as the deepest fix — host-agnostic, AI-agnostic,
trigger-free.

**Gemini-2.5-pro (devil's advocate)** rated the plan `needs_rework` and
**directly challenged making writer-path hardening the centerpiece**:
"it provides a false sense of security — the problem explicitly includes
AI and humans HAND-EDITING files, which completely bypasses the hardened
code paths. The true centerpiece must be the CI gate, the only layer that
can catch a violation regardless of source. Writer-path work is essential
housekeeping, not the strategic core." Its strongest objection: the
**"new/changed files" detection in CI is brittle** (git history, rebase,
squash merges, merge commits) and the plan hand-waves it — the single
most likely failure point.

**Synthesis for S1 (provisional, not locked):** the two views reconcile
as *coverage* vs *depth*. The **CI gate is the only non-bypassable layer
that catches hand-edits** (Copilot/human editing JSON in the editor never
touches code paths), so it is the true backstop. **Writer-path hardening
closes the code-path vector** (the orchestrator's own writes) but cannot
see a hand-edit. Hooks give early local catch. The honest framing: **CI
is the centerpiece for coverage; writer-hardening is necessary but
insufficient alone.** This stub's "centerpiece" label on writer-hardening
(below) is therefore demoted to a candidate — S1 locks the real priority.

### What this set delivers (subject to S1 lock)

1. **CI-agnostic gate (coverage backstop — the true centerpiece per the
   tension above), thin per-host wrappers.** The only layer that catches
   a violation *regardless of source*, including human/Copilot
   hand-edits. A canonical "run `check_migrations`, fail on non-zero"
   recipe with ready snippets for **Azure Pipelines**
   (`azure-pipelines.yml` step) **and** GitHub Actions, plus a generic
   recipe for any other system. Documented "required-for-merge" mapping:
   Azure DevOps **branch policy → build validation** ≡ GitHub **required
   status check** — noting (per Gemini) that enabling it is a **manual
   out-of-band UI step**, not just YAML. Gemini's strongest objection —
   **new/changed-file detection is brittle** under rebase/squash/merge —
   is a load-bearing S1 question (Q7), not a settled detail.
2. **Writer-path hardening (necessary, not sufficient).** Every code
   path that writes `session-state.json` stamps the canonical
   `schemaVersion` from the `SESSION_STATE_SCHEMA_VERSION` constant —
   never from a prompt or template. Closes the *code-path* vector (the
   orchestrator's own writes) but cannot see a hand-edit, which is why
   it is not the sole guard. (Audit confirms which writers already do
   this and closes gaps; presentation of an existing constant, not new
   schema logic.)
3. **Host-agnostic git hooks.** A repo-committed pre-commit (and
   optional pre-push) hook that runs the scan and blocks a stale write
   before it lands. Git hooks are host-independent — identical on Azure
   Repos, GitHub, GitLab. Plus a portable installer (a setup script
   and/or an extension command) since hooks aren't auto-enabled on
   clone.
4. **AGENTS.md / copilot-instructions advisory layer.** A reworded note
   — "never hand-edit `schemaVersion`; run the check/fix command" —
   added to the narration-template regeneration
   (`regenerateNarrationTemplates.ts`) so it ships to consumers.
   Explicitly the *weakest* layer, documented as such.
5. **Consumer rollout doc** extending
   `cross-repo-migration-guard-notice.md` with the CI-agnostic +
   Azure-DevOps install paths.

### Non-goals

- **Not GitHub-specific.** No solution that only works on GitHub
  Actions. Azure DevOps is a first-class target.
- **Not a removal of the Claude Code hook.** The Set 050 SessionStart
  trigger stays as *one* trigger among many — additive, not replaced.
- **No silent auto-migration.** Enforcement detects/blocks/instructs;
  migration stays operator-invoked, `.bak`-backed, reversible (Set 050
  non-goal carried forward).
- **No new migrator logic** and **no change to schema metering** beyond
  ensuring writers stamp from the constant.
- **No automated provider-pricing or unrelated CI** — scope is the
  drift guard only.

---

## Open design questions (S1 audit — cross-provider consensus)

1. **Layer priority & which to ship.** CI required-check + pre-commit +
   advisory + writer-hardening — all four, or a subset? Is writer-path
   hardening sufficient on its own to demote the others to belt-and-
   suspenders?
2. **Hook installation & bypass.** How are git hooks enabled per clone
   (setup script, `core.hooksPath` committed dir, husky-style, or an
   extension command)? How to handle `--no-verify` bypass and
   tooling/bot commits — pre-push too? Is CI the only truly
   non-bypassable layer (and therefore mandatory)?
3. **CI wrapper packaging.** Ship copy-paste snippets only, or a
   committed `azure-pipelines.yml` / `.github/workflows/*` template, or
   a single script (`scripts/check-schema.sh`/`.ps1`) the CI just
   invokes? Windows-shell vs POSIX (operator is on Windows;
   cross-platform matters).
4. **Writer-path audit scope.** Which writers stamp `schemaVersion`
   from the constant today vs. from a literal/template? (Set 050 already
   pins the JS invoker constant via CI; this asks the same of every
   state writer.) Any consumer-side hand-author path that can't be
   reached by code?
5. **AGENTS.md wording & distribution.** Exact advisory text; whether
   `regenerateNarrationTemplates.ts` is the distribution mechanism;
   whether `.github/copilot-instructions.md` is generated too.
6. **Scope of "required-for-merge" guidance.** Do we document/recommend
   protected-branch policies (Azure build validation / GitHub required
   checks), or only provide the failing command and leave policy to each
   repo's admins?
7. **Repo-wide vs. changed-files scan — and its brittleness (Gemini's
   strongest objection).** Should CI fail on ANY sub-current set in the
   repo, or only files touched by the PR? (Set 050's "old schema is
   acceptable" non-goal complicates a repo-wide fail — reconcile: enforce
   on NEW/CHANGED writes, not pre-existing intentionally-old sets.) But
   "changed files" detection is **notoriously brittle** — sensitive to
   git history, rebase, squash merges, and merge commits where git
   presents a file state that existed on no branch. How is the diff base
   discovered reliably on Azure (`System.PullRequest.TargetBranch`) vs
   GitHub? Is the brittleness cost high enough to reconsider Q11?

The following were added from the stub-time devil's-advocate pass
(Gemini-2.5-pro, 2026-05-29):

8. **Centerpiece: CI vs writer-hardening.** Resolve the provider
   disagreement (see Motivation). Is writer-path hardening "false
   security" because hand-edits bypass it, making CI the only real
   guard — or do the layers compose such that each is load-bearing?
9. **A `--fix` / fixer for DX.** A dev who hits a CI failure should not
   hand-edit JSON. Should `check_migrations` (or a sibling) gain a
   `--fix` that runs the existing migrator chain (`.bak`-backed) on the
   offending files? Reconcile against the Set 050 non-goal "no silent
   auto-migration" — an *operator-invoked* `--fix` is not silent, but the
   boundary needs a clear line.
10. **Reader-shim resilience & test matrix.** When a bad write slips
    through, does `normalize_to_v4_shape` fail gracefully, throw a clear
    error, or silently corrupt? Full test matrix across every supported
    old version + malformed/mismatched input. Should `check_migrations`
    validate that JSON **content conforms** to the declared
    `schemaVersion`, not just compare the version number?
11. **Challenge the "old schema acceptable" non-goal itself.** What is
    the true cost of a one-time forced migration sweep vs. the ongoing
    complexity/fragility of a "changed-files-only" detector? (If a sweep
    is cheap, much of Q7's brittleness evaporates.) How does the check
    differentiate a pre-existing *valid* v3 file from a *newly
    mis-authored* v3 file — by `git diff` alone, or another signal?
12. **Escape hatch for intentional older schema.** Is there a legitimate
    case for committing an older-schema file (test fixtures,
    backward-compat)? If so the gate needs an opt-out marker; if not,
    document that none exists.
13. **Azure DevOps wrapper specifics.** Beyond the YAML step: explicit
    Python-setup + pip-install on the build agent; PR error reporting via
    `##vso[task.logissue type=error;]` (surface on the PR overview, not
    just an exit code); target-branch discovery for the diff; and the
    fact that build-validation enablement is a manual Branch-Policy UI
    step the rollout doc must spell out.

---

## Sessions (provisional — S1 may reshape)

### Session 1 of 3: Audit & design-lock

**Steps:**
1. Register the set; inventory every `session-state.json` writer
   (Python + TS) and whether each stamps `schemaVersion` from the
   constant; inventory the Set 050 trigger surface, the
   `regenerateNarrationTemplates.ts` template path, and the existing
   `cross-repo-migration-guard-notice.md`.
2. Cross-provider consensus on the seven open questions (layer priority,
   bypass posture, CI packaging, writer-audit scope, and the
   changed-vs-repo-wide reconciliation are load-bearing).
3. Lock the layer set, the CI-agnostic packaging shape, the writer-
   hardening scope, and S2/S3 scope.

**Creates:** `docs/proposals/2026-05-XX-ci-agnostic-drift-enforcement/proposal.md` + verdict.
**Touches:** this `spec.md`.
**Ends with:** locked design; S2/S3 scope confirmed.
**Progress keys:** S1 verdict committed; design locked.

### Session 2 of 3: Implementation

**Steps:**
1. Writer-path hardening: close any writer that doesn't stamp from the
   constant; add a static-analysis/convention test pinning it.
2. Host-agnostic git hooks + portable installer; `--no-verify`/pre-push
   handling per S1.
3. CI-agnostic gate: canonical script + Azure Pipelines & GitHub Actions
   snippets/templates per S1; changed-vs-repo-wide behavior per Q7.
4. AGENTS.md / copilot-instructions advisory via the regeneration
   command.
5. Tests: writer-stamp convention test, hook-script unit tests, CI-script
   exit-code tests, regeneration-template assertions.

**Creates:** hook scripts, CI templates/snippets, installer code, tests.
**Touches:** state writers, `regenerateNarrationTemplates.ts`,
`package.json` (if a command is added), CHANGELOG.
**Ends with:** a stale `schemaVersion` write is blocked at commit (hook),
fails CI on Azure *and* GitHub (wrapper), and cannot originate from a
hardened writer; advisory shipped.
**Progress keys:** writer-hardening + hooks + CI wrappers + advisory shipped + tested.

### Session 3 of 3: Consumer rollout, docs, close-out

**Steps:**
1. Extend `cross-repo-migration-guard-notice.md` with the CI-agnostic +
   Azure-DevOps install paths and the writer-hardening note.
2. Update `ai-led-session-workflow.md` to describe the multi-trigger
   guard (not Claude-hook-only).
3. Version bumps (PyPI if `ai_router` writers changed; Marketplace if the
   extension changed), CHANGELOG, CLAUDE.md walk, change-log.md.
4. Cross-provider verification; close-out; publishes **held** for
   operator-initiated tag-push.

**Creates:** `change-log.md`.
**Touches:** docs, `pyproject.toml`/`package.json`, `CHANGELOG.md`, `CLAUDE.md`.
**Ends with:** consumers have an Azure-or-GitHub install path; docs
reconciled; versions bumped; publishes queued.
**Progress keys:** rollout doc shipped; versions bumped; close-out verdict recorded.

---

## End-of-set deliverables

- Writer-path hardening (every state writer stamps `schemaVersion` from
  the code constant) + a convention test.
- Host-agnostic git pre-commit (+ optional pre-push) hook and a portable
  installer.
- CI-agnostic enforcement: canonical script + Azure Pipelines & GitHub
  Actions wrappers + generic recipe; documented required-for-merge
  mapping (Azure build validation ≡ GitHub required check).
- AGENTS.md / `.github/copilot-instructions.md` advisory note (explicitly
  the weakest layer) shipped via the regeneration command.
- Extended `cross-repo-migration-guard-notice.md` (Azure + GitHub paths).
- Version bumps + CHANGELOG + change-log; publishes held for operator.
