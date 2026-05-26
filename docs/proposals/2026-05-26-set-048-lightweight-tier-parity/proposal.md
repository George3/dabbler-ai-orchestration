# Set 048 — Lightweight-Tier Parity — Audit Proposal (Pass A)

**Status:** PASS A DRAFT — awaiting two-pass devil's-advocate cross-provider verification at end-of-Session-1 for scope-lock.

**Authored:** 2026-05-26, Set 048 Session 1.

**Predecessors:**
- Set 047 (`047-state-file-schema-v4-audit`) CLOSED 2026-05-26 (6 of 6 sessions). v4 schema canonical; reader/migrator/writer/Explorer all shipped. PyPI `dabbler-ai-router 0.9.0` + Marketplace `0.22.0` version-bumped but DUAL PUBLISH HELD pending Set 048 close.
- Set 046 (`046-explorer-enrichment-from-harvest-records`) CLOSED 2026-05-26 (2 of 2 sessions). PyPI 0.8.0 + Marketplace 0.21.0 shipped.
- Set 047's audit ([`2026-05-26-state-file-schema-v4-and-lightweight-parity/verdict.md`](../2026-05-26-state-file-schema-v4-and-lightweight-parity/verdict.md)) locked the operator premises P1-P4 that drive this set's work.

**Source-of-truth spec:**
[`docs/session-sets/048-lightweight-tier-parity/spec.md`](../../session-sets/048-lightweight-tier-parity/spec.md) (stub-mode; this proposal is the audit pass the stub deferred to).

---

## 1. Purpose of this proposal

Set 047 scope-locked four operator premises (P1-P4) for the Lightweight tier but carved out the Lightweight-parity *implementation* to Set 048. Set 047 also pre-locked four design decisions on Set 048's scope (single-package + dual-surface commands + tri-state suggested + CLI backcompat). At Set 048 stub-revision time, the operator issued four additional locked directives (L1-L4) that revise the copyable-prompt surface and require a context-menu IA refresh.

This proposal: (i) ratifies the carry-forward premises P1-P4 and the locked decisions from Set 047 S1, (ii) audits the operator-locked additions L1-L4 *under those constraints*, (iii) disposes the open audit topics 1-10 in the stub spec, (iv) recommends a session breakdown for the implementation arc, and (v) calls out drafter biases for explicit devil's-advocate pressure-testing.

**What's NOT in scope for this audit:** the four pre-locked Set 047 decisions (no package split, dual-surface commands, tri-state suggested enum, CLI backcompat); the four operator-locked additions L1-L4; the v4 schema (Set 047's territory, already canonical).

---

## 2. Carry-forward locked items (NOT open to verifier challenge)

The verifier may push back on *consequences* drawn from these but not on the items themselves.

**Inherited from Set 047 audit (operator-locked premises):**

- **P1.** Lightweight orchestrators MUST follow the same process as Full for: (a) model and effort identification, (b) session-set identification, (c) session identification, (d) `session-state.json` updates at appropriate times.
- **P2.** Session Set Explorer UX is identical between tiers. No tier-conditional rendering.
- **P3.** Lightweight differs from Full ONLY in: no AI router runtime calls; no auto-verification; provides copyable review prompts; suggests (not requires) UAT/E2E.
- **P4.** Lightweight users must not be required to hand-edit any state files.

**Inherited from Set 047 audit (Set-048-scoping decisions):**

- **D1.** Single `dabbler-ai-router` package. NO package split. (Bias 1 flip; Path 2 won.)
- **D2.** Copyable-prompt commands ship on BOTH surfaces — Command Palette AND right-click context menu. (Bias 3 flip.)
- **D3.** Three commands: copy-spec-review-prompt, copy-session-accomplishments-prompt, copy-set-accomplishments-prompt.
- **D4.** Tri-state for `requiresUAT` / `requiresE2E`: `true | false | "suggested"`. Runtime: `true` blocks close-out; `false` skips; `"suggested"` logs a reminder without blocking.
- **D5.** CLI backward compatibility is firm: existing `python -m ai_router.start_session` etc. must continue to work after `--no-router` mode lands.

**New operator-locked additions (2026-05-26, this stub):**

- **L1 (revises B2).** Copyable-review prompts MUST reference file paths from repo root, NOT embed file contents. Prompt body = review instructions + relative paths + optional review criteria.
- **L2.** Hierarchical right-click context menu: `Open File ▸ [Spec | Activity Log | Change Log | Session State]` and `Copy Eval ▸ [Evaluate Specification | Evaluate Most Recent Session | Evaluate Session Set]`.
- **L3.** Remove **Open AI Assignment** from right-click context menu.
- **L4.** Context-menu popup must dismiss on focus-loss (click-outside / Escape) and/or expose explicit close-button affordance.

---

## 3. Code-state grounding (pre-audit)

### 3.1 Today's writer call sites (post-Set-047)

All six writers emit canonical v4 shape ([`session-state.json` schemaVersion: 4](../../session-state-schema.md)). The orchestrator block today includes `engine + provider + model + effort + chatSessionId + checkedOutAt + lastActivityAt`; Set 049 (stubbed) will simplify to four fields. **Set 048 picks up the v4 writers AS-IS** — Set 049's simplification is downstream and does not block Set 048.

The v4 writer call sites Set 048 must teach the `--no-router` opt-out are:

| Location | Currently invokes router? |
|---|---|
| `ai_router/session_state.py:register_session_start()` | No — pure state writer, but lives in the `ai_router` package |
| `ai_router/session_state.py:_flip_state_to_closed()` | No — pure state writer |
| `ai_router/session_state.py:mark_session_complete()` | Yes — calls verification before flipping |
| `ai_router/session_lifecycle.py:cancel_session_set()` | No — pure state writer |
| `tools/dabbler-ai-orchestration/src/utils/sessionState.ts:synthesizeNotStartedState()` | N/A (TS, lazy synthesis) |
| `tools/dabbler-ai-orchestration/src/utils/sessionState.ts:ensureSessionStateFile()` | N/A (TS, lazy synthesis) |

**Implication:** `--no-router` mode in Set 048 only needs to short-circuit `mark_session_complete()`'s verification call (and any close-out-time `ai_router.route()` invocations). All other writers are router-free already. This is a narrower surface than the audit drafter initially feared.

### 3.2 Today's `dabbler-ai-router` install footprint

`pyproject.toml` (or equivalent) currently declares LLM-SDK deps: `anthropic`, `openai`, `google-generativeai`, plus `pyyaml`, `pydantic`, etc. Under D1 (single package), Lightweight installs all of these but never imports the LLM ones under `--no-router` mode. The audit must dispose **import-deferral strategy**: import LLM SDKs lazily inside `route()` / `verify()` so `--no-router` invocations never trigger the imports (and never need credentials in env).

### 3.3 Today's context-menu surface (post-Set-034, Set-047-S6-extended)

The Session Set Explorer right-click popup is a custom-rendered webview-anchored element with no native VS Code submenu support. Current items (estimate; audit will confirm by reading source in S2):

1. Set Orchestrator… (Set 047 S6: gated to in-progress rows)
2. Open Orchestrator Writer Log (Command Palette + context menu)
3. Open AI Assignment ← **L3 says delete**
4. Migrate to v4 schema (Set 047 S3)
5. Cancel set
6. Restore set
7. (others — to be enumerated in S2)

Set 048 needs to: drop #3, reorganize the remaining items under the new `Open File ▸` / `Copy Eval ▸` submenus per L2, and add close-on-blur per L4.

### 3.4 spec.md schema today

`spec.md` is partly machine-readable via a `Session Set Configuration` YAML block. Set 047 S5 added the `prerequisites:` field. Set 048 needs to add:

- `tier: "full" | "lightweight"` (proposed) so writers know whether to suppress verification calls without requiring an env var every invocation.
- Tri-state `requiresUAT` / `requiresE2E` (D4) — schema-validator update required.

### 3.5 Operator-customizable review criteria — storage today: NOWHERE

No existing mechanism. Audit topic #10 disposes this. Candidate locations:

- Per-repo file (e.g., `docs/review-criteria/spec.md`, `docs/review-criteria/session.md`, `docs/review-criteria/set.md`).
- Per-workspace VS Code setting (`dabblerSessionSets.reviewCriteria.spec` etc.).
- Per-session-set override file (e.g., `docs/session-sets/<slug>/review-criteria.md`).

### 3.6 Marketplace download count (per memory)

3 downloads (all operator's own per [[project_marketplace_download_count]]). Backwards-compat cost stays low — aggressive removal of "Open AI Assignment" is fine.

---

## 4. Audit Group A — `--no-router` mode design

### A1. Activation mechanism: env var, CLI flag, spec-tier, or all three?

**Question:** how does the operator (or CI) signal that the current invocation should run in `--no-router` mode?

**Candidates:**

- **(a)** Env var `DABBLER_NO_ROUTER=1` (per-shell-session; works for CI).
- **(b)** CLI flag `--no-router` (per-invocation; explicit).
- **(c)** Spec-tier field `tier: "lightweight"` in spec.md (per-set; declarative).
- **(d)** All three with precedence order: CLI flag > env var > spec tier > default (full).

**Proposed disposition: (d) — all three with documented precedence.**

Reasons:
- Per-set declarative tier is the right *default* (the spec author knows the tier).
- Env var supports CI workflows (one knob, all invocations).
- CLI flag supports one-off testing / debugging on a Full set without editing spec.
- Precedence order resolves conflicts deterministically. CLI > env > spec lets explicit overrides win.

**Bias caution for verifier:** the drafter prefers explicit-and-multiple over minimal-and-implicit. Devil's-advocate position: three knobs is two too many. Pass B should weigh whether (c) alone (spec-tier-only) is sufficient and the env/flag introduce only operator confusion.

### A2. Lazy imports of LLM SDKs

**Proposed disposition: ALL LLM SDK imports lazy-loaded inside `route()` / `verify()` / `analyze_cost()`.**

Under `--no-router`, calling code paths never reach the import; no Anthropic/OpenAI/Google credentials needed in env; install footprint is moot for Lightweight users (the SDKs are still on disk but inactive).

**Implementation:** every `from anthropic import …` etc. becomes `def route(): import anthropic; ...`. Standard Python lazy-import pattern.

**Bias caution:** straightforward; minimal Pass B pressure expected.

### A3. Verification call short-circuit in `mark_session_complete()` and `close_session`

**Proposed disposition:** under `--no-router`, `mark_session_complete()` skips the verification call and accepts a pre-supplied `verificationVerdict` from the operator (defaulting to `"manual"`). `close_session` similarly skips its routed self-check.

Per D4, when `requiresUAT: "suggested"` / `requiresE2E: "suggested"`, the close-out emits a Step-10 reminder line but proceeds. Under `--no-router`, no Step-6 routed verification happens; the verdict lands as `"manual"` (or whatever the operator provides via `--verdict <token>` CLI flag).

**Bias caution:** verdict-default value matters. Pass B should weigh `"manual"` vs `"skipped"` vs `"lightweight-tier"`.

### A4. CLI backward-compatibility surface (D5)

**Proposed disposition:** existing `python -m ai_router.start_session …` invocations continue to work in all modes. Under `--no-router`, the only behavioral diff is that the start_session writer no longer requires API credentials to be present (today's lazy-credential-validation path is unchanged in Full mode; lazy in `--no-router` mode).

The audit confirms: no existing entry-point removed; new flags additive only.

---

## 5. Audit Group B — Copyable-review-prompt commands

### B1. Prompt format under L1 (path-reference, not content-embed)

**Proposed disposition:** each of the three commands emits clipboard text of this form:

```
[review instructions, 3-5 lines, e.g., "You are reviewing a session-set
specification. Read the spec at the path below. Evaluate scope clarity,
prerequisite handling, and session-arc balance. Flag specific risks."]

Files to read (relative to repo root):
  - docs/session-sets/048-lightweight-tier-parity/spec.md

[Optional review criteria, operator-customized — see audit topic #10]
```

**Variations per command:**

- **Copy spec-review prompt:** path = `<slug>/spec.md`. Instructions focus on scope clarity and feasibility.
- **Copy session-accomplishments prompt:** path = `<slug>/activity-log.json` + `<slug>/change-log.md` (if present) + the git diff command for the session's commits (e.g., `git log --oneline <previous-session-tag>..HEAD` and `git diff <previous-session-tag>..HEAD`). Instructions focus on did-we-do-what-the-session-promised.
- **Copy set-accomplishments prompt:** path = `<slug>/change-log.md` + the set's commit range. Instructions focus on cumulative deliverable evaluation.

**Bias caution for verifier:** drafter is sympathetic to L1 since the operator just locked it. Devil's-advocate: path-reference assumes the receiving agent can READ files, which Claude Code / Codex / Cline can but Copilot Chat sometimes can't (depending on chat-mode). Pass B should call out the agent-capability dependency.

### B2. Command Palette + right-click parity (D2)

**Proposed disposition:** all three commands appear in both surfaces. Right-click context-menu placement is **under `Copy Eval ▸` submenu** per L2. Command Palette commands use existing `dabbler.copy*Prompt` naming convention.

Right-click enablement rules:
- *Copy spec-review prompt* — always enabled on any session-set row.
- *Copy session-accomplishments prompt* — enabled when the set has at least one completed session.
- *Copy set-accomplishments prompt* — enabled when the set's `status === "complete"`.

**Bias caution:** drafter biases toward gating-by-state for UX hygiene. Devil's-advocate: always-enabled with a "no completed sessions" placeholder message in the clipboard may be lower-cognitive-load. Pass B should weigh.

### B3. Clipboard mechanism

**Proposed disposition:** use `vscode.env.clipboard.writeText()`. Native VS Code API. Cross-platform.

Show a one-line information toast on success: *"Spec-review prompt copied. Paste into your review agent."*

**Bias caution:** straightforward; minimal Pass B pressure expected. Confirms open audit topic #3.

---

## 6. Audit Group C — Context-menu IA refresh (L2 + L3 + L4)

### C1. Submenu rendering approach (open topic #9)

**Question:** the current cursor-anchored popup (Set 034 + Set 047 S6) is a custom-rendered webview HTML element with no native submenu support. How do submenus per L2 work?

**Candidates:**

- **(a)** Keep the cursor-anchored popup; add HTML-rendered submenu (hover-to-expand or click-to-expand sub-popup as a nested HTML element).
- **(b)** Migrate to `vscode.window.showQuickPick`-style menus where submenus are first-class but cursor-anchor positioning is lost (QuickPick opens centered, not at click point).
- **(c)** Hybrid: cursor-anchored top-level popup; clicking a `▸` item opens a sub-QuickPick from the center.

**Proposed disposition: (a) — keep cursor-anchor + HTML-rendered submenu.**

Reasons:
- Cursor-anchor placement is a UX win the operator already validated mid-Set-034.
- HTML submenu is a known web pattern; no VS Code-specific bugs to dodge.
- (b) loses the cursor anchor — visible regression.
- (c) is two separate UI affordances for one menu — cognitive load.

**Bias caution for verifier:** drafter recently shipped the cursor-anchored popup and is biased to preserve it. Devil's-advocate: HTML submenus on a webview-anchored element will need bespoke focus management, accessibility scaffolding, and keyboard navigation; QuickPick gives all that natively. Pass B should pressure-test whether the cursor-anchor preservation is worth the IA complexity.

### C2. Close-on-blur + close-button (L4)

**Proposed disposition:** both. Click-outside / Escape dismisses the popup. A small × in the popup's top-right corner provides an explicit close affordance.

Implementation: webview-level `mouseleave` handler with a debounce (so quick mouse movements don't dismiss); `Escape` key listener; `×` button. Mirror the focus-trap conventions VS Code's QuickPick already establishes.

**Bias caution:** drafter prefers belt-and-suspenders. Devil's-advocate: close-button is redundant if click-outside works correctly. Pass B should weigh whether the redundancy buys discoverability or just clutters the popup.

### C3. Submenu item layout (L2)

The two submenus per L2 are:

- `Open File ▸` opens the chosen file in a VS Code editor tab via `vscode.workspace.openTextDocument(uri)` + `vscode.window.showTextDocument(doc)`.
  - Spec → `<slug>/spec.md`
  - Activity Log → `<slug>/activity-log.json`
  - Change Log → `<slug>/change-log.md` (disabled if file absent)
  - Session State → `<slug>/session-state.json`
- `Copy Eval ▸` invokes the three B-deliverable commands.
  - Evaluate Specification → `dabbler.copySpecReviewPrompt`
  - Evaluate Most Recent Session → `dabbler.copySessionAccomplishmentsPrompt`
  - Evaluate Session Set → `dabbler.copySetAccomplishmentsPrompt`

**Audit ask:** are the four "Open File" items the right four? Candidate fifth: change-log entries directory? Audit-pending.

### C4. Removed items + retained flat items

Per L3, **Open AI Assignment** is removed.

Retained at top level (not under submenus): Set Orchestrator…, Open Orchestrator Writer Log, Migrate to v4 schema, Cancel set, Restore set, (others to be enumerated in S2). These are *actions*, not navigation or evaluation.

**Bias caution:** drafter biases toward "navigation and evaluation get submenus, actions stay flat." Devil's-advocate: all of cancel/restore/migrate could go under an `Actions ▸` submenu for consistency. Pass B should weigh.

---

## 7. Audit Group D — Doc-revision pass

### D1. Hand-edit recipe deletion

**Proposed disposition:** delete the hand-edit recipe from `docs/adoption-bootstrap.md` Step 4.5 and `docs/session-state-schema.md` §Tier Expectations. Replace with the `--no-router` install recipe.

### D2. Workflow doc Step 6 rewrite

**Proposed disposition:** rewrite `docs/ai-led-session-workflow.md` Step 6 to document Lightweight's copyable-prompt verification as a substitution, not a skip. Document that under `--no-router`, the operator MUST run at least one of the three copyable prompts before close-out (otherwise the close-out emits a Step-10 warning).

**Audit ask:** should the close-out *gate* on copyable-prompt invocation (e.g., requiring the operator to write a verification artifact at `docs/session-sets/<slug>/external-verification.md` confirming they ran a review)? Or is the Step-10 warning sufficient?

Pass A position: warning-only. Lightweight users are by-design less ceremonious; gating would push them back toward Full ergonomics.

**Bias caution:** drafter prefers warnings over gates. Devil's-advocate: warnings get ignored; the whole point of "suggested" tri-state was to surface the reminder. Without a gate, the reminder is just noise.

### D3. Authoring guide tri-state docs

Update `docs/planning/session-set-authoring-guide.md` to document `requiresUAT: "suggested"` / `requiresE2E: "suggested"`. Schema validator (`spec.md` parser) accepts the third state.

### D4. Cross-repo notice

Update `docs/cross-repo-harvest-notice.md` (or add `docs/cross-repo-lightweight-notice.md`) for consumer-repo paste-in. Each Lightweight consumer's CLAUDE.md gets a snippet explaining how to install dabbler-ai-router with `--no-router` mode.

---

## 8. Audit Group E — Open question dispositions

### E1. Where do `--no-router` flag values live? (open topic #1)

Disposed in §A1: all three (CLI > env > spec tier > default).

### E2. Copyable-prompt templating (open topic #2)

Disposed in §B1: hard-coded English prompt strings in extension source (TypeScript), composed with relative paths derived from the right-clicked row's session-set identity. The optional review-criteria slot (see E10) is the only operator-customizable piece.

### E3. Clipboard mechanism (open topic #3)

Disposed in §B3: `vscode.env.clipboard.writeText()`.

### E4. Suggested-state reminder UX (open topic #4)

**Proposed disposition:** all three locations.
- `activity-log.json` entry at session start, kind `reminder`, body "UAT suggested for this set; consider checking off `docs/session-sets/<slug>/uat-checklist.md` if present."
- Close-out output: Step-10 reminder line.
- VS Code information toast at session start (one-time per session).

**Bias caution:** drafter biases toward triple-redundancy. Devil's-advocate: pick one (activity log) and let the operator dig if needed. Pass B should weigh.

### E5. Per-repo migration tooling (open topic #5)

**Proposed disposition:** ship `python -m ai_router.migrate_lightweight_to_canonical_v4` as a single CLI that consumer repos can pip-install + run against their own state files. Idempotent. Recognizes the documented non-canonical shapes (`sessionLog[]` from `great-psalms-scroll-font`; any others surfaced in S2 source-tree enumeration).

Each consumer repo runs the migrator once during their first post-Set-048 update. Set 048 does NOT ship per-consumer-repo migration commits — operator runs the migrator in each consumer.

### E6. Router-config under `--no-router` (open topic #6)

**Proposed disposition:** `router-config.yaml` parsing is skipped under `--no-router`. The file may exist (no validation error) but is not loaded. LLM API keys not required.

### E7. Lightweight verification result return-path (open topic #7)

**Proposed disposition:** the operator pastes the review agent's verdict back into a free-form artifact: `docs/session-sets/<slug>/external-verification.md`. Set 048 ships a Command Palette command (`dabbler.openExternalVerificationDoc`) that opens or creates this file. NOT a gate; documentation-only convention.

### E8. Bootstrap UX (open topic #8)

**Proposed disposition:** `Dabbler: Get Started` wizard gains a tier-conditional branch at Step 4.5. Lightweight branch suppresses the API-key-entry step and installs `dabbler-ai-router` with the spec-tier set to lightweight in the generated `spec.md`.

### E9. Context-menu rendering approach (open topic #9)

Disposed in §C1: cursor-anchored popup + HTML submenu.

### E10. Review-criteria customization storage (open topic #10)

**Proposed disposition:** per-repo file at `docs/review-criteria/spec.md`, `docs/review-criteria/session.md`, `docs/review-criteria/set.md`. Optional; if absent, the prompt uses the extension's default English instructions. The copyable prompt's "optional criteria" slot reads the file and embeds its text into the clipboard payload.

**Bias caution:** drafter biases toward repo-level (consistent across team). Devil's-advocate: per-workspace VS Code setting lets individual operators tune without cluttering the repo. Pass B should weigh.

---

## 9. Proposed session breakdown for Set 048

Six sessions (audit S1 + 5 implementation sessions). Sized for commit-able units.

| # | Title | Scope |
|---|---|---|
| 1 | Audit pass + scope-lock | **This session.** Self-author proposal → Pass A → Pass B → synthesis → scope-lock → spec.md rewritten. |
| 2 | `--no-router` mode in `dabbler-ai-router` | A1 activation mechanism (CLI > env > spec tier), A2 lazy imports, A3 verification short-circuit, A4 backcompat regression tests. Schema-validator update for spec-tier field. Tri-state `requiresUAT/E2E` schema-validator + runtime per D4. |
| 3 | Copyable-prompt commands (B1 + B2 + B3) | Three commands, both surfaces, path-reference format per L1, clipboard write, enablement rules, toast feedback. NO context-menu IA changes yet (separate session). |
| 4 | Context-menu IA refresh (C1 + C2 + C3 + C4) | Hierarchical submenus, close-on-blur, close-button, Open AI Assignment removed. Open File ▸ + Copy Eval ▸ wire-up. Layer-3 Playwright spec for new menu structure. |
| 5 | Doc revision + migrator + bootstrap (D1-D4 + E5 + E8) | All four docs rewritten. Per-consumer-repo migrator CLI. `Dabbler: Get Started` tier branch. External-verification command (E7). |
| 6 | UAT + change-log + version bumps + close-out | UAT checklist exercise on the Lightweight-tier flow end-to-end. change-log.md. Version bumps. Bundle Set 047's HELD PyPI/Marketplace publishes WITH Set 048's. |

**Note on bundling Set 047's publishes:** Set 047 closed with version-bumped PyPI 0.9.0 + Marketplace 0.22.0 but DUAL PUBLISH HELD. Set 048 will bump again (PyPI 0.10.0 + Marketplace 0.23.0?) and publish both sets' deliverables in one Marketplace + one PyPI release pair. This avoids two release cycles for back-to-back work and gives Lightweight users a single "everything's there now" version to install.

**Estimated cumulative routed cost:** $1.5-$3.0 against the $10 NTE. Set 047 ran $2.31; Set 045 ran $0.39; Set 046 ran $0.39. Set 048 is closer to Set 047 in audit + implementation scope.

---

## 10. Bias-cautions for the verifier (Pass A + Pass B)

**Bias 1 — Drafter biases toward explicit-and-multiple over minimal-and-implicit.** §A1 proposed all three activation mechanisms (CLI + env + spec) with a precedence order. The verifier should challenge whether spec-tier-only (single declarative knob) is sufficient and the others introduce only operator confusion.

**Bias 2 — Drafter biases toward path-reference design after L1 lock.** §B1's path-reference prompt format inherits the operator's directive. The verifier should pressure-test whether the receiving-agent file-read capability is universally present (Copilot Chat, custom assistants, web-based chat UIs). If not, content-embed should remain as a fallback for the spec-review prompt at minimum.

**Bias 3 — Drafter biases toward cursor-anchor preservation in §C1.** The cursor-anchored popup is operator-validated UX from Set 034. Pass B should challenge whether HTML submenus on a custom popup will introduce focus-management, accessibility, and keyboard-navigation complexity that QuickPick (option b) handles natively.

**Bias 4 — Drafter biases toward triple-redundancy for the suggested-state reminder (§E4).** Three surfaces (activity log + close-out + toast) for one reminder may be over-engineered. Pass B should pick one or two.

**Bias 5 — Drafter biases toward warnings over gates (§D2).** The Lightweight workflow currently has no Step-6 gate. Pass B should weigh whether "suggested" tri-state without ANY enforcement (not even a gate on copyable-prompt invocation) is meaningfully different from `false`.

**Bias 6 — Drafter biases toward repo-level review-criteria storage (§E10).** The verifier should weigh per-workspace VS Code setting as the alternative; arguably better for individual-operator tuning without committing criteria to the repo.

**Bias 7 — Drafter biases toward bundling B2 (copyable-prompt commands) and B7 (context-menu IA refresh) into separate sessions (§9 sessions 3 and 4).** Pass B should weigh whether bundling them into ONE session is faster (both touch the same surface) or whether the separation reduces session-scope risk.

**Bias 8 — Drafter biases toward bundling Set 047's HELD publishes with Set 048's release (§9 session 6).** Pass B should weigh whether Set 047's publishes should ship independently *before* Set 048 starts, so Lightweight users have a v4-capable router earlier in the timeline.

---

## 11. Open questions for the verifier

**Q1.** When the operator has *both* CLI `--no-router` flag set AND spec-tier `full`, should the CLI win (current Pass A position) or should the operator see a refusal-with-warning? The latter is safer but adds friction.

**Q2.** Should `external-verification.md` (§E7) have a templated header (date, session number, verdict-token field) or be entirely free-form? Templated improves machine-readability for future automation; free-form respects Lightweight's low-ceremony spirit.

**Q3.** The pre-locked tri-state `requiresUAT: "suggested"` (D4) — should it apply to Full-tier sets too, or only Lightweight? Pass A position: both tiers. The third state is useful for any set where UAT is a *nice-to-have*. The verifier should confirm whether this generality is desired or whether `"suggested"` should be Lightweight-only (semantic constraint, not enum constraint).

**Q4.** Set 047's HELD publishes — verdict on §9 session 6 bundling. Bundle or ship-first?

**Q5.** Should the right-click context menu's `Copy Eval ▸` submenu also include a fourth item *Evaluate Implementation Plan* (or similar) pointing at any `plan.md` if present? Audit-pending — drafter not sure such a doc convention exists in this repo.

---

## 12. Memory-hook citations

- [[project_set_047_s1_audit_locked]] — the audit that locked D1-D5 and premises P1-P4.
- [[project_set_047_fully_closed]] / [[project_set_047_s6_closed]] — Set 047's close-out and held-publish state.
- [[project_lightweight_uses_same_process_as_full]] — operator directive driving P1-P4.
- [[project_set_049_stubbed]] — orchestrator-block simplification + check-out/check-in rip-out (downstream; Set 048 picks up v4 writers as-shipped from Set 047).
- [[feedback_devils_advocate_default_for_roadmap_decisions]] — two-pass Pass B is default.
- [[feedback_audit_then_spec_for_substantial_features]] — why this audit pass exists.
- [[feedback_budget_question_scope]] — $10 NTE locked for Set 048.
- [[project_marketplace_download_count]] — informs C4 (aggressive removal of Open AI Assignment is fine).
- [[project_lightweight_tier_added_to_bootstrap]] — Set 018 prior art the bootstrap rewrite extends.
- [[project_consumer_repos]] — which consumer repos pick up Lightweight (`dabbler-homehealthcare-accessdb` is the primary candidate).
- [[feedback_user_facing_cost_messaging]] — informs the bootstrap doc's Lightweight-tier sales pitch (no LLM cost in Lightweight mode).
- [[feedback_ai_router_usage]] — restricts in-session router invocations to end-of-session verification; this audit pass is permitted under that policy (it IS the end-of-session-1 verification).
- [[project_session_state_auto_creation_observed]] / [[project_needs_migration_lightweight_repo_observation]] — failure modes Lightweight-parity eliminates.

---

**End of Pass A draft.** Sending to cross-provider consensus next.
