# Set 025 — AI Assignment

> **Status:** Authored at start of Session 1 (2026-05-15). Authored
> directly by the Session 1 orchestrator per the operator's
> standing constraint that the router is reserved for
> end-of-session verification (memory:
> `feedback_ai_router_usage`). Set 025 is a single-session set;
> there is no next-session recommendation.

---

## Session 1 of 1: Author the implementation spec, schema example, and wireframes

### Recommended orchestrator

Claude Opus 4.7 @ effort=medium (per `start_session` invocation)

### Rationale

Doc-only synthesis session. The design space is already locked
across three frontier models (Claude Opus 4.7, GPT-5.4, Gemini Pro
— see `docs/proposals/2026-05-15-router-config-editor-design-audit/`);
this session's job is to translate eight gating decisions into a
form Set 026 can build to. The work is mostly editorial — table
authoring, schema diffing, ASCII layout. The risk is
internal-consistency drift between the three deliverable docs (which
round-1 verification confirmed: 12 specific cross-doc drift issues
were caught, all fixed in-session). `effort: medium` matches the
spec authoring complexity.

### Estimated routed cost

Single cross-provider verification call at session end
(`task_type='session-verification'`, model: `gpt-5-4`). Estimated
$0.10 – $0.30 depending on diff size; actual: **$0.1846**.

This is exclusive of the prior design-audit cost ($0.1197 spent
before Set 025 started at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`).

### Actuals

- Orchestrator used: Claude Opus 4.7 @ effort=medium
- Routed calls: 1 (end-of-session verification only)
- Total routed spend (this session): $0.1846
- Total routed spend (this set, all sessions): $0.1846
- Verification verdict: round 1 found 12 doc-only drift issues
  (no architectural defects); all 5 minimum fixes + 2 Q7
  refinements applied in-session; round-2 reroute skipped per
  Set 023 Session 4 precedent.
- Deviations from recommendation: none.

---

## Next-session orchestrator recommendation

Not applicable — Set 025 is a single-session set. **Set 026
(router-config-editor-implementation)** begins next as a fresh
session set; the operator can spin it up in a new conversation
when ready. Set 026's own ai-assignment.md will be authored at
its Session 1 start with per-session recommendations:

- **Session 1 (outsourceMode clean-sweep):** Claude Opus 4.7 @
  effort=low — mechanical deletion across ~10 Python modules +
  docs; matches the Set 024 deletion-only profile.
- **Session 2 (schema migration + resolver abstraction):** Claude
  Opus 4.7 @ effort=medium — Python schema work; risk is reader
  back-compatibility.
- **Session 3 (webview implementation):** Claude Opus 4.7 @
  effort=high — largest TypeScript surface to date; risk is
  YAML round-trip fidelity + cross-doc consistency with Appendix B.
- **Session 4 (significance-flagging command + annotation):**
  Claude Opus 4.7 @ effort=low — bounded surface (one command +
  one parser).
- **Session 5 (wizard integration + test-notification + release):**
  Claude Opus 4.7 @ effort=medium — coordination work, plus the
  final Marketplace + Open VSX release.

These are guidance for Set 026's authoring; the operator can
re-route any session to a cheaper tier if the work turns out
simpler than estimated.
