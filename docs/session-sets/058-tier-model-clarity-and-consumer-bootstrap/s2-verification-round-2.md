# Session 2 cross-provider verification — ROUND 2 (Set 058)

- Verifier model: gpt-5-4 (gpt-5.4)
- Tier: 3
- Cost (total incl. verification): $0.2427
- Escalated: False
- Truncated: False

---

## VERDICT
**ISSUES_FOUND**

## Critical
- None.

## Major
- **Issue →** `expandSpecSessions()` is line-ending fragile. It hard-codes LF markers (`"## Sessions\n"` and `"\n\n---\n\n"`), so a CRLF-checked-out template bundle will not expand at all. That leaves the illustrative sample blocks in place instead of emitting exactly `N` numbered blocks, and it affects both real scaffolds and the worked example embedded by `sessionGenPrompt`.
  **Location →** `tools/dabbler-ai-orchestration/src/utils/consumerBootstrap.ts`, `expandSpecSessions()`.
  **Fix →** Normalize input first (`specText.replace(/\r\n/g, "\n")`) or rewrite the section/block detection to tolerate `\r?\n`; add a test that feeds CRLF template text into `renderSpec()` and asserts headers `[1..N]` plus only `session-00K/` prefixes.

## Minor
- **Issue →** The packaged-runtime tests do not pin the actual built artifact contract; they only verify that a synthetic `<fakeExt>/dist/templates/consumer-bootstrap` can be loaded. A broken copy step or missing packaged `dist/templates` could still ship and fail at runtime.
  **Location →** `tools/dabbler-ai-orchestration/src/test/suite/consumerBootstrap.test.ts` packaged-runtime suite; `tools/dabbler-ai-orchestration/esbuild.js`, `copyTemplateBundle()`.
  **Fix →** Add a post-build/package smoke test that asserts the real `dist/templates/consumer-bootstrap` exists with all required files, and make `copyTemplateBundle()` fail the build when the source bundle is missing instead of only warning.

- **Issue →** The spec-expansion test still does not fully pin the “exact `session-00K/` progress keys” contract. It checks the unique prefix set, so stray stale `session-001/` references in later blocks could slip through if the correct prefixes also appear somewhere.
  **Location →** `tools/dabbler-ai-orchestration/src/test/suite/consumerBootstrap.test.ts`, test `"expands to EXACTLY totalSessions numbered blocks with the right prefixes"`.
  **Fix →** Assert per-block isolation: split the rendered Sessions region into blocks and verify block `K` contains only `session-${padSessionNumber(K)}/` keys, or assert no `session-001/` appears outside Session 1.