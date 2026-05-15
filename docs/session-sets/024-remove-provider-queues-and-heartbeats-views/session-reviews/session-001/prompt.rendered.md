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


---

## Unified diff (session 1 work vs. HEAD)

```diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 705de97..f41e6fb 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -39,7 +39,7 @@ is a required duplicate — `vsce package` expects the file alongside
 
 ## Extension versioning
 
-- Current: **v0.13.13**
+- Current: **v0.13.14**
 - Publisher: `DarndestDabbler` (VS Code Marketplace: `DarndestDabbler.dabbler-ai-orchestration`)
 - Namespace: `dabblerSessionSets` (shared across all consumers)
 - Build: `cd tools/dabbler-ai-orchestration && npx vsce package`
diff --git a/docs/session-sets/024-remove-provider-queues-and-heartbeats-views/session-state.json b/docs/session-sets/024-remove-provider-queues-and-heartbeats-views/session-state.json
index 5c16351..6972c4e 100644
--- a/docs/session-sets/024-remove-provider-queues-and-heartbeats-views/session-state.json
+++ b/docs/session-sets/024-remove-provider-queues-and-heartbeats-views/session-state.json
@@ -1,13 +1,17 @@
 {
   "schemaVersion": 2,
   "sessionSetName": "024-remove-provider-queues-and-heartbeats-views",
-  "currentSession": null,
+  "currentSession": 1,
   "totalSessions": 1,
-  "status": "not-started",
-  "lifecycleState": null,
-  "startedAt": null,
+  "status": "in-progress",
+  "lifecycleState": "work_in_progress",
+  "startedAt": "2026-05-15T08:12:06.548963-04:00",
   "completedAt": null,
   "verificationVerdict": null,
-  "orchestrator": null,
-  "completedSessions": []
+  "orchestrator": {
+    "engine": "claude-code",
+    "provider": "anthropic",
+    "model": "claude-opus-4-7",
+    "effort": "medium"
+  }
 }
diff --git a/tools/dabbler-ai-orchestration/CHANGELOG.md b/tools/dabbler-ai-orchestration/CHANGELOG.md
index 632def1..c688707 100644
--- a/tools/dabbler-ai-orchestration/CHANGELOG.md
+++ b/tools/dabbler-ai-orchestration/CHANGELOG.md
@@ -5,6 +5,38 @@ Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
 
 ## [Unreleased]
 
+## [0.13.14] — 2026-05-15
+
+### Removed
+- **Provider Queues and Provider Heartbeats tree views (Set 024).** Both
+  views, their five commands
+  (`dabblerProviderQueues.refresh` / `.openPayload` / `.markFailed` /
+  `.forceReclaim`, `dabblerProviderHeartbeats.refresh`), their menu
+  contributions, and their six configuration properties under
+  `dabblerProviderQueues.*` and `dabblerProviderHeartbeats.*` are gone.
+  These views were scaffolding for the `outsourceMode: last`
+  (subscription-CLI verifier daemon) path; no session set in this repo
+  has declared `outsourceMode: last`, and the persistent yellow
+  warning triangle that surfaced on every refresh ("Failed to read
+  queue status. queue_status exited 1 …") was worse UX than no view at
+  all. The Python CLI surface (`python -m ai_router.queue_status` and
+  `python -m ai_router.heartbeat_status`) stays — operators who run
+  outsource-last in other repos can still invoke those commands from a
+  terminal, and `ai_router/docs/two-cli-workflow.md` still documents
+  the path. The shared `dabblerSessionSetsContainer` activity-bar
+  container stays for the Session Sets view.
+- Five TypeScript source files
+  (`ProviderQueuesProvider.ts`, `ProviderHeartbeatsProvider.ts`,
+  `queueActions.ts`, and the two corresponding test suites) plus
+  `utils/pythonRunner.ts` (now unused after the providers and
+  `queueActions` that called it were removed).
+- The "Falls back to `dabblerProviderQueues.pythonPath` if unset"
+  fallback sentence on `dabblerSessionSets.pythonPath`'s markdown
+  description, and the corresponding code-side fallback in
+  `installAiRouterCommands.ts → resolvePythonPath`. Operators who want
+  to point the install command at a venv interpreter should set
+  `dabblerSessionSets.pythonPath` directly.
+
 ## [0.13.13] — 2026-05-15
 
 ### Changed
diff --git a/tools/dabbler-ai-orchestration/package-lock.json b/tools/dabbler-ai-orchestration/package-lock.json
index 3605e05..26862b5 100644
--- a/tools/dabbler-ai-orchestration/package-lock.json
+++ b/tools/dabbler-ai-orchestration/package-lock.json
@@ -1,12 +1,12 @@
 {
   "name": "dabbler-ai-orchestration",
-  "version": "0.13.13",
+  "version": "0.13.14",
   "lockfileVersion": 3,
   "requires": true,
   "packages": {
     "": {
       "name": "dabbler-ai-orchestration",
-      "version": "0.13.13",
+      "version": "0.13.14",
       "license": "MIT",
       "dependencies": {
         "simple-git": "^3.22.0"
diff --git a/tools/dabbler-ai-orchestration/package.json b/tools/dabbler-ai-orchestration/package.json
index 82d3d6e..7222f25 100644
--- a/tools/dabbler-ai-orchestration/package.json
+++ b/tools/dabbler-ai-orchestration/package.json
@@ -2,7 +2,7 @@
   "name": "dabbler-ai-orchestration",
   "displayName": "Dabbler AI Orchestration",
   "description": "Project wizard, session-set explorer, cost dashboard, and adoption-bootstrap entry point for the Dabbler AI-led workflow.",
-  "version": "0.13.13",
+  "version": "0.13.14",
   "publisher": "DarndestDabbler",
   "private": true,
   "engines": {
@@ -44,16 +44,6 @@
           "id": "dabblerSessionSets",
           "name": "Session Sets",
           "contextualTitle": "Dabbler AI Orchestration"
-        },
-        {
-          "id": "dabblerProviderQueues",
-          "name": "Provider Queues",
-          "contextualTitle": "Dabbler AI Orchestration"
-        },
-        {
-          "id": "dabblerProviderHeartbeats",
-          "name": "Provider Heartbeats",
-          "contextualTitle": "Dabbler AI Orchestration"
         }
       ]
     },
@@ -159,33 +149,6 @@
         "category": "Dabbler",
         "icon": "$(graph)"
       },
-      {
-        "command": "dabblerProviderQueues.refresh",
-        "title": "Refresh Provider Queues",
-        "category": "Dabbler",
-        "icon": "$(refresh)"
-      },
-      {
-        "command": "dabblerProviderQueues.openPayload",
-        "title": "Open Payload",
-        "category": "Dabbler"
-      },
-      {
-        "command": "dabblerProviderQueues.markFailed",
-        "title": "Mark Failed",
-        "category": "Dabbler"
-      },
-      {
-        "command": "dabblerProviderQueues.forceReclaim",
-        "title": "Force Reclaim",
-        "category": "Dabbler"
-      },
-      {
-        "command": "dabblerProviderHeartbeats.refresh",
-        "title": "Refresh Provider Heartbeats",
-        "category": "Dabbler",
-        "icon": "$(refresh)"
-      },
       {
         "command": "dabblerSessionSets.cancel",
         "title": "Cancel Session Set",
@@ -235,16 +198,6 @@
           "command": "dabbler.getStarted",
           "when": "view == dabblerSessionSets",
           "group": "navigation@3"
-        },
-        {
-          "command": "dabblerProviderQueues.refresh",
-          "when": "view == dabblerProviderQueues",
-          "group": "navigation@1"
-        },
-        {
-          "command": "dabblerProviderHeartbeats.refresh",
-          "when": "view == dabblerProviderHeartbeats",
-          "group": "navigation@1"
         }
       ],
       "view/item/context": [
@@ -307,21 +260,6 @@
           "command": "dabblerSessionSets.restore",
           "when": "view == dabblerSessionSets && viewItem =~ /^sessionSet:cancelled/",
           "group": "9_lifecycle@2"
-        },
-        {
-          "command": "dabblerProviderQueues.openPayload",
-          "when": "view == dabblerProviderQueues && viewItem =~ /^queueMessage:/",
-          "group": "1_inspect@1"
-        },
-        {
-          "command": "dabblerProviderQueues.markFailed",
-          "when": "view == dabblerProviderQueues && viewItem =~ /^queueMessage:(new|claimed)/",
-          "group": "9_danger@1"
-        },
-        {
-          "command": "dabblerProviderQueues.forceReclaim",
-          "when": "view == dabblerProviderQueues && viewItem =~ /^queueMessage:claimed/",
-          "group": "9_danger@2"
         }
       ]
     },
@@ -348,47 +286,12 @@
         "dabblerSessionSets.pythonPath": {
           "type": "string",
           "default": "python",
-          "markdownDescription": "Python executable used by `Dabbler: Install ai-router` and `Dabbler: Update ai-router` for venv detection / creation and `pip install` commands. Accepts an absolute path, a workspace-relative path (e.g. `.venv/Scripts/python.exe`), or a bare command on `PATH`. When the path points at an interpreter inside an existing venv (parent dir is `Scripts/` or `bin/`), the install command treats that venv as the install target instead of hunting for `.venv/` at the workspace root. Falls back to `dabblerProviderQueues.pythonPath` if unset."
+          "markdownDescription": "Python executable used by `Dabbler: Install ai-router` and `Dabbler: Update ai-router` for venv detection / creation and `pip install` commands. Accepts an absolute path, a workspace-relative path (e.g. `.venv/Scripts/python.exe`), or a bare command on `PATH`. When the path points at an interpreter inside an existing venv (parent dir is `Scripts/` or `bin/`), the install command treats that venv as the install target instead of hunting for `.venv/` at the workspace root."
         },
         "dabblerSessionSets.aiRouterRepoUrl": {
           "type": "string",
           "default": "",
           "markdownDescription": "Git repo URL the `Dabbler: Install ai-router` command's GitHub-fallback path clones from. Leave blank to use the upstream Dabbler repository. Override to point at a fork — handy for fork-trackers who want the GitHub fallback to pull *their* tags / branches rather than upstream's."
-        },
-        "dabblerProviderQueues.autoRefreshSeconds": {
-          "type": "number",
-          "default": 15,
-          "minimum": 0,
-          "markdownDescription": "Auto-refresh interval (seconds) for the Provider Queues view. Set to `0` to disable auto-refresh; manual refresh remains available via the toolbar button."
-        },
-        "dabblerProviderQueues.pythonPath": {
-          "type": "string",
-          "default": "python",
-          "markdownDescription": "Python executable used to invoke `python -m ai_router.queue_status`. Override if your environment requires a virtualenv path (e.g. `.venv/Scripts/python.exe`)."
-        },
-        "dabblerProviderQueues.messageLimit": {
-          "type": "number",
-          "default": 50,
-          "minimum": 1,
-          "markdownDescription": "Maximum number of messages fetched per provider per refresh."
-        },
-        "dabblerProviderHeartbeats.autoRefreshSeconds": {
-          "type": "number",
-          "default": 15,
-          "minimum": 0,
-          "markdownDescription": "Auto-refresh interval (seconds) for the Provider Heartbeats view. Set to `0` to disable auto-refresh."
-        },
-        "dabblerProviderHeartbeats.lookbackMinutes": {
-          "type": "number",
-          "default": 60,
-          "minimum": 1,
-          "markdownDescription": "Lookback window (minutes) for the heartbeats view's completion / token counts. **Observational only** — this does not predict subscription-window exhaustion."
-        },
-        "dabblerProviderHeartbeats.silentWarningMinutes": {
-          "type": "number",
-          "default": 30,
-          "minimum": 1,
-          "markdownDescription": "Show a silent-provider warning when a provider's last completion was more than this many minutes ago."
         }
       }
     }
diff --git a/tools/dabbler-ai-orchestration/src/commands/installAiRouterCommands.ts b/tools/dabbler-ai-orchestration/src/commands/installAiRouterCommands.ts
index 9813b00..96c072c 100644
--- a/tools/dabbler-ai-orchestration/src/commands/installAiRouterCommands.ts
+++ b/tools/dabbler-ai-orchestration/src/commands/installAiRouterCommands.ts
@@ -101,12 +101,8 @@ function resolveAiRouterRepoUrl(): string | undefined {
 }
 
 function resolvePythonPath(workspaceRoot: string): string {
-  // Per spec: install command reads ``dabblerSessionSets.pythonPath``
-  // (separate from the per-view ``dabblerProviderQueues.pythonPath`` so
-  // the views and the install command can target different interpreters
-  // if a workspace ever needs to). Falls back to the queue setting for
-  // backward compatibility with workspaces that only set that one, then
-  // to bare ``"python"`` on PATH.
+  // Install command reads ``dabblerSessionSets.pythonPath``, falling
+  // back to bare ``"python"`` on PATH.
   //
   // Use ``inspect()`` to distinguish "operator explicitly set it" from
   // "the contributed default fired" — `getConfiguration().get()` can't
@@ -114,7 +110,6 @@ function resolvePythonPath(workspaceRoot: string): string {
   // the fallback. Round-6 verifier catch.
   const raw = (
     explicitConfigValue("dabblerSessionSets", "pythonPath") ??
-    explicitConfigValue("dabblerProviderQueues", "pythonPath") ??
     "python"
   ).trim();
   if (!raw) return "python";
diff --git a/tools/dabbler-ai-orchestration/src/commands/queueActions.ts b/tools/dabbler-ai-orchestration/src/commands/queueActions.ts
deleted file mode 100644
index 37119a8..0000000
--- a/tools/dabbler-ai-orchestration/src/commands/queueActions.ts
+++ /dev/null
@@ -1,210 +0,0 @@
-import * as vscode from "vscode";
-import { runPythonModule } from "../utils/pythonRunner";
-import { ProviderQueuesProvider } from "../providers/ProviderQueuesProvider";
-
-/**
- * Right-click commands on Provider Queues tree items.
- *
- * Open Payload     — read-only ``dabbler-queue-payload://`` virtual document
- *                    with the message JSON. Read-only because mutating a
- *                    payload mid-flight would be a queue-contract violation.
- * Mark Failed      — operator escape hatch for stuck ``new``/``claimed``
- *                    messages. Confirmation dialog, then shells out to
- *                    ``queue_status --mark-failed``.
- * Force Reclaim    — releases a stuck lease (``claimed`` -> ``new``).
- *                    Confirmation dialog, then shells out to
- *                    ``queue_status --force-reclaim``.
- */
-
-interface MessageNodeArg {
-  kind: "message";
-  provider: string;
-  message: { id: string; state: string; task_type: string };
-}
-
-const PAYLOAD_SCHEME = "dabbler-queue-payload";
-
-class QueuePayloadContentProvider implements vscode.TextDocumentContentProvider {
-  private readonly _onDidChange = new vscode.EventEmitter<vscode.Uri>();
-  readonly onDidChange = this._onDidChange.event;
-  private readonly _store = new Map<string, string>();
-
-  setContent(uri: vscode.Uri, body: string): void {
-    this._store.set(uri.toString(), body);
-    this._onDidChange.fire(uri);
-  }
-
-  provideTextDocumentContent(uri: vscode.Uri): string {
-    return this._store.get(uri.toString()) ?? "(payload not loaded)";
-  }
-}
-
-export interface QueueActionsContext {
-  getWorkspaceRoot: () => string | undefined;
-  refreshView: () => void;
-}
-
-export function registerQueueActionCommands(
-  ctx: vscode.ExtensionContext,
-  qctx: QueueActionsContext,
-): void {
-  const contentProvider = new QueuePayloadContentProvider();
-  ctx.subscriptions.push(
-    vscode.workspace.registerTextDocumentContentProvider(PAYLOAD_SCHEME, contentProvider),
-  );
-
-  ctx.subscriptions.push(
-    vscode.commands.registerCommand(
-      "dabblerProviderQueues.openPayload",
-      async (arg: MessageNodeArg | undefined) => {
-        if (!arg || arg.kind !== "message") {
-          vscode.window.showWarningMessage("Open Payload: select a queue message first.");
-          return;
-        }
-        const root = qctx.getWorkspaceRoot();
-        if (!root) {
-          vscode.window.showErrorMessage("Open Payload: no workspace folder open.");
-          return;
-        }
-        const result = await runPythonModule({
-          cwd: root,
-          module: "ai_router.queue_status",
-          args: [
-            "--provider",
-            arg.provider,
-            "--get-payload",
-            arg.message.id,
-          ],
-          pythonPathSetting: "dabblerProviderQueues.pythonPath",
-          timeoutMs: 10000,
-        });
-        if (result.exitCode !== 0 && result.exitCode !== 1) {
-          vscode.window.showErrorMessage(
-            `queue_status --get-payload failed: ${(result.stderr || result.stdout).trim() || "no output"}`,
-          );
-          return;
-        }
-        let parsed: { ok?: boolean; message?: unknown; error?: string };
-        try {
-          parsed = JSON.parse(result.stdout);
-        } catch (err) {
-          vscode.window.showErrorMessage(
-            `Open Payload: malformed JSON from queue_status: ${err instanceof Error ? err.message : String(err)}`,
-          );
-          return;
-        }
-        if (!parsed.ok) {
-          vscode.window.showWarningMessage(
-            `Open Payload: ${parsed.error ?? "message not found"}`,
-          );
-          return;
-        }
-        const body = JSON.stringify(parsed.message, null, 2);
-        // URI carries provider and id so VS Code can dedupe re-opens of the
-        // same message into a single virtual document.
-        const uri = vscode.Uri.parse(
-          `${PAYLOAD_SCHEME}:/${encodeURIComponent(arg.provider)}/${encodeURIComponent(arg.message.id)}.json`,
-        );
-        contentProvider.setContent(uri, body);
-        const doc = await vscode.workspace.openTextDocument(uri);
-        await vscode.languages.setTextDocumentLanguage(doc, "json");
-        await vscode.window.showTextDocument(doc, { preview: true });
-      },
-    ),
-  );
-
-  ctx.subscriptions.push(
-    vscode.commands.registerCommand(
-      "dabblerProviderQueues.markFailed",
-      async (arg: MessageNodeArg | undefined) => {
-        if (!arg || arg.kind !== "message") {
-          vscode.window.showWarningMessage("Mark Failed: select a queue message first.");
-          return;
-        }
-        const choice = await vscode.window.showWarningMessage(
-          `Force ${arg.message.id.slice(0, 8)} (${arg.message.task_type}, state=${arg.message.state}) into state=failed?`,
-          { modal: true, detail: "Bypasses the normal ownership check. Use only when the worker is known dead." },
-          "Mark Failed",
-        );
-        if (choice !== "Mark Failed") return;
-        const root = qctx.getWorkspaceRoot();
-        if (!root) return;
-        const result = await runPythonModule({
-          cwd: root,
-          module: "ai_router.queue_status",
-          args: [
-            "--provider",
-            arg.provider,
-            "--mark-failed",
-            arg.message.id,
-          ],
-          pythonPathSetting: "dabblerProviderQueues.pythonPath",
-        });
-        await reportInterventionResult("Mark Failed", result, qctx);
-      },
-    ),
-  );
-
-  ctx.subscriptions.push(
-    vscode.commands.registerCommand(
-      "dabblerProviderQueues.forceReclaim",
-      async (arg: MessageNodeArg | undefined) => {
-        if (!arg || arg.kind !== "message") {
-          vscode.window.showWarningMessage("Force Reclaim: select a queue message first.");
-          return;
-        }
-        const choice = await vscode.window.showWarningMessage(
-          `Release the lease on ${arg.message.id.slice(0, 8)} (${arg.message.task_type})?`,
-          { modal: true, detail: "Returns state=claimed -> new and bumps attempts. The next claim() will pick it up." },
-          "Force Reclaim",
-        );
-        if (choice !== "Force Reclaim") return;
-        const root = qctx.getWorkspaceRoot();
-        if (!root) return;
-        const result = await runPythonModule({
-          cwd: root,
-          module: "ai_router.queue_status",
-          args: [
-            "--provider",
-            arg.provider,
-            "--force-reclaim",
-            arg.message.id,
-          ],
-          pythonPathSetting: "dabblerProviderQueues.pythonPath",
-        });
-        await reportInterventionResult("Force Reclaim", result, qctx);
-      },
-    ),
-  );
-}
-
-async function reportInterventionResult(
-  label: string,
-  result: { stdout: string; stderr: string; exitCode: number | null; timedOut: boolean },
-  qctx: QueueActionsContext,
-): Promise<void> {
-  if (result.timedOut) {
-    vscode.window.showErrorMessage(`${label}: queue_status timed out.`);
-    return;
-  }
-  let parsed: { ok?: boolean; error?: string; previous_state?: string } = {};
-  try {
-    parsed = JSON.parse(result.stdout || "{}");
-  } catch {
-    // fall through to generic failure path
-  }
-  if (parsed.ok) {
-    const prev = parsed.previous_state ? ` (was ${parsed.previous_state})` : "";
-    vscode.window.showInformationMessage(`${label} succeeded${prev}.`);
-    qctx.refreshView();
-    return;
-  }
-  const detail = parsed.error || (result.stderr || result.stdout).trim() || "no output";
-  vscode.window.showErrorMessage(`${label} failed: ${detail}`);
-}
-
-export function attachProviderForRefresh(
-  provider: ProviderQueuesProvider,
-): QueueActionsContext["refreshView"] {
-  return () => provider.refresh();
-}
diff --git a/tools/dabbler-ai-orchestration/src/extension.ts b/tools/dabbler-ai-orchestration/src/extension.ts
index c7d3ef3..11f2e0e 100644
--- a/tools/dabbler-ai-orchestration/src/extension.ts
+++ b/tools/dabbler-ai-orchestration/src/extension.ts
@@ -2,18 +2,12 @@ import * as vscode from "vscode";
 import * as fs from "fs";
 import * as path from "path";
 import { SessionSetsProvider } from "./providers/SessionSetsProvider";
-import { ProviderQueuesProvider } from "./providers/ProviderQueuesProvider";
-import {
-  ProviderHeartbeatsProvider,
-  HEARTBEAT_FOOTER,
-} from "./providers/ProviderHeartbeatsProvider";
 import { discoverRoots, readAllSessionSets } from "./utils/fileSystem";
 import { registerOpenFileCommands } from "./commands/openFile";
 import { registerCopyCommands } from "./commands/copyCommand";
 import { registerGitScaffoldCommand } from "./commands/gitScaffold";
 import { registerCopyAdoptionBootstrapPromptCommand } from "./commands/copyAdoptionBootstrapPrompt";
 import { registerTroubleshootCommand } from "./commands/troubleshoot";
-import { registerQueueActionCommands } from "./commands/queueActions";
 import { registerCancelLifecycleCommands } from "./commands/cancelLifecycleCommands";
 import { registerInstallAiRouterCommands } from "./commands/installAiRouterCommands";
 import { registerWizardCommands } from "./wizard/WizardPanel";
@@ -154,105 +148,6 @@ export function activate(context: vscode.ExtensionContext): void {
     vscode.commands.registerCommand("dabblerSessionSets.refresh", refreshAll)
   );
 
-  // --- Provider Queues view ---
-  const queuesProvider = new ProviderQueuesProvider({
-    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
-  });
-  context.subscriptions.push(
-    vscode.window.registerTreeDataProvider("dabblerProviderQueues", queuesProvider),
-  );
-  context.subscriptions.push(
-    vscode.commands.registerCommand("dabblerProviderQueues.refresh", () =>
-      queuesProvider.refresh(),
-    ),
-  );
-
-  // Auto-refresh; settings-configurable, 0 disables.
-  let queuesPoll: NodeJS.Timeout | undefined;
-  const rebindQueuesPoll = () => {
-    if (queuesPoll) clearInterval(queuesPoll);
-    const seconds = vscode.workspace
-      .getConfiguration("dabblerProviderQueues")
-      .get<number>("autoRefreshSeconds", 15);
-    if (seconds > 0) {
-      queuesPoll = setInterval(() => queuesProvider.refresh(), seconds * 1000);
-    } else {
-      queuesPoll = undefined;
-    }
-  };
-  rebindQueuesPoll();
-  context.subscriptions.push({
-    dispose: () => {
-      if (queuesPoll) clearInterval(queuesPoll);
-    },
-  });
-  context.subscriptions.push(
-    vscode.workspace.onDidChangeConfiguration((e) => {
-      if (e.affectsConfiguration("dabblerProviderQueues.autoRefreshSeconds")) {
-        rebindQueuesPoll();
-      }
-    }),
-  );
-
-  registerQueueActionCommands(context, {
-    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
-    refreshView: () => queuesProvider.refresh(),
-  });
-
-  // --- Provider Heartbeats view ---
-  const heartbeatsProvider = new ProviderHeartbeatsProvider({
-    getWorkspaceRoot: () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
-  });
-  // The footer makes the observational framing impossible to miss; it
-  // sits in the view header at all times so a user can't skim past it.
-  const heartbeatsTreeView = vscode.window.createTreeView("dabblerProviderHeartbeats", {
-    treeDataProvider: heartbeatsProvider,
-    showCollapseAll: false,
-  });
-  heartbeatsTreeView.description = HEARTBEAT_FOOTER;
-  context.subscriptions.push(heartbeatsTreeView);
-  context.subscriptions.push(
-    vscode.commands.registerCommand("dabblerProviderHeartbeats.refresh", () =>
-      heartbeatsProvider.refresh(),
-    ),
-  );
-
-  let heartbeatsPoll: NodeJS.Timeout | undefined;
-  const rebindHeartbeatsPoll = () => {
-    if (heartbeatsPoll) clearInterval(heartbeatsPoll);
-    const seconds = vscode.workspace
-      .getConfiguration("dabblerProviderHeartbeats")
-      .get<number>("autoRefreshSeconds", 15);
-    if (seconds > 0) {
-      heartbeatsPoll = setInterval(
-        () => heartbeatsProvider.refresh(),
-        seconds * 1000,
-      );
-    } else {
-      heartbeatsPoll = undefined;
-    }
-  };
-  rebindHeartbeatsPoll();
-  context.subscriptions.push({
-    dispose: () => {
-      if (heartbeatsPoll) clearInterval(heartbeatsPoll);
-    },
-  });
-  context.subscriptions.push(
-    vscode.workspace.onDidChangeConfiguration((e) => {
-      // Only the polling-interval setting actually requires rebinding the
-      // setInterval; the other two only affect what the next refresh pulls.
-      const affectsTiming = e.affectsConfiguration(
-        "dabblerProviderHeartbeats.autoRefreshSeconds",
-      );
-      const affectsContent =
-        e.affectsConfiguration("dabblerProviderHeartbeats.lookbackMinutes") ||
-        e.affectsConfiguration("dabblerProviderHeartbeats.silentWarningMinutes");
-      if (affectsTiming) rebindHeartbeatsPoll();
-      if (affectsTiming || affectsContent) heartbeatsProvider.refresh();
-    }),
-  );
-
   // --- Register feature command groups ---
   //
   // Each register*Commands call is wrapped in its own try/catch so a
diff --git a/tools/dabbler-ai-orchestration/src/providers/ProviderHeartbeatsProvider.ts b/tools/dabbler-ai-orchestration/src/providers/ProviderHeartbeatsProvider.ts
deleted file mode 100644
index ad26f9f..0000000
--- a/tools/dabbler-ai-orchestration/src/providers/ProviderHeartbeatsProvider.ts
+++ /dev/null
@@ -1,437 +0,0 @@
-import * as vscode from "vscode";
-import { runPythonModule, PythonRunResult } from "../utils/pythonRunner";
-import { isAiRouterNotInstalled } from "../utils/aiRouterInstall";
-
-/**
- * Tree view backing the ``Provider Heartbeats`` activity-bar entry.
- *
- * Shells out to ``python -m ai_router.heartbeat_status --format json``
- * for the same reason :class:`ProviderQueuesProvider` shells out to
- * ``queue_status``: the on-disk format lives in :mod:`ai_router.capacity`
- * and a TS reader would either duplicate or drift from it.
- *
- * **Framing.** Every visible string in this view is backward-looking.
- * The Python helper ships a ``_disclaimer`` field with every payload,
- * and the tree's view-description footer echoes it. The cross-provider
- * v1 review explicitly rejected predictive framings (subscription-window
- * exhaustion, throttle risk, "is this provider healthy") — see the
- * Set 005 spec, Risks section, "Heartbeat misuse".
- */
-
-const CACHE_TTL_MS = 5_000;
-const DEFAULT_LOOKBACK_MINUTES = 60;
-const DEFAULT_SILENT_WARNING_MINUTES = 30;
-
-export const HEARTBEAT_FOOTER =
-  "Observational only. Subscription windows are not introspectable. Use as a heartbeat signal, not as routing guidance.";
-
-export interface ProviderHeartbeat {
-  signal_path: string;
-  signal_file_present: boolean;
-  last_completion_at: string | null;
-  minutes_since_last_completion: number | null;
-  /** ``completions_in_last_<N>min`` — N = lookback_minutes. */
-  completions_in_window: number;
-  /** ``tokens_in_last_<N>min`` — N = lookback_minutes. */
-  tokens_in_window: number;
-  lookback_minutes: number;
-  disclaimer: string;
-}
-
-export interface HeartbeatStatusPayload {
-  providers: Record<string, ProviderHeartbeat>;
-  disclaimer: string;
-}
-
-// ---------- tree node shapes ----------
-
-export type HeartbeatTreeNode =
-  | ProviderNode
-  | InfoNode
-  | NotInstalledNode
-  | NotInstalledActionNode;
-
-interface ProviderNode {
-  kind: "provider";
-  provider: string;
-  data: ProviderHeartbeat;
-  silentWarningMinutes: number;
-}
-interface InfoNode {
-  kind: "info";
-  label: string;
-  detail?: string;
-  isError?: boolean;
-}
-/** See ProviderQueuesProvider.NotInstalledNode — same shape, same purpose. */
-interface NotInstalledNode {
-  kind: "notInstalled";
-}
-interface NotInstalledActionNode {
-  kind: "notInstalledAction";
-}
-
-// ---------- provider ----------
-
-export interface ProviderHeartbeatsDeps {
-  getWorkspaceRoot: () => string | undefined;
-  /** Override for tests. */
-  fetchPayload?: (
-    workspaceRoot: string,
-    lookbackMinutes: number,
-  ) => Promise<
-    | { ok: true; payload: HeartbeatStatusPayload }
-    | { ok: false; message: string; reason?: "module_not_installed" }
-  >;
-  /** Override for tests. */
-  getSettings?: () => { lookbackMinutes: number; silentWarningMinutes: number };
-  /** Clock — overridable for tests. */
-  now?: () => number;
-}
-
-export class ProviderHeartbeatsProvider
-  implements vscode.TreeDataProvider<HeartbeatTreeNode>
-{
-  private readonly _onDidChangeTreeData = new vscode.EventEmitter<
-    HeartbeatTreeNode | undefined | void
-  >();
-  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
-
-  private _cache:
-    | { fetchedAt: number; payload: HeartbeatStatusPayload; lookback: number }
-    | null = null;
-  private _lastError: string | null = null;
-  private _lastErrorReason: "module_not_installed" | null = null;
-  private _inFlight: Promise<void> | null = null;
-
-  constructor(private readonly deps: ProviderHeartbeatsDeps) {}
-
-  refresh(): void {
-    this._cache = null;
-    this._onDidChangeTreeData.fire();
-  }
-
-  /** Test-only — inject a payload and skip the spawn path. */
-  _setPayloadForTest(payload: HeartbeatStatusPayload, lookback: number): void {
-    this._cache = {
-      fetchedAt: this.deps.now?.() ?? Date.now(),
-      payload,
-      lookback,
-    };
-    this._lastError = null;
-  }
-
-  // ---------- TreeDataProvider ----------
-
-  getTreeItem(element: HeartbeatTreeNode): vscode.TreeItem {
-    return buildTreeItem(element);
-  }
-
-  async getChildren(element?: HeartbeatTreeNode): Promise<HeartbeatTreeNode[]> {
-    if (element?.kind === "notInstalled") {
-      return [{ kind: "notInstalledAction" }];
-    }
-    if (element) return [];
-
-    const root = this.deps.getWorkspaceRoot();
-    if (!root) {
-      return [{ kind: "info", label: "No workspace folder open." }];
-    }
-    const settings = this._readSettings();
-    const payload = await this._getPayload(root, settings.lookbackMinutes);
-    if (!payload) {
-      if (this._lastErrorReason === "module_not_installed") {
-        return [{ kind: "notInstalled" }];
-      }
-      const detail = this._lastError ?? "Unknown error.";
-      return [
-        {
-          kind: "info",
-          label: "Failed to read heartbeat status.",
-          detail,
-          isError: true,
-        },
-      ];
-    }
-    const providers = Object.keys(payload.providers).sort();
-    if (providers.length === 0) {
-      return [
-        {
-          kind: "info",
-          label: "No provider capacity signals found.",
-          detail:
-            "Looked for capacity_signal.jsonl files under provider-queues/. Run a session that emits work to populate this view.",
-        },
-      ];
-    }
-    return providers.map<ProviderNode>((p) => ({
-      kind: "provider",
-      provider: p,
-      data: payload.providers[p],
-      silentWarningMinutes: settings.silentWarningMinutes,
-    }));
-  }
-
-  // ---------- internals ----------
-
-  private _readSettings(): { lookbackMinutes: number; silentWarningMinutes: number } {
-    if (this.deps.getSettings) return this.deps.getSettings();
-    const cfg = vscode.workspace.getConfiguration("dabblerProviderHeartbeats");
-    return {
-      lookbackMinutes: cfg.get<number>("lookbackMinutes", DEFAULT_LOOKBACK_MINUTES),
-      silentWarningMinutes: cfg.get<number>(
-        "silentWarningMinutes",
-        DEFAULT_SILENT_WARNING_MINUTES,
-      ),
-    };
-  }
-
-  private async _getPayload(
-    root: string,
-    lookback: number,
-  ): Promise<HeartbeatStatusPayload | null> {
-    const now = this.deps.now?.() ?? Date.now();
-    if (
-      this._cache &&
-      this._cache.lookback === lookback &&
-      now - this._cache.fetchedAt < CACHE_TTL_MS
-    ) {
-      return this._cache.payload;
-    }
-    if (this._inFlight) {
-      await this._inFlight;
-      return this._cache?.payload ?? null;
-    }
-    const fetcher = this.deps.fetchPayload ?? defaultFetchPayload;
-    this._inFlight = (async () => {
-      const result = await fetcher(root, lookback);
-      if (result.ok) {
-        this._cache = {
-          fetchedAt: this.deps.now?.() ?? Date.now(),
-          payload: result.payload,
-          lookback,
-        };
-        this._lastError = null;
-        this._lastErrorReason = null;
-      } else {
-        this._lastError = result.message;
-        this._lastErrorReason = result.reason ?? null;
-        // Round-5 verifier catch: clear the cache so the failure
-        // surfaces. See ProviderQueuesProvider for the full rationale.
-        this._cache = null;
-      }
-    })();
-    try {
-      await this._inFlight;
-    } finally {
-      this._inFlight = null;
-    }
-    return this._cache?.payload ?? null;
-  }
-}
-
-// ---------- tree-item rendering ----------
-
-export function isSilent(data: ProviderHeartbeat, silentMinutes: number): boolean {
-  // No signal file or no completions ever recorded both count as silent —
-  // the operator cannot tell the difference between "never ran" and "stopped
-  // running" without other context, and either way the provider has not
-  // produced anything.
-  if (!data.signal_file_present) return true;
-  if (data.minutes_since_last_completion === null) return true;
-  return data.minutes_since_last_completion > silentMinutes;
-}
-
-export function formatMinutesAgo(m: number | null): string {
-  if (m === null) return "never";
-  if (m < 60) return `${m} min ago`;
-  const h = Math.floor(m / 60);
-  const rem = m % 60;
-  return rem === 0 ? `${h}h ago` : `${h}h ${rem}m ago`;
-}
-
-export function buildTreeItem(node: HeartbeatTreeNode): vscode.TreeItem {
-  switch (node.kind) {
-    case "provider": {
-      const d = node.data;
-      const silent = isSilent(d, node.silentWarningMinutes);
-      const item = new vscode.TreeItem(
-        node.provider,
-        vscode.TreeItemCollapsibleState.None,
-      );
-      const lookback = d.lookback_minutes;
-      if (!d.signal_file_present) {
-        item.description = "no capacity signal yet";
-      } else if (d.minutes_since_last_completion === null) {
-        item.description = `silent · 0 completions / ${lookback}m`;
-      } else {
-        const ago = formatMinutesAgo(d.minutes_since_last_completion);
-        item.description = `last seen ${ago} · ${d.completions_in_window} completions / ${lookback}m`;
-      }
-      item.iconPath = new vscode.ThemeIcon(
-        silent ? "warning" : "pulse",
-        silent
-          ? new vscode.ThemeColor("notificationsWarningIcon.foreground")
-          : undefined,
-      );
-      item.tooltip = buildProviderTooltip(node.provider, d, silent);
-      item.contextValue = silent ? "heartbeatProvider:silent" : "heartbeatProvider:active";
-      return item;
-    }
-    case "info": {
-      const item = new vscode.TreeItem(node.label, vscode.TreeItemCollapsibleState.None);
-      item.description = node.detail;
-      item.tooltip = node.detail ? new vscode.MarkdownString(node.detail) : undefined;
-      item.iconPath = new vscode.ThemeIcon(node.isError ? "warning" : "info");
-      item.contextValue = node.isError ? "heartbeatInfo:error" : "heartbeatInfo";
-      return item;
-    }
-    case "notInstalled": {
-      const item = new vscode.TreeItem(
-        "ai_router not installed in this Python environment.",
-        vscode.TreeItemCollapsibleState.Expanded,
-      );
-      item.iconPath = new vscode.ThemeIcon("info");
-      item.contextValue = "heartbeatInfo:notInstalled";
-      return item;
-    }
-    case "notInstalledAction": {
-      const item = new vscode.TreeItem(
-        'Click here to run "Dabbler: Install ai-router"',
-        vscode.TreeItemCollapsibleState.None,
-      );
-      item.iconPath = new vscode.ThemeIcon("cloud-download");
-      item.command = {
-        command: "dabblerSessionSets.installAiRouter",
-        title: "Install ai-router",
-      };
-      item.contextValue = "heartbeatInfo:notInstalledAction";
-      return item;
-    }
-  }
-}
-
-function buildProviderTooltip(
-  provider: string,
-  d: ProviderHeartbeat,
-  silent: boolean,
-): vscode.MarkdownString {
-  const lines: string[] = [
-    `**${provider}** ${silent ? "· ⚠️ silent" : ""}`.trim(),
-    `Last completion: ${d.last_completion_at ?? "—"}`,
-    `Completions in last ${d.lookback_minutes}m: ${d.completions_in_window}`,
-    `Tokens in last ${d.lookback_minutes}m: ${d.tokens_in_window}`,
-    `Signal file: \`${d.signal_path}\``,
-    `_${d.disclaimer}_`,
-  ];
-  return new vscode.MarkdownString(lines.join("\n\n"));
-}
-
-// ---------- default fetcher (production path) ----------
-
-async function defaultFetchPayload(
-  workspaceRoot: string,
-  lookbackMinutes: number,
-): Promise<
-  | { ok: true; payload: HeartbeatStatusPayload }
-  | { ok: false; message: string; reason?: "module_not_installed" }
-> {
-  const result = await runPythonModule({
-    cwd: workspaceRoot,
-    module: "ai_router.heartbeat_status",
-    args: [
-      "--format",
-      "json",
-      "--lookback-minutes",
-      String(lookbackMinutes),
-    ],
-    pythonPathSetting: "dabblerProviderQueues.pythonPath",
-  });
-  return parseFetchResult(result, lookbackMinutes);
-}
-
-export function parseFetchResult(
-  result: PythonRunResult,
-  lookbackMinutes: number,
-): { ok: true; payload: HeartbeatStatusPayload } | { ok: false; message: string; reason?: "module_not_installed" } {
-  if (result.timedOut) {
-    return { ok: false, message: "heartbeat_status timed out (10s)" };
-  }
-  if (result.exitCode !== 0) {
-    if (isAiRouterNotInstalled(result.stderr)) {
-      return {
-        ok: false,
-        message: "ai_router is not installed in the configured Python environment.",
-        reason: "module_not_installed",
-      };
-    }
-    const trimmed = (result.stderr || result.stdout).trim();
-    const detail = trimmed ? ` — ${trimmed.split("\n").slice(-3).join(" / ")}` : "";
-    return {
-      ok: false,
-      message: `heartbeat_status exited ${result.exitCode}${detail}`,
-    };
-  }
-  try {
-    const raw = JSON.parse(result.stdout) as {
-      providers: Record<string, Record<string, unknown>>;
-      _disclaimer?: string;
-    };
-    if (!raw || typeof raw !== "object" || !raw.providers) {
-      return { ok: false, message: "heartbeat_status returned malformed JSON (missing 'providers')" };
-    }
-    const providers: Record<string, ProviderHeartbeat> = {};
-    for (const [name, info] of Object.entries(raw.providers)) {
-      providers[name] = normalizeProvider(info, lookbackMinutes);
-    }
-    return {
-      ok: true,
-      payload: { providers, disclaimer: String(raw._disclaimer ?? HEARTBEAT_FOOTER) },
-    };
-  } catch (err) {
-    const msg = err instanceof Error ? err.message : String(err);
-    return { ok: false, message: `Failed to parse heartbeat_status JSON: ${msg}` };
-  }
-}
-
-/**
- * Normalize the Python payload's embedded-N field names
- * (``completions_in_last_60min``) into stable names. Falls back to the
- * default lookback if the payload disagrees with the request — defensive
- * against a future helper-version mismatch where the CLI ignores
- * ``--lookback-minutes`` or rounds it.
- */
-function normalizeProvider(
-  info: Record<string, unknown>,
-  requestedLookback: number,
-): ProviderHeartbeat {
-  const lookback =
-    typeof info.lookback_minutes === "number" ? info.lookback_minutes : requestedLookback;
-  const completions =
-    pickNumber(info, `completions_in_last_${lookback}min`) ??
-    pickNumber(info, `completions_in_last_${requestedLookback}min`) ??
-    0;
-  const tokens =
-    pickNumber(info, `tokens_in_last_${lookback}min`) ??
-    pickNumber(info, `tokens_in_last_${requestedLookback}min`) ??
-    0;
-  return {
-    signal_path: String(info.signal_path ?? ""),
-    signal_file_present: Boolean(info.signal_file_present),
-    last_completion_at:
-      typeof info.last_completion_at === "string" ? info.last_completion_at : null,
-    minutes_since_last_completion:
-      typeof info.minutes_since_last_completion === "number"
-        ? info.minutes_since_last_completion
-        : null,
-    completions_in_window: completions,
-    tokens_in_window: tokens,
-    lookback_minutes: lookback,
-    disclaimer: String(info._disclaimer ?? HEARTBEAT_FOOTER),
-  };
-}
-
-function pickNumber(obj: Record<string, unknown>, key: string): number | null {
-  const v = obj[key];
-  return typeof v === "number" ? v : null;
-}
diff --git a/tools/dabbler-ai-orchestration/src/providers/ProviderQueuesProvider.ts b/tools/dabbler-ai-orchestration/src/providers/ProviderQueuesProvider.ts
deleted file mode 100644
index 5e9466e..0000000
--- a/tools/dabbler-ai-orchestration/src/providers/ProviderQueuesProvider.ts
+++ /dev/null
@@ -1,481 +0,0 @@
-import * as vscode from "vscode";
-import { runPythonModule, PythonRunResult } from "../utils/pythonRunner";
-import { isAiRouterNotInstalled } from "../utils/aiRouterInstall";
-
-/**
- * Tree view backing the ``Provider Queues`` activity-bar entry.
- *
- * Reads queue state by shelling out to ``python -m ai_router.queue_status
- * --format json`` rather than embedding a SQLite client in the extension.
- * Two reasons to keep the source-of-truth on the Python side:
- *
- * 1. The queue schema lives in :mod:`queue_db`. A second TS reader would
- *    drift the moment the next migration lands.
- * 2. Right-click interventions (Mark Failed, Force Reclaim) need the same
- *    transactional guarantees as the role-loop daemons; reusing the Python
- *    helper inherits them for free.
- *
- * The provider caches the parsed JSON for ``CACHE_TTL_MS`` so a tree
- * expand/collapse cycle doesn't re-spawn Python on every click. The
- * auto-refresh interval (configurable, default 15s) drives the visible
- * refresh cadence.
- */
-
-// Mirrors `ai_router.queue_db.VALID_STATES`. Update both lists together if
-// the queue state machine ever grows a new state.
-export const QUEUE_STATES = ["new", "claimed", "completed", "failed", "timed_out"] as const;
-export type QueueState = (typeof QUEUE_STATES)[number];
-
-export interface QueueMessageSummary {
-  id: string;
-  task_type: string;
-  session_set: string | null;
-  session_number: number | null;
-  state: QueueState;
-  claimed_by: string | null;
-  lease_expires_at: string | null;
-  enqueued_at: string;
-  completed_at?: string | null;
-  attempts: number;
-  max_attempts: number;
-  from_provider: string;
-}
-
-export interface ProviderQueueInfo {
-  queue_path: string;
-  queue_present: boolean;
-  states: Record<QueueState, number>;
-  messages: QueueMessageSummary[];
-}
-
-export interface QueueStatusPayload {
-  providers: Record<string, ProviderQueueInfo>;
-}
-
-const CACHE_TTL_MS = 5_000;
-
-// Codicon names by queue state, picked from the built-in product icons so we
-// don't have to ship SVGs. The spec calls for state-correlated glyphs; these
-// codicons read cleanly in both light and dark themes.
-const STATE_ICONS: Record<QueueState, string> = {
-  new: "circle-large-outline",
-  claimed: "sync",
-  completed: "pass",
-  failed: "error",
-  timed_out: "watch",
-};
-
-const STATE_LABELS: Record<QueueState, string> = {
-  new: "new",
-  claimed: "claimed",
-  completed: "completed",
-  failed: "failed",
-  timed_out: "timed_out",
-};
-
-// ---------- tree node shapes ----------
-
-export type QueueTreeNode =
-  | RootNode
-  | ProviderNode
-  | StateGroupNode
-  | MessageNode
-  | InfoNode
-  | NotInstalledNode
-  | NotInstalledActionNode;
-
-interface RootNode {
-  kind: "root";
-}
-interface ProviderNode {
-  kind: "provider";
-  provider: string;
-  info: ProviderQueueInfo;
-}
-interface StateGroupNode {
-  kind: "stateGroup";
-  provider: string;
-  state: QueueState;
-  count: number;
-  messages: QueueMessageSummary[];
-}
-interface MessageNode {
-  kind: "message";
-  provider: string;
-  message: QueueMessageSummary;
-}
-interface InfoNode {
-  kind: "info";
-  label: string;
-  detail?: string;
-  isError?: boolean;
-}
-/**
- * Surfaced when ``python -m ai_router.queue_status`` fails because the
- * ``ai_router`` package is not installed in the configured Python
- * environment. Has one child :class:`NotInstalledActionNode` carrying
- * the install command — separate from the generic red-error info node
- * so first-time users get a single click to the fix instead of an opaque
- * traceback.
- */
-interface NotInstalledNode {
-  kind: "notInstalled";
-}
-interface NotInstalledActionNode {
-  kind: "notInstalledAction";
-}
-
-// ---------- provider ----------
-
-export interface ProviderQueuesDeps {
-  /** Returns the workspace root that owns ``ai_router/`` and ``provider-queues/``. */
-  getWorkspaceRoot: () => string | undefined;
-  /** Spawn helper. Injected for tests. */
-  fetchPayload?: (
-    workspaceRoot: string,
-  ) => Promise<
-    | { ok: true; payload: QueueStatusPayload }
-    | { ok: false; message: string; reason?: "module_not_installed" }
-  >;
-  /** Clock — overridable for tests. */
-  now?: () => number;
-}
-
-export class ProviderQueuesProvider implements vscode.TreeDataProvider<QueueTreeNode> {
-  private readonly _onDidChangeTreeData = new vscode.EventEmitter<QueueTreeNode | undefined | void>();
-  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
-
-  private _cache:
-    | { fetchedAt: number; payload: QueueStatusPayload }
-    | null = null;
-  private _lastError: string | null = null;
-  private _lastErrorReason: "module_not_installed" | null = null;
-  private _inFlight: Promise<void> | null = null;
-
-  constructor(private readonly deps: ProviderQueuesDeps) {}
-
-  refresh(): void {
-    this._cache = null;
-    this._onDidChangeTreeData.fire();
-  }
-
-  /** Test-only — inject a payload directly and skip the spawn path. */
-  _setPayloadForTest(payload: QueueStatusPayload): void {
-    this._cache = { fetchedAt: (this.deps.now?.() ?? Date.now()), payload };
-    this._lastError = null;
-  }
-
-  // ---------- TreeDataProvider ----------
-
-  getTreeItem(element: QueueTreeNode): vscode.TreeItem {
-    return buildTreeItem(element);
-  }
-
-  async getChildren(element?: QueueTreeNode): Promise<QueueTreeNode[]> {
-    const root = this.deps.getWorkspaceRoot();
-    if (!root) {
-      return [
-        { kind: "info", label: "No workspace folder open." },
-      ];
-    }
-
-    if (!element || element.kind === "root") {
-      const payload = await this._getPayload(root);
-      if (!payload) {
-        if (this._lastErrorReason === "module_not_installed") {
-          return [{ kind: "notInstalled" }];
-        }
-        const detail = this._lastError ?? "Unknown error.";
-        return [
-          { kind: "info", label: "Failed to read queue status.", detail, isError: true },
-        ];
-      }
-      const providers = Object.keys(payload.providers).sort();
-      if (providers.length === 0) {
-        return [
-          {
-            kind: "info",
-            label: "No provider queues found.",
-            detail: "Looked for queue.db files under provider-queues/. Run a session that routes work to populate this view.",
-          },
-        ];
-      }
-      return providers.map<ProviderNode>((p) => ({
-        kind: "provider",
-        provider: p,
-        info: payload.providers[p],
-      }));
-    }
-
-    if (element.kind === "provider") {
-      if (!element.info.queue_present) {
-        return [
-          {
-            kind: "info",
-            label: "queue.db not present",
-            detail: element.info.queue_path,
-          },
-        ];
-      }
-      // One bucket per state, in queue-db lifecycle order.
-      return QUEUE_STATES.map<StateGroupNode>((state) => {
-        const count = element.info.states[state] ?? 0;
-        const messages = element.info.messages.filter((m) => m.state === state);
-        return {
-          kind: "stateGroup",
-          provider: element.provider,
-          state,
-          count,
-          messages,
-        };
-      });
-    }
-
-    if (element.kind === "notInstalled") {
-      return [{ kind: "notInstalledAction" }];
-    }
-
-    if (element.kind === "stateGroup") {
-      // The Python helper caps the message list (--limit, default 50). When the
-      // count exceeds the messages we got back, surface the gap so the operator
-      // doesn't think the queue is shorter than it is.
-      const items: QueueTreeNode[] = element.messages.map<MessageNode>((m) => ({
-        kind: "message",
-        provider: element.provider,
-        message: m,
-      }));
-      if (element.count > element.messages.length) {
-        items.push({
-          kind: "info",
-          label: `… ${element.count - element.messages.length} more not shown`,
-          detail: "Increase dabblerProviderQueues.messageLimit to see more.",
-        });
-      }
-      return items;
-    }
-
-    return [];
-  }
-
-  // ---------- internals ----------
-
-  private async _getPayload(root: string): Promise<QueueStatusPayload | null> {
-    const now = this.deps.now?.() ?? Date.now();
-    if (this._cache && now - this._cache.fetchedAt < CACHE_TTL_MS) {
-      return this._cache.payload;
-    }
-    if (this._inFlight) {
-      await this._inFlight;
-      return this._cache?.payload ?? null;
-    }
-    const fetcher = this.deps.fetchPayload ?? defaultFetchPayload;
-    this._inFlight = (async () => {
-      const result = await fetcher(root);
-      if (result.ok) {
-        this._cache = { fetchedAt: this.deps.now?.() ?? Date.now(), payload: result.payload };
-        this._lastError = null;
-        this._lastErrorReason = null;
-      } else {
-        this._lastError = result.message;
-        this._lastErrorReason = result.reason ?? null;
-        // Round-5 verifier catch: clear the cache on failure so the
-        // failure surfaces. Otherwise a previously-successful fetch
-        // would mask the new ``module_not_installed`` / red-error
-        // states until the next successful refresh, which on the
-        // not-installed path never comes.
-        this._cache = null;
-      }
-    })();
-    try {
-      await this._inFlight;
-    } finally {
-      this._inFlight = null;
-    }
-    return this._cache?.payload ?? null;
-  }
-}
-
-// ---------- tree-item rendering ----------
-
-export function buildTreeItem(node: QueueTreeNode): vscode.TreeItem {
-  switch (node.kind) {
-    case "root": {
-      const item = new vscode.TreeItem("Provider Queues", vscode.TreeItemCollapsibleState.Expanded);
-      item.contextValue = "queueRoot";
-      return item;
-    }
-    case "provider": {
-      const item = new vscode.TreeItem(
-        node.provider,
-        vscode.TreeItemCollapsibleState.Expanded,
-      );
-      const totals = node.info.states;
-      const total = QUEUE_STATES.reduce((acc, s) => acc + (totals[s] ?? 0), 0);
-      const claimed = totals.claimed ?? 0;
-      const failed = totals.failed ?? 0;
-      const timedOut = totals.timed_out ?? 0;
-      const bits: string[] = [`${total} msgs`];
-      if (claimed > 0) bits.push(`${claimed} claimed`);
-      if (failed > 0) bits.push(`${failed} failed`);
-      if (timedOut > 0) bits.push(`${timedOut} timed_out`);
-      item.description = bits.join("  ·  ");
-      item.iconPath = node.info.queue_present
-        ? new vscode.ThemeIcon("database")
-        : new vscode.ThemeIcon("circle-slash");
-      item.tooltip = new vscode.MarkdownString(
-        [
-          `**${node.provider}**`,
-          `Queue: \`${node.info.queue_path}\``,
-          node.info.queue_present ? null : "_queue.db not yet created_",
-        ]
-          .filter(Boolean)
-          .join("\n\n"),
-      );
-      item.contextValue = `queueProvider:${node.info.queue_present ? "present" : "absent"}`;
-      return item;
-    }
-    case "stateGroup": {
-      // Empty buckets collapsed; non-empty expanded. Mirrors how the operator
-      // typically wants to scan the view: claimed/failed jump out, completed
-      // is usually a long uninteresting list.
-      const collapsible =
-        node.count > 0 && node.state !== "completed"
-          ? vscode.TreeItemCollapsibleState.Expanded
-          : node.count > 0
-            ? vscode.TreeItemCollapsibleState.Collapsed
-            : vscode.TreeItemCollapsibleState.None;
-      const item = new vscode.TreeItem(
-        `${STATE_LABELS[node.state]} (${node.count})`,
-        collapsible,
-      );
-      item.iconPath = new vscode.ThemeIcon(STATE_ICONS[node.state]);
-      item.contextValue = `queueState:${node.state}`;
-      return item;
-    }
-    case "message": {
-      const m = node.message;
-      const idShort = m.id.length > 8 ? m.id.slice(0, 8) : m.id;
-      const ss = m.session_set ?? "-";
-      const sn = m.session_number ?? "-";
-      const item = new vscode.TreeItem(
-        `${idShort}  ·  ${m.task_type}`,
-        vscode.TreeItemCollapsibleState.None,
-      );
-      const descBits: string[] = [`${ss}/${sn}`];
-      if (m.claimed_by) descBits.push(`by=${m.claimed_by}`);
-      if (m.attempts > 0) descBits.push(`try ${m.attempts}/${m.max_attempts}`);
-      item.description = descBits.join("  ·  ");
-      item.iconPath = new vscode.ThemeIcon(STATE_ICONS[m.state]);
-      item.tooltip = buildMessageTooltip(node.provider, m);
-      item.contextValue = `queueMessage:${m.state}`;
-      // Single-click opens the payload — same as the right-click action.
-      item.command = {
-        command: "dabblerProviderQueues.openPayload",
-        title: "Open Payload",
-        arguments: [node],
-      };
-      return item;
-    }
-    case "info": {
-      const item = new vscode.TreeItem(node.label, vscode.TreeItemCollapsibleState.None);
-      item.description = node.detail;
-      item.tooltip = node.detail ? new vscode.MarkdownString(node.detail) : undefined;
-      item.iconPath = new vscode.ThemeIcon(node.isError ? "warning" : "info");
-      item.contextValue = node.isError ? "queueInfo:error" : "queueInfo";
-      return item;
-    }
-    case "notInstalled": {
-      const item = new vscode.TreeItem(
-        "ai_router not installed in this Python environment.",
-        vscode.TreeItemCollapsibleState.Expanded,
-      );
-      // Neutral info icon — this is a "configuration needed" state, not
-      // an error. The red-error path remains for genuine failures (other
-      // non-zero exits, malformed JSON, timeouts).
-      item.iconPath = new vscode.ThemeIcon("info");
-      item.contextValue = "queueInfo:notInstalled";
-      return item;
-    }
-    case "notInstalledAction": {
-      const item = new vscode.TreeItem(
-        'Click here to run "Dabbler: Install ai-router"',
-        vscode.TreeItemCollapsibleState.None,
-      );
-      item.iconPath = new vscode.ThemeIcon("cloud-download");
-      item.command = {
-        command: "dabblerSessionSets.installAiRouter",
-        title: "Install ai-router",
-      };
-      item.contextValue = "queueInfo:notInstalledAction";
-      return item;
-    }
-  }
-}
-
-function buildMessageTooltip(provider: string, m: QueueMessageSummary): vscode.MarkdownString {
-  const lines: string[] = [
-    `**${m.task_type}** · ${m.state}`,
-    `Provider: ${provider}`,
-    `ID: \`${m.id}\``,
-    `Session set: ${m.session_set ?? "—"} / session ${m.session_number ?? "—"}`,
-    `From provider: ${m.from_provider}`,
-    `Enqueued: ${m.enqueued_at}`,
-    `Attempts: ${m.attempts} / ${m.max_attempts}`,
-  ];
-  if (m.claimed_by) lines.push(`Claimed by: ${m.claimed_by}`);
-  if (m.lease_expires_at) lines.push(`Lease expires: ${m.lease_expires_at}`);
-  if (m.completed_at) lines.push(`Completed: ${m.completed_at}`);
-  return new vscode.MarkdownString(lines.join("\n\n"));
-}
-
-// ---------- default fetcher (production path) ----------
-
-async function defaultFetchPayload(
-  workspaceRoot: string,
-): Promise<
-  | { ok: true; payload: QueueStatusPayload }
-  | { ok: false; message: string; reason?: "module_not_installed" }
-> {
-  const cfg = vscode.workspace.getConfiguration("dabblerProviderQueues");
-  const limit = cfg.get<number>("messageLimit", 50);
-  const result = await runPythonModule({
-    cwd: workspaceRoot,
-    module: "ai_router.queue_status",
-    args: ["--format", "json", "--limit", String(limit)],
-    pythonPathSetting: "dabblerProviderQueues.pythonPath",
-  });
-  return parseFetchResult(result);
-}
-
-export function parseFetchResult(
-  result: PythonRunResult,
-): { ok: true; payload: QueueStatusPayload } | { ok: false; message: string; reason?: "module_not_installed" } {
-  if (result.timedOut) {
-    return { ok: false, message: "queue_status timed out (10s)" };
-  }
-  if (result.exitCode !== 0) {
-    if (isAiRouterNotInstalled(result.stderr)) {
-      return {
-        ok: false,
-        message: "ai_router is not installed in the configured Python environment.",
-        reason: "module_not_installed",
-      };
-    }
-    const trimmed = (result.stderr || result.stdout).trim();
-    const detail = trimmed ? ` — ${trimmed.split("\n").slice(-3).join(" / ")}` : "";
-    return {
-      ok: false,
-      message: `queue_status exited ${result.exitCode}${detail}`,
-    };
-  }
-  try {
-    const parsed = JSON.parse(result.stdout) as QueueStatusPayload;
-    if (!parsed || typeof parsed !== "object" || !parsed.providers) {
-      return { ok: false, message: "queue_status returned malformed JSON (missing 'providers')" };
-    }
-    return { ok: true, payload: parsed };
-  } catch (err) {
-    const msg = err instanceof Error ? err.message : String(err);
-    return { ok: false, message: `Failed to parse queue_status JSON: ${msg}` };
-  }
-}
diff --git a/tools/dabbler-ai-orchestration/src/test/suite/installAiRouter.test.ts b/tools/dabbler-ai-orchestration/src/test/suite/installAiRouter.test.ts
index 0cbbd2c..5877239 100644
--- a/tools/dabbler-ai-orchestration/src/test/suite/installAiRouter.test.ts
+++ b/tools/dabbler-ai-orchestration/src/test/suite/installAiRouter.test.ts
@@ -19,16 +19,6 @@ import {
   GITHUB_CHECKOUT_REL,
   REPO_URL,
 } from "../../utils/aiRouterInstall";
-import {
-  ProviderQueuesProvider,
-  buildTreeItem as buildQueueTreeItem,
-  parseFetchResult as parseQueueFetchResult,
-} from "../../providers/ProviderQueuesProvider";
-import {
-  ProviderHeartbeatsProvider,
-  buildTreeItem as buildHeartbeatTreeItem,
-  parseFetchResult as parseHeartbeatFetchResult,
-} from "../../providers/ProviderHeartbeatsProvider";
 
 // Standalone-mocha pattern: no electron host required. Each test wires up
 // a sandbox workspace under os.tmpdir(), an in-process spawner that
@@ -1033,285 +1023,3 @@ suite("aiRouterInstall — install-method marker round-trip", () => {
     fs.rmSync(ws, { recursive: true, force: true });
   });
 });
-
-// ---------- Provider graceful "not installed" path ----------
-
-function fakeRun(over: Partial<{
-  stdout: string;
-  stderr: string;
-  exitCode: number | null;
-  timedOut: boolean;
-}> = {}) {
-  return {
-    stdout: "",
-    stderr: "",
-    exitCode: 0 as number | null,
-    signal: null,
-    timedOut: false,
-    ...over,
-  };
-}
-
-suite("ProviderQueuesProvider — graceful not-installed (parseFetchResult)", () => {
-  test("returns reason=module_not_installed for the ai_router import error", () => {
-    const r = parseQueueFetchResult(
-      fakeRun({
-        exitCode: 1,
-        stderr:
-          "Error while finding module specification for 'ai_router.queue_status' (ModuleNotFoundError: No module named 'ai_router')",
-      }),
-    );
-    assert.strictEqual(r.ok, false);
-    if (!r.ok) {
-      assert.strictEqual(r.reason, "module_not_installed");
-      assert.match(r.message, /not installed/);
-    }
-  });
-
-  test("leaves reason undefined for unrelated non-zero exits", () => {
-    const r = parseQueueFetchResult(fakeRun({ exitCode: 2, stderr: "RuntimeError: queue corrupt" }));
-    assert.strictEqual(r.ok, false);
-    if (!r.ok) {
-      assert.strictEqual(r.reason, undefined);
-      assert.match(r.message, /exited 2/);
-    }
-  });
-});
-
-suite("ProviderQueuesProvider — failure invalidates cache (no stale-data masking)", () => {
-  test("a successful fetch followed by a module_not_installed failure renders notInstalled, not the cached payload", async () => {
-    const successPayload = {
-      providers: {
-        anthropic: {
-          queue_path: "/ws/provider-queues/anthropic/queue.db",
-          queue_present: true,
-          states: { new: 0 as number, claimed: 0, completed: 0, failed: 0, timed_out: 0 },
-          messages: [] as Array<unknown>,
-        },
-      },
-    };
-    // Manual clock so both refreshes fall on opposite sides of the
-    // 5s cache TTL. Each refresh advances the clock past CACHE_TTL_MS.
-    let nowMs = 1_000_000;
-    let call = 0;
-    const provider = new ProviderQueuesProvider({
-      getWorkspaceRoot: () => "/ws",
-      now: () => nowMs,
-      fetchPayload: async () => {
-        call++;
-        if (call === 1) return { ok: true, payload: successPayload as never };
-        return {
-          ok: false,
-          message: "ai_router is not installed in the configured Python environment.",
-          reason: "module_not_installed",
-        };
-      },
-    });
-
-    const first = await provider.getChildren();
-    assert.ok(first.length > 0 && first[0].kind === "provider",
-      "first refresh should surface the cached success payload");
-
-    nowMs += 10_000; // advance past CACHE_TTL_MS so the next call refetches
-    const second = await provider.getChildren();
-    assert.strictEqual(second.length, 1);
-    assert.strictEqual(second[0].kind, "notInstalled",
-      "second refresh must surface notInstalled, not the cached success payload");
-  });
-
-  test("a successful fetch followed by an unrelated non-zero failure renders the red-error info node, not the cached payload", async () => {
-    const successPayload = {
-      providers: {
-        anthropic: {
-          queue_path: "/ws/provider-queues/anthropic/queue.db",
-          queue_present: true,
-          states: { new: 0 as number, claimed: 0, completed: 0, failed: 0, timed_out: 0 },
-          messages: [] as Array<unknown>,
-        },
-      },
-    };
-    let nowMs = 1_000_000;
-    let call = 0;
-    const provider = new ProviderQueuesProvider({
-      getWorkspaceRoot: () => "/ws",
-      now: () => nowMs,
-      fetchPayload: async () => {
-        call++;
-        if (call === 1) return { ok: true, payload: successPayload as never };
-        return { ok: false, message: "queue_status exited 2 — RuntimeError: queue corrupt" };
-      },
-    });
-
-    await provider.getChildren();
-    nowMs += 10_000;
-    const second = await provider.getChildren();
-    assert.strictEqual(second.length, 1);
-    assert.strictEqual(second[0].kind, "info");
-    assert.strictEqual(
-      (second[0] as { isError?: boolean }).isError,
-      true,
-    );
-  });
-});
-
-suite("ProviderHeartbeatsProvider — failure invalidates cache (no stale-data masking)", () => {
-  test("a successful fetch followed by a module_not_installed failure renders notInstalled, not the cached payload", async () => {
-    const successPayload = {
-      providers: {
-        anthropic: {
-          signal_path: "/ws/provider-queues/anthropic/capacity_signal.jsonl",
-          signal_file_present: true,
-          last_completion_at: "2026-04-30T14:00:00Z",
-          minutes_since_last_completion: 12,
-          completions_in_window: 3,
-          tokens_in_window: 4231,
-          lookback_minutes: 60,
-          disclaimer: "obs only",
-        },
-      },
-      disclaimer: "obs only",
-    };
-    let nowMs = 1_000_000;
-    let call = 0;
-    const provider = new ProviderHeartbeatsProvider({
-      getWorkspaceRoot: () => "/ws",
-      now: () => nowMs,
-      getSettings: () => ({ lookbackMinutes: 60, silentWarningMinutes: 30 }),
-      fetchPayload: async () => {
-        call++;
-        if (call === 1) return { ok: true, payload: successPayload as never };
-        return {
-          ok: false,
-          message: "ai_router is not installed in the configured Python environment.",
-          reason: "module_not_installed",
-        };
-      },
-    });
-
-    const first = await provider.getChildren();
-    assert.ok(first.length > 0 && first[0].kind === "provider",
-      "first refresh should surface the cached success payload");
-
-    nowMs += 10_000;
-    const second = await provider.getChildren();
-    assert.strictEqual(second.length, 1);
-    assert.strictEqual(second[0].kind, "notInstalled");
-  });
-});
-
-suite("ProviderQueuesProvider — graceful not-installed tree-item rendering", () => {
-  function makeNotInstalledProvider(): ProviderQueuesProvider {
-    return new ProviderQueuesProvider({
-      getWorkspaceRoot: () => "/ws",
-      fetchPayload: async () => ({
-        ok: false,
-        message: "ai_router is not installed in the configured Python environment.",
-        reason: "module_not_installed",
-      }),
-    });
-  }
-
-  test("module_not_installed surfaces a notInstalled root with a clickable child", async () => {
-    const provider = makeNotInstalledProvider();
-    const top = await provider.getChildren();
-    assert.strictEqual(top.length, 1);
-    assert.strictEqual(top[0].kind, "notInstalled");
-
-    const children = await provider.getChildren(top[0]);
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "notInstalledAction");
-
-    const actionItem = buildQueueTreeItem(children[0]);
-    assert.strictEqual(actionItem.command?.command, "dabblerSessionSets.installAiRouter");
-    assert.strictEqual(actionItem.contextValue, "queueInfo:notInstalledAction");
-  });
-
-  test("notInstalled root uses a neutral info icon (not the red error icon) and a distinct contextValue", async () => {
-    const provider = makeNotInstalledProvider();
-    const top = await provider.getChildren();
-    const rootItem = buildQueueTreeItem(top[0]);
-    assert.strictEqual(rootItem.contextValue, "queueInfo:notInstalled");
-    // Distinguish from the existing error path (`queueInfo:error`); the
-    // not-installed state is "configuration needed", not a bug.
-    assert.notStrictEqual(rootItem.contextValue, "queueInfo:error");
-  });
-
-  test("unrelated non-zero exit still renders the existing red-error info node", async () => {
-    const provider = new ProviderQueuesProvider({
-      getWorkspaceRoot: () => "/ws",
-      fetchPayload: async () => ({ ok: false, message: "queue_status exited 2 — RuntimeError: queue corrupt" }),
-    });
-    const top = await provider.getChildren();
-    assert.strictEqual(top.length, 1);
-    assert.strictEqual(top[0].kind, "info");
-    const item = buildQueueTreeItem(top[0]);
-    assert.strictEqual(item.contextValue, "queueInfo:error");
-  });
-});
-
-suite("ProviderHeartbeatsProvider — graceful not-installed (parseFetchResult)", () => {
-  test("returns reason=module_not_installed for the ai_router import error", () => {
-    const r = parseHeartbeatFetchResult(
-      fakeRun({
-        exitCode: 1,
-        stderr:
-          "Error while finding module specification for 'ai_router.heartbeat_status' (ModuleNotFoundError: No module named 'ai_router')",
-      }),
-      60,
-    );
-    assert.strictEqual(r.ok, false);
-    if (!r.ok) {
-      assert.strictEqual(r.reason, "module_not_installed");
-      assert.match(r.message, /not installed/);
-    }
-  });
-
-  test("leaves reason undefined for unrelated non-zero exits", () => {
-    const r = parseHeartbeatFetchResult(
-      fakeRun({ exitCode: 2, stderr: "ConnectionRefusedError: signal file busy" }),
-      60,
-    );
-    assert.strictEqual(r.ok, false);
-    if (!r.ok) {
-      assert.strictEqual(r.reason, undefined);
-      assert.match(r.message, /exited 2/);
-    }
-  });
-});
-
-suite("ProviderHeartbeatsProvider — graceful not-installed tree-item rendering", () => {
-  function makeNotInstalledProvider(): ProviderHeartbeatsProvider {
-    return new ProviderHeartbeatsProvider({
-      getWorkspaceRoot: () => "/ws",
-      fetchPayload: async () => ({
-        ok: false,
-        message: "ai_router is not installed in the configured Python environment.",
-        reason: "module_not_installed",
-      }),
-      getSettings: () => ({ lookbackMinutes: 60, silentWarningMinutes: 30 }),
-    });
-  }
-
-  test("module_not_installed surfaces a notInstalled root with a clickable child", async () => {
-    const provider = makeNotInstalledProvider();
-    const top = await provider.getChildren();
-    assert.strictEqual(top.length, 1);
-    assert.strictEqual(top[0].kind, "notInstalled");
-
-    const children = await provider.getChildren(top[0]);
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "notInstalledAction");
-
-    const actionItem = buildHeartbeatTreeItem(children[0]);
-    assert.strictEqual(actionItem.command?.command, "dabblerSessionSets.installAiRouter");
-    assert.strictEqual(actionItem.contextValue, "heartbeatInfo:notInstalledAction");
-  });
-
-  test("notInstalled root uses a distinct contextValue from the red-error path", async () => {
-    const provider = makeNotInstalledProvider();
-    const top = await provider.getChildren();
-    const rootItem = buildHeartbeatTreeItem(top[0]);
-    assert.strictEqual(rootItem.contextValue, "heartbeatInfo:notInstalled");
-    assert.notStrictEqual(rootItem.contextValue, "heartbeatInfo:error");
-  });
-});
diff --git a/tools/dabbler-ai-orchestration/src/test/suite/providerHeartbeats.test.ts b/tools/dabbler-ai-orchestration/src/test/suite/providerHeartbeats.test.ts
deleted file mode 100644
index a0c48fc..0000000
--- a/tools/dabbler-ai-orchestration/src/test/suite/providerHeartbeats.test.ts
+++ /dev/null
@@ -1,274 +0,0 @@
-import * as assert from "assert";
-import * as vscode from "vscode";
-import {
-  ProviderHeartbeatsProvider,
-  HeartbeatStatusPayload,
-  HeartbeatTreeNode,
-  HEARTBEAT_FOOTER,
-  buildTreeItem,
-  formatMinutesAgo,
-  isSilent,
-  parseFetchResult,
-} from "../../providers/ProviderHeartbeatsProvider";
-
-const SETTINGS = { lookbackMinutes: 60, silentWarningMinutes: 30 };
-
-function samplePayload(): HeartbeatStatusPayload {
-  return {
-    disclaimer: HEARTBEAT_FOOTER,
-    providers: {
-      anthropic: {
-        signal_path: "/ws/provider-queues/anthropic/capacity_signal.jsonl",
-        signal_file_present: true,
-        last_completion_at: "2026-04-30T14:00:00Z",
-        minutes_since_last_completion: 12,
-        completions_in_window: 3,
-        tokens_in_window: 4231,
-        lookback_minutes: 60,
-        disclaimer: HEARTBEAT_FOOTER,
-      },
-      openai: {
-        signal_path: "/ws/provider-queues/openai/capacity_signal.jsonl",
-        signal_file_present: true,
-        last_completion_at: "2026-04-30T14:10:00Z",
-        minutes_since_last_completion: 2,
-        completions_in_window: 8,
-        tokens_in_window: 9001,
-        lookback_minutes: 60,
-        disclaimer: HEARTBEAT_FOOTER,
-      },
-      google: {
-        signal_path: "/ws/provider-queues/google/capacity_signal.jsonl",
-        signal_file_present: true,
-        last_completion_at: "2026-04-30T10:50:00Z",
-        minutes_since_last_completion: 202,
-        completions_in_window: 0,
-        tokens_in_window: 0,
-        lookback_minutes: 60,
-        disclaimer: HEARTBEAT_FOOTER,
-      },
-    },
-  };
-}
-
-function makeProvider(payload: HeartbeatStatusPayload): ProviderHeartbeatsProvider {
-  return new ProviderHeartbeatsProvider({
-    getWorkspaceRoot: () => "/ws",
-    fetchPayload: async () => ({ ok: true, payload }),
-    getSettings: () => SETTINGS,
-  });
-}
-
-suite("ProviderHeartbeatsProvider — tree shape", () => {
-  test("root level lists providers alphabetically", async () => {
-    const provider = makeProvider(samplePayload());
-    const children = await provider.getChildren();
-    assert.strictEqual(children.length, 3);
-    const names = children.map((c) => (c as { provider?: string }).provider);
-    assert.deepStrictEqual(names, ["anthropic", "google", "openai"]);
-  });
-
-  test("provider nodes are leaves (no further expansion)", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const grandchildren = await provider.getChildren(top[0]);
-    assert.deepStrictEqual(grandchildren, []);
-  });
-
-  test("empty payload renders a guidance info node, not an empty tree", async () => {
-    const provider = makeProvider({ providers: {}, disclaimer: HEARTBEAT_FOOTER });
-    const children = await provider.getChildren();
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "info");
-    assert.match((children[0] as { label: string }).label, /no provider capacity signals/i);
-  });
-
-  test("fetch failure surfaces an error info node", async () => {
-    const provider = new ProviderHeartbeatsProvider({
-      getWorkspaceRoot: () => "/ws",
-      fetchPayload: async () => ({ ok: false, message: "exit 2" }),
-      getSettings: () => SETTINGS,
-    });
-    const children = await provider.getChildren();
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "info");
-    assert.strictEqual((children[0] as { isError?: boolean }).isError, true);
-  });
-
-  test("missing workspace yields an info node", async () => {
-    const provider = new ProviderHeartbeatsProvider({
-      getWorkspaceRoot: () => undefined,
-      getSettings: () => SETTINGS,
-    });
-    const children = await provider.getChildren();
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "info");
-  });
-});
-
-suite("ProviderHeartbeatsProvider — silent-warning threshold", () => {
-  test("active provider (12m < 30m) is not silent", () => {
-    const d = samplePayload().providers.anthropic;
-    assert.strictEqual(isSilent(d, 30), false);
-  });
-
-  test("provider just above threshold (31m > 30m) is silent", () => {
-    const d = { ...samplePayload().providers.anthropic, minutes_since_last_completion: 31 };
-    assert.strictEqual(isSilent(d, 30), true);
-  });
-
-  test("provider exactly at threshold (30m, not >) is not silent", () => {
-    const d = { ...samplePayload().providers.anthropic, minutes_since_last_completion: 30 };
-    assert.strictEqual(isSilent(d, 30), false);
-  });
-
-  test("provider with no signal file is silent (covers never-ran case)", () => {
-    const d = { ...samplePayload().providers.anthropic, signal_file_present: false };
-    assert.strictEqual(isSilent(d, 30), true);
-  });
-
-  test("provider with file but no completions ever is silent", () => {
-    const d = {
-      ...samplePayload().providers.anthropic,
-      minutes_since_last_completion: null,
-    };
-    assert.strictEqual(isSilent(d, 30), true);
-  });
-
-  test("provider tree item uses warning icon when silent", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const google = top.find((n) => (n as { provider?: string }).provider === "google")!;
-    const item = buildTreeItem(google);
-    const icon = item.iconPath as vscode.ThemeIcon;
-    assert.strictEqual(icon.id, "warning");
-    assert.strictEqual(item.contextValue, "heartbeatProvider:silent");
-  });
-
-  test("provider tree item uses pulse icon when active", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const anthropic = top.find((n) => (n as { provider?: string }).provider === "anthropic")!;
-    const item = buildTreeItem(anthropic);
-    const icon = item.iconPath as vscode.ThemeIcon;
-    assert.strictEqual(icon.id, "pulse");
-    assert.strictEqual(item.contextValue, "heartbeatProvider:active");
-  });
-});
-
-suite("ProviderHeartbeatsProvider — rendering", () => {
-  test("description includes 'last seen' and completions/window", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const item = buildTreeItem(top.find((n) => (n as { provider?: string }).provider === "anthropic")!);
-    const desc = String(item.description);
-    assert.match(desc, /last seen 12 min ago/);
-    assert.match(desc, /3 completions \/ 60m/);
-  });
-
-  test("description for missing signal file is explicit", async () => {
-    const payload = samplePayload();
-    payload.providers.anthropic = {
-      ...payload.providers.anthropic,
-      signal_file_present: false,
-      minutes_since_last_completion: null,
-      completions_in_window: 0,
-    };
-    const provider = makeProvider(payload);
-    const top = await provider.getChildren();
-    const item = buildTreeItem(top.find((n) => (n as { provider?: string }).provider === "anthropic")!);
-    assert.strictEqual(String(item.description), "no capacity signal yet");
-  });
-
-  test("tooltip echoes the disclaimer", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const item = buildTreeItem(top[0]);
-    const tip = (item.tooltip as vscode.MarkdownString).value;
-    assert.match(tip, /Observational only/);
-  });
-
-  test("formatMinutesAgo: null → 'never'; <60 → 'Nm'; ≥60 → 'Hh Mm'", () => {
-    assert.strictEqual(formatMinutesAgo(null), "never");
-    assert.strictEqual(formatMinutesAgo(0), "0 min ago");
-    assert.strictEqual(formatMinutesAgo(45), "45 min ago");
-    assert.strictEqual(formatMinutesAgo(120), "2h ago");
-    assert.strictEqual(formatMinutesAgo(202), "3h 22m ago");
-  });
-});
-
-suite("ProviderHeartbeatsProvider — parseFetchResult", () => {
-  function fakeRun(over: Partial<{
-    stdout: string;
-    stderr: string;
-    exitCode: number | null;
-    timedOut: boolean;
-  }> = {}) {
-    return {
-      stdout: "",
-      stderr: "",
-      exitCode: 0,
-      signal: null,
-      timedOut: false,
-      ...over,
-    };
-  }
-
-  test("normalizes embedded-N field names to stable shape", () => {
-    const stdout = JSON.stringify({
-      providers: {
-        anthropic: {
-          signal_path: "/p",
-          signal_file_present: true,
-          last_completion_at: "2026-04-30T14:00:00Z",
-          minutes_since_last_completion: 5,
-          completions_in_last_60min: 7,
-          tokens_in_last_60min: 1234,
-          lookback_minutes: 60,
-          _disclaimer: "Observational only; …",
-        },
-      },
-      _disclaimer: "Observational only; …",
-    });
-    const r = parseFetchResult(fakeRun({ stdout }), 60);
-    assert.ok(r.ok);
-    if (r.ok) {
-      const a = r.payload.providers.anthropic;
-      assert.strictEqual(a.completions_in_window, 7);
-      assert.strictEqual(a.tokens_in_window, 1234);
-      assert.strictEqual(a.minutes_since_last_completion, 5);
-    }
-  });
-
-  test("falls back to default lookback when payload lookback differs", () => {
-    const stdout = JSON.stringify({
-      providers: {
-        anthropic: {
-          signal_path: "/p",
-          signal_file_present: true,
-          last_completion_at: null,
-          minutes_since_last_completion: null,
-          // Helper actually returned a 30m window even though we asked for 60.
-          completions_in_last_30min: 2,
-          tokens_in_last_30min: 99,
-          lookback_minutes: 30,
-        },
-      },
-    });
-    const r = parseFetchResult(fakeRun({ stdout }), 60);
-    assert.ok(r.ok);
-    if (r.ok) {
-      const a = r.payload.providers.anthropic;
-      assert.strictEqual(a.completions_in_window, 2);
-      assert.strictEqual(a.tokens_in_window, 99);
-      assert.strictEqual(a.lookback_minutes, 30);
-    }
-  });
-
-  test("rejects timeout, non-zero exit, malformed JSON, missing 'providers'", () => {
-    assert.strictEqual(parseFetchResult(fakeRun({ timedOut: true, exitCode: null }), 60).ok, false);
-    assert.strictEqual(parseFetchResult(fakeRun({ exitCode: 2, stderr: "boom" }), 60).ok, false);
-    assert.strictEqual(parseFetchResult(fakeRun({ stdout: "not json" }), 60).ok, false);
-    assert.strictEqual(parseFetchResult(fakeRun({ stdout: '{"foo":1}' }), 60).ok, false);
-  });
-});
diff --git a/tools/dabbler-ai-orchestration/src/test/suite/providerQueues.test.ts b/tools/dabbler-ai-orchestration/src/test/suite/providerQueues.test.ts
deleted file mode 100644
index bb16555..0000000
--- a/tools/dabbler-ai-orchestration/src/test/suite/providerQueues.test.ts
+++ /dev/null
@@ -1,240 +0,0 @@
-import * as assert from "assert";
-import * as vscode from "vscode";
-import {
-  ProviderQueuesProvider,
-  QueueStatusPayload,
-  QueueTreeNode,
-  buildTreeItem,
-  parseFetchResult,
-} from "../../providers/ProviderQueuesProvider";
-
-function samplePayload(): QueueStatusPayload {
-  return {
-    providers: {
-      anthropic: {
-        queue_path: "/ws/provider-queues/anthropic/queue.db",
-        queue_present: true,
-        states: { new: 1, claimed: 2, completed: 5, failed: 1, timed_out: 0 },
-        messages: [
-          {
-            id: "abcdef0123456789",
-            task_type: "session-verification",
-            session_set: "my-feature",
-            session_number: 3,
-            state: "claimed",
-            claimed_by: "verifier-google-1",
-            lease_expires_at: "2026-04-30T15:30:00Z",
-            enqueued_at: "2026-04-30T15:00:00Z",
-            attempts: 1,
-            max_attempts: 3,
-            from_provider: "anthropic",
-          },
-          {
-            id: "fedcba9876543210",
-            task_type: "session-verification",
-            session_set: "my-feature",
-            session_number: 2,
-            state: "completed",
-            claimed_by: null,
-            lease_expires_at: null,
-            enqueued_at: "2026-04-30T14:00:00Z",
-            completed_at: "2026-04-30T14:10:00Z",
-            attempts: 1,
-            max_attempts: 3,
-            from_provider: "anthropic",
-          },
-        ],
-      },
-      openai: {
-        queue_path: "/ws/provider-queues/openai/queue.db",
-        queue_present: false,
-        states: { new: 0, claimed: 0, completed: 0, failed: 0, timed_out: 0 },
-        messages: [],
-      },
-    },
-  };
-}
-
-function makeProvider(payload: QueueStatusPayload): ProviderQueuesProvider {
-  const provider = new ProviderQueuesProvider({
-    getWorkspaceRoot: () => "/ws",
-    fetchPayload: async () => ({ ok: true, payload }),
-  });
-  return provider;
-}
-
-suite("ProviderQueuesProvider — tree shape", () => {
-  test("root level lists providers alphabetically", async () => {
-    const provider = makeProvider(samplePayload());
-    const children = await provider.getChildren();
-    assert.strictEqual(children.length, 2);
-    assert.strictEqual(children[0].kind, "provider");
-    assert.strictEqual((children[0] as { provider: string }).provider, "anthropic");
-    assert.strictEqual((children[1] as { provider: string }).provider, "openai");
-  });
-
-  test("absent queue surfaces a single info child", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const openai = top.find(
-      (c) => c.kind === "provider" && (c as { provider: string }).provider === "openai",
-    );
-    assert.ok(openai, "expected openai provider node");
-    const children = await provider.getChildren(openai);
-    assert.strictEqual(children.length, 1);
-    assert.strictEqual(children[0].kind, "info");
-  });
-
-  test("present queue expands to one bucket per state in lifecycle order", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const anthropic = top.find(
-      (c) => c.kind === "provider" && (c as { provider: string }).provider === "anthropic",
-    );
-    assert.ok(anthropic);
-    const buckets = await provider.getChildren(anthropic);
-    assert.deepStrictEqual(
-      buckets.map((b) => (b as { state?: string }).state),
-      ["new", "claimed", "completed", "failed", "timed_out"],
-    );
-  });
-
-  test("state bucket holds only messages for that state", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const anthropic = top[0] as Extract<QueueTreeNode, { kind: "provider" }>;
-    const buckets = await provider.getChildren(anthropic);
-    const claimedBucket = buckets.find(
-      (b) => (b as { state?: string }).state === "claimed",
-    )!;
-    const completedBucket = buckets.find(
-      (b) => (b as { state?: string }).state === "completed",
-    )!;
-    const claimedMsgs = await provider.getChildren(claimedBucket);
-    const completedMsgs = await provider.getChildren(completedBucket);
-    assert.strictEqual(claimedMsgs.length, 1);
-    assert.strictEqual(claimedMsgs[0].kind, "message");
-    assert.strictEqual(completedMsgs.length, 1);
-    assert.strictEqual(completedMsgs[0].kind, "message");
-  });
-
-  test("state bucket appends 'more not shown' info node when count exceeds messages", async () => {
-    const payload = samplePayload();
-    payload.providers.anthropic.states.completed = 50; // 1 returned, 49 hidden
-    const provider = makeProvider(payload);
-    const top = await provider.getChildren();
-    const buckets = await provider.getChildren(top[0]);
-    const completedBucket = buckets.find(
-      (b) => (b as { state?: string }).state === "completed",
-    )!;
-    const items = await provider.getChildren(completedBucket);
-    assert.strictEqual(items.length, 2);
-    assert.strictEqual(items[1].kind, "info");
-    assert.match(
-      (items[1] as { label: string }).label,
-      /49 more not shown/,
-    );
-  });
-
-  test("empty payload renders a guidance info node, not an empty tree", async () => {
-    const provider = makeProvider({ providers: {} });
-    const top = await provider.getChildren();
-    assert.strictEqual(top.length, 1);
-    assert.strictEqual(top[0].kind, "info");
-    assert.match((top[0] as { label: string }).label, /no provider queues/i);
-  });
-
-  test("fetch failure surfaces an error info node", async () => {
-    const provider = new ProviderQueuesProvider({
-      getWorkspaceRoot: () => "/ws",
-      fetchPayload: async () => ({ ok: false, message: "exit 2" }),
-    });
-    const top = await provider.getChildren();
-    assert.strictEqual(top.length, 1);
-    assert.strictEqual(top[0].kind, "info");
-    assert.strictEqual((top[0] as { isError?: boolean }).isError, true);
-  });
-});
-
-suite("ProviderQueuesProvider — tree item rendering", () => {
-  test("provider node tooltip and description use queue totals", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const item = buildTreeItem(top[0]);
-    assert.match(String(item.description), /9 msgs/);
-    assert.match(String(item.description), /2 claimed/);
-    assert.match(String(item.description), /1 failed/);
-  });
-
-  test("message node carries openPayload command and queueMessage:<state> contextValue", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const buckets = await provider.getChildren(top[0]);
-    const claimedBucket = buckets.find(
-      (b) => (b as { state?: string }).state === "claimed",
-    )!;
-    const claimedMsgs = await provider.getChildren(claimedBucket);
-    const item = buildTreeItem(claimedMsgs[0]);
-    assert.strictEqual(item.contextValue, "queueMessage:claimed");
-    assert.strictEqual(item.command?.command, "dabblerProviderQueues.openPayload");
-  });
-
-  test("collapsible state buckets: 'completed' starts collapsed, 'claimed' expanded", async () => {
-    const provider = makeProvider(samplePayload());
-    const top = await provider.getChildren();
-    const buckets = await provider.getChildren(top[0]);
-    const completed = buildTreeItem(
-      buckets.find((b) => (b as { state?: string }).state === "completed")!,
-    );
-    const claimed = buildTreeItem(
-      buckets.find((b) => (b as { state?: string }).state === "claimed")!,
-    );
-    assert.strictEqual(completed.collapsibleState, vscode.TreeItemCollapsibleState.Collapsed);
-    assert.strictEqual(claimed.collapsibleState, vscode.TreeItemCollapsibleState.Expanded);
-  });
-});
-
-suite("ProviderQueuesProvider — parseFetchResult", () => {
-  function fakeRun(over: Partial<{
-    stdout: string;
-    stderr: string;
-    exitCode: number | null;
-    timedOut: boolean;
-  }> = {}) {
-    return {
-      stdout: "",
-      stderr: "",
-      exitCode: 0,
-      signal: null,
-      timedOut: false,
-      ...over,
-    };
-  }
-
-  test("parses valid JSON", () => {
-    const r = parseFetchResult(fakeRun({ stdout: '{"providers":{}}' }));
-    assert.ok(r.ok);
-    if (r.ok) assert.deepStrictEqual(r.payload.providers, {});
-  });
-
-  test("rejects timeout", () => {
-    const r = parseFetchResult(fakeRun({ timedOut: true, exitCode: null }));
-    assert.strictEqual(r.ok, false);
-  });
-
-  test("rejects non-zero exit", () => {
-    const r = parseFetchResult(fakeRun({ exitCode: 2, stderr: "boom" }));
-    assert.strictEqual(r.ok, false);
-    if (!r.ok) assert.match(r.message, /exited 2/);
-  });
-
-  test("rejects malformed JSON", () => {
-    const r = parseFetchResult(fakeRun({ stdout: "not json" }));
-    assert.strictEqual(r.ok, false);
-  });
-
-  test("rejects JSON missing 'providers' field", () => {
-    const r = parseFetchResult(fakeRun({ stdout: '{"foo":1}' }));
-    assert.strictEqual(r.ok, false);
-  });
-});
diff --git a/tools/dabbler-ai-orchestration/src/utils/aiRouterInstall.ts b/tools/dabbler-ai-orchestration/src/utils/aiRouterInstall.ts
index dfa698b..f6b5161 100644
--- a/tools/dabbler-ai-orchestration/src/utils/aiRouterInstall.ts
+++ b/tools/dabbler-ai-orchestration/src/utils/aiRouterInstall.ts
@@ -161,8 +161,7 @@ export function isAiRouterNotInstalled(stderr: string): boolean {
  *
  * Returns an :class:`InstallOutcome` describing what happened. Never throws
  * for spawn / fs failures — the outcome carries an operator-facing
- * ``message`` instead, mirroring the pattern in ``runPythonModule`` so the
- * UI can surface results uniformly.
+ * ``message`` instead, so the UI can surface results uniformly.
  */
 export async function installAiRouter(deps: InstallDeps): Promise<InstallOutcome> {
   return doInstall(deps, { mode: "install" });
diff --git a/tools/dabbler-ai-orchestration/src/utils/pythonRunner.ts b/tools/dabbler-ai-orchestration/src/utils/pythonRunner.ts
deleted file mode 100644
index c0d8e5a..0000000
--- a/tools/dabbler-ai-orchestration/src/utils/pythonRunner.ts
+++ /dev/null
@@ -1,93 +0,0 @@
-import * as cp from "child_process";
-import * as path from "path";
-import * as vscode from "vscode";
-
-export interface PythonRunOptions {
-  /** Path to the workspace root that owns the ai_router/ directory. */
-  cwd: string;
-  /** Module name passed to ``python -m`` (e.g. ``ai_router.queue_status``). */
-  module: string;
-  /** Module arguments. */
-  args: string[];
-  /** Configuration setting key holding the python executable path. */
-  pythonPathSetting: string;
-  /** Hard cap on the subprocess in ms. */
-  timeoutMs?: number;
-}
-
-export interface PythonRunResult {
-  stdout: string;
-  stderr: string;
-  exitCode: number | null;
-  signal: NodeJS.Signals | null;
-  /** True if the runner killed the process via ``timeoutMs``. */
-  timedOut: boolean;
-}
-
-/**
- * Resolve the configured Python interpreter for a given setting key.
- *
- * The setting holds a string like ``"python"`` or ``".venv/Scripts/python.exe"``.
- * Relative paths resolve against the workspace root so users can point at a
- * checked-in virtualenv without writing a machine-specific absolute path.
- */
-export function resolvePythonPath(workspaceRoot: string, settingKey: string): string {
-  const dotIndex = settingKey.indexOf(".");
-  if (dotIndex < 0) return "python";
-  const section = settingKey.slice(0, dotIndex);
-  const key = settingKey.slice(dotIndex + 1);
-  const cfg = vscode.workspace.getConfiguration(section);
-  const raw = (cfg.get<string>(key) ?? "python").trim();
-  if (!raw) return "python";
-  if (path.isAbsolute(raw)) return raw;
-  if (raw.includes(path.sep) || raw.includes("/")) {
-    return path.resolve(workspaceRoot, raw);
-  }
-  return raw;
-}
-
-/**
- * Spawn ``python -m <module> [args...]`` and resolve once the process exits.
- *
- * Always resolves — non-zero exit codes and timeouts are returned in the
- * result, never thrown — so the tree-view caller can render an error node
- * without try/catch noise around every refresh.
- */
-export function runPythonModule(opts: PythonRunOptions): Promise<PythonRunResult> {
-  const exe = resolvePythonPath(opts.cwd, opts.pythonPathSetting);
-  const timeoutMs = opts.timeoutMs ?? 10000;
-  return new Promise((resolve) => {
-    const child = cp.spawn(exe, ["-m", opts.module, ...opts.args], {
-      cwd: opts.cwd,
-      env: process.env,
-      windowsHide: true,
-    });
-    let stdout = "";
-    let stderr = "";
-    let timedOut = false;
-    const timer = setTimeout(() => {
-      timedOut = true;
-      child.kill();
-    }, timeoutMs);
-    child.stdout.on("data", (chunk: Buffer) => {
-      stdout += chunk.toString("utf8");
-    });
-    child.stderr.on("data", (chunk: Buffer) => {
-      stderr += chunk.toString("utf8");
-    });
-    child.on("error", (err: Error) => {
-      clearTimeout(timer);
-      resolve({
-        stdout,
-        stderr: stderr + (stderr ? "\n" : "") + `spawn error: ${err.message}`,
-        exitCode: null,
-        signal: null,
-        timedOut,
-      });
-    });
-    child.on("close", (code: number | null, signal: NodeJS.Signals | null) => {
-      clearTimeout(timer);
-      resolve({ stdout, stderr, exitCode: code, signal, timedOut });
-    });
-  });
-}

```
