# chatSessionId identity refinement + MVVM watcher-scope discipline — implementation

> **Purpose:** ship the chatSessionId identity refinement and the
> MVVM-watcher-scope discipline locked by the cross-provider audit
> at
> [`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/).
> Refines H4 from `engine + provider` to
> `engine + provider + chatSessionId`. Retires the codex config-
> toml watcher and `signalKind` inference variants. Adds the
> per-set lifecycle lock that Q5 made load-bearing.
> **Created:** 2026-05-21 (post-Set-033-close)
> **Session Set:** `docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/`
> **Prerequisites:**
> - Set 033 (`033-orchestrator-checkout-checkin-implementation`) CLOSED
>   — shipped H1+H2+H3+H4 base composite + OQ1+OQ2.
> - Audit-locked proposal at
>   `docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`
>   with `proposal-addendum.md` capturing the locked verdicts.
> **Pattern:** audit-then-spec per
> [[feedback_audit_then_spec_for_substantial_features]] —
> the audit half ran informally (Gemini Pro routed + GPT-5.4
> manual paste); this set is the implementation half.

---

## Session Set Configuration

```yaml
totalSessions: 6
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
```

> **`requiresE2E: true`** — the chatSessionId-mismatch takeover
> UX is a new operator-visible affordance (modal in IDE / CLI
> prompt in terminal). Layer-3 Playwright coverage is the right
> layer for "what the operator sees painted on screen."
>
> **`effort: high`** — the change touches:
> - The Python writer (`ai_router/start_session.py`,
>   `ai_router/close_session.py`, `ai_router/session_state.py`,
>   `ai_router/session_events.py`).
> - A new Python CLI (`ai_router/new_chat_id.py`).
> - The Claude Code hook invoker (Node).
> - The extension's reader (`OrchestratorAccordion.ts`,
>   `inProgressSetsService.ts`).
> - The Codex config-toml watcher (RETIRED entirely).
> - Layer-2 + Layer-3 test surfaces.
> - All three canonical docs + the cross-repo notice.
> - A new convention test (Q7 watcher-inventory).
> - Two registry releases (PyPI + Marketplace).
>
> Similar scope to Set 033; same effort grade.

---

## Project Overview

### What the audit locked (compact recap)

The proposal-addendum at
[`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/proposal-addendum.md`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/proposal-addendum.md)
locked the following pattern (operator-adjudicated, GPT-leaning):

| Item | Locked verdict |
|---|---|
| **D1** Watcher-scope discipline | REFINED — discipline applies to *orchestrator-state inference*; non-orchestrator UI refresh watchers stay permitted |
| **D2** MVC-shaped agent API | REFINED — token source is native per-chat metadata surface (env, hook, or fallback CLI), not env-var-only |
| **Q1** chatSessionId source per orchestrator | REFINED — no env var confirmed for any orchestrator; Claude Code uses hook-payload `session_id`; others use the fallback CLI |
| **Q2** Cadence of identity checks | REFINED — per-boundary; "destructive ops" narrowly defined (ownership transitions + --force + repo-wide git + repo-wide scripts) |
| **Q3** Takeover UX | REFINED — modal in IDE; CLI prompt in terminal; toast is secondary notification only |
| **Q4** chatSessionId on close | REFINED — clear from `session-state.json`; persist in `closeout_succeeded` event payload alongside engine + provider + (optional) model |
| **Q5** Hybrid migration tolerance | REFINED — hybrid only with explicit cross-process serialization (shared per-set lifecycle lock) |
| **Q6** `requireExplicitTakeover` setting | REJECTED — no persistent off-switch; if real friction surfaces later, ship a one-shot affordance |
| **Q7** Watcher-scope enforcement | REFINED — allowlisted watcher-inventory unit test |

### What ships across the six sessions

- **S1** — Writer migration + per-set lifecycle lock. Q5's lock
  is the gating prerequisite for the hybrid-migration safety;
  everything else builds on it.
- **S2** — `new_chat_id` CLI + Claude Code hook-invoker passes
  through the per-chat `session_id`. Q1 native-source wiring.
- **S3** — `signalKind` retirement + Codex config-toml watcher
  retirement. D1 watcher-scope discipline applied.
- **S4** — Takeover UX (modal + CLI) + watcher-inventory
  convention test. Q3 + Q7 user-facing surface.
- **S5** — Layer-3 Playwright coverage + cross-tier docs +
  cross-repo notice update.
- **S6** — Final tests + change-log + dual-registry release.

---

## Session 1 of 6: Writer migration + per-set lifecycle lock (Q5 prerequisite)

**Goal:** add `chatSessionId` to the orchestrator block + refine
H4 + add the per-set lifecycle lock that makes the hybrid
migration safe.

**Steps:**

1. **Schema delta** — `orchestrator` block gains
   `chatSessionId: string | null` field.
   `session-state.json` invariant: `orchestrator` is `null` when
   `status != in-progress` (unchanged); when non-null, the
   `chatSessionId` field is present (may be null for legacy
   sets, per Q5 tolerant-on-read).
2. **`start_session.py` refinement:**
   - New `--chat-session-id <value>` argument (optional;
     defaults to value of `$CHAT_SESSION_ID` env if set,
     otherwise None).
   - H4 identity predicate refined to:
     `existing.engine == new.engine
     AND existing.provider == new.provider
     AND existing.chatSessionId == new.chatSessionId`.
   - Tolerant-on-read: a missing `chatSessionId` in the existing
     orchestrator block is treated as "same holder" for engine +
     provider matches (Q5 tolerant-on-read).
   - Strict-on-write: the new write always populates
     `chatSessionId` (from arg, env, or null if neither
     supplied).
   - Refusal message extended to name the existing chatSessionId
     (or "no chat session ID recorded" for legacy state files).
3. **Per-set lifecycle lock (Q5 hard requirement):**
   - Rename `.close_session.lock` to `.lifecycle.lock` in
     `ai_router/close_lock.py` (or wherever the lock helper
     lives).
   - Both `start_session` AND `close_session` acquire this lock
     for the duration of their read/check/write window.
   - Stale-window reaping semantics preserved.
   - Lock contention: blocks for a bounded timeout (default
     30s), then exits with `EXIT_LOCK_CONTENTION = 5` (new exit
     code; document in `start_session.py` exit-code table).
4. **`close_session.py` extension** —
   `closeout_succeeded` event payload gains `chatSessionId`,
   `engine`, `provider`, and `model` fields (Q4 audit
   trail). Reader tolerance for older payloads without these
   fields.
5. **`session_state.py` writer** —
   `_flip_state_to_closed()` continues to set
   `orchestrator: None` on close (Set 033 Session 6 behavior);
   the chatSessionId is naturally cleared as part of nulling
   the block.
6. **`session_events.py`** — the `closeout_succeeded` event's
   payload contract documented; the existing `append_event()`
   helper signature unchanged (payload is already open-shape).
7. **Unit tests** in `ai_router/tests/`:
   - Fresh check-out writes `chatSessionId` correctly.
   - Same-(engine, provider, chatSessionId) re-attach is benign.
   - Different chatSessionId (with matching engine+provider) is
     refused; refusal message names the holder's chatSessionId.
   - `--force` overrides and rewrites chatSessionId.
   - Legacy state file (no chatSessionId) is tolerated on read;
     first new write populates the field.
   - Lock contention between simultaneous start_session calls
     serializes correctly.
   - `closeout_succeeded` event payload includes chatSessionId
     + engine + provider + model.
8. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `ai_router/tests/test_chatsessionid_writer.py`

**Touches:**
- `ai_router/start_session.py`
- `ai_router/close_session.py`
- `ai_router/session_state.py`
- `ai_router/session_events.py`
- `ai_router/close_lock.py` (rename + extend)

**Ends with:** writer side ships chatSessionId; per-set
lifecycle lock prevents the migration race Q5 flagged; tests
cover all branches.

**Progress keys:** `session-001/schema-delta-applied`,
`session-001/start-session-refined`,
`session-001/lifecycle-lock-introduced`,
`session-001/close-session-event-payload-extended`,
`session-001/legacy-tolerance-wired`,
`session-001/unit-tests-green`,
`session-001/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 2 of 6: `new_chat_id` CLI + Claude Code hook-invoker pass-through

**Goal:** the agent-facing token-source plumbing. Claude Code
gets its native per-chat ID (from the hook payload's
`session_id`) wired through to `start_session`. All other
orchestrators use the new `new_chat_id` CLI.

**Steps:**

1. **`ai_router/new_chat_id.py`** — new module + CLI entrypoint:
   - `python -m ai_router.new_chat_id` prints a UUID v4.
   - `--export` prints a shell-eval-able line; `--shell
     bash|powershell|fish` selects the syntax (default: detect
     via `$SHELL` env / `os.name`).
   - Idempotent within a shell session: if `$CHAT_SESSION_ID`
     (or `$env:CHAT_SESSION_ID`) is already set, the CLI emits
     the existing value rather than a fresh one.
   - Exits 0 on success; 1 on shell-detect failure when
     `--shell` not provided.
2. **`tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`**
   — extend to parse `session_id` from the stdin JSON payload
   that Claude Code's SessionStart hook delivers, and forward
   it as `--chat-session-id <value>` to
   `python -m ai_router.start_session`. Best-effort: if the
   payload doesn't contain `session_id`, omit the argument
   (start_session falls through to None, which the legacy-
   tolerance branch handles).
3. **Installer-shim updates** for the manual-only orchestrators
   (Codex, Gemini Code Assist, Copilot, manual Lightweight):
   - `installOrchestratorHookCopilot.ts` /
     `installOrchestratorHookGemini.ts`: documentation copy
     mentions the `python -m ai_router.new_chat_id` workflow
     as the per-session prerequisite. No code-side hook is
     installable for these.
   - A small READMEish snippet in the wizard output explains
     the workflow to operators.
4. **Tests:**
   - `ai_router/tests/test_new_chat_id.py` — CLI behavior,
     idempotency, shell-syntax selection.
   - Smoke test for the Claude invoker's `session_id`
     extraction (Layer-2 test with a fixture stdin payload).
5. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `ai_router/new_chat_id.py`
- `ai_router/tests/test_new_chat_id.py`
- Layer-2 test for invoker `session_id` pass-through

**Touches:**
- `tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookCopilot.ts`
- (possibly) wizard / README copy in
  `tools/dabbler-ai-orchestration/`

**Ends with:** Claude Code chats automatically pass their
per-chat session_id; non-Claude orchestrators have a documented
fallback CLI; tests cover both paths.

**Progress keys:** `session-002/new-chat-id-cli-implemented`,
`session-002/claude-invoker-passes-session-id`,
`session-002/installer-shims-updated`,
`session-002/unit-tests-green`,
`session-002/layer2-invoker-test-green`,
`session-002/round-a-verification`

**Estimated cost:** $0.03–$0.10.

---

## Session 3 of 6: `signalKind` retirement + Codex config-toml watcher retirement

**Goal:** apply the D1 watcher-scope discipline. The Codex
config-toml watcher is retired entirely (it was the inference
watcher that caused the stale-gauge bug observed during Set 033
Session 6). The `signalKind` enum and all its UI variants
disappear because the system no longer infers state from
indirect signals.

**Steps:**

1. **Codex config-toml watcher retirement:**
   - Delete `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts`.
   - Remove the `safeRegister` call from `extension.ts`.
   - Remove the Codex-detection wiring from any place that
     consumed the watcher's events.
   - Update `installOrchestratorHookGemini.ts` /
     `installOrchestratorHookCopilot.ts` documentation to
     note that no auto-detect exists for these orchestrators
     (consistent with Set 033 Session 3 audit).
2. **`signalKind` retirement:**
   - `OrchestratorAccordion.ts` — remove the `signalKind` enum;
     remove the conditional rendering of the clock-overlay (⏱)
     for `last-observed`; remove the "(configured default)"
     qualifier appended to the model line for
     `configured-default`; simplify `modelTooltip()` /
     `effortTooltip()` to one branch.
   - `OrchestratorMarker` view-model simplified: the in-memory
     shape is now identical to the on-disk `orchestrator`
     block (plus display metadata like color tier).
   - CSS cleanup in `media/orchestrator-indicator/indicator.css`:
     remove `.signal-configured-default` /
     `.signal-last-observed` rules; the only remaining variant
     is the default (formerly `signal-current`).
   - Tests in `src/test/suite/orchestratorAccordion.test.ts`
     updated to assert the simplified shape.
3. **MarkerPullthrough check:** ensure no code path is still
   computing `signalKind` from indirect signals (e.g., reading
   MRU file age). The audit's D1 discipline says these are
   forbidden. If any remain, retire them.
4. **`installOrchestratorHookClaudeCode.ts`** — confirm the
   `UserPromptSubmit` hook removal (done in Set 033 Session 3)
   is still in effect; no `signalKind` updates were happening
   there anyway.
5. **Unit tests** updated for the simplified accordion shape.
6. **End-of-session verification** (gemini-pro, Round A).

**Touches:**
- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts` (DELETE)
- `tools/dabbler-ai-orchestration/src/codex/` (DELETE if directory empty)
- `tools/dabbler-ai-orchestration/src/extension.ts`
- `tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
- `tools/dabbler-ai-orchestration/media/orchestrator-indicator/indicator.css`
- `tools/dabbler-ai-orchestration/src/test/suite/orchestratorAccordion.test.ts`

**Deletes:**
- `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts`
- Possibly the `src/codex/` directory itself

**Ends with:** No inference watchers in the extension. Accordion
renders from the orchestrator block directly with no
confidence-level variants. CSS simpler.

**Progress keys:** `session-003/codex-watcher-retired`,
`session-003/signal-kind-enum-removed`,
`session-003/clock-overlay-ui-removed`,
`session-003/configured-default-qualifier-removed`,
`session-003/css-cleaned-up`,
`session-003/marker-view-model-simplified`,
`session-003/tests-updated`,
`session-003/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 4 of 6: Takeover UX (Q3) + watcher-inventory convention test (Q7)

**Goal:** the user-facing takeover UX (modal in IDE / CLI prompt
in terminal) and the code-level enforcement of the watcher-scope
policy.

**Steps:**

1. **Takeover modal in VS Code** —
   - New `chatSessionMismatchModal()` helper invoked by the
     extension code path that consumes the H3 refusal sentinel
     (`CheckoutPollService.ts` is the natural integration
     point).
   - Three actions: **Take Over** (proceeds via
     `start_session --force`), **Open in Read-Only Mode**
     (no-op claim; agent treats subsequent state mutations
     as refused — implementation: a transient flag on the
     in-memory marker that prevents writes through the
     extension's surfaces), **Cancel** (abort).
   - Modal copy resolved in-session (deferred from the
     audit-addendum per [[project_034_035_state_file_sole_truth_audit]]
     pattern of in-session decisions): name the existing
     chatSessionId (truncated to 8 chars), the proposing
     orchestrator's identity, and the three options.
2. **CLI prompt for terminal-only flows** —
   - When `start_session` detects an interactive TTY
     (`sys.stdin.isatty()` true), surface a 1-line prompt
     asking for Take Over / Read-Only / Cancel (single-
     character entry).
   - When non-interactive (no TTY, e.g., scripted invocation),
     refuse with the existing `EXIT_CHECKOUT_CONFLICT` and
     direct the operator to re-run with `--force`.
3. **One-shot affordance** (Q6 fallback). The takeover modal
   has a `Take Over` button; do NOT ship a persistent
   "Remember this choice" checkbox (per Q6 REJECTED).
4. **Toast notifications** retained for secondary awareness
   only:
   - "Another orchestrator is waiting on this set." (informs
     the current holder)
   - "Forced check-out applied by `<identity>`." (audit toast
     visible to other watchers)
5. **Watcher-inventory convention test** (Q7) —
   - New test file
     `tools/dabbler-ai-orchestration/src/test/suite/watcherInventory.test.ts`.
   - Test structure: a hand-maintained `WATCHER_ALLOWLIST`
     array listing each `fs.watch` /
     `vscode.workspace.createFileSystemWatcher` callsite with
     `(file, line, target, purpose)`. The test greps the
     source for watcher primitives and asserts each match is
     in the allowlist. New watchers without allowlist entries
     fail the test with a clear "add me to the allowlist with
     a rationale" message.
   - Initial allowlist entries (post-Set-036):
     - `inProgressSetsService.ts` — `session-state.json`
       truth-source watcher (D1 permitted)
     - `CheckoutPollService.ts` — `~/.dabbler/checkout-conflicts/`
       conflict-prompt watcher (D1 permitted)
     - Any remaining non-orchestrator UI refresh watchers
       (e.g., `activity-log.json` re-render) — explicitly
       permitted under D1 for non-orchestrator purposes.
6. **Unit tests** for the takeover-modal helper + CLI prompt
   flow.
7. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `tools/dabbler-ai-orchestration/src/providers/chatSessionMismatchModal.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/chatSessionMismatchModal.test.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/watcherInventory.test.ts`

**Touches:**
- `tools/dabbler-ai-orchestration/src/providers/CheckoutPollService.ts`
  (integration point for the modal)
- `ai_router/start_session.py` (CLI prompt flow)

**Ends with:** Operator-visible takeover affordances ship;
watcher-scope policy enforced at code-review time via the
inventory test.

**Progress keys:** `session-004/chat-session-mismatch-modal`,
`session-004/cli-takeover-prompt`,
`session-004/exit-checkout-conflict-non-interactive`,
`session-004/toast-secondary-only`,
`session-004/watcher-inventory-test-green`,
`session-004/unit-tests-green`,
`session-004/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 5 of 6: Layer-3 Playwright coverage + cross-tier docs + cross-repo notice

**Goal:** end-to-end test coverage + canonical docs aligned +
cross-repo notice updated for consumer repos.

**Steps:**

1. **Layer-3 Playwright scenarios** in
   `tools/dabbler-ai-orchestration/src/test/playwright/`:
   - `chatsessionid-takeover.spec.ts` — two-chat-instance
     scenario: chat A checks out a set with chatSessionId A1;
     chat B (different chatSessionId B1, same engine+provider)
     attempts to check out the same set; assert the takeover
     modal renders with the correct copy; click Take Over;
     assert state file's chatSessionId is now B1;
     assert the writer log has the handoff audit line.
   - `chatsessionid-missing-tolerance.spec.ts` — start with a
     legacy state file (no `chatSessionId` field); chat C
     runs `start_session`; assert the field is populated on
     first write; subsequent reads from chat D enforce
     strictly.
   - `new-chat-id-cli-flow.spec.ts` — manual flow via the
     fallback CLI. Spawn `python -m ai_router.new_chat_id`,
     capture the UUID, set it as env, then run
     `start_session`. Assert the orchestrator block records
     the UUID.
2. **`docs/session-state-schema.md`** — add the `chatSessionId`
   nested field to the orchestrator-block JSON-shape example.
   Update the "Check-out / check-in (Set 033)" section's H4
   identity-equality rule to reference the chatSessionId
   composite. Update "Block-null invariant" framing to mention
   that chatSessionId is part of what gets cleared on close.
3. **`ai_router/docs/close-out.md`** —
   - Section 2 paragraph extended: mention the `closeout_succeeded`
     event payload extension (Q4 — audit trail).
   - Section 3 step 9 updated: the mark_session_complete bullet
     mentions the chatSessionId clear.
   - Section 4 stranded-checkout recovery paragraph extended:
     a stale chatSessionId triggers the same recovery paths
     (`start_session --force` or "Release Check-Out").
4. **`docs/ai-led-session-workflow.md`** —
   - "Orchestrator check-out / check-in (Set 033)" subsection
     extended for the chatSessionId refinement.
   - New paragraph on the per-set lifecycle lock (Q5).
   - Tier symmetry restated: the chatSessionId requirement
     applies to Lightweight tier too (humans paste their
     `new_chat_id`-generated UUID into the manual state-file
     write).
5. **`docs/cross-repo-checkout-notice.md`** — UPDATE the
   existing one-time copy source. The original (from Set 033)
   described the H4 base composite; the update adds the
   chatSessionId refinement, the `new_chat_id` CLI workflow,
   and the takeover-modal behavior. Operator pulls into each
   consumer manually per the existing pattern.
6. **End-of-session verification** (gemini-pro, Round A; budget
   for Round B given the cross-tier doc reach).

**Creates:**
- `tools/dabbler-ai-orchestration/src/test/playwright/chatsessionid-takeover.spec.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/chatsessionid-missing-tolerance.spec.ts`
- `tools/dabbler-ai-orchestration/src/test/playwright/new-chat-id-cli-flow.spec.ts`

**Touches:**
- `docs/session-state-schema.md`
- `ai_router/docs/close-out.md`
- `docs/ai-led-session-workflow.md`
- `docs/cross-repo-checkout-notice.md`

**Ends with:** Three new Playwright scenarios green; canonical
docs aligned; cross-repo notice ready for operator to push to
the three consumer repos.

**Progress keys:** `session-005/playwright-takeover-green`,
`session-005/playwright-tolerance-green`,
`session-005/playwright-cli-flow-green`,
`session-005/schema-doc-updated`,
`session-005/close-out-doc-updated`,
`session-005/workflow-doc-updated`,
`session-005/cross-repo-notice-updated`,
`session-005/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 6 of 6: Tests + change-log + dual-registry release

**Goal:** final test sweep, change-log aggregation, dual release.

**Steps:**

1. **Full test sweep:**
   - `python -m pytest` (writer changes from S1).
   - `cd tools/dabbler-ai-orchestration && npm run test:unit`
     (Layer-2 coverage for the modal, CLI prompt, watcher-
     inventory).
   - `cd tools/dabbler-ai-orchestration && npm run test:playwright`
     (S5's three new scenarios + the existing Set 033 S4
     scenarios remain green).
   - `npx tsc --noEmit` clean.
2. **Set 036 change-log.md** — final-session aggregation per
   [[project_final_session_changelog_pre_close]].
3. **Version bumps:**
   - `pyproject.toml` 0.6.x → **0.7.0** (minor — feature
     release for the chatSessionId addition).
   - `ai_router/CHANGELOG.md` 0.7.0 entry.
   - `tools/dabbler-ai-orchestration/package.json` 0.18.x →
     **0.19.0** (minor — feature release for the takeover UX
     + watcher retirement).
   - `tools/dabbler-ai-orchestration/CHANGELOG.md` 0.19.0
     entry.
   - `CLAUDE.md` Extension versioning walk extended.
4. **End-of-session verification** (gemini-pro, Round A;
   budget for Round B given the cross-tier writer change).
5. **PyPI release** of `dabbler-ai-router` 0.7.0 (operator-
   gated).
6. **VS Code Marketplace publish** of
   `DarndestDabbler.dabbler-ai-orchestration` 0.19.0 (operator-
   gated; runs `npx vsce package && npx vsce publish
   --pat $env:AZURE_VSCODE_MARKETPLACE_TOKEN` per
   [[reference_vsce_pat]]; honor [[feedback_no_env_var_probing]]
   — do NOT probe the env var with shell substitutions).
7. **`close_session` invocation** for Set 036 Session 6.

**Creates:**
- `docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/change-log.md`

**Touches:**
- `pyproject.toml`
- `ai_router/CHANGELOG.md`
- `tools/dabbler-ai-orchestration/package.json`
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md`

**Ends with:** Migration complete. Both registries shipped.
Cross-repo notice updated for operator to push to the three
consumer repos.

**Progress keys:** `session-006/test-sweep-green`,
`session-006/change-log-generated`,
`session-006/version-bumps-applied`,
`session-006/round-a-verification`,
`session-006/pypi-release-pushed`,
`session-006/marketplace-publish-completed`,
`session-006/close-session-succeeded`

**Estimated cost:** $0.05–$0.20 (verification + dual release).

---

## Risks

- **R1 — Per-set lifecycle lock breaks existing close_session
  callers.** The lock file rename
  (`.close_session.lock` → `.lifecycle.lock`) changes a path
  that some external integration may reference (cleanup
  scripts, monitoring). Mitigation: implement as alias for one
  release — accept either name on read, write only the new
  name. Schedule the alias retirement for a follow-on set.
- **R2 — Claude Code hook payload schema drift.** The audit
  identified `session_id` as the field name in Claude Code's
  SessionStart payload. If a future Claude Code update changes
  the field name, the invoker's pass-through breaks silently.
  Mitigation: the invoker logs a warning when `session_id` is
  not in the payload; the legacy-tolerance branch in
  `start_session` handles the missing field gracefully.
- **R3 — `new_chat_id` CLI shell-flavor coverage.** The audit-
  addendum deferred the exact shell-flavor list to the
  implementation spec. Initial scope: bash + PowerShell.
  Operators on fish / nu / others fall back to manual env-var
  setting. Mitigation: document the limitation in the CLI's
  `--help` output; extend as needed in future patches.
- **R4 — Takeover modal mid-tool-call.** The modal fires at
  session boundaries (per Q2), not mid-tool-call, but a
  partial migration could surface the modal during work if the
  chatSessionId mismatch is detected later than expected.
  Mitigation: Q2's narrow destructive-ops definition limits
  the surfaces where the check runs. Layer-3 test
  `chatsessionid-takeover.spec.ts` exercises the boundary
  behavior end-to-end.
- **R5 — `signalKind` retirement breaks legacy data readers.**
  Marketplace download count is 5 as of 2026-05-21 (was 3 at
  Set 033 close; operator's own + a few new). Internal readers
  update in lockstep; external consumers are negligible.
  Mitigation: reader-side tolerance for `signalKind` in older
  on-disk data (silently dropped on read; not surfaced in UI).
- **R6 — Cross-repo notice fan-out gap.** The three consumer
  repos need the updated notice; operator-driven pull pattern
  has worked historically but is asymmetric. Mitigation: the
  notice itself is timestamped + version-stamped, so
  consumer repos can self-audit by comparing their pasted
  version to the canonical.
- **R7 — Six-session set creep.** The session set is at the
  upper edge of effort:high. If any session blows its
  estimated cost (e.g., S1's lock implementation finds an
  unexpected concurrency bug), the implementation may need a
  session-7 carve-out. Mitigation: keep S1's scope tight to
  writer + lock; defer any deeper investigation to a follow-on.

---

## Routing notes

- **Within-session verification (every session):** gemini-pro
  per [[feedback_ai_router_usage]] (end-of-session only).
  Round A first; Round B only if must-fix.
- **No routed mid-session API calls.** All design questions are
  closed by the audit-locked addendum + this spec; in-session
  decisions (e.g., modal copy, `new_chat_id` shell-flavor
  coverage) are operator-driven via `AskUserQuestion` or
  implementation default.
- **Cross-provider review of this spec** — operator decision
  whether to route a `spec-review-request.md` to Gemini Pro
  before kicking off S1 (Set 032 Session 2 pattern). Optional;
  the addendum already encoded cross-provider consensus on the
  direction.

---

## Total estimated cost

- Session 1: $0.05–$0.15
- Session 2: $0.03–$0.10
- Session 3: $0.05–$0.15
- Session 4: $0.05–$0.15
- Session 5: $0.05–$0.15
- Session 6: $0.05–$0.20
- **Total Set 036 forecast: $0.28–$0.90.**

For context: Set 033's 6 sessions totaled ~$0.20 of $1.25 NTE.
Set 036 is similar scope (writer + reader + UI + tests + docs +
release) but the audit prep was minimal (informal cross-
provider already done), so per-session verification spend
should be similar.

---

## Cross-references

- **Prerequisite session set:** Set 033 (closed 2026-05-21) —
  shipped H1+H2+H3+H4 base composite + OQ1+OQ2. This set
  refines H4 with chatSessionId and reaches into the watcher
  scope discipline.
- **Audit-locked proposal:**
  [`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/)
  — read `proposal-addendum.md` for the locked verdicts.
- **Memory:**
  - [[project_set_032_033_orchestrator_checkout_checkin]] —
    Set 032+033 closure; this set is the follow-on.
  - [[feedback_audit_then_spec_for_substantial_features]] —
    the audit half ran informally; this is the spec half.
  - [[feedback_no_env_var_probing]] — secret-handling
    discipline (relevant to S6's Marketplace publish step).
  - [[reference_vsce_pat]] — Marketplace PAT location.
- **Queue position:** Set 035
  (`035-state-file-sole-truth-marker-retirement`) and Set 034
  (`034-session-set-explorer-styling-iteration`) are queued
  ahead of this set. Recommended execution order:
  Set 035 → Set 034 → Set 036. Set 036 has no hard dependency
  on the others; the recommended order is by impact magnitude
  (smallest reader-only change first, then styling, then this
  larger migration).
