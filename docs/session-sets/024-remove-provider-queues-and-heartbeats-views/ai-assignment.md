# Set 024 — AI Assignment

> **Status:** Authored at start of Session 1 (2026-05-15). Authored
> directly by the Session 1 orchestrator per the operator's standing
> constraint that the router is reserved for end-of-session
> verification (memory: `feedback_ai_router_usage`). For Set 023 and
> earlier multi-session sets, the workflow's Step 3.5 routed-analysis
> call would normally produce this recommendation; here the
> orchestrator self-authors and documents the choice explicitly.

---

## Session 1 of 1: Strip the two views + their settings

### Recommended orchestrator

Claude Opus 4.7 @ effort=medium (per `start_session` invocation)

### Rationale

Single-session, deletion-only change. The risk is *unintentional*
removal — an import we didn't notice, a `when` clause that still
references a removed view ID, a stale fallback path in a config
resolver. That risk is best controlled by an orchestrator with strong
surrounding-code awareness, which is why Opus 4.7 is the right choice
over a cheaper tier here. `effort: low` was tempting given the
mechanical nature, but `medium` matches the spec's stated routing note
("Claude Opus 4.7 — has the surrounding-code context to confirm no
stranded imports") and is what `start_session` was invoked with.

### Estimated routed cost

Single cross-provider verification call at session end
(`task_type='session-verification'`, model: `gpt-5-4`). Estimated
$0.05 – $0.30 depending on diff size; actual: **$0.1394**.

### Actuals

- Orchestrator used: Claude Opus 4.7 @ effort=medium
- Routed calls: 1 (end-of-session verification only, per operator's
  standing constraint)
- Total routed spend (this session): $0.1394
- Total routed spend (this set, all sessions): $0.1394
- Verification verdict: SAFE TO SHIP across all six questions
  (Q1–Q6). Two non-blocking refinements raised; one applied
  in-session (CHANGELOG migration sentence), one deferred
  (resolvePythonPath unit test — out of scope for deletion-only).
- Deviations from recommendation: none.

---

## Next-session orchestrator recommendation

Not applicable — Set 024 is a single-session set. The set is complete
once this session closes out.
