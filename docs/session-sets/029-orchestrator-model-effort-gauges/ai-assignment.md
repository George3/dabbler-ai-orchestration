# Set 029 — AI Assignment

> **Status:** Authored at set-creation time (2026-05-17) by Claude
> Opus 4.7 during the spec-authoring conversation. Per memory
> `feedback_ai_router_usage`, the router is reserved for
> end-of-session verification — this file was authored directly by
> the spec-author without router invocation.

---

## Session 1 of 4: Cross-provider design audit

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Audit synthesis work; needs
high-quality reasoning to draft the proposal coherently and to
synthesize two verifier verdicts into a single locked summary.

### Rationale

Six open design questions hinge on how four different orchestrator
surfaces expose their state. The proposal must be coherent and
specific enough that two frontier verifiers can give meaningful
feedback rather than vague generalities. Opus is the right model
for that synthesis. Effort=high because the design space is large
and the verifier-disagreement resolution will need careful
judgment.

### Estimated routed cost

- 2 audit calls (`task_type='cross-provider-audit'`, gpt-5-4 + gemini-pro):
  $0.15 – $0.50
- 1 session-verification call (`task_type='session-verification'`,
  gpt-5-4): $0.10 – $0.30

Total Session 1: $0.25 – $0.80.

### Constraint reminders

- **Memory `feedback_ai_router_route_result_handling`:** dump
  `RouteResult` to JSON before any attribute access in `route_audit.py`.
  Lost $0.34 across two prior sessions to wrapper-crash bugs.
- **Memory `feedback_split_large_verification_bundles`:** proposal
  doc will be ~400-500 LOC; well under the 700 LOC threshold.

---

## Session 2 of 4: Core webview + Claude detection + hook installer

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Substantial TypeScript +
HTML/CSS + Node/Python hook script + Playwright test. Multiple
surfaces (webview provider, command, helper script, smoke test)
must integrate cleanly.

### Rationale

The webview is non-trivial: CSS gauges, message-passing to/from
the extension host, filesystem watcher, idempotent settings.json
edits in the hook installer. Lots of moving parts; Opus's
multi-file coherence matters.

### Estimated routed cost

$0.10 – $0.30 (one session-verification call only).

---

## Session 3 of 4: Non-Claude provider detection + manual override

### Recommended orchestrator

Claude Opus 4.7 @ effort=high. Each provider's detection mechanism
is its own little system; need to handle them all without
introducing regressions in the Claude path from S2.

### Rationale

S2 establishes the marker-file protocol; S3 adds three new
writers (or three new "manual fallback" paths). The empty-state
CTA logic that picks the right installer is the trickiest piece —
detecting which orchestrator is *currently active* is fuzzy.

### Estimated routed cost

$0.10 – $0.30.

---

## Session 4 of 4: Polish, README, marketplace publish

### Recommended orchestrator

Claude Sonnet 4.6 @ effort=medium. Documentation, screenshot,
version bump, publish. Lower complexity than S1–S3; Sonnet is
sufficient and cheaper. Marketplace publish itself requires
operator confirmation per the standard pre-publish gate.

### Rationale

Editorial work. Sonnet handles README polish and changelog
synthesis well at lower cost. Publish step is operator-driven
(quote the publish command, get confirmation, execute).

### Estimated routed cost

$0.05 – $0.15.

---

## Total set cost forecast

$0.55 – $1.55 (sum across all four sessions). Comfortably within
typical operator NTE thresholds; operator should confirm at start
of Session 1 per memory `feedback_budget_question_scope`.

---

## Next-set recommendations

None planned. If audit (S1) surfaces a sub-design that warrants
its own set (e.g., Gemini Code Assist detection turns out to need
a separate shim with its own release), recommend spinning that as
a Set 030 follow-on rather than expanding 029's scope mid-flight.
