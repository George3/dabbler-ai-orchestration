# Lightweight-Tier Parity — Audit-Locked Spec

> **Status:** **AUDIT-LOCKED 2026-05-26 (S1 closed).** This document
> was originally a STUB; Session 1 ran a two-pass devil's-advocate
> cross-provider audit and rewrote it into this scope-locked spec.
> The audit verdict lives at
> [`docs/proposals/2026-05-26-set-048-lightweight-tier-parity/verdict.md`](../../proposals/2026-05-26-set-048-lightweight-tier-parity/verdict.md).
> **Session Set:** `docs/session-sets/048-lightweight-tier-parity/`
> **Prerequisite:** Set 047 (`047-state-file-schema-v4-audit`) CLOSED 2026-05-26.
> v4 schema canonical and stable. Set 047's HELD PyPI/Marketplace
> publishes will ship BEFORE Set 048 S2 (per audit verdict §4.2 +
> operator confirmation).
> **Workflow:** Orchestrator → AI Router → Cross-provider verification.

## Session Set Configuration

```yaml
totalSessions: 5
prerequisites:
  - 047-state-file-schema-v4-audit
requiresUAT: true
requiresE2E: false
uatStyle: ad-hoc
effort: high
tier: full
```

`requiresUAT: true` because Session 5 ships user-visible Lightweight-tier
flow with new context-menu IA — must be exercised end-to-end before
release. `requiresE2E: false` because the Lightweight path runs through
shells/CLIs primarily; Playwright Layer-3 coverage of the new context-
menu IA lives inside the unit-test surface for that session.
`effort: high` because the touch surface spans Python (router opt-out
+ tri-state runtime), TypeScript (context-menu IA refresh, copyable-
prompt commands), and four doc rewrites. `tier: full` because Set 048
itself is authored on Full-tier discipline; the deliverables ENABLE
Lightweight tier but the development arc is Full.

---

## 1. What this set ships

End-to-end Lightweight-tier parity per the operator-locked premises
(P1-P4 inherited from Set 047 audit) and the four operator-locked
additions L1-L4 (this stub's pre-audit notes). The Lightweight tier
becomes a first-class peer to Full: same writers, same Explorer UX,
same `session-state.json` lifecycle. Differences from Full are limited
to (a) no AI router runtime calls, (b) no auto-verification, (c)
copyable review prompts in lieu of routed verification, (d) suggested-
not-required UAT/E2E.

The set delivers:
- `--no-router` mode on the single `dabbler-ai-router` package
- Tri-state `requiresUAT` / `requiresE2E` (`true | false | "suggested"`)
- Three copyable-review-prompt commands (path-reference format per L1)
- Hierarchical right-click context menu via QuickPick rebuild (per
  audit Bias 3 flip; satisfies L2 + L4 simultaneously)
- "Open AI Assignment" removed (L3)
- Operator upfront positive-confirmation prompt for `"suggested"`
  UAT/E2E (per operator override of audit Bias 4)
- Per-consumer-repo migrator CLI for Lightweight-shape state files
- Doc revisions across bootstrap, schema doc, workflow doc, and
  authoring guide
- `Dabbler: Get Started` wizard gains a tier-conditional branch
- Cross-repo notice for Lightweight consumer paste-in

---

## 2. Operator-locked premises (carry-forward, NOT open to challenge)

**Inherited from Set 047 audit:**

- **P1.** Lightweight orchestrators MUST follow the same process as
  Full for: (a) model and effort identification, (b) session-set
  identification, (c) session identification, (d) `session-state.json`
  updates at appropriate times.
- **P2.** Session Set Explorer UX is identical between tiers.
- **P3.** Lightweight differs from Full ONLY in: no AI router runtime
  calls; no auto-verification; copyable review prompts; suggested-
  not-required UAT/E2E.
- **P4.** Lightweight users must not be required to hand-edit any
  state files.

**Inherited from Set 047 audit (Set-048-scoping decisions D1-D5):**

- **D1.** Single `dabbler-ai-router` package. NO package split.
- **D2.** Copyable-prompt commands ship on Command Palette AND right-
  click context menu.
- **D3.** Three commands: copy-spec-review-prompt, copy-session-
  accomplishments-prompt, copy-set-accomplishments-prompt.
- **D4.** Tri-state for `requiresUAT` / `requiresE2E`: `true | false |
  "suggested"`. Runtime per §3.4 below.
- **D5.** CLI backward compatibility is firm.

**New operator-locked additions (2026-05-26):**

- **L1.** Copyable prompts MUST reference file paths from repo root,
  NOT embed contents.
- **L2.** Hierarchical right-click context menu: `Open File ▸ [Spec |
  Activity Log | Change Log | Session State]` and `Copy Eval ▸
  [Evaluate Specification | Evaluate Most Recent Session | Evaluate
  Session Set]`.
- **L3.** Remove "Open AI Assignment" from right-click context menu.
- **L4.** Context-menu popup must dismiss on focus-loss / Escape
  and/or expose explicit close-button affordance.
- **L5.** Left-click on a Session Set Explorer row ALWAYS opens
  `spec.md` in an editor tab (current behavior preserved). When the
  set is not in a terminal state (not `complete` and not `cancelled`),
  the left-click ALSO copies `Start the next session of \`<slug>\`.`
  to the clipboard and shows a one-line information toast
  (`Copied: Start the next session of <slug>`) so the non-obvious
  clipboard action is discoverable. Terminal-state rows skip the
  clipboard write and toast (spec.md opens only). The same
  "start-next-session" clipboard action is also exposed in the
  right-click QuickPick under `Copy Eval ▸ Start Next Session`.

---

## 3. Scope-locked decisions (from S1 audit verdict)

### 3.1 `--no-router` mode (Group A)

**Activation:** three knobs with documented precedence:

1. CLI flag `--no-router` (highest)
2. Env var `DABBLER_NO_ROUTER=1`
3. `tier: "lightweight"` field in `spec.md`'s YAML config block
4. Default: `full` mode (router enabled)

When a higher-precedence source overrides a lower one, the CLI emits a
`log.info` line: e.g., `"CLI flag --no-router overrides spec tier 'full'
for this invocation."` No refusal; explicit overrides win.

**Lazy LLM-SDK imports:** all `anthropic` / `openai` / `google-
generativeai` imports move inside `ai_router.route()` / `verify()` /
`analyze_cost()`. Under `--no-router`, calling code paths never reach
these imports. Lightweight installations don't need API credentials
in env.

**Verification short-circuit:** under `--no-router`, `mark_session_
complete()` skips the verification call and accepts a pre-supplied
`verificationVerdict` from the operator (default `"manual"`).
`close_session` skips its routed self-check.

**CLI backward compatibility (D5):** existing
`python -m ai_router.start_session …` invocations continue to work
unmodified. The new flags are additive only.

### 3.2 Copyable-review-prompt commands (Group B)

**Format per L1 — path-reference, NEVER content-embed:**

```
[2-5 lines of review instructions tailored to the command]

Files to read (relative to repo root):
  - docs/session-sets/<slug>/spec.md
  - docs/session-sets/<slug>/activity-log.json   (if applicable)
  - docs/session-sets/<slug>/change-log.md       (if present)

[Optional operator-customizable review criteria, embedded from
docs/review-criteria/<spec|session|set>.md if that file exists]
```

**Per-command variations:**

- *Copy spec-review prompt* — path = `<slug>/spec.md`. Instructions
  focus on scope clarity and feasibility. Always enabled on any row.
- *Copy session-accomplishments prompt* — paths = `<slug>/activity-
  log.json` + `<slug>/change-log.md` (if present) + the git command
  `git log --oneline <prev-session-tag>..HEAD` and `git diff <prev-
  session-tag>..HEAD`. Enabled when the set has ≥1 completed session.
- *Copy set-accomplishments prompt* — paths = `<slug>/change-log.md`
  + the set's commit range command. Enabled when `status === "complete"`.

**Clipboard mechanism:** `vscode.env.clipboard.writeText()`. One-line
information toast on success.

**Surfaces (D2):** Command Palette (`dabbler.copySpecReviewPrompt`,
`dabbler.copySessionAccomplishmentsPrompt`, `dabbler.copySet
AccomplishmentsPrompt`) AND right-click context menu under
`Copy Eval ▸` submenu (§3.3).

**Agent-capability documentation:** the Lightweight bootstrap doc
and cross-repo notice must explicitly state that prompts require a
path-aware review agent (Claude Code, Codex, Cline, Cursor). For chat
agents without file access (some Copilot Chat modes, web-based UIs),
the bootstrap doc recommends `Open File ▸ Spec` + manual paste as a
workaround. This handles the agent-capability concern surfaced in
both audit passes WITHOUT violating L1.

### 3.3 Context-menu IA refresh — Bias 3 FLIP locks QuickPick (Group C)

**Decision per S1 audit:** the cursor-anchored HTML popup (Set 034 +
Set 047 S6) is RETIRED. Right-click context menu rebuilt on
`vscode.window.showQuickPick`. Cursor positioning lost; native
accessibility, keyboard navigation, focus management, and theme
respect gained.

**Top-level menu structure:**

| Section | Items |
|---|---|
| `Open File ▸` (submenu) | Spec → `<slug>/spec.md` |
| | Activity Log → `<slug>/activity-log.json` |
| | Change Log → `<slug>/change-log.md` (disabled if file absent) |
| | Session State → `<slug>/session-state.json` |
| `Copy Eval ▸` (submenu) | Evaluate Specification → `dabbler.copySpecReviewPrompt` |
| | Evaluate Most Recent Session → `dabbler.copySessionAccomplishmentsPrompt` |
| | Evaluate Session Set → `dabbler.copySetAccomplishmentsPrompt` |
| | Start Next Session → `dabbler.copyStartNextSessionPrompt` (disabled on terminal-state rows; mirrors the left-click clipboard action per L5) |
| Flat actions | Set Orchestrator… (gated to in-progress rows) |
| | Open Orchestrator Writer Log |
| | Migrate to v4 schema (Set 047 S3 action) |
| | Cancel set |
| | Restore set |

**REMOVED per L3:** *Open AI Assignment* — fully deleted from the menu
schema, the command registration, and any associated code path.

**Close-on-blur (L4):** free byproduct of QuickPick — VS Code's
QuickPick handles click-outside, Escape, and dismiss natively. No
custom close-button needed.

**Submenu rendering implementation:** VS Code QuickPick does not have
native nested-submenu support, but a two-step QuickPick flow (top-
level shows `Open File ▸` / `Copy Eval ▸` / flat actions; selecting
a `▸` item opens a second QuickPick with the submenu items) is the
standard pattern. Cancellation in the second-level QuickPick returns
to the first level; Escape from the first level dismisses entirely.

**Left-click action (per L5):** the existing left-click → opens
`spec.md` behavior is preserved. Additionally, when the row's set
is not in a terminal state (not `complete` and not `cancelled`), the
left-click ALSO writes `Start the next session of \`<slug>\`.` to
the clipboard via `vscode.env.clipboard.writeText()` and shows a
one-line information toast (`Copied: Start the next session of <slug>`).
Terminal-state rows skip the clipboard write and toast entirely
(spec.md opens only). This dual-action left-click is the operator's
high-frequency starting-shortcut; the right-click `Copy Eval ▸ Start
Next Session` exposes the same clipboard action for discoverability.

### 3.4 Tri-state `requiresUAT` / `requiresE2E` runtime (D4)

| Value | At session start | At close-out |
|---|---|---|
| `true` | Full-tier behavior unchanged | Blocks close-out until checklist evidence present |
| `false` | Skipped | No gate |
| `"suggested"` | **If session has UX scope, AI orchestrator asks operator: "E2E tests, UAT checklist, both, or neither?"** Choice recorded in `activity-log.json` (kind: `suggestion_disposition`) | Gate behavior derives from recorded choice — see §3.5 |

**The upfront question is the operator override of audit Bias 4.**
Triple-redundancy reminders (toast + log + close-out warning) are
EXPLICITLY OUT OF SCOPE — replaced by this single positive-confirmation
prompt at session start.

**The tri-state applies to BOTH Full and Lightweight tiers.** A
"suggested" UAT/E2E value is a useful semantic for any set where the
work merits validation but the operator opts to make the call live
rather than commit at spec-authoring time.

### 3.5 Soft gate for `external-verification.md` (Bias 5 PARTIAL FLIP)

Per audit verdict §2.2: `close_session` checks for the presence of
`docs/session-sets/<slug>/external-verification.md` when running under
`--no-router`. If missing AND the session is `"in-progress"`:

- **Interactive mode (TTY):** prints a one-line warning and prompts
  `Continue closing session without verification artifact? [y/N]`.
  Operator answers; close-out proceeds or aborts accordingly.
- **Non-interactive mode (CI, no TTY):** emits the warning to stderr
  and proceeds without prompting.

A `--accept-suggestions` CLI flag forces non-interactive behavior even
in TTY mode (useful for batch operations).

The gate is independent of the UAT/E2E choice from §3.4 — those are
two distinct verification mechanisms.

### 3.6 spec.md schema additions

New fields in the spec.md YAML config block:

- `tier: "full" | "lightweight"` — required for Set 048+ specs.
  Spec validator gains an error on missing-tier in new specs;
  pre-Set-048 specs default to `"full"` for backwards compatibility.
- `requiresUAT: true | false | "suggested"` — schema enum updated.
- `requiresE2E: true | false | "suggested"` — schema enum updated.

### 3.7 Per-consumer-repo migrator (E5)

Set 048 ships `python -m ai_router.migrate_lightweight_to_canonical_v4`
as a single CLI. Idempotent. Recognizes documented non-canonical
shapes (`sessionLog[]` from `great-psalms-scroll-font`; any others
catalogued in S2 source-tree enumeration). Writes `session-state.lwbak.json`
backup file alongside for one-cycle rollback.

Consumer repos run the migrator once during their first post-Set-048
update. Set 048 does NOT ship per-consumer migration commits.

### 3.8 External-verification.md (E7)

Free-form text per audit verdict Q2. No templated header. The
Lightweight workflow doc documents the convention but does not enforce
a format.

Set 048 ships `dabbler.openExternalVerificationDoc` Command Palette
command that opens or creates the file in an editor tab.

### 3.9 Review-criteria storage (E10)

Per-repo files at `docs/review-criteria/spec.md`, `docs/review-
criteria/session.md`, `docs/review-criteria/set.md`. Optional. If
absent, the copyable prompt uses default English instructions. If
present, the file's content is embedded into the prompt's "optional
review criteria" slot.

Set 048 ships template versions of all three files as part of the
bootstrap kit, with a comment header inviting the operator to edit.

---

## 4. Session breakdown

5 sessions (audit S1 already complete + 4 implementation sessions).

| # | Title | Scope |
|---|---|---|
| 1 | Audit pass + scope-lock | **Closed 2026-05-26.** This session. |
| 2 | `--no-router` mode + tri-state schema/runtime + soft gate | §3.1 (activation, lazy imports, verification short-circuit, CLI backcompat). §3.4 (tri-state schema validator + upfront-prompt runtime; AI-orchestrator question recorded in activity-log). §3.5 (external-verification.md soft gate). §3.6 (spec.md schema additions). Python-side primarily; some TS schema-validator updates. |
| 3 | Copyable-prompt commands + Context-menu IA refresh (COMBINED per audit Bias 7 flip) | §3.2 (three commands, Command Palette + context menu, path-reference format, agent-capability docs deferred to S4). §3.3 (QuickPick rebuild, hierarchical submenus, Open AI Assignment removal, close-on-blur free via QuickPick). Layer-3 Playwright spec for new menu structure. |
| 4 | Doc revision + per-consumer migrator + bootstrap tier-branch | §3.7 (migrator CLI). §3.8 (external-verification command). §3.9 (review-criteria template files). Doc rewrites: bootstrap Step 4.5, schema doc §Tier Expectations, workflow doc Step 6, authoring guide tri-state docs. Agent-capability documentation per §3.2 lands here. Wizard tier-branch (E8). Cross-repo notice (D4 in proposal). |
| 5 | UAT + change-log + version bumps + publish | End-to-end Lightweight UAT via `--no-router` + copyable-prompt + tier-branch wizard. UAT checklist. change-log.md. Version bumps: `dabbler-ai-router 0.10.0` + Marketplace `0.23.0`. Single PyPI + single Marketplace publish (Set 047's HELD publishes shipped BEFORE S2). |

---

## 5. Non-goals

- **v4 schema design** — Set 047's territory; Set 048 builds against
  canonical v4.
- **PyPI package split** — rejected in Set 047 Bias 1 flip.
- **Auto-verification for Lightweight** — excluded by premise P3.
- **Orchestrator-block simplification + check-out/check-in rip-out +
  Session Set Explorer orchestrator-rendering removal** — Set 049's
  territory (stub at [`docs/session-sets/049-orchestrator-coordination-removal/`](../049-orchestrator-coordination-removal/)).
  Set 048's writers emit the v4 orchestrator block as-shipped from
  Set 047. Set 049 will reshape AFTER Set 048 lands.
- **Cursor-anchor preservation** — flipped to QuickPick per audit
  Bias 3 flip (§3.3). The Set 034 cursor-anchored popup is retired.
- **Triple-redundancy reminders for `"suggested"` UAT/E2E** —
  operator override of audit Bias 4. Replaced by single upfront
  positive-confirmation prompt (§3.4).
- **Content-embed fallback for copyable prompts** — explicitly
  excluded by L1. Both audit passes recommended it; the cross-provider
  verifier flagged the recommendation as a Critical L1 violation.
  Resolved via agent-capability documentation instead (§3.2).

---

## 6. Open follow-up items (parked for future sets)

- **Q5 deferred:** "Evaluate Implementation Plan" menu item NOT added.
  `plan.md` is not a documented repo convention; revisit if/when a
  plan-document convention emerges.
- **Telemetry on tier adoption** (Pass A suggestion, verifier flagged
  as out-of-scope): not in Set 048. If consumer-tier-adoption metrics
  become useful later, scope a separate audit.

---

## 7. Cross-references

- Audit verdict: [`docs/proposals/2026-05-26-set-048-lightweight-tier-parity/verdict.md`](../../proposals/2026-05-26-set-048-lightweight-tier-parity/verdict.md)
- Audit proposal: [`docs/proposals/2026-05-26-set-048-lightweight-tier-parity/proposal.md`](../../proposals/2026-05-26-set-048-lightweight-tier-parity/proposal.md)
- Pass A primary + verify: [pass_a_primary.md](../../proposals/2026-05-26-set-048-lightweight-tier-parity/pass_a_primary.md), [pass_a_verify.md](../../proposals/2026-05-26-set-048-lightweight-tier-parity/pass_a_verify.md)
- Pass B primary + verify: [pass_b_primary.md](../../proposals/2026-05-26-set-048-lightweight-tier-parity/pass_b_primary.md), [pass_b_verify.md](../../proposals/2026-05-26-set-048-lightweight-tier-parity/pass_b_verify.md)
- Predecessor: [`docs/session-sets/047-state-file-schema-v4-audit/`](../047-state-file-schema-v4-audit/)
- Set 047 audit verdict (Set 048's grounding): [`docs/proposals/2026-05-26-state-file-schema-v4-and-lightweight-parity/verdict.md`](../../proposals/2026-05-26-state-file-schema-v4-and-lightweight-parity/verdict.md)
- Companion set: [`docs/session-sets/049-orchestrator-coordination-removal/`](../049-orchestrator-coordination-removal/) (downstream rip-out work)
- Operator directive memory: `project_lightweight_uses_same_process_as_full.md`
- Audit-then-spec discipline: `feedback_audit_then_spec_for_substantial_features.md`
- Devil's-advocate default: `feedback_devils_advocate_default_for_roadmap_decisions.md`
