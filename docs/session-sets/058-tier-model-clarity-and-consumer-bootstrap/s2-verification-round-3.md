# Session 2 cross-provider verification — ROUND 3 (Set 058)

- Verifier model: gpt-5-4 (gpt-5.4)
- Tier: 3
- Cost (total incl. verification): $0.2301
- Escalated: False
- Truncated: False

---

## VERDICT
**ISSUES_FOUND**

## Critical
- None.

## Major
- **Issue** → The installed-extension packaging contract is still not actually pinned. `resolveBundledTemplateDir()` is correct, and the local `dist/templates/...` checks are good, but nothing in this diff proves the published VSIX includes `dist/templates/consumer-bootstrap/**`. If that folder is excluded by `package.json`/`.vscodeignore`, both `dabbler.setupNewProject` and `dabbler.generateSessionSetPrompt` fail at runtime with “Could not load the consumer-bootstrap template bundle”.
  **Location** → `src/commands/gitScaffold.ts`, `src/wizard/sessionGenPrompt.ts`, `src/test/suite/consumerBootstrap.test.ts`; missing manifest-level packaging coverage in the provided diff.
  **Fix** → Explicitly include `dist/templates/**/*` in the extension package manifest / unignore it, and add a packaging test that inspects the built VSIX (or `vsce ls`) for all seven bundle files.

## Minor
- **Issue** → `--watch` builds can go stale: the template bundle is copied once before watch starts, but edits under `docs/templates/consumer-bootstrap/` are not recopied while commands read only `dist/templates/...`.
  **Location** → `tools/dabbler-ai-orchestration/esbuild.js`
  **Fix** → Re-run `copyTemplateBundle()` on rebuild, or add a watcher for `docs/templates/consumer-bootstrap/**/*`.

- **Issue** → The shared writer does not enforce its own `totalSessions >= 1` contract. A non-UI caller can produce malformed `spec.md` / `session-state.json` instead of failing fast.
  **Location** → `src/utils/consumerBootstrap.ts` (`expandSpecSessions`, `expandSessionState`, reachable via `renderSpec` / `renderSessionState`)
  **Fix** → Validate `totalSessions` once at the writer boundary and throw unless it is a positive integer.

- **Issue** → Prompt-contract tests are still weaker than the runtime contract: they assert `NNN-` is present, but not that bare-slug folder/state examples are absent.
  **Location** → `src/test/suite/sessionGenPrompt.test.ts`
  **Fix** → Add negative assertions that the prompt never shows bare-slug folder shapes / state names, and that worked examples use `001-...` everywhere relevant.