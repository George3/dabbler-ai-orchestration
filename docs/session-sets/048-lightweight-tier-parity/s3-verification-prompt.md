# Set 048 Session 3 cross-provider verification request

## Context

Set 048 Session 3 ships the Lightweight-tier copyable-prompt commands and the context-menu IA refresh, combined into one session per the operator's audit Bias 7 disposition. The audit-locked spec is at `docs/session-sets/048-lightweight-tier-parity/spec.md` §3.2 (copyable-review-prompt commands), §3.3 (context-menu IA refresh — Bias 3 FLIP locks QuickPick), and §3.9 (review-criteria storage convention).

Operator-locked additions in scope:
- **L1.** Prompts MUST reference paths, never embed contents.
- **L2.** Open File submenu locked to exactly 4 entries: Spec / Activity Log / Change Log / Session State.
- **L3.** `Open AI Assignment` is fully removed from the menu, command registration, and dispatch allowlist.
- **L4.** Close-on-blur / Escape / explicit dismiss — free byproduct of `vscode.window.showQuickPick`.
- **L5.** Left-click ALWAYS opens spec.md; non-terminal rows ALSO copy `Start the next session of `<slug>`.` + info toast.

Test counts at close:
- TypeScript: 662 passed + 2 pre-existing failures unrelated to S3
  (configEditor-foundation + notificationsSection — both predate Set 048).
- Python: 994 collected (no Python changes in S3).

## What I'm asking you to verify

1. **Correctness** — Does the code do what the spec says? In particular: are the four copy-prompt builders correct under the L1 path-reference format? Does the two-step QuickPick correctly model the spec §3.3 menu structure?
2. **L1 compliance** — Could any of the prompt builders accidentally embed file content (read-and-splice) instead of referencing paths?
3. **L3 completeness** — Are there any lingering references to `openAiAssignment` (command id, menu entry, allowlist) that would resurrect the surface?
4. **L5 invariants** — Does `planLeftClickActivation` ALWAYS open spec.md (preserved S4 default)? Does it correctly skip the clipboard write on `complete` and `cancelled` rows?
5. **Edge cases** — Race conditions, missing-set lookups, QuickPick cancellation paths (Escape on top-level or submenu), non-existent review-criteria files, empty changelog files, slug values containing characters that would break the back-tick-quoted clipboard payload.
6. **Backwards compatibility** — D5 firm CLI backcompat is not at risk (no Python changes), but: are there any retired VS Code command ids that consumers might be calling via the command palette? The pre-existing `copyStartCommand.default` and `copyStartCommand.parallel` remain registered (palette-accessible) so this should be a no-op.
7. **Scope discipline** — Anything obvious that S3 should have shipped per the spec but didn't?

## Code under review

### tools/dabbler-ai-orchestration/src/commands/copyPromptCommands.ts (new)

```typescript
// Copyable-review-prompt commands (Set 048 spec §3.2 + §3.3 L5).
//
// Four commands write a single path-reference prompt to the clipboard:
//
//   dabbler.copySpecReviewPrompt            (always enabled)
//   dabbler.copySessionAccomplishmentsPrompt (>=1 completed session)
//   dabbler.copySetAccomplishmentsPrompt    (set status === "complete")
//   dabbler.copyStartNextSessionPrompt      (non-terminal rows)
//
// L1: prompts MUST reference file paths from repo root, NEVER embed
// file contents. This module computes paths via `path.relative(set.root, …)`
// and lists them in the prompt body.
//
// §3.9: review-criteria/spec.md|session.md|set.md are optional per-repo
// override files. When present, their contents are spliced into an
// "Operator review criteria" trailer; when absent the prompt closes
// with a hint pointing the operator at the template path.

import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { SessionSet } from "../types";

interface SetItem extends vscode.TreeItem {
  set: SessionSet;
}

type ReviewKind = "spec" | "session" | "set";

const REVIEW_CRITERIA_DIRNAME = "review-criteria";

interface BuildContext {
  readReviewCriteria: (root: string, kind: ReviewKind) => string | null;
  fileExists: (filePath: string) => boolean;
}

const defaultBuildContext: BuildContext = {
  readReviewCriteria: defaultReadReviewCriteria,
  fileExists: defaultFileExists,
};

function defaultFileExists(filePath: string): boolean {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function defaultReadReviewCriteria(root: string, kind: ReviewKind): string | null {
  const candidate = path.join(root, "docs", REVIEW_CRITERIA_DIRNAME, `${kind}.md`);
  try {
    if (!fs.existsSync(candidate)) return null;
    const text = fs.readFileSync(candidate, "utf8");
    return text.length > 0 ? text : null;
  } catch {
    return null;
  }
}

function relFromRoot(root: string, abs: string): string {
  return path.relative(root, abs).split(path.sep).join("/");
}

function reviewCriteriaTrailer(
  root: string,
  kind: ReviewKind,
  ctx: BuildContext,
): string {
  const content = ctx.readReviewCriteria(root, kind);
  if (content === null) {
    const hintPath = `docs/${REVIEW_CRITERIA_DIRNAME}/${kind}.md`;
    return (
      `Operator review criteria (optional override):\n` +
      `  No \`${hintPath}\` present. Default review instructions above apply.\n` +
      `  Create \`${hintPath}\` to embed repo-specific criteria here.`
    );
  }
  return `Operator review criteria (from docs/${REVIEW_CRITERIA_DIRNAME}/${kind}.md):\n\n${content.trimEnd()}`;
}

export function buildSpecReviewPrompt(
  set: SessionSet,
  ctx: BuildContext = defaultBuildContext,
): string {
  const specRel = relFromRoot(set.root, set.specPath);
  const instructions =
    `Review the session-set specification for scope clarity, feasibility,\n` +
    `and internal consistency. Flag any session whose stated scope cannot\n` +
    `realistically be completed by one orchestrator in a single sitting, or\n` +
    `whose deliverables are ambiguous. Note whether the prerequisites and\n` +
    `non-goals are explicit.`;
  const files = `Files to read (relative to repo root):\n  - ${specRel}`;
  const trailer = reviewCriteriaTrailer(set.root, "spec", ctx);
  return `${instructions}\n\n${files}\n\n${trailer}\n`;
}

export function buildSessionAccomplishmentsPrompt(
  set: SessionSet,
  ctx: BuildContext = defaultBuildContext,
): string {
  const activityRel = relFromRoot(set.root, set.activityPath);
  const changeLogPresent = ctx.fileExists(set.changeLogPath);
  const changeLogRel = relFromRoot(set.root, set.changeLogPath);
  const specRel = relFromRoot(set.root, set.specPath);
  const instructions =
    `Review the most recent session of this set against its declared scope.\n` +
    `Read the spec for the session's promised deliverables, then cross-check\n` +
    `against the activity log entries and any change-log additions. Flag\n` +
    `scope creep, missing deliverables, or commits that look unrelated to\n` +
    `the stated session goal.`;
  const fileLines: string[] = [`  - ${specRel}`, `  - ${activityRel}`];
  if (changeLogPresent) {
    fileLines.push(`  - ${changeLogRel}`);
  }
  const files = `Files to read (relative to repo root):\n${fileLines.join("\n")}`;
  const gitCommands =
    `Git commands to run for the most recent session's diff and commit log\n` +
    `(substitute the previous session's commit SHA or tag for \`<prev-session-ref>\`):\n` +
    `  - \`git log --oneline <prev-session-ref>..HEAD\`\n` +
    `  - \`git diff <prev-session-ref>..HEAD\``;
  const trailer = reviewCriteriaTrailer(set.root, "session", ctx);
  return `${instructions}\n\n${files}\n\n${gitCommands}\n\n${trailer}\n`;
}

export function buildSetAccomplishmentsPrompt(
  set: SessionSet,
  ctx: BuildContext = defaultBuildContext,
): string {
  const changeLogPresent = ctx.fileExists(set.changeLogPath);
  const changeLogRel = relFromRoot(set.root, set.changeLogPath);
  const specRel = relFromRoot(set.root, set.specPath);
  const instructions =
    `Review the entire completed session set against its declared scope.\n` +
    `Confirm every promised deliverable shipped, flag any non-goals that\n` +
    `crept into scope, and assess whether the set's stated outcome\n` +
    `(version bump, doc revision, registry release) was actually achieved.`;
  const fileLines: string[] = [`  - ${specRel}`];
  if (changeLogPresent) {
    fileLines.push(`  - ${changeLogRel}`);
  }
  const files = `Files to read (relative to repo root):\n${fileLines.join("\n")}`;
  const gitCommands =
    `Git commands to run for the set's full diff and commit log\n` +
    `(substitute the set's first commit SHA or tag for \`<set-start-ref>\`):\n` +
    `  - \`git log --oneline <set-start-ref>..HEAD\`\n` +
    `  - \`git diff <set-start-ref>..HEAD\``;
  const trailer = reviewCriteriaTrailer(set.root, "set", ctx);
  return `${instructions}\n\n${files}\n\n${gitCommands}\n\n${trailer}\n`;
}

export function buildStartNextSessionPrompt(set: SessionSet): string {
  return `Start the next session of \`${set.name}\`.`;
}

async function copyToClipboard(text: string, statusMessage: string): Promise<void> {
  await vscode.env.clipboard.writeText(text);
  vscode.window.setStatusBarMessage(statusMessage, 4000);
}

export function registerCopyPromptCommands(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "dabbler.copySpecReviewPrompt",
      async (item: SetItem) => {
        if (!item?.set) return;
        const prompt = buildSpecReviewPrompt(item.set);
        await copyToClipboard(prompt, `Copied: Spec-review prompt for ${item.set.name}`);
      },
    ),
    vscode.commands.registerCommand(
      "dabbler.copySessionAccomplishmentsPrompt",
      async (item: SetItem) => {
        if (!item?.set) return;
        const prompt = buildSessionAccomplishmentsPrompt(item.set);
        await copyToClipboard(prompt, `Copied: Session-accomplishments prompt for ${item.set.name}`);
      },
    ),
    vscode.commands.registerCommand(
      "dabbler.copySetAccomplishmentsPrompt",
      async (item: SetItem) => {
        if (!item?.set) return;
        const prompt = buildSetAccomplishmentsPrompt(item.set);
        await copyToClipboard(prompt, `Copied: Set-accomplishments prompt for ${item.set.name}`);
      },
    ),
    vscode.commands.registerCommand(
      "dabbler.copyStartNextSessionPrompt",
      async (item: SetItem) => {
        if (!item?.set) return;
        const prompt = buildStartNextSessionPrompt(item.set);
        await copyToClipboard(prompt, `Copied: Start the next session of ${item.set.name}`);
      },
    ),
  );
}

export const __forTests = {
  defaultBuildContext,
  defaultFileExists,
  defaultReadReviewCriteria,
  relFromRoot,
  reviewCriteriaTrailer,
};

```

### tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts (reshape)

```typescript
// Typed action registry for the Set 029 Session 4 custom-tree view.
//
// Set 048 Session 3 reshape (spec §3.3 + L3): the menu structure
// gained two top-level submenus (`Open File ▸`, `Copy Eval ▸`) plus a
// row of flat actions. Each registry entry now carries a `category`
// discriminator so the runtime can group submenu items without having
// to infer from the command id. The cursor-anchored HTML popup that
// Set 034 introduced is retired in favor of `vscode.window.showQuickPick`
// (two-step pattern); see `CustomSessionSetsView.showContextMenu` for
// the consumer.
//
// L3 (operator-locked addition): `Open AI Assignment` is fully removed
// from the menu schema, the command registration, and the dispatch
// allowlist. The `ai-assignment.md` file on disk continues to exist —
// any future surface that needs to read it should depend on the
// `aiAssignmentPath` field, not on this menu entry.
//
// Set 047 Session 3 split the migration predicate by target version.
// `needsMigrationToV3` covers v1/v2 + broken-v3 (the operator runs
// "Migrate to v3 schema" first); `needsMigrationToV4` covers canonical
// v3 with sessions[] (the new "Migrate to v4 schema" affordance).
// A set has at most one migration target at a time — the two
// predicates are mutually exclusive by construction.

import { SessionSet } from "../types";

export interface ActionSupports {
  uat: boolean;
  e2e: boolean;
}

// Set 048 S3: category discriminator drives the two-step QuickPick
// grouping in `CustomSessionSetsView.showContextMenu`.
//   "openFile" → top-level "Open File ▸" submenu
//   "copyEval" → top-level "Copy Eval ▸" submenu
//   "flat"     → rendered inline on the top-level QuickPick
export type ActionCategory = "openFile" | "copyEval" | "flat";

export interface RowAction {
  id: string;
  label: string;
  group: number;
  category: ActionCategory;
  when: (set: SessionSet, supports: ActionSupports) => boolean;
}

const inFlightLike = (s: SessionSet): boolean =>
  s.state === "in-progress" || s.state === "not-started";

const cancellable = (s: SessionSet): boolean =>
  s.state === "in-progress" || s.state === "not-started" || s.state === "complete";

const isCancelled = (s: SessionSet): boolean => s.state === "cancelled";

const hasCompletedSession = (s: SessionSet): boolean => s.sessionsCompleted > 0;

const isCompleteState = (s: SessionSet): boolean => s.state === "complete";

const needsMigrationToV3 = (s: SessionSet): boolean =>
  s.needsMigration && s.migrationTargetSchemaVersion === 3;
const needsMigrationToV4 = (s: SessionSet): boolean =>
  s.needsMigration && s.migrationTargetSchemaVersion === 4;

// Ordered list. `group` controls QuickPick sort within a category;
// `category` controls which top-level item or submenu the entry lands
// under. The numeric bands:
//   1xx — Open File submenu
//   3xx — Copy Eval submenu
//   5xx — flat actions (orchestrator-related quick-access)
//   8xx — flat migrate actions
//   9xx — flat lifecycle actions (cancel / restore)
export const ROW_ACTIONS: RowAction[] = [
  // Open File ▸ submenu. L2 locks the four entries to: Spec, Activity
  // Log, Change Log, Session State. "Open AI Assignment" removed per
  // L3. Open UAT Checklist / Reveal Playwright Tests / Reveal Folder
  // remain registered as Command-Palette-only commands — they are not
  // surfaced on the right-click menu under L2.
  { id: "dabblerSessionSets.openSpec",          label: "Spec",                    group: 101, category: "openFile", when: () => true },
  { id: "dabblerSessionSets.openActivityLog",   label: "Activity Log",            group: 102, category: "openFile", when: () => true },
  { id: "dabblerSessionSets.openChangeLog",     label: "Change Log",              group: 103, category: "openFile", when: () => true },
  { id: "dabblerSessionSets.openSessionState",  label: "Session State",           group: 104, category: "openFile", when: () => true },

  // Copy Eval ▸ submenu — L2 labels match the spec §3.3 table.
  { id: "dabbler.copySpecReviewPrompt",         label: "Evaluate Specification",       group: 301, category: "copyEval", when: () => true },
  { id: "dabbler.copySessionAccomplishmentsPrompt", label: "Evaluate Most Recent Session", group: 302, category: "copyEval",
    when: (s) => hasCompletedSession(s) },
  { id: "dabbler.copySetAccomplishmentsPrompt", label: "Evaluate Session Set",         group: 303, category: "copyEval",
    when: (s) => isCompleteState(s) },
  { id: "dabbler.copyStartNextSessionPrompt",   label: "Start Next Session",           group: 304, category: "copyEval",
    when: (s) => inFlightLike(s) },

  // Flat actions — appear at the top level of the QuickPick. The
  // spec §3.3 table lists v4 only because v4 is the canonical target;
  // the v3 entry is kept here for legacy v1/v2 sets (mutually exclusive
  // with v4 — at most one of the two ever appears per row).
  { id: "dabbler.checkOutOrchestrator",         label: "Set Orchestrator…",            group: 501, category: "flat",
    when: (s) => s.state === "in-progress" },
  { id: "dabbler.openOrchestratorWriterLog",    label: "Open Orchestrator Writer Log", group: 502, category: "flat", when: () => true },
  { id: "dabblerSessionSets.migrate",           label: "Migrate to v3 schema",         group: 801, category: "flat", when: needsMigrationToV3 },
  { id: "dabblerSessionSets.migrateToV4",       label: "Migrate to v4 schema",         group: 802, category: "flat", when: needsMigrationToV4 },
  { id: "dabblerSessionSets.cancel",            label: "Cancel Session Set",           group: 901, category: "flat",
    when: (s) => cancellable(s) },
  { id: "dabblerSessionSets.restore",           label: "Restore Session Set",          group: 902, category: "flat",
    when: (s) => isCancelled(s) },
];

// Resolve the applicable subset for a given set + support flags,
// pre-sorted by `group` so the QuickPick / context-menu order is
// deterministic.
export function applicableActions(set: SessionSet, supports: ActionSupports): RowAction[] {
  return ROW_ACTIONS
    .filter((a) => a.when(set, supports))
    .slice()
    .sort((a, b) => a.group - b.group);
}

// Set 048 S3: split applicable actions into the three menu categories.
// The consumer presents `flat` inline on the top-level QuickPick and
// uses `openFile` / `copyEval` to populate the second-level pickers.
export interface CategorizedActions {
  openFile: RowAction[];
  copyEval: RowAction[];
  flat: RowAction[];
}

export function categorizedActions(
  set: SessionSet,
  supports: ActionSupports,
): CategorizedActions {
  const applicable = applicableActions(set, supports);
  return {
    openFile: applicable.filter((a) => a.category === "openFile"),
    copyEval: applicable.filter((a) => a.category === "copyEval"),
    flat: applicable.filter((a) => a.category === "flat"),
  };
}

```

### tools/dabbler-ai-orchestration/src/providers/rowMenuHelpers.ts (new)

```typescript
// Pure helpers for the Session Sets Explorer right-click QuickPick
// (Set 048 S3 spec §3.3, audit Bias 3 flip) and the L5 left-click
// dual-action. Extracted from `CustomSessionSetsView` so the
// decision logic is unit-testable without instantiating the webview
// provider — the view supplies its own vscode dependencies, this
// module is pure.

import type * as vscode from "vscode";
import type { CategorizedActions, RowAction } from "./ActionRegistry";

// ----- Two-step QuickPick decision logic -----

// `dabblerKind` (rather than `kind`) because VS Code reserves
// `QuickPickItem.kind` for its own `QuickPickItemKind` enum (Default
// / Separator). Using a custom name avoids the structural collision.
export interface TopLevelPickItem extends vscode.QuickPickItem {
  dabblerKind: "openFile" | "copyEval" | "action";
  action?: RowAction;
}

export interface SubmenuPickItem extends vscode.QuickPickItem {
  action: RowAction;
}

// Build the top-level QuickPick item list:
//   - "Open File ▸" when the openFile category is non-empty
//   - "Copy Eval ▸" when the copyEval category is non-empty
//   - one item per flat action (already sorted by `applicableActions`)
export function buildTopLevelItems(categorized: CategorizedActions): TopLevelPickItem[] {
  const items: TopLevelPickItem[] = [];
  if (categorized.openFile.length > 0) {
    items.push({ label: "Open File ▸", dabblerKind: "openFile" });
  }
  if (categorized.copyEval.length > 0) {
    items.push({ label: "Copy Eval ▸", dabblerKind: "copyEval" });
  }
  for (const action of categorized.flat) {
    items.push({ label: action.label, dabblerKind: "action", action });
  }
  return items;
}

export function buildSubmenuItems(submenu: RowAction[]): SubmenuPickItem[] {
  return submenu.map((action) => ({ label: action.label, action }));
}

// ----- L5 left-click dual-action decision -----

export interface LeftClickPlan {
  // Always non-null when the row resolved — left-click ALWAYS opens
  // spec.md (preserved S4 default).
  openCommand: { commandId: string; setName: string };
  // Present iff the row's state is non-terminal AND the L5 clipboard
  // shortcut should fire (`Start the next session of \`<slug>\`.`).
  clipboardWrite: { text: string; toast: string } | null;
}

export function planLeftClickActivation(
  setName: string,
  state: "in-progress" | "not-started" | "complete" | "cancelled",
): LeftClickPlan {
  const openCommand = { commandId: "dabblerSessionSets.openSpec", setName };
  if (state === "complete" || state === "cancelled") {
    return { openCommand, clipboardWrite: null };
  }
  return {
    openCommand,
    clipboardWrite: {
      text: `Start the next session of \`${setName}\`.`,
      toast: `Copied: Start the next session of ${setName}`,
    },
  };
}

```

### tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts (changes summary)

Three structural changes to `tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts`:

1. COMMAND_ALLOWLIST collapsed from 14 entries to 1 entry.
   Old: 14 row-context commands the cursor-anchored popup could
        dispatch via the webview->host `executeRowCommand` message.
   New: just `dabblerSessionSets.openSpec` for the L5 left-click
        activation path. The right-click menu now invokes commands
        directly via `vscode.commands.executeCommand` from the host
        (no webview round-trip needed for QuickPick selections).

2. `showContextMenu` rewritten as a two-step QuickPick flow:
       const categorized = categorizedActions(set, supports);
       const topLevelChoice = await pickTopLevel(...);
       if (!topLevelChoice) return;
       if (topLevelChoice.kind === 'action') {
         this.executeRowAction(topLevelChoice.action, set);
         return;
       }
       const submenu = topLevelChoice.kind === 'openFile'
         ? categorized.openFile : categorized.copyEval;
       const submenuChoice = await pickSubmenu(submenu, ...);
       if (!submenuChoice) return;
       this.executeRowAction(submenuChoice, set);

   The pure decision logic for building QuickPick items + planning
   left-click activation lives in rowMenuHelpers.ts (below).

3. `handleActivateRow` implements L5 dual-action:
       private async handleActivateRow(slug: string): Promise<void> {
         const set = this.findSetBySlug(slug);
         if (!set) return;
         const plan = planLeftClickActivation(set.name, set.state);
         this.dispatchCommand(plan.openCommand.commandId, [{ set }]);
         if (!plan.clipboardWrite) return;
         try {
           await vscode.env.clipboard.writeText(plan.clipboardWrite.text);
           vscode.window.showInformationMessage(plan.clipboardWrite.toast);
         } catch (err) {
           console.warn(`[CustomSessionSetsView] left-click clipboard write failed for "${slug}"`, err);
         }
       }


### Other file edits (summary)

Other Set 048 S3 edits, by file:

- `src/commands/openFile.ts` — removed the `openAiAssignment` command registration per L3.
- `src/extension.ts` — added `registerCopyPromptCommands` to the `safeRegister` chain.
- `package.json` — removed the `openAiAssignment` command declaration; added 4 new copy-prompt declarations (`dabbler.copySpecReviewPrompt`, `dabbler.copySessionAccomplishmentsPrompt`, `dabbler.copySetAccomplishmentsPrompt`, `dabbler.copyStartNextSessionPrompt`).
- `src/types/sessionSetsWebviewProtocol.ts` — removed `RenderContextMenuMsg`, `ContextMenuItem`, and `ExecuteRowCommandMsg` (the cursor-anchored popup protocol).
- `media/session-sets-tree/client.js` — deleted ~100 lines: the `showCursorContextMenu` / `ensureContextMenuEl` / `hideContextMenu` / `bandForCommandId` functions; the click + keydown + resize + scroll listeners that managed the popup; the `lastContextMenuPos` state and `contextMenuEl` reference; the `renderContextMenu` host-to-webview case. The contextmenu event listener on `treeitem` rows survives — it now just posts `showRowContextMenu` to the host, which opens the native QuickPick.
- `media/session-sets-tree/tree.css` — removed `.context-menu`, `.context-menu.is-open`, `.context-menu-item`, `.context-menu-item:hover`, `.context-menu-item.is-active`, `.context-menu-separator` rules.
- `src/test/suite/actionRegistry.test.ts` — rewrote to assert the 14-entry registry (was 15), the L2-locked 4-item Open File submenu, the four copyEval entries with their gating predicates, and the openAiAssignment absence invariant.
- `src/test/suite/copyPromptCommands.test.ts` — NEW, 12 prompt-builder tests covering path-reference format, review-criteria embedding, change-log conditional inclusion, and L1 (no embedded content).
- `src/test/suite/rowMenuHelpers.test.ts` — NEW, 13 tests covering buildTopLevelItems / buildSubmenuItems / planLeftClickActivation pure functions.
- `src/test/playwright/context-menu-quickpick.spec.ts` — NEW, 2 Layer-3 scenarios pinning the negative invariant (no `.context-menu*` DOM) and L3 absence (no `openAiAssignment` data-command attribute).
- `src/test/suite/watcherInventory.test.ts` — bumped one pinned line number from 148 to 149 (the new import added an earlier line to extension.ts).


## Verdict format

Return a verdict (VERIFIED / ISSUES_FOUND) at the top of your response, then itemize concerns by Category (Correctness / Safety / Completeness / Backcompat / Edge-case / Other), Severity (Critical / Important / Nice-to-have), Location (file:line or section reference), Details, and Fix suggestion. If VERIFIED with no items, say so explicitly.
