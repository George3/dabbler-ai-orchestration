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

## Session 2 — `--no-router` mode + tri-state schema/runtime + soft gate

Closed 2026-05-26 with disposition `completed`.

Four commits land the Lightweight-tier `--no-router` mode infrastructure
per audit-locked spec §3.1, §3.4, §3.5, §3.6:

- **A** ([`44a1d45`](../../../../commit/44a1d45)) — spec.md schema additions: `tier` field +
  tri-state UAT/E2E. New `ai_router/spec_config.py` Python parser
  mirroring the TS parser at
  `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`. 16 Python +
  10 TS tests; 6 TS test fixtures updated for the new required field.
- **B** ([`90b7c0c`](../../../../commit/90b7c0c)) — `--no-router` activation infrastructure.
  New `ai_router/runtime_mode.py` with three-knob precedence
  (CLI flag > env var `DABBLER_NO_ROUTER` > spec.md `tier` field >
  default `full`). CLI flags `--no-router` (start_session + close_session)
  and `--accept-suggestions` (close_session) added; `main()` resolves
  runtime mode at entry-point startup. Override logging via `log.info`
  names the source that won when CLI/env contradicts spec. Lazy
  LLM-SDK imports per §3.1 A2 documented as no-op (providers.py uses
  httpx directly). 29 new unit tests.
- **C** ([`1eed29a`](../../../../commit/1eed29a)) — `route()` / `verify()` short-circuit +
  `external-verification.md` soft gate. `route()` and `verify()`
  prologues return zero-cost stubs without calling `_init()` when
  `is_no_router_mode()` is True. `close_session.run()` integration:
  manual-attestation block + method resolution + new soft gate after
  gate_checks pass + before state flip. Soft gate branches on
  `--accept-suggestions` / TTY / non-TTY; aborts with
  `result="aborted_at_soft_gate"` + `closeout_failed` event on TTY
  non-affirmative answer. 5 route/verify short-circuit + 12
  close_session integration tests.
- **D** ([`bd94205`](../../../../commit/bd94205)) — `suggestion_disposition` reader/writer
  helpers (new `ai_router/suggestion_disposition.py`) + 13 CLI
  backward-compat regression tests. **Deferral note**: the close-out
  *gate* that USES these helpers ships in S3 because Full-tier
  `close_session.py` has no existing UAT/E2E gate today — adding one
  would touch Full behavior outside the audit scope. Documented in
  module docstring + commit message + this change-log.

### Cross-provider verification round

Route (`sonnet`, $0.132) + verify (`gemini-pro`, $0.015) = **$0.147**
routed for S2. Verifier confirmed `ISSUES_FOUND` with 7 findings:

| # | Severity | Disposition |
|---|---|---|
| 1 | Critical — route/verify silent-swallow falls back to live LLM | **FIXED** in-flight (fail-CLOSED with top-level import) |
| 2 | Major — bare imports | **FALSE POSITIVE** (matches existing package convention) |
| 3 | Major — race condition on activity-log read-modify-write | **FIXED** in-flight (write-temp + atomic-rename) |
| 4 | Major — `resolve_no_router_mode` re-entry overwrites cache | **FIXED** in-flight (no-op on re-entry) |
| 5 | Important — false-positive tier detection from full-file fallback | **FIXED** in-flight (`tier:` read only from canonical YAML block; UAT/E2E retain Set 015 plain-text fallback) |
| 6 | Minor — timestamp not UTC | **FIXED** in-flight |
| 7 | Suggestion — lazy cache consistency | **DEFERRED** (production callers always resolve at entry-point startup) |

2 new regression tests for I5 lock in the behavior:
`test_tier_from_free_form_prose_is_ignored` and
`test_requiresUAT_in_plain_text_still_parses_set015_compat`.

### Test counts at close

- **Python:** 982 passed + 1 skipped (98 new for S2). Cumulative
  Set 048 routed spend $0.250 of $10 NTE (2.5%).
- **TypeScript:** 633 passed + 2 pre-existing failures unrelated to S2.

<!-- Sessions 3-5 to be appended on each session close-out -->
