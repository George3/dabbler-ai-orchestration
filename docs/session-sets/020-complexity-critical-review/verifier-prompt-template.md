# Verifier prompt template — Set 020 complexity audit

**Used by:** `c:\tmp\route_set020.py`
**Routes sent to:** GPT-5.4 (`task_type="session-verification"`) and Gemini 2.5 Pro (`task_type="analysis"`, `max_tier=2`)
**Date sent:** 2026-05-11

This document is a record of what was sent. The routing script inlines the
inventory text and excerpts directly into the prompt; it does not read this file.

---

## Prompt structure

```
[Context block: repo purpose + set 020 purpose + cross-provider intent note]
[Philosophy frame: CLAUDE.md quote]
[Full audit-inventory.md text]
[Targeted excerpts: Rules list / close-out modes / task type table / adjudication ladder / NextOrchestrator]
[Scoring instructions + JSON response schema]
```

---

## Context block (verbatim)

```
You are reviewing the `dabbler-ai-orchestration` repo — a Python / TypeScript
repo that houses shared AI orchestration infrastructure used across three consumer
repos. You are one of two independent verifiers being asked for a complexity
audit. The other verifier is seeing the exact same prompt. Your responses will be
compared without synthesis or peer-influence — independence is the value here.

This is Set 020 of an ongoing internal improvement cycle. The stated reason for
this audit (from the operator, 2026-05-11): "I just want to make sure that the AI
Orchestration hasn't become too complicated. I think that we should critically
evaluate the current functionality to determine if it should be simplified a bit."

The output of this audit is a simplification-proposal.md — a written proposal
listing high-confidence cuts (both verifiers agreed), split-opinion items (one
cut / one defended), defended-as-load-bearing items, and deferred items. The
operator then decides which cuts to implement in a follow-on set. Your job is
to give an honest, independent opinion — not to validate the existing surface.

The orchestrator (running this session) is Anthropic Claude Opus 4.7. You are a
different provider. Differences in opinion are the point.

Note: Set 019 shipped just before this audit (2026-05-11). It added the `uatStyle`
DSL/ad-hoc split and the `disposition.json` schema doc. When evaluating complexity,
assess the steady-state surface — not the recency of the additions.
```

---

## Philosophy frame (verbatim)

```
From CLAUDE.md (the repo's canonical instruction file):

  Universal core, gated extensions, addendum specifics.

  Anything in the core must work unmodified when `requiresUAT: false` and
  `requiresE2E: false` are permanent defaults. UI/UAT/E2E-specific behavior
  must be gated on spec-level flags.

This is the architectural principle the audit should evaluate compliance with.
```

---

## Targeted excerpts (verbatim blocks sent inline)

### Excerpt 1: Rules list (workflow doc §Rules 1–16)

```
(from docs/ai-led-session-workflow.md)

1. One session only. Never execute more than the assigned session.
2. Never skip verification. Every session must be independently verified by a
   different AI provider via route(task_type="session-verification").
3. Never edit session review files.
4. Log every step via log.log_step() — including build, test, and verification.
5. Delegate reasoning to route(). Code review, security review, analysis,
   architecture, documentation, test generation, and session verification always
   go through route(). Do the work directly only for mechanical, single-file
   edits under ~50 lines.
6. Do not commit with unresolved Critical/Major issues.
7. The human controls orchestrator choice.
8. Before every session, read all required-reading files (project-guidance.md,
   lessons-learned.md, session-set-authoring-guide.md).
9. Treat pending human UAT as blocking (applies only when requiresUAT: true).
10. One UAT checklist per session set (applies only when requiresUAT: true).
11. UAT mechanical-verification floor (applies only when requiresUAT: true):
    - 11a. DSL-driven (uatStyle: "dsl") — requires requiresE2E: true; Playwright
      parity; uat-coverage-review task gates handoff.
    - 11b. Ad-hoc (uatStyle: "ad-hoc", the default) — per-item
      ProgrammaticVerification or NoProgrammaticPathReason; orchestrator validates
      locally.
12. Share screenshots during UI and E2E work when practical.
13. Escalate durable new guidance to project-guidance.md.
14. Recommend lessons learned after failures.
15. Run the Step 9 reorganization review on the last session of every set.
16. Register session start before the first activity-log entry.
```

### Excerpt 2: close_session.py invocation modes

```
(from ai_router/close_session.py, 1677 lines total)

Mode 1 — Normal: python -m ai_router.close_session --session-set-dir <path>
  Runs 5 gate checks → waits on verification (if queue mode) → emits events
  → flips session-state.json to closed.

Mode 2 — Force: --force + env var AI_ROUTER_ALLOW_FORCE_CLOSE_OUT=1 + --reason-file
  Bypasses all gate checks. Hard-scoped to incident recovery. Emits
  closeout_force_used event with operator narrative. Writes forceClosed=true.

Mode 3 — Manual-verify: --manual-verify + (--interactive or --reason-file)
  Bypasses the queue-verification wait. Operator attests manually. Audit-trail
  event recorded with attestation text. Cannot combine with --force.

Mode 4 — Repair: --repair
  Diagnostic walk of session-state.json ↔ session-events.jsonl ↔
  disposition.json ↔ queue messages. Reports 4 drift cases. Does not modify state.

Mode 5 — Repair+apply: --repair --apply
  Applies corrections for drift cases 1 and 2 (synthetic event append and
  state flip). Cases 3 (missing queue messages) and 4 (stranded mid-closeout)
  are report-only.

Five gate checks (gate_checks.py, 630 lines):
  - check_working_tree_clean
  - check_pushed_to_remote
  - check_activity_log_entry
  - check_next_orchestrator_present
  - check_change_log_fresh
```

### Excerpt 3: disposition.json schema (from docs/disposition-schema.md)

```
Fields:
  status: "completed" | "failed" | "requires_review"
  summary: str  (non-empty narrative)
  verification_method: "api" | "queue"
  files_changed: List[str]
  verification_message_ids: List[str]  (non-empty iff verification_method=="queue")
  next_orchestrator: NextOrchestrator | null
    (required when status=="completed" AND not final session of set)
  blockers: List[str]
    (non-empty when next_orchestrator.reason.code=="switch-due-to-blocker")

NextOrchestrator fields:
  engine, provider, model, effort
  reason: { code: continue-current-trajectory | switch-due-to-blocker |
                   switch-due-to-cost | other
            specifics: str (>=30 chars) }
```

### Excerpt 4: Task-type taxonomy (from router-config.yaml + workflow doc)

```
13 task types; relevant forced-model overrides:
  session-verification  → gpt-5-4  (cross-provider pin for Claude orchestrators)
  architecture          → opus     (100% verifier rejection at tier-2 in early metrics)
  code-review           → sonnet   (rationale: Anthropic better at line-by-line)
  uat-plan-generation   → opus
  uat-coverage-review   → opus
  session-close-out     → sonnet

Types without forced model (tier-based routing): formatting, summarization,
documentation, test-generation, analysis, refactoring, security-review, planning.

Tier mapping: tier-1 = gemini-flash, tier-2 = gemini-pro + sonnet + gpt-5-4-mini,
tier-3 = opus + gpt-5-4.

Complexity estimation weights: context_length 30%, keyword_signals 35%,
task_type 20%, explicit_hint 15%.

DELIBERATE NON-GOAL (comment in router-config.yaml): "Do not invest further
engineering in tightening this heuristic." The 2-try escalation safety net is the
intended stopping point.
```

### Excerpt 5: Adjudication ladder (Step 7, workflow doc)

```
When the orchestrator disagrees with a verifier finding it must present to
the human: the exact finding, the dismissal reason, the context sent to the
verifier, and a self-assessment of context completeness.

The human then chooses:
  (a) Accept verifier finding — fix it.
  (b) Accept orchestrator's dismissal — close without changes.
  (c) Re-verify with reshaped context — same verifier, adjusted input.
  (d) Second opinion from a different provider — uses tiebreaker_model from
      router-config.yaml verification.settings.on_disagreement.

Whichever option the human picks, the orchestrator logs via record_adjudication()
which writes one JSON line to router-metrics.jsonl with fields:
  task_type, cause (context-gap | genuine-split | orchestrator-error),
  resolution (accept-finding | accept-dismissal | reverify-reshaped | second-opinion),
  session_set, session_number, generator_model, verifier_model,
  finding_summary, dismissal_reason.
```

### Excerpt 6: Session spec configuration flags

```
Spec-level configuration (per session set, declared in spec.md):
  totalSessions: int
  requiresUAT: false | true
  requiresE2E: false | true
  uatStyle: "ad-hoc" | "dsl"   (default "ad-hoc"; only meaningful if requiresUAT: true)
  uatScope: "none" | "per-session" | "per-set"
  effort: low | normal | high
  outsourceMode: first | last

Invalid combination: uatStyle: "dsl" + requiresE2E: false → rejected at Step 2.
```

---

## Scoring instructions and JSON schema (verbatim)

```
Score each of the 10 buckets (A through J) listed in the inventory on:

  1. load_bearing (1-10): How essential is this to the stated repo philosophy?
     10 = impossible to remove; 1 = pure ornament, all consumers could skip it.

  2. lightweight_consumer_cost ("high"|"medium"|"low"|"none"): How much dead
     weight does a Lightweight-tier consumer (Explorer + spec files only,
     no ai_router) encounter in this bucket's docs/code? "high" = they're
     forced to read past/understand it; "none" = completely skipped.

  3. no_uat_e2e_consumer_cost ("high"|"medium"|"low"|"none"): How much of this
     bucket's surface is consumed by a Full-tier consumer that always has
     requiresUAT: false and requiresE2E: false?

  4. cuts: Array of concrete cut suggestions. Each cut:
     - what: one-line description of what to remove or simplify
     - file: the primary file (path is fine)
     - rationale: one-sentence rationale
     - risk: "low" | "medium" | "high"

  5. defenses: Array of items you think should stay despite being complex.
     Each defense:
     - what: one-line description of what to keep
     - rationale: one-sentence rationale

  6. overall_complexity_score (1-10): Your aggregate verdict on the whole
     surface — is this framework over-, right-, or under-engineered for its
     three stated consumers?

Return ONLY a JSON object matching this schema. No surrounding prose.

{
  "overall_complexity_score": <int 1-10>,
  "overall_verdict": "<one sentence>",
  "buckets": {
    "A": {
      "load_bearing": <int>,
      "lightweight_consumer_cost": "<high|medium|low|none>",
      "no_uat_e2e_consumer_cost": "<high|medium|low|none>",
      "cuts": [{"what": "...", "file": "...", "rationale": "...", "risk": "..."}],
      "defenses": [{"what": "...", "rationale": "..."}]
    },
    "B": { ... },
    "C": { ... },
    "D": { ... },
    "E": { ... },
    "F": { ... },
    "G": { ... },
    "H": { ... },
    "I": { ... },
    "J": { ... }
  }
}
```
