# Route response

- **Provider:** claude-sonnet-4-6
- **Model:** sonnet
- **Cost:** 0.1469835

---

## Verdict: ISSUES_FOUND

---

### Category: Safety (L1 Compliance)
**Severity: Critical**
**Location:** `copyPromptCommands.ts` — `defaultReadReviewCriteria` (lines ~53–62) and `reviewCriteriaTrailer` (lines ~72–82)

**Issue:** `defaultReadReviewCriteria` calls `fs.readFileSync` and returns the raw file content; `reviewCriteriaTrailer` splices that content directly into the prompt body via string interpolation. This is a literal content-embedding, not a path reference. L1 states unconditionally: *"Prompts MUST reference file paths, never embed contents."* The file header's §3.9 gloss ("their contents are spliced into an 'Operator review criteria' trailer") **describes the current behavior but does not resolve the L1 conflict** — L1 is listed as an operator-locked addition, which should take precedence over an inline implementation note.

The review-criteria files are the only path through which an external file's bytes can enter a prompt string. If L1 is intended to be absolute (and the wording gives no carve-out), this is the one place that violates it.

**Fix — option A (strict L1 compliance):** Replace the content-embed with a path reference in the trailer:
```typescript
function reviewCriteriaTrailer(root: string, kind: ReviewKind, ctx: BuildContext): string {
  const candidatePath = `docs/${REVIEW_CRITERIA_DIRNAME}/${kind}.md`;
  const exists = ctx.fileExists(path.join(root, candidatePath));
  if (!exists) {
    return (
      `Operator review criteria (optional override):\n` +
      `  No \`${candidatePath}\` present. Default review instructions above apply.\n` +
      `  Create \`${candidatePath}\` to embed repo-specific criteria here.`
    );
  }
  return (
    `Operator review criteria:\n` +
    `  Read \`${candidatePath}\` for repo-specific review instructions.`
  );
}
```
`defaultReadReviewCriteria` and `fileExists` can then be collapsed to a single `fileExists` predicate; `BuildContext.readReviewCriteria` is deleted entirely.

**Fix — option B (explicit §3.9 exception):** If the spec intends §3.9 to carve out review-criteria files from L1, that exception must be stated explicitly in L1 and in the §3.9 operator note, and the test suite assertion in `copyPromptCommands.test.ts` should include a case that verifies content is embedded *only* from `docs/review-criteria/` and from no other path. The current test description "L1 (no embedded content)" is then misleading and should be renamed.

---

### Category: Correctness — Dispatch key mismatch
**Severity: Critical**
**Location:** `rowMenuHelpers.ts` — `TopLevelPickItem.dabblerKind` vs. `CustomSessionSetsView.ts` pseudocode (changes summary)

**Issue:** `TopLevelPickItem` declares the discriminator as `dabblerKind`:
```typescript
export interface TopLevelPickItem extends vscode.QuickPickItem {
  dabblerKind: "openFile" | "copyEval" | "action";
  ...
}
```
The `CustomSessionSetsView.ts` summary pseudocode reads the discriminator as `.kind`:
```typescript
if (topLevelChoice.kind === 'action') { ... }
```
`vscode.QuickPickItem` itself does not have a `.kind` field in the QuickPick selection callback (only in the item list rendering context). If the actual implementation uses `.kind`, every top-level dispatch check evaluates `undefined === 'action'` → `false`, causing **all flat actions to silently no-op** and both submenus to fall through to the submenu branch unconditionally.

Since only the summary is provided (not the actual file), this cannot be confirmed from the diff. It must be verified before ship.

**Fix:** Audit `CustomSessionSetsView.showContextMenu` to confirm every read of the discriminator uses `dabblerKind`, not `kind`. Add a narrow type-narrowing helper if needed:
```typescript
function isSubmenuKind(item: TopLevelPickItem): item is TopLevelPickItem & { dabblerKind: "openFile" | "copyEval" } {
  return item.dabblerKind === "openFile" || item.dabblerKind === "copyEval";
}
```

---

### Category: Edge-case — Backtick injection in clipboard payload
**Severity: Important**
**Location:** `copyPromptCommands.ts:buildStartNextSessionPrompt` (line ~153); `rowMenuHelpers.ts:planLeftClickActivation` (line ~62)

**Issue:** Both sites produce:
```typescript
`Start the next session of \`${set.name}\`.`
// or
`Start the next session of \`${setName}\`.`
```
If `set.name` / `setName` contains a backtick character (e.g., `"my-set\`name"`), the output is:
```
Start the next session of `my-set`name`.
```
The payload is syntactically broken in any Markdown context. The spec's L5 template uses the exact backtick-delimited form `\`<slug>\``, implying the slug is assumed safe, but there is no validation or escape.

**Fix:** Sanitize the slug before inserting it into the backtick-delimited literal. Since slugs are typically kebab-case identifiers, a guard is sufficient:
```typescript
function sanitizeSlugForPrompt(slug: string): string {
  // Backtick in a slug would break the L5 template literal payload.
  return slug.replace(/`/g, "'");
}
```
Apply in both `buildStartNextSessionPrompt` and `planLeftClickActivation`. Alternatively, add a `SessionSet` invariant that rejects slugs containing backticks at parse time.

---

### Category: Edge-case — `findSetBySlug` missing-set path in `handleActivateRow`
**Severity: Important**
**Location:** `CustomSessionSetsView.ts` (summary) — `handleActivateRow`

**Issue:** The implementation guards `if (!set) return` after `findSetBySlug`, which is correct. However, there is no guard on the `set.state` field being one of the four known literals before passing it to `planLeftClickActivation`. `planLeftClickActivation`'s parameter type is a closed union:
```typescript
state: "in-progress" | "not-started" | "complete" | "cancelled"
```
If `SessionSet.state` is typed as `string` (or a wider union) in `types/index.ts`, TypeScript will compile the call, but at runtime a stale state value (e.g., `"archived"` from a future schema migration) falls through the `if (state === "complete" || state === "cancelled")` check and writes a clipboard entry it should not. This is spec §3.3 compliance risk.

**Fix:** Either widen `planLeftClickActivation`'s state parameter to `string` and add an explicit default-arm, or narrow `SessionSet.state` in the type definition to the closed four-value union and keep `planLeftClickActivation`'s signature as-is:
```typescript
// In planLeftClickActivation — add explicit exhaustive fallthrough:
if (state === "complete" || state === "cancelled" || 
    (state !== "in-progress" && state !== "not-started")) {
  return { openCommand, clipboardWrite: null };
}
```

---

### Category: Correctness — `applicableActions` redundant `.slice()`
**Severity: Minor**
**Location:** `ActionRegistry.ts:applicableActions` (line ~93)

**Issue:** `.filter()` already returns a new array; the chained `.slice()` allocates a second copy for no purpose. Not a logic error, but a misleading signal (reader may infer the slice was needed to avoid mutating `ROW_ACTIONS`, obscuring that `.filter()` already provides that guarantee).

**Fix:**
```typescript
export function applicableActions(set: SessionSet, supports: ActionSupports): RowAction[] {
  return ROW_ACTIONS
    .filter((a) => a.when(set, supports))
    .sort((a, b) => a.group - b.group);
}
```

---

### Category: Safety — `copyToClipboard` swallows no error
**Severity: Minor**
**Location:** `copyPromptCommands.ts:copyToClipboard` (lines ~157–160)

**Issue:** `vscode.env.clipboard.writeText` is awaited but wrapped in no `try/catch`. If the clipboard API rejects (sandboxed environments, Wayland permission failure), the rejection propagates unhandled through the registered command handler, producing an uncaught rejection that VS Code surfaces as a generic error notification with no actionable message.

**Fix:**
```typescript
async function copyToClipboard(text: string, statusMessage: string): Promise<void> {
  try {
    await vscode.env.clipboard.writeText(text);
    vscode.window.setStatusBarMessage(statusMessage, 4000);
  } catch (err) {
    vscode.window.showWarningMessage(`Failed to copy to clipboard: ${err instanceof Error ? err.message : String(err)}`);
  }
}
```

---

### Category: Completeness — `buildSetAccomplishmentsPrompt` omits activity log
**Severity: Minor**
**Location:** `copyPromptCommands.ts:buildSetAccomplishmentsPrompt` (lines ~122–145)

**Issue:** The session-level prompt references spec + activity log + change log (conditional). The set-level prompt references only spec + change log (conditional), with no activity log. For a full set retrospective, the activity log is the primary evidence source for what each session actually delivered. This may be intentional per spec §3.2 but deserves explicit acknowledgement; there is no comment in the function explaining the omission.

**Fix:** Either add the activity log to the set-level file list (matching the session-level pattern) or add an inline comment stating the omission is deliberate per §3.2:
```typescript
// Activity log intentionally omitted from set-level prompt per spec §3.2:
// set retrospectives assess outcomes (spec vs changelog), not per-session detail.
```

---

### Category: Backcompat — `COMMAND_ALLOWLIST` collapse scope
**Severity: Minor**
**Location:** `CustomSessionSetsView.ts` (summary) — COMMAND_ALLOWLIST

**Issue:** The allowlist collapsed from 14 entries to 1 (`dabblerSessionSets.openSpec`). The summary confirms the right-click commands now execute via `vscode.commands.executeCommand` directly from the host, bypassing the allowlist entirely. This means the allowlist now only gates the L5 left-click path. If a future session re-introduces webview-to-host command dispatch for any other command, the allowlist provides no protection by default. This is not a current bug but is a latent architectural footgun.

**Fix:** Add a comment in `CustomSessionSetsView.ts` making the narrowed purpose explicit:
```typescript
// COMMAND_ALLOWLIST: governs only webview→host executeRowCommand messages
// (currently used exclusively by the L5 left-click activation path).
// Right-click commands execute via vscode.commands.executeCommand directly
// and do NOT pass through this list — any new webview dispatch path must
// add its allowed command ids here explicitly.
```

---

### Summary Table

| # | Severity | Category | File | Issue |
|---|----------|----------|------|-------|
| 1 | **Critical** | Safety / L1 | `copyPromptCommands.ts` | Review-criteria content embedded into prompt body — violates L1 |
| 2 | **Critical** | Correctness | `CustomSessionSetsView.ts` (summary) | `dabblerKind` vs `.kind` dispatch key mismatch — requires manual verification |
| 3 | **Important** | Edge-case | `copyPromptCommands.ts`, `rowMenuHelpers.ts` | Backtick in slug corrupts L5 clipboard payload |
| 4 | **Important** | Edge-case | `CustomSessionSetsView.ts` (summary) | Unknown `state` value falls through to clipboard write |
| 5 | Minor | Correctness | `ActionRegistry.ts` | Redundant `.slice()` after `.filter()` |
| 6 | Minor | Safety | `copyPromptCommands.ts` | `copyToClipboard` has no error handling |
| 7 | Minor | Completeness | `copyPromptCommands.ts` | `buildSetAccomplishmentsPrompt` silently omits activity log |
| 8 | Minor | Backcompat | `CustomSessionSetsView.ts` (summary) | Narrowed allowlist purpose undocumented |