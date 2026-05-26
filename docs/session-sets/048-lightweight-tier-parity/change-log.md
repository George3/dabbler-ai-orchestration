# Set 048 Change Log

**Lightweight-Tier Parity — audit, scope-lock, `--no-router` mode,
tri-state UAT/E2E with upfront positive-confirmation prompt,
copyable-review-prompt commands (path-reference per L1), context-menu
IA refresh on `showQuickPick` (per audit Bias 3 flip), per-consumer
migrator, doc revisions across bootstrap + schema + workflow + authoring
guide, single PyPI + Marketplace publish.**

This set ships end-to-end parity between the Full and Lightweight tiers
per the operator-locked premises P1-P4 (carry-forward from Set 047) and
the four new operator-locked additions L1-L4. The Lightweight tier
becomes a first-class peer to Full: same writers, same Explorer UX,
same `session-state.json` lifecycle. Differences from Full are limited
to no AI router runtime calls, no auto-verification, copyable review
prompts in lieu of routed verification, and suggested-not-required
UAT/E2E.

The audit-locked spec at [`spec.md`](spec.md) scopes 5 sessions: an
audit pass (this S1), then `--no-router` mode + tri-state runtime + soft
gate (S2), then combined copyable-prompt commands + context-menu IA
refresh (S3 — Bias 7 flipped to combine), then doc revision + per-
consumer migrator + bootstrap tier-branch (S4), then UAT + change-log +
version bumps + single bundled publish (S5). Set 047's HELD PyPI +
Marketplace publishes will ship BEFORE S2 begins (Bias 8 flipped to
ship-first) so Set 048 implementation builds against a stable published
v4 baseline.

## Session 1 — Audit pass + scope-lock

Closed 2026-05-26 with disposition `completed`.

- Two-pass devil's-advocate cross-provider consensus over the audit
  proposal at
  [`docs/proposals/2026-05-26-set-048-lightweight-tier-parity/proposal.md`](../../proposals/2026-05-26-set-048-lightweight-tier-parity/proposal.md).
- Verdict at
  [`verdict.md`](../../proposals/2026-05-26-set-048-lightweight-tier-parity/verdict.md):
  8 biases dispositioned (Bias 3 + Bias 5 flipped after Pass B,
  Biases 7 + 8 dispositioned by operator on split votes, Bias 4
  overridden by operator; Biases 1 + 2 + 6 stood by); 5 open questions
  resolved.
- Cross-provider verifier (gpt-5-4-mini) caught a Critical correctness
  issue on BOTH Pass A and Pass B independently: both reviewers
  recommended adding a content-embed fallback for the L1 path-only
  prompt format. The verifier ruled both recommendations as L1
  violations. Resolution: agent-capability variance handled via UX
  documentation, not by reintroducing content-embed.
- Operator override on Bias 4: triple-redundancy reminders (toast +
  activity-log + close-out) replaced by single upfront positive-
  confirmation prompt from the AI orchestrator at session start when
  the session has UX scope and `requiresUAT`/`requiresE2E` is
  `"suggested"`. The operator's four-way choice (E2E / UAT / both /
  neither) is recorded once in `activity-log.json` and read by close-
  out to gate appropriately.
- Stub spec.md rewritten from STUB AUDIT-PENDING to AUDIT-LOCKED with
  `Session Set Configuration` (totalSessions=5, prerequisites=[047],
  tier=full, requiresUAT=true, requiresE2E=false, uatStyle=ad-hoc,
  effort=high), §1-§7 covering full scope-lock.
- Cumulative S1 routed cost: **$0.1027 of $10 NTE (1.0%)**.

### Next-session prerequisite

Before S2 starts: ship Set 047's HELD PyPI `dabbler-ai-router 0.9.0` +
Marketplace `dabbler-ai-orchestration 0.22.0` publishes. Publish action
is operator-initiated (requires Marketplace PAT + PyPI twine
credentials).

<!-- Sessions 2-5 to be appended on each session close-out -->
