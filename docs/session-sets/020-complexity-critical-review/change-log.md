# Set 020: complexity-critical-review — Change Log

**Session:** 1 of 1 completed (2026-05-11)
**Orchestrator:** Anthropic / Claude Opus 4.7 (1M context)
**Verifier 1:** GPT-5.4 (session-verification task type, config-forced)
**Verifier 2:** Gemini 2.5 Pro (analysis task type, max_tier=2)
**Cumulative metered cost:** $0.2337 (GPT: $0.1954, Gemini: $0.0383)
**Within projection?** Yes — spec budgeted $0.35–$1.00; actual was $0.2337.

---

## What this set delivers

A written complexity audit and simplification proposal for the
`dabbler-ai-orchestration` repo surface as of 2026-05-11 (post-Set-019).

**Deliverables:**

| File | Purpose |
|---|---|
| `audit-inventory.md` | 10-bucket structural inventory of the audit surface (A-J), with per-bucket line counts, flags/modes, dependency relationships, and consumer fit notes. Reviewed and approved by operator before routing to verifiers. |
| `verifier-prompt-template.md` | Record of the prompt structure sent to both verifiers (context + philosophy + inventory + targeted excerpts + scoring schema). |
| `provider-responses/gpt-5-4-cuts.md` | GPT-5.4's independent complexity audit. Per-bucket load_bearing scores, Lightweight/no-UAT consumer cost assessments, concrete cut suggestions, and defenses. Overall score: 7/10. |
| `provider-responses/gemini-2-5-pro-cuts.md` | Gemini 2.5 Pro's independent audit. Same structure. Overall score: 7/10. |
| `simplification-proposal.md` | Synthesis: 9 high-confidence cuts, 3 split-opinion items with operator flags, 14 defended-as-load-bearing items, 5 deferred items, and a 3-session Set 021 implementation roadmap. |

**No code or canonical-doc edits landed in this set.** This is analysis-only.

---

## Key findings

**Both verifiers: 7/10 overall complexity score.**

GPT-5.4 verdict: "The repo is functional and mostly principled, but the steady-state
surface is broader than it needs to be because platform-only, recovery-only, and
onboarding-only concerns leak into the default docs and config."

Gemini Pro verdict: "The system is powerfully equipped for its full-tier consumers
but violates its own philosophy by failing to gate extension complexity, imposing
high cognitive costs on simpler consumers."

No philosophical disagreement between verifiers. Tiebreaker route not invoked
(saved $0.10–$0.20 vs. projection).

**Top three unanimous findings:**
1. `docs/ai-led-session-workflow.md` (1,752 lines) imposes HIGH Lightweight consumer
   cost because platform-specific sections (UAT/E2E, outsource-last, adjudication
   detail) are in the universal mandatory-read path.
2. `_wait_for_verifications()` in `close_session.py` — 150+ lines of outsource-last
   queue polling — belongs in its own module rather than the universal close-out script.
3. The router task-type taxonomy (13 types) is wider than the 3-4 types in routine
   use; the others are speculative generality with ongoing sync cost.

---

## What Set 021 should address (operator approves which cuts to implement)

**Session 1 (low-risk doc cleanup, $0 metered):**
- Remove adoption-vs-budget disambiguation from mandatory workflow read
- Remove dabbler-platform migration note from universal authoring guide
- Archive `backfill_session_state.py` + `dump_session_state_schema.py`
- Simplify bootstrap's abstract pattern catalog to concrete examples
- Remove `uatScope: none` as an explicit spec value (derive from `requiresUAT: false`)

**Session 2 (workflow doc restructuring, $0.10–$0.25 metered):**
- Restructure `docs/ai-led-session-workflow.md` into core + full-tier extension
- Move UAT/E2E authoring heuristics from universal guide to platform-addendum.md

**Session 3 (code refactoring, $0.15–$0.35 metered):**
- Extract `_wait_for_verifications()` + queue helpers to `ai_router/queue_verification.py`
- Simplify `--repair` / `--apply` flags
- Prune `router-config.yaml` task types to actually-used set (audit metrics first)
- Add VS Code `when` clauses to hide Full-tier/outsource-last extension views

**Three items flagged for operator decision before Set 021:**
1. SO-1: Remove or addendum-ize the ad-hoc UAT path (depends on healthcare-accessdb timeline)
2. SO-2: Simplify NEXT_ORCHESTRATOR_REASON_CODES to 2+other (depends on whether adjudication metrics are being read)
3. SO-3: Memory system pruning (operator decides which consumer-specific memories to migrate)

---

## Files created in this set

- `spec.md`
- `ai-assignment.md`
- `audit-inventory.md`
- `verifier-prompt-template.md`
- `provider-responses/gpt-5-4-cuts.md`
- `provider-responses/gemini-2-5-pro-cuts.md`
- `simplification-proposal.md`
- `change-log.md` (this file)
- `disposition.json`
- `activity-log.json`
- `session-state.json`
- `session-events.jsonl`
