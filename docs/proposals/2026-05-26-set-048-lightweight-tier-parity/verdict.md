# Set 048 — Lightweight-Tier Parity — Audit Verdict

**Decided:** 2026-05-26, Set 048 Session 1 close-out.

**Inputs:**
- [proposal.md](proposal.md) (Pass A draft, 414 lines, authored by Claude Opus 4.7)
- [pass_a_primary.md](pass_a_primary.md) — Gemini 2.5 Pro straight read; verdict ENDORSE WITH REVISIONS
- [pass_a_verify.md](pass_a_verify.md) — GPT-5.4-mini cross-provider verify; ISSUES_FOUND on Pass A (L1-violation fix + missing-topic completeness + speculative additions)
- [pass_b_primary.md](pass_b_primary.md) — Gemini 2.5 Pro devil's-advocate; verdict ENDORSE WITH SPECIFIC BIAS FLIPS
- [pass_b_verify.md](pass_b_verify.md) — GPT-5.4-mini cross-provider verify; ISSUES_FOUND on Pass B (Bias 2 fallback violates L1)
- [cost_summary.json](cost_summary.json) — Pass A: $0.024 + $0.027 = $0.051; Pass B: $0.031 + $0.021 = $0.052; **cumulative $0.103 against $10 NTE (1.0%)**

---

## 1. Cross-provider consensus summary

| # | Bias | Pass A | Pass B | Verifier callout | **Verdict** |
|---|---|---|---|---|---|
| 1 | Three-knob activation (CLI/env/spec) | sound | stand by | none | **STAND BY** |
| 2 | Path-reference prompts (L1) | wants content-embed fallback | wants content-embed fallback | **CRITICAL: violates L1** on both passes | **STAND BY (path-reference only)** |
| 3 | Cursor-anchor preservation + HTML submenu | wants QuickPick | wants QuickPick | none | **FLIP → QuickPick** |
| 4 | Triple-redundancy reminder (toast + log + close-out) | sound | stand by | none | **OPERATOR OVERRIDE → upfront positive-confirmation prompt** |
| 5 | Warnings over gates for `"suggested"` | endorse warning | wants soft gate w/ interactive confirm | none | **PARTIAL FLIP → soft gate + CI bypass** |
| 6 | Repo-level review-criteria storage | sound | stand by | none | **STAND BY** |
| 7 | Separate S3 (prompts) + S4 (menu IA) | endorse separation | wants combine | none | **OPERATOR DECISION** (see §4) |
| 8 | Bundle Set 047 + Set 048 publish | endorse bundle | wants ship-first | none | **OPERATOR DECISION** (see §4) |

**Cross-provider verifier (GPT-5.4-mini) caught a Critical correctness error in both passes:** Pass A and Pass B both recommended adding a content-embed fallback to address receiving-agent capability variation. **This violates L1 — the operator-locked premise that copyable prompts MUST reference file paths and NOT embed contents.** The right resolution is to address agent-capability variance in **UX documentation, not in the prompt body** (see §3.5 below).

---

## 2. LOCKED scope decisions (consensus-driven flips)

### 2.1 Bias 3 FLIP — Context-menu rendering: QuickPick, not HTML submenu

**Decision:** Migrate the right-click context menu to `vscode.window.showQuickPick`-based rendering. Drop the cursor-anchored popup with custom HTML submenus.

**Reasoning (both passes agree):**
- Native VS Code API gives accessibility (ARIA + screen reader), keyboard navigation, focus management, and theme-respecting rendering for free.
- HTML submenus on a custom popup would require bespoke implementation of all four, with high ongoing maintenance cost.
- Cursor-anchor positioning is lost — QuickPick opens centered. This is an acceptable regression for a Lightweight UI affordance.
- Forward-compatibility with VS Code updates is guaranteed for QuickPick; not guaranteed for HTML popup.
- Marketplace count is 3 ([[project_marketplace_download_count]]) — the cost of regressing cursor-anchor positioning is bounded.

**Consequence for L4 (close-on-blur):** QuickPick handles click-outside + Escape natively. The L4 directive is satisfied by switching to QuickPick; no separate close-button affordance needed (QuickPick has its own dismiss UI). **L4 is now a free byproduct of the Bias 3 flip.**

### 2.2 Bias 5 PARTIAL FLIP — Soft gate for `"suggested"`, with CI bypass

**Decision:** `"suggested"` UAT/E2E gets a soft gate at close-out. In interactive mode (TTY), the close-out checks for `docs/session-sets/<slug>/external-verification.md`. If missing, the close-out prints a one-line warning and prompts `Continue closing session without verification artifact? [y/N]`. In non-interactive mode (CI, no TTY), close-out emits the warning to stderr and proceeds without prompting (functional equivalent of `false`).

**Reasoning:**
- Pass B's framing — "warning-only renders 'suggested' functionally identical to `false`" — is sharp.
- Pass A's framing — "gating runs counter to Lightweight's low-ceremony spirit" — is also valid for interactive operators.
- Synthesis: interactive operators get the friction (which is the whole point of `"suggested"`); CI invocations don't get hung.
- Detection: `sys.stdin.isatty()` Python-side; `process.stdout.isTTY` Node-side. A `--accept-suggestions` CLI flag forces non-interactive behavior even in TTY mode.

### 2.3 Open-question dispositions (locked)

- **Q1.** CLI flag `--no-router` wins over env var wins over spec-tier setting. Override emits a `log.info` line: `"CLI flag --no-router overrides spec tier 'full' for this invocation."` Stand by proposal's precedence; add the override-notification line.
- **Q2.** `external-verification.md` is free-form text. No templated header. Aligns with low-ceremony Lightweight tier.
- **Q3.** Tri-state `"suggested"` applies to BOTH Full and Lightweight tiers. Not artificially constrained.
- **Q5.** Do NOT add "Evaluate Implementation Plan" to `Copy Eval ▸` submenu. `plan.md` is not a documented repo convention; adding speculative UI is clutter.

---

## 3. STAND-BY scope decisions (proposal as-drafted wins)

### 3.1 Bias 1 — Three-knob activation (CLI > env > spec > default)

Pass A endorsed; Pass B stood by. Three knobs is defensible because each serves a distinct workflow: spec-tier for declarative-default, env var for CI, CLI for one-off debugging.

### 3.2 Bias 2 — Path-reference prompts only (L1 locked, no content-embed fallback)

**Both Pass A and Pass B recommended a content-embed fallback. The cross-provider verifier flagged this as a Critical correctness error on both passes — it violates L1.** Verdict stands: path-reference design only.

**Agent-capability concern is real but resolved via UX documentation, not prompt-format compromise:** the receiving agent must be able to read local file paths (Claude Code, Codex, Cline, Cursor support this; Copilot Chat support varies; web-based chat UIs typically don't). The Set 048 bootstrap doc + the Lightweight notice will document this expectation and recommend compatible review agents. Incompatible chat modes can `Open File ▸` the spec and paste contents manually as a workaround.

### 3.3 Bias 4 — OPERATOR OVERRIDE: upfront positive-confirmation prompt, not triple-redundancy

**Operator decision 2026-05-26 (this audit close):** the triple-redundancy proposal (toast + activity-log + close-out reminder) is **overridden** in favor of a **single upfront positive-confirmation prompt** issued by the AI orchestrator at session start, when the session has a UX component.

**Behavior:**
- At session start, when (a) the session's work has a UX component AND (b) `requiresUAT` and/or `requiresE2E` is `"suggested"`, the AI orchestrator asks the operator a single multiple-choice question: *"This session has UX work. Want E2E tests, a UAT checklist, both, or neither?"*
- The operator's positive choice is recorded once in `activity-log.json` for that session (kind: `suggestion_disposition`, body includes the four-way choice).
- No further nag during the session. Close-out reads the recorded disposition and gates accordingly:
  - "neither" → close-out proceeds, no soft gate.
  - "E2E only" → close-out requires evidence of E2E pass (existing Full-tier gate); UAT checklist gate skipped.
  - "UAT only" → close-out requires UAT checklist evidence; E2E gate skipped.
  - "both" → both Full-tier gates apply.

**Reasoning:**
- Triple-redundancy is passive (operator must notice the reminder). The operator's override makes it active (operator must answer).
- Once answered, the decision is durable — no need for multiple reminder surfaces.
- This collapses the `"suggested"` enum's runtime behavior to: "ask once, gate appropriately, never nag." Cleaner than soft-gate-at-close-out.

**Carry-over for Bias 5 (soft gate for `external-verification.md`):** the Bias 5 disposition (soft gate at close-out for verification) remains separate — it gates on the verification artifact, not on UAT/E2E choice. The two gates are independent.

**Implication for the workflow doc:** `docs/ai-led-session-workflow.md` Step 1 (session start) gains a documented branch — "if requiresUAT/E2E is 'suggested' and UX is in scope, ask the operator."

### 3.4 Bias 6 — Repo-level review-criteria storage

Pass B stood by. `docs/review-criteria/*.md` makes criteria version-controlled, shareable, team-consistent. Per-workspace VS Code setting would decouple criteria from the repo but accommodate only individual preferences — worse default for collaborative repos.

### 3.5 Missing-audit-topic completeness (Pass A verifier callout)

Pass A verifier flagged that the proposal should have explicit "missing topic" sections for (a) receiver-capability variation, (b) submenu accessibility, (c) tri-state generality. **Addressed in this verdict at §2.1 (accessibility via QuickPick flip), §3.2 (capability via UX docs), and §2.3 Q3 (tri-state both tiers).** No spec changes needed beyond the bias-flip absorption.

---

## 4. OPERATOR-DECISION items (split votes)

Two items had genuine split between Pass A (endorse proposal) and Pass B (invert). These are surfaced for operator disposition rather than auto-resolved by the audit:

### 4.1 Bias 7 split — Combine S3 (prompts) + S4 (menu IA) into one session?

**Proposal (Pass A endorsed):** keep separate. S3 ships copyable-prompt commands + Command Palette wiring. S4 ships the context-menu IA refresh (QuickPick migration + L3 removal of Open AI Assignment + submenu wiring).

**Pass B inversion:** combine. Argument: "Session 3 creates commands that Session 4 immediately moves." Implementing them separately means S3 places commands somewhere temporary (top-level menu?) and S4 moves them to the new `Copy Eval ▸` submenu — that's throwaway work.

**Audit's lean (per [[feedback_devils_advocate_default_for_roadmap_decisions]]):** Pass B's argument is rigorous. The commands ARE the items being placed under `Copy Eval ▸`. Combining them would mean: one session implements `dabbler.copySpecReviewPrompt` etc., wires Command Palette entries, and wires them into the QuickPick context-menu in one pass — no throwaway. Net effect: 6-session arc collapses to 5 sessions.

### 4.2 Bias 8 split — Bundle Set 047's HELD publishes with Set 048's release?

**Proposal (Pass A endorsed):** bundle. Set 048's final session ships both Set 047's HELD `dabbler-ai-router 0.9.0` + `0.22.0` Marketplace publishes AND Set 048's new bumps (proposed `0.10.0` + `0.23.0`) in one PyPI + one Marketplace release pair.

**Pass B inversion:** ship Set 047's HELD publishes immediately, BEFORE Set 048 implementation begins. Argument: "Set 048 can then be built and tested against a stable, published v4 baseline, which is a cleaner engineering practice than building on an unreleased foundation."

**Audit's lean:** Pass B is right on engineering hygiene grounds. The HELD publishes are also a memory hazard — operators landing on this repo a month from now will see "PyPI 0.9.0 HELD" with no obvious next step and may publish stale bits. **Recommendation: ship Set 047's publishes BEFORE Set 048 S2 (the first implementation session).** Set 048's eventual close-out then publishes ONLY Set 048's deliverables.

These two items are surfaced for explicit operator confirmation before spec.md is rewritten.

---

## 5. Locked session breakdown (pre-operator-decision; awaiting §4.1)

**If §4.1 disposition is COMBINE (Pass B):** 5 sessions.

| # | Title | Scope |
|---|---|---|
| 1 | Audit pass + scope-lock | **This session.** |
| 2 | `--no-router` mode + tri-state schema/runtime | A1 activation (CLI > env > spec > default), A2 lazy imports, A3 verification short-circuit, A4 backcompat regression tests, D4 tri-state schema validator + runtime, soft-gate close-out per §2.2. |
| 3 | Copyable-prompt commands + Context-menu IA refresh (merged) | Three commands (B1 + B2 + B3), `Copy Eval ▸` + `Open File ▸` submenus, QuickPick migration (Bias 3 flip), Open AI Assignment removed (L3), close-on-blur free via QuickPick (L4). One session, no throwaway. |
| 4 | Doc revision + migrator + bootstrap | All four docs (D1-D4), per-consumer migrator CLI (E5), `Dabbler: Get Started` tier branch (E8), `dabbler.openExternalVerificationDoc` command (E7), `docs/review-criteria/*.md` template files (E10). |
| 5 | UAT + change-log + version bumps + close-out | End-to-end Lightweight UAT. change-log.md. Version bumps (`dabbler-ai-router 0.10.0` + Marketplace `0.23.0`). Publish per §4.2 disposition. |

**If §4.1 disposition is SEPARATE (Pass A):** original 6-session arc from proposal §9.

---

## 6. Cost summary

| Pass | Route model | Route cost | Verify model | Verify cost |
|---|---|---|---|---|
| A | gemini-2.5-pro | $0.0239 | gpt-5-4-mini | $0.0268 |
| B | gemini-2.5-pro | $0.0309 | gpt-5-4-mini | $0.0211 |
| **Total** | | | | **$0.1027** |

**$10 NTE remaining after audit:** ~$9.90. Comfortable headroom for the remaining 4-5 sessions.

---

## 7. Next step

Operator dispositions §4.1 (combine vs separate) and §4.2 (bundle vs ship-first), then spec.md is rewritten to the audit-locked shape and Session 1 closes via `close_session`.
