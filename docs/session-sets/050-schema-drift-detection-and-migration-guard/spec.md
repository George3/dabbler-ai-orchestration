# Session-Set Currency & Addressing Spec (Schema-Drift Guard + Number-Prefix Convention)

> **Purpose:** Two related improvements to session-set hygiene across all
> consumer repos.
>
> **Feature 1 — Schema-drift guard.** Replace the unreliable "the
> orchestrator remembers to fetch the canonical schema from GitHub"
> pattern with a deterministic, code-driven guard. At session-set start a
> `SessionStart` hook scans every local `session-state.json`, detects any
> whose `schemaVersion` is behind the current canonical version, and —
> when drift is found — surfaces the authoritative migration instructions
> (resolved from a GitHub-published manifest so it works even when the
> locally installed router is stale). The orchestrator can no longer skip
> the check.
>
> **Feature 2 — Number-prefix addressing.** Standardize a monotonic
> `NNN-` prefix on session-set slugs (the convention this repo already
> follows) across consumer repos, and add a number→slug resolver so an
> operator can refer to a set as "Set 50" instead of typing the full
> slug. Forward-only: new sets get prefixes; existing dirs are not
> mass-renamed.
>
> **Created:** 2026-05-29
> **Session Set:** `docs/session-sets/050-schema-drift-detection-and-migration-guard/`
> (Note: the slug under-describes the broadened scope — itself a small
> illustration of why number handles beat long descriptive slugs. Kept
> as-is to avoid the rename churn this set is partly about avoiding.)
> **Prerequisite:** None
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
# prerequisites: none — this set is self-contained shared infra.
```

> Rationale: This is tooling/infra (a `SessionStart` hook template, a new
> `ai_router` CLI, a small canonical JSON manifest, and a consumer-repo
> rollout doc). No browser-visible behavior and no UI contract change, so
> `requiresUAT`/`requiresE2E` stay `false`. The extension may gain a
> "regenerate/install migration-guard hook" affordance reusing the
> existing template-regeneration command; if that surface grows beyond a
> trivial command wiring, the implementing session re-evaluates whether a
> `"suggested"` UAT flag is warranted (decided at S1 audit).

---

## Project Overview

### Motivation — Feature 1 (the incident that triggered this set)

`dabbler-access-harvester` produced two session sets
(`harvester-cli-distribution`, `harvester-manifest-index-and-batch-readiness`)
stamped `"schemaVersion": 2` on 2026-05-29, while the 45 sets authored
before them were all `v4`. Root cause: the harvester has **no
`SessionStart` hook** and an **ancient pinned router (0.1.1)**, so its AI
orchestrator hand-authors `session-state.json`. It writes the current
shape only when it actively fetches the canonical
`docs/session-state-schema.md` (a *GitHub blob URL* in its `CLAUDE.md`).
On 2026-05-29 the orchestrator wrote from stale memory instead and
regressed to `v2`. The Session Set Explorer then flags both as
"needs migration."

The lesson (recorded across multiple memories): **relying on AI memory
or on the AI remembering to fetch a URL is flaky.** The fix is to move
detection into a mechanical hook and to make "what is the current
schema, and how do I migrate to it" resolvable from an authoritative,
fetchable source rather than from the orchestrator's recollection.

> **Already done (2026-05-29, ahead of this set):** the two harvester
> files were migrated to v4 (lossless), the harvester router pin raised
> to `>=0.10.0` + venv upgraded, and the harvester `CLAUDE.md` gained the
> inlined `"schemaVersion": 4` stamp rule + raw-URL swap. So the
> *immediate* harvester unblock is complete; this set generalizes the
> prevention into shared infra and installs the hook there.

### Motivation — Feature 2 (number-prefix addressing)

This repo already prefixes its session sets `NNN-` (`047-…`, `048-…`,
`050-…`), but the consumer repos do **not** — harvester slugs are bare
descriptive names (`harvester-cli-distribution`, `vba-symbol-db`). Two
problems follow: (a) referring to a set in conversation means typing or
copy-pasting a long slug — and "Copy Slug" was only wired in extension
v0.24.1, which is currently unpublished, so operators can't even click
it; (b) without a sequence prefix the Explorer sorts alphabetically, so
"what's the latest set" is not obvious. A monotonic number prefix plus a
"Set 50"→slug resolver fixes both. The authoring guide currently
*discourages* number prefixes — but that rule targets *semantic* names
(`phase-3-week-2`), not monotonic creation-order sequence numbers; the
guide needs to distinguish the two.

### What this set delivers

1. A **canonical, fetchable schema manifest** (`docs/schema-current.json`)
   published in this repo: the current schema version, the migration-guide
   URL, and the ordered migrator chain (each step's version range + the
   exact CLI to run).
2. A **deterministic detection CLI** — `python -m ai_router.check_migrations`
   — that scans `docs/session-sets/*/session-state.json`, compares each
   `schemaVersion` against a target, and reports drift with the exact
   remediation commands. Offline-capable (uses the installed router's
   knowledge) with an optional `--manifest-url` mode that consults the
   GitHub manifest so a *stale local router* still learns about a newer
   schema.
3. A **`SessionStart` hook template** that runs the check and injects its
   findings into the orchestrator's session context, plus a documented
   install path (via the extension's template-regeneration command and a
   copy-paste fallback) so consumer repos gain the guard.
4. **Consumer rollout**: a cross-repo notice, updated consumer `CLAUDE.md`
   guidance (raw URLs, inlined `schemaVersion` stamp), and the hook
   installed in the harvester as the first adopter.
5. **A `NNN-` slug-prefix convention** (Feature 2): an updated authoring
   guide that distinguishes monotonic sequence prefixes from discouraged
   semantic names, the per-repo sequencing rule, and the forward-only
   (no mass-rename) policy.
6. **A number→slug resolver** (Feature 2): the extension's trigger-phrase
   handling, copy-prompt commands, and Explorer accept a bare number
   ("50") as a handle that resolves to the full slug within the active
   repo; plus publishing the held v0.24.1 Copy-Slug fix.

### Non-goals

- **No silent auto-migration.** The guard *detects and instructs*; it
  never rewrites state files unattended. Migration remains an
  operator/orchestrator-invoked, `.bak`-backed, reversible action.
  **(S1-locked: `--apply` was CUT — `check_migrations` is detect-only; the
  bulk "Upgrade older session sets" action runs the two existing migrators
  in sequence.)**
- **Old schema is acceptable; no forced per-set migration (operator-directed
  2026-05-29).** A set that ran under an older schema may stay on it —
  the `normalize_to_v4_shape` reader shim already consumes v2/v3
  transparently, so there is no functional break. The Explorer must NOT
  nag per-row. Replace the intrusive `(needs migration)` row description
  with an **unobtrusive asterisk + hover tooltip** ("Ran under schema
  v\<N\>"). Upgrading is offered as a **single repo-level bulk action**
  (one "Upgrade older session sets" icon that runs the migrator chain
  across all sub-current sets at once), never as a per-row obligation.
- **No new migrator logic.** The v2→v3 and v3→v4 migrators already exist
  (`migrate_lightweight_to_canonical_v4`, `migrate_v3_to_v4`). This set
  *orchestrates and surfaces* them; it does not write a new transform.
- **Not a router-pin fixer.** Bumping each consumer's
  `dabbler-ai-router` pin and reinstalling is operator-run remediation,
  documented here but not automated by the hook.
- **No mass-rename of existing session sets (Feature 2).** The number
  prefix is forward-only. Retroactively renaming existing dirs would
  break `prerequisites:` slug references, each state file's
  `sessionSetName`, and git history. A backfill, if ever wanted, is a
  separate opt-in exercise — explicitly out of scope here.

---

## Open design questions (RESOLVED — S1 audit-locked 2026-05-29)

> **AUDIT-LOCKED.** All eleven questions were resolved by cross-provider
> consensus (devil's-advocate two-pass, `gemini-pro` + `gpt-5-4`) on
> 2026-05-29. The authoritative answers and rationale live in
> [`docs/proposals/2026-05-29-session-set-currency-and-addressing/verdict.md`](../../proposals/2026-05-29-session-set-currency-and-addressing/verdict.md).
> Eight of eleven dispositions changed from the draft. The load-bearing
> changes:
>
> - **The SessionStart drift scan is pure-JS (no `ai_router` dependency,
>   no network).** The incident repo had an *ancient router* with no
>   `check_migrations`; a Python-CLI-on-the-hot-path guard would have left
>   it unprotected. The scan reads `session-state.json` files and compares
>   to a **bundled current-version constant** kept == `SESSION_STATE_SCHEMA_VERSION`
>   by a CI test. `python -m ai_router.check_migrations` remains as the
>   richer CI/manual surface.
> - **The GitHub manifest is advisory and off the hot path** (cached,
>   fail-open, consulted only by `check_migrations --manifest-url` / a
>   future Explorer action) — never fetched at every session start. It is
>   **declarative** (symbolic migrator IDs + version ranges, NOT executable
>   shell strings). Source stays raw-on-`master` with release-coupling
>   discipline + a `manifest==constant` CI guard (frozen tag rejected — it
>   reintroduces stale-blindness).
> - **`--apply` is cut.** `check_migrations` is detect-only; bulk upgrade
>   runs the two existing migrators in sequence
>   (`migrate_lightweight_to_canonical_v4 --in-place` then
>   `migrate_v3_to_v4 --in-place`; idempotent; handles v2-needs-both).
> - **Feature 2 gains a minimal extension affordance** (a Command-Palette
>   number→slug quick-input command) in addition to the `ai_router`
>   resolver — not CLI-only.
> - **`NNN-` prefix is required for newly-created sets** (canonical repo +
>   any scaffolder) and recommended/forward-only for consumer repos.
> - **`requiresUAT` stays `false`** (Explorer change is a small render
>   tweak covered by Layer-3 Playwright).
>
> The questions below are preserved as the audit's input record.

These went to cross-provider consensus in Session 1 and the verdicts lock
the rest of the set:

1. **Source of "current version" truth.** Installed-router constant vs.
   GitHub manifest vs. both (manifest authoritative, router as offline
   fallback). Affects network-dependency posture.
2. **Network-failure posture.** When the hook cannot reach GitHub, does
   it fail open (warn, proceed on the router's local knowledge) or fail
   loud (block)? Default lean: fail open with a visible warning — a
   transient network blip must not block a session.
3. **Manifest schema & location.** Exact shape of `schema-current.json`;
   whether migrators are expressed as a version-range chain or a flat map;
   whether to pin consumers to a tag vs. `master`.
4. **Hook output contract.** What the hook prints into context — a terse
   "N sets need migration, run X" line vs. the full guide. Token budget
   matters (this runs every session start).
5. **Where the scan scope comes from.** Single workspace root vs. the
   extension's merged multi-root set list. The hook only sees its own
   repo; cross-root detection stays the Explorer's job.
6. **Extension surface.** Reuse the existing "Regenerate Narration
   Templates" command to also write the hook + `settings.json` stanza,
   vs. a dedicated command. Whether to re-evaluate the `requiresUAT`
   flag if this grows.
7. **`--apply` convenience.** Detect-only (locked non-goal) vs. an
   opt-in `--apply` that runs the migrator chain with confirmation.

Feature 2 (number-prefix addressing):

8. **Resolver matching rules.** How a bare "50" resolves: exact prefix
   match within the active repo; behavior on collision (two repos both
   have a Set 50 — resolver is per-repo so this only bites in a merged
   multi-root Explorer view); behavior on no-match / ambiguous partial.
9. **Surfaces the handle applies to.** Trigger phrase ("Start the next
   session of 50."), the copy-prompt commands, the Explorer — which of
   these accept a number, and whether the canonical trigger phrase
   wording changes.
10. **Authoring-guide reconciliation.** Exact wording that permits
    monotonic `NNN-` prefixes while keeping the ban on semantic
    date/phase names; whether the prefix is mandatory or recommended for
    consumer repos.
11. **Numbering authority per repo.** How a consumer repo discovers its
    next number (max existing prefix + 1) and whether `start_session` /
    the extension scaffolds it, vs. left to the orchestrator.

---

## Sessions

### Session 1 of 5: Audit & design-lock

**Steps:**
1. Register the set; read required-reading docs and the relevant memories
   (the harvester incident, the deferred drift-detector note, the
   router-cost restriction).
2. Inventory the existing pieces this set must compose: the extension's
   `needsMigration` detector (`fileSystem.ts`), the two migrator CLIs,
   `docs/v3-to-v4-rollback-procedure.md`, the consumer `CLAUDE.md`
   GitHub-URL pattern; for Feature 2, the trigger-phrase wording, the
   `dabbler.copy*Prompt` commands, the Explorer slug handling, and the
   authoring-guide slug-naming section.
3. Run cross-provider consensus (devil's-advocate two-pass default) on
   the eleven open design questions above (7 for Feature 1, 4 for
   Feature 2). Produce a `proposal.md` + verdict.
4. Lock the manifest schema, the hook output contract, the
   network-failure posture, the resolver matching rules, the
   authoring-guide wording, and the S2–S5 scope.

**Creates:** `docs/proposals/2026-05-29-session-set-currency-and-addressing/proposal.md`,
verdict + pass artifacts under the same dir.
**Touches:** this `spec.md` (scope-lock edits if the audit reshapes sessions).
**Ends with:** an audit-locked design; the open-questions list resolved
and recorded; S2–S5 scope confirmed.
**Progress keys:** S1 audit verdict committed; spec scope-locked.

---

### Session 2 of 5: Manifest + `check_migrations` CLI (detect-only)

**Steps:**
1. Add **declarative** `docs/schema-current.json` per the S1-locked schema
   (symbolic migrator IDs + version ranges; NO executable shell strings).
2. Implement `python -m ai_router.check_migrations` **(detect-only)**: scan
   `docs/session-sets/*/session-state.json`, derive each `schemaVersion`,
   compare against the local `SESSION_STATE_SCHEMA_VERSION` constant by
   default; **optional** `--manifest-url` advisory fetch (fail-open +
   cached) to learn of an upstream-newer schema; map symbolic migrator IDs
   to the local migrator CLIs for the remediation hint. Terse default;
   `--verbose`/`--json` for per-set detail. Exit non-zero on drift
   (configurable) for CI use. `--strict-manifest` flips advisory fetch to
   fail-loud.
3. Honor the fail-open posture from S1 for network errors (the manifest is
   advisory; never block).
4. Unit tests: clean repo, mixed v2/v3/v4, unreadable/corrupt state file,
   manifest success+failure, offline fallback, **`manifest.currentSchemaVersion
   == SESSION_STATE_SCHEMA_VERSION`**, **v2-needs-both-migrators sequence**.

**Creates:** `ai_router/check_migrations.py`, `docs/schema-current.json`,
test files.
**Touches:** `ai_router/__main__`/CLI registration as needed; CHANGELOG.
**Ends with:** `python -m ai_router.check_migrations` correctly reports
drift on a fixture mirroring the harvester (2 v2 among N v4); tests green.
**Progress keys:** CLI shipped; manifest published; tests pass.

---

### Session 3 of 5: Pure-JS hot-path drift scan + install path

**Steps:**
1. Author the **pure-JS drift-scan module** (no `ai_router` dependency, no
   network) that reads `docs/session-sets/*/session-state.json`, compares
   each `schemaVersion` to a **bundled current-version constant**, and
   formats the S1-locked terse output (one summary line; clean = silent).
   Wire it as a **chained step** in `scripts/claude-session-start-invoker.js`
   (orchestrator start-session, then drift scan — independent concerns).
2. Extend the existing `dabbler.installOrchestratorHook.claudeCode` command
   to write the chained step + `settings.json` stanza; provide a copy-paste
   fallback (the JS snippet + stanza) for repos not running the extension —
   works with **no router installed at all**.
3. Add a **CI test asserting the bundled JS constant ==
   `SESSION_STATE_SCHEMA_VERSION`** so the two sources of truth cannot
   drift. Handle no-router/stale-router gracefully (pure-JS scan still
   works; `check_migrations` absence is non-fatal).
4. Tests: JS scan logic (fixture state files), constant-equality CI test,
   extension command writes the expected files; Layer-appropriate coverage
   only if a rendered surface is added.

**Creates:** hook template file, install-path code, tests.
**Touches:** extension command registry / `package.json` (if a command is
added/extended), `ai-led-session-workflow.md` (document the guard at the
session-start step).
**Ends with:** installing the hook into a test repo causes drift to be
reported in the session context at start; uninstalled repos get a clear
copy-paste path.
**Progress keys:** hook template shipped; install path shipped + tested.

---

### Session 4 of 5: Number-prefix convention + number→slug resolver (Feature 2) + Explorer UX revision

> **Scope assignment (operator-directed 2026-05-29, post-S3 close-out):**
> the end-of-set **Explorer UX revision** deliverable — previously listed
> only under End-of-set deliverables with no session owner — lands here in
> **S4** (the natural fit; S4 already touches the extension). Added as
> Step 5 below.

**Steps:**
1. Update `docs/planning/session-set-authoring-guide.md` per the
   S1-locked wording: permit monotonic `NNN-` prefixes, keep the ban on
   semantic date/phase names, state the per-repo sequencing rule and the
   forward-only (no mass-rename) policy.
2. Implement the number→slug resolver in **two places** (S1-locked):
   (a) **load-bearing** — an `ai_router` resolver consumed by
   `start_session --session-set-dir <n>` plus a standalone
   `python -m ai_router.resolve_set <n>` / `--next`; (b) **minimal
   extension affordance** — a Command-Palette command taking a number via
   `showInputBox`, resolving to the slug and reusing existing copy logic.
   Exact integer-prefix match, leading-zeros normalized; collision → error
   naming both; no-match → list available prefixes (no fuzzy "nearest").
   The Explorer already shows the `NNN-` prefix, so no Explorer rebuild.
3. `next_session_set_number(scan_root)` returns the int **and** a
   zero-padded string (`width = max(3, widest existing prefix)`; `001` if
   none). No new "create set" command — the orchestrator calls the helper.
4. Tests: resolver match/collision/no-match unit tests; authoring-guide
   prose has no machine contract so no test, but add a convention-lint
   check if S1 calls for one. Layer-appropriate extension coverage.
5. **Explorer UX revision (operator-directed; assigned to S4 2026-05-29).**
   Per the End-of-set deliverables item and the operator non-goal
   ("Old schema is acceptable; no per-row nag"): replace the intrusive
   `(needs migration)` row description in `fileSystem.ts` needsMigration
   rendering with an **unobtrusive asterisk + hover tooltip** ("Ran under
   schema v\<N\>"). Add a single **Explorer title-bar icon** ("Upgrade
   older session sets", enabled only when sub-current sets exist) via an
   `ActionRegistry` entry + the view's title-bar `menus` contribution in
   `package.json`; the action runs the **corrected three-migrator bulk
   chain** (`migrate_session_state` → `migrate_lightweight_to_canonical_v4`
   → `migrate_v3_to_v4`, each `--in-place`/idempotent — the S2 empirical
   correction, NOT the verdict's two) across all sub-current sets at once,
   never as a per-row obligation. Layer-3 Playwright covers the rendered
   asterisk/tooltip + the title-bar-icon enabled/disabled states
   (`requiresUAT` stays `false` — small render tweak, S1-locked).

**Creates:** resolver module/tests.
**Touches:** `docs/planning/session-set-authoring-guide.md`, extension
trigger-phrase + copy-prompt command code, `fileSystem.ts` (needsMigration
rendering), `ActionRegistry`, `package.json` (resolver command + title-bar
`menus` contribution).
**Ends with:** "Set 50" resolves to the full slug in the targeted
surfaces; authoring guide reconciled; the `(needs migration)` row label is
replaced by the asterisk/tooltip; the "Upgrade older session sets"
title-bar icon runs the three-migrator chain across sub-current sets;
tests green.
**Progress keys:** authoring guide updated; resolver shipped + tested;
Explorer UX revision shipped (asterisk/tooltip + bulk-upgrade title-bar
icon).

---

### Session 5 of 5: Consumer rollout, docs, close-out

**Steps:**
1. Write `docs/cross-repo-migration-guard-notice.md` (paste-in for
   consumer `CLAUDE.md`): install the hook, raise the `>=0.10.0` pin
   (latest published; 0.11.0 is held), use **raw** GitHub URLs, inline
   the `"schemaVersion": <current>` stamp, and adopt the `NNN-` prefix
   for new sets.
2. Install the hook in the harvester as first adopter (the harvester's
   v2→v4 migration, pin bump, and `CLAUDE.md` stamp/raw-URL edits were
   already done 2026-05-29 ahead of this set — see Motivation). Apply
   the same to the other consumer repos as operator-scoped commits.
3. Publish the held v0.24.1 Copy-Slug fix as part of the release (note:
   `VSCE_PAT` was expired 2026-05-28 — confirm PAT freshness first).
4. Version bumps (PyPI `dabbler-ai-router` + Marketplace extension),
   CHANGELOG, CLAUDE.md version walk, change-log.md.
5. Cross-provider verification; close-out; publishes **held** for
   operator-initiated tag-push (per established release discipline).

**Creates:** `docs/cross-repo-migration-guard-notice.md`,
`change-log.md`.
**Touches:** `pyproject.toml`, `package.json`, `CHANGELOG.md`, `CLAUDE.md`,
consumer `CLAUDE.md` files (operator-scoped).
**Ends with:** every consumer re-scanned shows zero needs-migration; the
hook is installed in the harvester; "Set N" addressing works; consumer
notice published; versions bumped; publishes queued for operator.
**Progress keys:** rollout doc shipped; hook installed in harvester;
versions bumped; close-out verdict recorded.

---

## End-of-set deliverables

> Reflects the S1 audit-lock (see verdict.md). Items marked **[changed]**
> differ from the pre-audit draft.

- `docs/schema-current.json` — **declarative, advisory** schema manifest
  (symbolic migrator IDs; consulted off the hot path). **[changed]**
- `ai_router/check_migrations.py` + `python -m ai_router.check_migrations`
  — **detect-only**; default uses local constant; optional cached
  `--manifest-url` advisory fetch. **[changed]**
- **Pure-JS hot-path drift scan** (no router/network) chained into the
  existing `claude-session-start-invoker.js`, installed via the existing
  `installOrchestratorHook.claudeCode` command + copy-paste fallback; a CI
  test pins the bundled JS constant to `SESSION_STATE_SCHEMA_VERSION`.
  **[changed]**
- **Explorer UX revision (operator-directed; assigned to S4 Step 5
  on 2026-05-29):** replace the
  `(needs migration)` row description with an asterisk + "Ran under
  schema v\<N\>" tooltip, plus a single **Explorer title-bar icon**
  ("Upgrade older session sets", enabled only when sub-current sets
  exist) that runs the corrected three-migrator chain across all of
  them at once.
  (Touches `fileSystem.ts` needsMigration rendering + `ActionRegistry`
  + the view's title-bar `menus` contribution in `package.json`.)
- Number→slug resolver: `ai_router` resolver (start_session + standalone
  CLI) **plus** a minimal extension Command-Palette quick-input command.
  **[changed: two surfaces, not CLI-only]**
- Updated `docs/planning/session-set-authoring-guide.md` (NNN- prefix:
  **required for new sets**, recommended/forward-only for consumers).
- `docs/cross-repo-migration-guard-notice.md`.
- Updated `ai-led-session-workflow.md` (session-start guard step).
- Version bumps + CHANGELOG + change-log; v0.24.1 Copy-Slug fix published
  with the release; publishes held for operator.
- Hook installed in the harvester as first adopter (operator-scoped).
