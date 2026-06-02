# ai-assignment.md — 054-verification-verdict-persistence

Per-session ledger of the cheapest-capable orchestrator. Recommendations
are produced via `route(task_type="analysis")` (never self-opined).

---

## Session 1: Audit & design-lock

### Recommended orchestrator
- N/A (audit session ran on the operator's selected engine).

### Actuals
- **Orchestrator used:** Claude Opus 4.8 (anthropic).
- **Routed spend this session:** ~$0.218
  - cross-provider design consensus — `opus` (mis-routed first attempt,
    same-provider; complexity_hint=70 pushed to tier 3): $0.1398
  - cross-provider design consensus — `gpt-5-4` (OpenAI, the real
    cross-provider critique): $0.0687
  - next-session analysis — `gemini-pro`: $0.0042
- **Deviation / lesson:** the first consensus call used
  `complexity_hint=70`, which routed to tier-3 `opus` — the orchestrator's
  *own* provider, defeating the cross-provider purpose. Fix: target a
  non-Anthropic model explicitly via `providers.call_model` +
  `cfg["providers"][provider]` rather than relying on `route()`'s tier
  selection when cross-provider is the point. (The wasted $0.14 is the
  cost of that lesson; recorded so S2/S3 pin the verifier provider.)
- **Notes for next session:** the design is locked in
  `docs/proposals/2026-06-02-verification-verdict-persistence/verdict.md`
  and summarized in the spec's "S1 Audit Lock" block. Read `verdict.md`
  first — it supersedes `proposal.md` where they differ (the consensus
  collapsed the verdict domain to `VERIFIED`/`ISSUES_FOUND`/`null`).

### Recommendation for Session 2 (routed: `gemini-pro`)
**Sonnet-tier.** S2 is a self-contained, moderate-complexity Python
implementation within an established architecture (Disposition dataclass
field + (de)serialize + soft-warn validation, `resolve_close_verdict`
helper + threading, omit-null event payloads, ~10-14 unit tests including
the idempotent-re-close regression). Existing patterns to mirror
(`check_next_orchestrator_present`, the v4-writer tests). A Sonnet-tier
orchestrator balances code-generation capability against cost; reserve a
flagship engine only if the operator wants maxout.

### Recommendation for Session 3 (routed: `gemini-pro`)
**Haiku-tier.** S3 is low-complexity, procedural: doc reconciliation at
known anchors (`session-state-schema.md` 219/994, workflow Step 6/8,
`close-out.md`), CHANGELOG / change-log / CLAUDE.md walk, `pyproject`
minor bump, cross-provider verify, held publish. Highly constrained
instruction-following work; a cost-effective engine suffices. (The
end-of-session cross-provider verification is non-negotiable regardless
of orchestrator tier.)
