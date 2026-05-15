# Set 024: remove-provider-queues-and-heartbeats-views — Change Log

**Sessions:** 1 of 1 completed (2026-05-15)
**Orchestrator:** Anthropic / Claude Opus 4.7 (1M context) — single session
**Cumulative routed cost:** $0.1394 — Session 1 verification only
(gpt-5-4, task_type=`session-verification`)

---

## What Set 024 delivers

Set 024 removes the Provider Queues and Provider Heartbeats tree views
from the Dabbler AI Orchestration extension. These views were
scaffolding for the `outsourceMode: last` (subscription-CLI verifier
daemon) workflow. No session set in this repo has ever declared
`outsourceMode: last` — every set is outsource-first — and the views
were rendering a persistent yellow warning triangle ("Failed to read
queue status. queue_status exited 1 …") because there is no
`provider-queues/` directory on disk for them to read. That UX was
strictly worse than no view at all. The operator confirmed full
removal (option A) over hide-behind-setting (option B) and
remove-outsource-last-end-to-end (option C) in the 2026-05-15 scoping
dialog.

After this set ships (extension v0.13.14), the Dabbler activity-bar
icon surfaces only the Session Sets view; Settings → Extensions
→ Dabbler AI Orchestration lists four contributed settings (down from
ten); and the persistent warning triangle is gone by construction —
the views that used to surface it are no longer registered.

### The Python CLI surface stays

`python -m ai_router.queue_status` and `python -m ai_router.heartbeat_status`
remain available in the Python package, and `ai_router/docs/two-cli-workflow.md`
still documents the outsource-last operating procedure end-to-end.
Operators who run outsource-last in *other* repos can still invoke
the CLIs from a terminal — what's gone is only the extension-side UI
that was unique to this repo's outsource-first reality.

The shared `dabblerSessionSetsContainer` activity-bar container also
stays: the Session Sets view still uses it. Removing only the two
views (not the container or the Python CLIs) is the minimal change
that fixes the operator-visible UX problem.

### Session 1 — Strip the two views + their settings (released as extension v0.13.14)

**Source deletions (6 files, ~1,735 LOC):**

- `src/providers/ProviderQueuesProvider.ts` (481 LOC)
- `src/providers/ProviderHeartbeatsProvider.ts` (437 LOC)
- `src/commands/queueActions.ts` (210 LOC)
- `src/test/suite/providerQueues.test.ts` (240 LOC)
- `src/test/suite/providerHeartbeats.test.ts` (274 LOC)
- `src/utils/pythonRunner.ts` (93 LOC) — confirmed dead via Grep
  after the providers and `queueActions` (its only callers in `src/`)
  were removed. Per the spec's "Keep generic helpers used by other
  commands" wording, no remaining commands use it, so it goes.

**`package.json`:** two `views` entries, five `commands`, four
`menus` entries (2 `view/title` + 2 `view/item/context`), and six
`configuration.properties` (queues: `autoRefreshSeconds`, `pythonPath`,
`messageLimit`; heartbeats: `autoRefreshSeconds`, `lookbackMinutes`,
`silentWarningMinutes`) removed. The `dabblerSessionSets.pythonPath`
description loses its "Falls back to `dabblerProviderQueues.pythonPath`
if unset" clause; the setting itself stays.

**`extension.ts`:** three imports stripped (`ProviderQueuesProvider`,
`ProviderHeartbeatsProvider` + `HEARTBEAT_FOOTER`,
`registerQueueActionCommands`); both view-registration blocks gone
(`createTreeView`, the `setInterval` auto-refresh wiring, the
`onDidChangeConfiguration` listeners, and the `registerQueueActionCommands`
call). Net: ~105 lines removed.

**`installAiRouterCommands.ts`:** `resolvePythonPath()`'s fallback
chain simplified from
`dabblerSessionSets.pythonPath → dabblerProviderQueues.pythonPath → "python"`
to `dabblerSessionSets.pythonPath → "python"`, since the middle key
no longer exists in the schema. The CHANGELOG's `### Migration`
subsection documents the rename path for operators who had been using
the old key to point the install command at a venv.

**`installAiRouter.test.ts`:** import block for the deleted provider
modules removed, file truncated at line 1025 to drop the five
provider-related suites (parseFetchResult, failure-invalidates-cache,
tree-item-rendering — each for both providers). 35 install-only
suites remain; isolated mocha run (`npx mocha --ui tdd --require
ts-node/register src/test/suite/installAiRouter.test.ts`) shows 35/35
passing.

**`aiRouterInstall.ts`:** stale JSDoc reference to `runPythonModule`
trimmed (was "…mirroring the pattern in `runPythonModule` so the
UI…", now "…so the UI…").

**Version bump:** `0.13.13` → `0.13.14` in `package.json`,
`package-lock.json` (top-level + root package node), `CHANGELOG.md`
(new `[0.13.14]` section with `### Removed` + `### Migration`
subsections), and `CLAUDE.md` (Current line).

### Cross-provider verification

Routed `task_type='session-verification'` to `gpt-5-4` (Anthropic
orchestrator → OpenAI verifier, satisfying the different-provider
rule). The verifier received the rendered prompt with six targeted
questions plus the full unified `git diff HEAD` (102,925 chars). The
verdict was **SAFE TO SHIP** across all six questions (stranded
imports, package.json consistency, `resolvePythonPath` simplification,
`pythonPath` description consistency, CHANGELOG fidelity, overall).
Two non-blocking refinements raised:

- **Applied in-session:** add a `### Migration` subsection to the
  CHANGELOG making the rename path for `dabblerProviderQueues.pythonPath`
  explicit. Done.
- **Deferred to follow-up:** add a focused unit test locking in that
  `dabblerSessionSets.pythonPath` is honored and the removed key is
  ignored. The test would target a function (`resolvePythonPath` in
  `installAiRouterCommands.ts`) that imports `vscode` and is therefore
  loadable only inside the Electron test host, not via the mocha CLI
  used for the `installAiRouter.test.ts` pure-logic suite. Adding it
  would require either mocking the `vscode.workspace.getConfiguration().inspect()`
  API or refactoring `resolvePythonPath` to take its config inputs as
  parameters — both larger than Set 024's deletion-only scope. Punted
  to a future "add resolvePythonPath unit test" follow-up.

Verifier cost: $0.1394 (26,696 input tokens, 4,847 output tokens).
Raw verifier output preserved at
`session-reviews/session-001/verify-result.json` +
`session-001-review.md`.

---

## What this set does NOT do

- It does not remove the Python CLI surface
  (`ai_router.queue_status`, `ai_router.heartbeat_status`). Those
  stay for operators running outsource-last in other repos.
- It does not touch `ai_router/docs/two-cli-workflow.md`. The
  outsource-last operating procedure remains documented; only the
  extension-side UI for it is gone.
- It does not change the shared activity-bar container. Removing
  `dabblerSessionSetsContainer` would have orphaned the Session Sets
  view; the container stays.
- It does not add a deprecation grace period. The views were
  erroring out persistently before the set started, so there was no
  working behavior to deprecate gracefully.

---

## Release

Extension v0.13.14 ships to the VS Code Marketplace
(`DarndestDabbler.dabbler-ai-orchestration`) via the existing
tag-driven workflow: `git tag vsix-v0.13.14 && git push --tags`,
then approve the `marketplace` deployment in the GitHub Actions UI
per `docs/planning/marketplace-release-process.md`. Open VSX
dual-publish proceeds via the same tag through its existing job; no
divergence between registries.
