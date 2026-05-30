Set 051 Session 3 (3 of 4) close-out — retire the superseded Claude SessionStart hook (extension).

Executed the spec's Session 3 plan + verdict V10 (hook retirement,
out-of-panel-scope, plan stood). The premise was re-verified before any
deletion: Set 053's lifecycle drift advisory IS live — `summarize_drift`
is imported and called in BOTH `ai_router/start_session.py` (prints to
stderr after the boundary write) and `ai_router/close_session.py`. So
retiring the Claude-only hook loses no drift coverage; it removes a
redundant, divergence-prone duplicate. (My pre-session memory said Set
053 was un-started; that was stale — 053 has shipped S1+S2.)

DELETED (4 files):
- tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js
  (the invoker shim; its scanSchemaDrift + CURRENT_SCHEMA_VERSION
  duplicated 053's summarize_drift). The extension scripts/ dir is now
  empty.
- tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts
  (the installer command + its "Copy manual setup" toast/action).
- ai_router/tests/test_invoker_schema_constant.py (the CI pin test for
  the deleted JS constant — the one ai_router/Python item in the surface).
- tools/dabbler-ai-orchestration/src/test/suite/claudeSessionStartInvoker.test.ts
  — SPEC-IMPLIED CONSEQUENCE, flag for S4 verifier. Not explicitly named
  in the spec's S3 delete list, but it is the Layer-2 suite that
  dynamic-imports the now-deleted invoker JS; it cannot pass without the
  file. Deleting it is the direct, unavoidable consequence of step 1.

WIRING REMOVED:
- src/extension.ts: dropped the `registerInstallOrchestratorHookClaudeCodeCommand`
  import + its `safeRegister` block; rewrote the stale Set-049 comment to
  record the Set 051 S3 retirement and that drift now rides the lifecycle.
- package.json: removed the `dabbler.installOrchestratorHook.claudeCode`
  command contribution (no menu entry existed — single declaration).

DOCS RECONCILED (hook described as historical, pointing at the Set 053
lifecycle advisory as the live mechanism):
- CLAUDE.md — retirement note appended to the v0.25.0 (Set 050) bullet
  (full version-walk restructure deferred to S4's version bump).
- docs/ai-led-session-workflow.md — rewrote the "Schema-drift guard"
  section to make the lifecycle advisory the sole mechanism + a
  historical note; updated the T3 per-orchestrator declaration bullet.
- docs/session-state-schema.md — rewrote the Writer-Contract hook bullet
  as a `start_session` invocation, hook retired.
- docs/cross-repo-migration-guard-notice.md (Set 050) — superseded banner
  at top; neutralized the "Install the SessionStart drift guard" step
  (now "RETIRED — skip"); updated the paste-snippet drift paragraph + the
  adoption-status table ("Drift hook" → "Drift coverage: router lifecycle").

CREATED:
- docs/cross-repo-hook-retirement-notice.md — consumer-repo + operator
  remediation note (spec step 5): remove the dabbler `SessionStart` entry
  containing `claude-session-start-invoker.js` from
  ~/.claude/settings.json; drift is now automatic via the lifecycle;
  consumer CLAUDE.md edit to drop the hook-install instruction. Does NOT
  edit the operator's machine settings — documents the removal only.

ALSO (mechanical, flag for S4 verifier):
- src/test/suite/watcherInventory.test.ts — the Q7 D1 watcher-allowlist
  pins extension.ts:154; removing one import line shifted the lone
  watcher callsite to :153. Bumped the allowlist line number to match
  (the test's own maintenance contract: "when a refactor shifts lines,
  update this list in the same commit"). No watcher added/removed.
- dist/extension.js(.map) recompiled (`npm run compile`) so the shipped
  bundle no longer references the removed command. Version unchanged at
  0.25.0; S4 owns the bump + repackage.

VERIFICATION: MANUAL. Quality bar per spec = no extension/Python
regressions.
- Python: `python -m pytest` → 1028 passed, 1 skipped (was 1029 in S2;
  −1 = the deleted test_invoker_schema_constant.py, exactly the one test
  removed with its dead surface).
- TypeScript: `npx tsc --noEmit` clean; `npm run test:unit` → 554
  passing, 2 failing. The 2 failures are the known pre-existing Set-026
  scaffolding failures (configEditor panel-lifecycle "createOrShow
  registers currentPanel" + notificationsSection rendering) — unrelated
  to the hook; both watcher-inventory tests now pass.
- package.json re-validated as well-formed JSON after the command removal.
Cross-provider verification of the whole set is scoped to S4 per the spec.

COST: S3 invoked no router (all local work) — $0 routed this session.
Cumulative set spend: $0.0272 of $10 NTE (0.27%, from S1 consensus).

NEXT (S4): docs/CHANGELOG reconciliation; dual version bumps (PyPI
dabbler-ai-router for the joiner/packaging removals AND the VS Code
Marketplace extension for this hook retirement); change-log.md;
cross-provider verification; close-out; both publishes held for
operator-initiated tag-push (PyPI v<X.Y.Z> + Marketplace vsix-v<X.Y.Z>).
