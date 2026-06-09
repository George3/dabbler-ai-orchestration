# Session 2 cross-provider verification (Set 058)

- Verifier model: gpt-5-4 (gpt-5.4)
- Tier: 3
- Cost (total incl. verification): $0.3056
- Escalated: False
- Truncated: True

---

## VERDICT
`ISSUES_FOUND`

## Critical
- None.

## Major
- **Issue** → `sessionGenPrompt` is not actually using the shared render contract. It embeds the raw `.template` files, not writer-rendered outputs, so the AI is shown unresolved `{{TOKEN}}` placeholders and the unexpanded sample shapes. That means the prompt can still yield:
  - a `spec.md` with only the sample session block(s) instead of exactly `N`,
  - stale `session-001/` progress-key prefixes,
  - a `session-state.json` with only the sample session object instead of one object per planned session.
  
  It also wraps `bundle.specTemplate` in a triple-backtick fence even though the spec template itself contains fenced blocks (` ```yaml `), so the prompt’s Markdown fencing is malformed.
  
  **Location** → `tools/dabbler-ai-orchestration/src/wizard/sessionGenPrompt.ts`, `buildSessionGenPrompt()`
  
  **Fix** → Build the prompt from shared-writer exemplars, not raw templates. Use `renderSpec()` / `renderSessionState()` with a concrete sample `BootstrapContext` (e.g. 3 sessions, `001-example-set`) so the prompt shows the final expanded contract. If you still include raw templates, use non-colliding outer fences (`~~~~` or indented blocks).

- **Issue** → The packaged-runtime bundle contract is not pinned by tests. All test helpers prefer repo-root `docs/templates/consumer-bootstrap`, so they do not exercise the actual installed-extension path (`resolveBundledTemplateDir(extensionPath)`). The fallback dist path is also wrong: `path.resolve(__dirname, "dist/templates/consumer-bootstrap")` resolves under the test directory, not the extension root. A missing or mispackaged `dist/templates/consumer-bootstrap` can break real scaffolding in an installed extension while tests still pass.
  
  **Location** →  
  - `tools/dabbler-ai-orchestration/src/test/suite/consumerBootstrap.test.ts`  
  - `tools/dabbler-ai-orchestration/src/test/suite/gitScaffoldCore.test.ts`  
  - `tools/dabbler-ai-orchestration/src/test/suite/sessionGenPrompt.test.ts`
  
  **Fix** → Add a test that uses `resolveBundledTemplateDir()` against a fake extension root and successfully `loadTemplateBundle()` from `<root>/dist/templates/consumer-bootstrap`. Fix the dist fallback to point at the extension root, not `__dirname/dist/...`.

## Minor
- **Issue** → The tests do not fully pin the session-expansion contract. The implementation in `expandSpecSessions()` looks correct for the current marker shape, but the test only checks that sessions `1..N` exist and `N+1` does not. It does not assert:
  - exactly `N` session headers total,
  - exactly the expected `session-00K/` prefixes,
  - absence of duplicate leftover sample blocks.
  
  `sessionGenPrompt.test.ts` is similarly loose: it checks substrings, but would not catch the current raw-template / broken-fence regression.
  
  **Location** →  
  - `tools/dabbler-ai-orchestration/src/test/suite/consumerBootstrap.test.ts`  
  - `tools/dabbler-ai-orchestration/src/test/suite/sessionGenPrompt.test.ts`
  
  **Fix** → Tighten tests to assert exact counts/sets:
  - `spec.match(/### Session \d+ of 4:/g)?.length === 4`
  - extract all `session-\d{3}/` prefixes and compare against the exact expected set
  - assert no extra session headers remain
  - for the prompt, assert it contains writer-rendered expanded examples rather than raw template sections.