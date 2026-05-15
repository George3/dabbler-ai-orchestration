# Session 1 verification prompt — Set 024 (extension v0.13.14)

## Context

Set 024 is a single-session, deletion-only change that removes the
Provider Queues and Provider Heartbeats tree views from the Dabbler AI
Orchestration VS Code extension. These views were scaffolding for the
`outsourceMode: last` (subscription-CLI verifier daemon) workflow.
**No session set in this repo has ever declared `outsourceMode: last`**
(every set is outsource-first), and the views currently render a
persistent yellow warning ("Failed to read queue status. queue_status
exited 1 …") because there is no `provider-queues/` directory on disk
for them to read. That UX is strictly worse than no view at all.

The operator confirmed (decision capture in `spec.md` § "Decisions
confirmed with the human"):

1. **Full removal**, not hide-behind-setting.
2. The shared `dabblerSessionSetsContainer` activity-bar container
   **stays** (the Session Sets view still uses it).
3. **No deprecation grace period** — the views error out today, so
   there is no working behavior to deprecate.
4. The Python CLI surface (`ai_router.queue_status`,
   `ai_router.heartbeat_status`) and the operating guide
   (`ai_router/docs/two-cli-workflow.md`) **stay** — operators who run
   outsource-last in *other* repos can still invoke those CLIs directly.
5. Six contributed settings under `dabblerProviderQueues.*` and
   `dabblerProviderHeartbeats.*` are removed; the
   `dabblerSessionSets.pythonPath` description loses its fallback
   sentence; the setting itself stays.

Extension version bumps `0.13.13` → `0.13.14` and ships via the
existing tag-driven Marketplace + Open VSX workflow.

## What was deleted

**Source files (6 total, ~2,000 LOC removed):**

- `tools/dabbler-ai-orchestration/src/providers/ProviderQueuesProvider.ts` (481 LOC)
- `tools/dabbler-ai-orchestration/src/providers/ProviderHeartbeatsProvider.ts` (437 LOC)
- `tools/dabbler-ai-orchestration/src/commands/queueActions.ts` (210 LOC)
- `tools/dabbler-ai-orchestration/src/test/suite/providerQueues.test.ts` (240 LOC)
- `tools/dabbler-ai-orchestration/src/test/suite/providerHeartbeats.test.ts` (274 LOC)
- `tools/dabbler-ai-orchestration/src/utils/pythonRunner.ts` (93 LOC) — confirmed dead
  after the providers and `queueActions` (its only callers in `src/`)
  were removed.

**`package.json` deletions:**

- Two `views` entries (`dabblerProviderQueues`, `dabblerProviderHeartbeats`).
- Five `commands` entries (queues: `refresh`/`openPayload`/`markFailed`/`forceReclaim`; heartbeats: `refresh`).
- Four `menus` entries (2 `view/title` + 2 `view/item/context`).
- Six configuration properties under `dabblerProviderQueues.*` and
  `dabblerProviderHeartbeats.*`.
- The "Falls back to `dabblerProviderQueues.pythonPath` if unset" clause
  from `dabblerSessionSets.pythonPath`'s markdown description.

**`extension.ts` deletions:**

- Three imports (`ProviderQueuesProvider`, `ProviderHeartbeatsProvider`,
  `registerQueueActionCommands`).
- The `vscode.window.registerTreeDataProvider("dabblerProviderQueues", ...)`
  block and its auto-refresh `setInterval` + config-change listener.
- The `vscode.window.createTreeView("dabblerProviderHeartbeats", ...)`
  block, its `HEARTBEAT_FOOTER` description, and its
  auto-refresh `setInterval` + config-change listener.
- The `registerQueueActionCommands(...)` call.
- Net: 105 lines removed from `extension.ts`.

**`installAiRouterCommands.ts` change:** `resolvePythonPath()` chain
simplified from
`explicitConfigValue("dabblerSessionSets", "pythonPath") ?? explicitConfigValue("dabblerProviderQueues", "pythonPath") ?? "python"`
to
`explicitConfigValue("dabblerSessionSets", "pythonPath") ?? "python"`,
since the middle setting no longer exists in the schema. Comment block
trimmed accordingly.

**`installAiRouter.test.ts` change:** The import block for
`ProviderQueuesProvider` and `ProviderHeartbeatsProvider` is gone, and
the five provider-related suites at the bottom of the file (parseFetchResult,
failure-invalidates-cache, tree-item rendering — each for both providers
plus shared) are removed. 35 install-only suites remain and all pass
when run via `npx mocha --ui tdd --require ts-node/register src/test/suite/installAiRouter.test.ts`.

**Comment cleanup in `aiRouterInstall.ts`:** A stale JSDoc reference to
`runPythonModule` (the function that lived in the now-deleted
`pythonRunner.ts`) trimmed to remove the dangling reference.

## What was kept

- The shared `dabblerSessionSetsContainer` activity-bar container.
- The Session Sets view (`SessionSetsProvider`).
- The cancel/restore lifecycle commands.
- The install/update ai-router commands.
- The cost dashboard, wizard, troubleshoot, and adoption-bootstrap-prompt
  commands.
- `dabblerSessionSets.pythonPath` and `dabblerSessionSets.aiRouterRepoUrl`
  configuration properties.
- Python CLI: `ai_router.queue_status`, `ai_router.heartbeat_status`
  (and the rest of the `ai_router/` package).

## Verification questions

Please review the unified diff (inlined below) and answer:

**Q1. Stranded imports / dead references.** Are there any code paths in
the remaining `src/` tree that still import from the deleted modules
(`ProviderQueuesProvider`, `ProviderHeartbeatsProvider`,
`queueActions`, `pythonRunner`), or that reference symbols those modules
exported? The orchestrator ran `Grep` across `src/` post-deletion and
found none, plus `npx tsc --outDir out` exited 0 with no warnings. Please
double-check by reading the diff.

**Q2. `package.json` consistency.** Are the deletions in `views`,
`commands`, `menus`, and `configuration.properties` all internally
consistent? Specifically: does any *remaining* entry (e.g., a
`menus/view/title` `when` clause, a `commandPalette` entry, an
`activationEvents` entry) still reference one of the five removed
command IDs or the two removed view IDs?

**Q3. `installAiRouterCommands.ts → resolvePythonPath`.** The fallback
to `dabblerProviderQueues.pythonPath` was removed because the contributed
default for that setting no longer exists. **However:** an *existing*
operator who had set `dabblerProviderQueues.pythonPath` in their
workspace `.vscode/settings.json` before this version would, on upgrade
to v0.13.14, find that the install command silently stops honoring
their value. Is this a sharp edge worth calling out in the CHANGELOG
beyond what's already there? Or is the simplified two-tier fallback
(`dabblerSessionSets.pythonPath` → bare `"python"` on PATH) the right
shape and operators with stranded settings should just re-set the
preferred key?

**Q4. `dabblerSessionSets.pythonPath` description.** The description
currently still mentions venv detection logic ("When the path points at
an interpreter inside an existing venv (parent dir is `Scripts/` or
`bin/`)…"). That language is unchanged. Is anything in the description
inconsistent with the simpler two-tier resolution now in place?

**Q5. CHANGELOG fidelity.** Read the `[0.13.14]` entry and the diff
together. Does the CHANGELOG accurately describe every visible operator
impact? Specifically, does it cover (a) the disappearing views, (b) the
disappearing settings, (c) the disappearing commands, (d) the
`pythonPath` fallback removal? Any operator-visible impact missing?

**Q6. Overall verdict.** Is the deletion safe to ship as v0.13.14? Any
blockers? Any *non-blocking* refinements worth landing now while the
diff is hot vs. punted to a follow-up?

A short, structured response (per-question verdict + reasoning + any
concrete suggestions) is fine.
