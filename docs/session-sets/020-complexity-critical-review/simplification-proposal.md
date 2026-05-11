# Simplification proposal — `dabbler-ai-orchestration`

**Audit date:** 2026-05-11
**Set:** 020-complexity-critical-review
**Verifiers:** GPT-5.4 (session-verification, $0.1954) + Gemini 2.5 Pro (analysis, $0.0383)
**Verifier total:** $0.2337

**Both verifiers scored the surface: 7/10 — functional and principled, but the steady-state surface is wider than it needs to be because platform-only and recovery-only concerns leak into the universal docs and config.**

No material philosophical divergence was found between verifiers. Tiebreaker route was not invoked. All split-opinion items are specific cuts rather than fundamental disagreements.

---

## Section 1 — High-confidence cuts

*Both verifiers independently proposed or strongly supported each item.*

### HC-1: Split `docs/ai-led-session-workflow.md` into core + full-tier extension

**Both verifiers flagged:** GPT-5.4 (Bucket A, medium risk) + Gemini Pro (Bucket A, low risk).
**Status: HIGH priority.** Bucket A scored Lightweight consumer cost: HIGH by both verifiers.

The 1,752-line workflow doc forces every orchestrator — including those running Lightweight or non-UAT sets — to read past sections on outsource-last queue mechanics, UAT/E2E gate stacks, verifier-disagreement adjudication detail, parallel trigger phrase variants, and orchestrator-switching instructions. These sections are never relevant to the majority of sessions.

**Concrete next step:**
Restructure `docs/ai-led-session-workflow.md` into two clearly marked halves:
- **Core (always-read):** Steps 0–10 (abbreviated — remove platform-specific elaborations from each), Rules 1–8 and 12–16, session set config block overview (one compact table, not per-flag prose), Orchestrator Instruction Files.
- **Full-tier extension (read only when `requiresUAT: true` or `outsourceMode: last` or when troubleshooting):** UAT Checklist Rules (both paths), E2E gate, adjudication ladder, delegation discipline, outsource-last queue flow, parallel trigger variants.

GPT suggested moving reference material to appendices within the same file; Gemini suggested a second file (`lightweight-workflow.md` + `full-tier-addendum.md`). **Recommendation: one file, but with a clearly-marked `---` divider and a "skip to here if requiresUAT:false and outsourceMode:first" shortcut note** — no new files to maintain. Estimated reduction: 400-600 lines from the mandatory-read path.

**Risk:** Medium. Every instruction file (CLAUDE.md, AGENTS.md, GEMINI.md) references this doc. The restructure must not break the pointer. Mitigation: keep the section headings (Steps, Rules) at the same depth; just reorder/group, don't rename.

---

### HC-2: Move UAT/E2E authoring content from the universal authoring guide to a consumer addendum

**Both verifiers flagged:** GPT-5.4 (Bucket B, low risk) + Gemini Pro (Bucket B, low risk).

`docs/planning/session-set-authoring-guide.md` itself references the "repo-specific addendum" pattern for UAT/E2E conventions. Currently the "When UAT is required," "When E2E is required," and "Choosing uatStyle" sections (~200 of 489 lines) live in the universal guide instead of following their own advice.

**Concrete next step:**
Move the three UAT/E2E heuristic sections to `docs/planning/session-set-authoring-guide.platform-addendum.md` (matching the convention already named in the universal guide). The universal guide retains the config-block field table (as reference) but the decision heuristics live in the addendum. The universal guide gains one pointer line: "For UI/UAT/E2E repos, see the repo-specific addendum."

Also per GPT: remove the `dabbler-platform` migration note from the universal guide (it belongs in the set's change-log, not a steady-state guide).

**Risk:** Low. The authoring guide is a spec-authoring reference, not a runtime contract. Pointer links are the only breakage risk.

---

### HC-3: Simplify the abstract pattern catalog in the adoption bootstrap

**Both verifiers flagged:** GPT-5.4 (Bucket C, low risk) + Gemini Pro (Bucket C, medium risk — "premature generalization").

Step 6 of `docs/adoption-bootstrap.md` offers a 7-pattern abstract catalog (input artifacts, output artifacts, cross-cutting themes, stated objectives, inferred organizational patterns, risk/dependency layers, stakeholder review boundaries) as guidance for a fresh AI to propose session-set decompositions. Gemini called it "a layer of abstraction that increases cognitive load during interactive onboarding." GPT said "helpful but not essential to the core bootstrap transaction."

**Concrete next step:**
Replace the 7-pattern abstract catalog with 2–3 concrete examples (e.g., "a UI-form feature set: one session per form flow + one testing session"; "a data-migration effort: schema → ETL → validation → rollback"). Abstract patterns become a brief appendix that an AI can consult but doesn't have to enumerate.

**Risk:** Low. The bootstrap is a clipboard prompt; an AI orchestrator adapts to example-based guidance as readily as to abstract catalogs.

---

### HC-4: Extract outsource-last queue polling from `close_session.py`

**Both verifiers flagged:** GPT-5.4 (Bucket D, low risk) + Gemini Pro (Bucket D, medium risk).

`_wait_for_verifications()` — the 150+ line function that polls `provider-queues/<provider>/queue.db` — lives inside `close_session.py`. It exists solely for `dabbler-platform`'s `outsourceMode: last` workflow. Every `close_session.py` reader encounters this function even on `outsourceMode: first` repos.

**Concrete next step:**
Extract `_wait_for_verifications()`, `_discover_queue_providers()`, `_lookup_message()`, and `_MessageOutcome` into `ai_router/queue_verification.py`. `close_session.py` imports and calls the function unchanged. No behavioral change; the module boundary makes the outsource-last dependency explicit and the main close-out script readable.

**Risk:** Low. Pure refactor — same logic, different module file. Test suite coverage is already in place.

---

### HC-5: Simplify `--repair` / `--repair --apply`

**Both verifiers flagged:** GPT-5.4 (Bucket D, medium risk) + Gemini Pro (Bucket D, low risk).

The current CLI has two separate flags: `--repair` (diagnostic, no state change) and `--repair --apply` (corrective). Gemini's proposed simplification: a single `--repair` that shows what it would do and prompts "Apply fixes? [y/N]" — consistent with standard dry-run patterns, no flag memorization. GPT goes further: a separate repair CLI. **Recommend Gemini's simpler form** (same file, just merge the flags with an interactive or `--yes` override).

**Concrete next step:**
In `ai_router/close_session.py`: deprecate `--apply` as a standalone flag; fold its behavior into `--repair` with an interactive confirmation prompt (or `--repair --yes` for non-interactive use). Keep the non-interactive `--yes` for scripted use. Net delta: remove one flag, add `--yes` alias.

**Risk:** Low. `--repair` is documented as a rare recovery path; no consumer has it scripted without `--apply`.

---

### HC-6: Archive `backfill_session_state.py` and `dump_session_state_schema.py`

**Both verifiers flagged:** GPT-5.4 (Bucket E, low risk) + Gemini Pro (Bucket E, low risk).

These two modules served the v1→v2 session-state schema migration. Assuming the migration is complete across all consumer repos, they are dead weight in the main `ai_router/` package.

**Concrete next step:**
Move both files to `ai_router/scripts/` (or delete them if no consumer needs them). Update `__init__.py` or `setup.py` if they are exported. Confirm migration complete by checking session-state.json schemaVersion in all consumer repos.

**Risk:** Low. Both are standalone scripts, not imported by runtime code. The test for "are they needed?" is: does any consumer's session-state.json still have `schemaVersion: 1`?

---

### HC-7: Prune the router task-type taxonomy

**Both verifiers flagged:** GPT-5.4 (Bucket F, medium risk) + Gemini Pro (Bucket F, medium risk).

The router config defines 13 task types but routine sessions use ~4 (session-verification, architecture, uat-plan-generation, uat-coverage-review, and occasionally analysis or code-review). The other 7–9 types are speculative generality — they are in the config, in the task_type_scores table, in the task_type_params section, and in the always_route_task_types list. All of those lists need to stay in sync.

**Concrete next step:**
Audit actual usage via `router-metrics.jsonl` across all consumer repos. Remove task types with zero or near-zero usage from the config. Types proposed for removal: `formatting`, `summarization`, `documentation`, `test-generation`, `refactoring` (rarely used; the `analysis` type covers most of their use cases). Types to keep: `session-verification`, `architecture`, `uat-plan-generation`, `uat-coverage-review`, `analysis`, `code-review`, `security-review`, `planning`, `session-close-out`.

**Risk:** Medium. Any consumer that calls `route(task_type="formatting")` would need to switch to a kept type. Confirm via grep across consumer repos before removing.

---

### HC-8: Fix the adoption × budget naming confusion

**Both verifiers flagged:** GPT-5.4 (Bucket G, low risk) + Gemini Pro (Bucket G, low risk).

The two-tier framing ("adoption tier" + "budget tier") is described in the workflow doc's mandatory read path even though already-adopted repos never need it re-explained. GPT flagged removing the disambiguation paragraph from the mandatory read; Gemini proposed merging the tiers into a single "Service Tier" concept.

**Recommend GPT's simpler cut:** The two dimensions ARE genuinely orthogonal (a $0 Full-tier consumer has the router machinery without metered calls — that's different from Lightweight). Merging would lose that nuance. The fix: remove the disambiguation paragraph from `docs/ai-led-session-workflow.md`'s mandatory read path and keep it only in `docs/adoption-bootstrap.md` where it is directly actionable.

**Concrete next step:**
Delete the ~12-line adoption-vs-budget disambiguation paragraph from `docs/ai-led-session-workflow.md` §"Cost-budgeted verification modes". Link to `docs/adoption-bootstrap.md` Step 4.5 for reference. The workflow doc's job is orchestrator operating procedure, not taxonomy education.

**Risk:** Low. The paragraph is explanatory; removing it doesn't change any behavior.

---

### HC-9: Use VS Code `when` clauses to hide Full-tier/outsource-last extension features

**Both verifiers flagged:** GPT-5.4 (Bucket I, low-medium risk) + Gemini Pro (Bucket I, low risk).

The Cost Dashboard, ProviderHeartbeatsProvider, and ProviderQueuesProvider tree views are always visible in the extension regardless of the project's adoption tier or outsource mode. Lightweight consumers see a Cost Dashboard with no data; non-outsource-last consumers see Provider Queues with nothing in them.

**Concrete next step:**
Add VS Code `when` clause conditions to the relevant `contributes.views` entries in `package.json` (e.g., `when: "dabbler.sessionSets.hasAiRouter"` or `when: "dabbler.sessionSets.outsourceLast"`). The extension already reads `session-state.json` on activation; detecting Full-tier vs. Lightweight is achievable by checking for the presence of `ai_router/router-config.yaml` in the workspace.

**Risk:** Low. `when` clauses are additive — if the condition is misconfigured, the view is visible when it shouldn't be (not hidden when it should). No data is at risk.

---

## Section 2 — Split-opinion items

*One verifier proposed a cut; the other defended keeping it. Operator adjudicates.*

### SO-1: Ad-hoc UAT path (`uatStyle: "ad-hoc"`, added Set 019)

**GPT-5.4:** Move Rule 11b and the ProgrammaticVerification/NoProgrammaticPathReason mechanics to a "dormant addendum" if the path remains unused. Don't remove — it'll be needed when healthcare-accessdb migrates.

**Gemini Pro:** Remove entirely. "No consumer has used it in production yet. This is speculative complexity (YAGNI) added for a potential future consumer." Cut it and re-add it when demonstrated need appears.

**Orchestrator read:** Gemini's YAGNI argument has merit — the path is untested in the wild, and untested rules accumulate bugs quietly. But the cut has a real cost: healthcare-accessdb is a stated candidate for Lightweight adoption or ad-hoc UAT, and cutting the rule would require re-opening Set 019 decisions the next time that repo migrates. The "dormant addendum" path (GPT) costs one small restructure vs. zero future work to re-add later. **Lean toward GPT: move to an addendum, not full removal.** But this is close enough that the operator's view of the healthcare-accessdb migration timeline should determine the call.

**Flag for operator decision:** If healthcare-accessdb migration is more than 6 months away, Gemini's cut is reasonable.

---

### SO-2: `NEXT_ORCHESTRATOR_REASON_CODES` (4 structured codes)

**GPT-5.4:** Defended "keep next_orchestrator validation for orderly handoff" (conflating the structural validation with the reason code taxonomy).

**Gemini Pro:** The four structured reason codes add validation complexity. "Unless a downstream system is programmatically consuming these specific codes for reporting, a single free-text `reason.specifics` field would be simpler and sufficient."

**Orchestrator read:** GPT defended the wrong thing — it defended the structural validation (keep next_orchestrator required when status=completed and not final session), not the reason code taxonomy. Both verifiers agree the structural validation should stay. The question is whether the four codes (`continue-current-trajectory`, `switch-due-to-blocker`, `switch-due-to-cost`, `other`) earn their complexity. They appear in `record_adjudication()` metrics aggregation — if the metrics are actually consulted for routing decisions, the codes earn their keep. If the metrics aggregation is aspirational, Gemini's cut is correct. **Lean toward partial accept:** Keep the structural validation; reduce to 2 codes (`continue`, `switch`) plus `other`, and fold `cost` into `switch`. That simplifies the taxonomy while preserving the routing-feedback value.

**Flag for operator decision:** Are the adjudication metrics actually being read and used to inform routing decisions? If not, free-text is simpler.

---

### SO-3: Memory system pruning

**GPT-5.4:** Three cuts — (1) trim MEMORY.md to rolling index, archive older entries; (2) delete feedback memories that restate workflow doc rules; (3) move consumer-specific project state to each consumer repo's own memory.

**Gemini Pro:** Keep the entire external memory system. "Formalizing project-specific context in operator-side files is a necessary practice for maintaining high-quality, long-term interaction, and is not frivolous complexity."

**Orchestrator read:** Gemini's defense of the memory system as a whole is valid, but GPT's three specific cuts are also reasonable — especially cut (3): notes about dabbler-platform's UAT DSL status, consumer repo workflow shapes, and other consumer-facing facts belong in those repos' own memory, not in the orchestration repo's memory. Cuts (1) and (2) are maintenance hygiene. **Partial accept:** Accept cuts (1) and (2) as hygiene; evaluate cut (3) case-by-case (some cross-repo project facts may legitimately live here if they inform decisions made in this repo's sessions).

**No operator decision needed** — hygiene cuts are safe. But Gemini's caution is a reminder not to over-prune: stable operator-preference memories (the feedback/* entries) are load-bearing.

---

## Section 3 — Defended as load-bearing

*Both verifiers examined these surfaces and concluded they should stay.*

| Item | Location | Why it's load-bearing |
|---|---|---|
| **Steps 0–10 ordered procedure** | `docs/ai-led-session-workflow.md` | Single source of truth for consistent orchestration behavior. Defended by both verifiers. |
| **Adjudication ladder (Step 7)** | `docs/ai-led-session-workflow.md` | Cross-provider verification only stays auditable if verifier disagreements have a standard, logged resolution path. Defended explicitly by both. |
| **Append-only session-events ledger** | `ai_router/session_events.py` | The immutable event history is the authoritative record. Gemini: "robust design choice that prevents data loss." |
| **session-state.json snapshot alongside ledger** | `ai_router/session_state.py` | The extension reads the snapshot cache; on-demand derivation from events would add latency without benefit. Defended by both (GPT with performance caveat). |
| **`next_orchestrator` structural validation** | `ai_router/session_state.py`, `disposition.py` | Required when status=completed, not final session — directly supports orderly handoff. Both defend the structural rule (even if they differ on reason codes). |
| **`--force` double-gated** | `ai_router/close_session.py` | Env var + reason file = high-friction, audited escape hatch for incident recovery. Gemini: "well-designed safety feature, not accidental complexity." |
| **File lock + deterministic gate checks** | `ai_router/close_lock.py`, `gate_checks.py` | Close-out is the synchronization barrier; correctness takes priority over elegance. |
| **Explicit adoption-tier choice (L/F) in bootstrap** | `docs/adoption-bootstrap.md` Step 4.5 | Gemini: "the single most important complexity gate in the repository." Both defend. |
| **Operator review/approve checklist step in bootstrap** | `docs/adoption-bootstrap.md` Step 7 | "Prevents bootstrap automation from overcommitting a new project into the wrong shape." |
| **`task_routing.forced_model` config** | `ai_router/router-config.yaml` | Explicit model pins for known provider strengths. Both defend as "pragmatic and effective." |
| **`session-verification` cross-provider model pin** | `ai_router/router-config.yaml` | Verification independence depends on this being explicit. Defended by GPT; implied by Gemini's defense of forced_model. |
| **Invalid-combination rule (`uatStyle:"dsl"` + `requiresE2E:false`)** | Workflow doc, authoring guide | "Makes an implicit dependency explicit and prevents a class of invalid configurations." Both defend. |
| **SessionSetsProvider / Session Set Explorer** | `tools/dabbler-ai-orchestration/src/SessionSetsProvider.ts` | The one extension feature that clearly serves all adoption tiers. Both defend. |
| **Adoption bootstrap prompt command** | `tools/dabbler-ai-orchestration/src/commands/copyAdoptionBootstrapPrompt.ts` | Primary user-friendly onboarding entry point. Both defend. |

---

## Section 4 — Deferred items

*Worth simplifying, but the cost of the cut exceeds the value today — or requires prior research.*

| Item | Reason for deferral | What would unlock it |
|---|---|---|
| **Derive session-state.json from events** (GPT, high risk) | Currently both a ledger (events.jsonl) and a snapshot (state.json) exist. On-demand derivation would remove one artifact but requires the extension to read events at activation — latency implications. | Benchmarking extension activation time with event-derived state; or a read-through cache in the extension. |
| **Merge `middle` and `ample` budget tiers** (GPT, medium risk) | Four budget labels may be redundant. Merging without data risks erasing meaningful behavioral differences. | A 3-month metrics pull showing whether middle-vs-ample routing decisions actually differ in practice. |
| **Retire `--manual-verify`** (GPT, medium risk) | The bootstrapping-window escape hatch should eventually go away, but both Full-tier consumers may still rely on it for edge cases. | Explicit "manual-verify not needed" confirmation from all Full-tier consumer teams. |
| **Per-repo uatStyle default** (GPT, medium risk) | A repo could declare `uatStyle: "dsl"` once in its addendum instead of per-spec. Reduces per-spec verbosity for dabbler-platform. | The addendum pattern (HC-2) landing first; then evaluate whether per-repo default reduces friction meaningfully. |
| **Separate Cost Dashboard from core extension for Lightweight** (GPT, medium risk) | Cost data is zero for Lightweight consumers; dashboard is noisy. But extension versioning complexity of having two extension IDs may outweigh the gain. | HC-9 landing first (when clauses may hide the dashboard sufficiently without a separate VSIX). |

---

## Section 5 — Implementation roadmap

*Suggested order for a follow-on Set 021. Items are grouped into sessions by independence and risk. This is a proposed order — the operator picks which cuts to approve and may reorder freely.*

### Set 021 Session 1 — Low-risk doc cleanup (no behavior changes)

Independent of all other sessions. Safe to run first without prerequisites.

| Action | Primary file | HC/SO ref |
|---|---|---|
| Remove adoption-vs-budget disambiguation from mandatory workflow read | `docs/ai-led-session-workflow.md` | HC-8 |
| Remove dabbler-platform migration note from universal authoring guide | `docs/planning/session-set-authoring-guide.md` | HC-2 |
| Derive uatScope:none from requiresUAT:false (remove explicit none value from spec template) | workflow doc + authoring guide | HC-7 (minor) |
| Replace abstract pattern catalog with 2–3 concrete examples | `docs/adoption-bootstrap.md` | HC-3 |
| Archive backfill_session_state.py + dump_session_state_schema.py (move to scripts/ or delete) | `ai_router/` | HC-6 |

**Estimated Set 021 Session 1 cost:** $0 metered (doc-only changes; no router routes).

---

### Set 021 Session 2 — Workflow doc restructuring (medium-risk)

Depends on Session 1 (disambiguation paragraph and migration note already removed).

| Action | Primary file | HC/SO ref |
|---|---|---|
| Restructure workflow doc: compact core + full-tier extension section (same file, clear divider) | `docs/ai-led-session-workflow.md` | HC-1 |
| Move UAT/E2E heuristic sections in authoring guide to platform-addendum.md | `docs/planning/session-set-authoring-guide.md` | HC-2 |
| Move ad-hoc UAT rule (Rule 11b + Choosing uatStyle for ad-hoc) to full-tier extension section | `docs/ai-led-session-workflow.md` | SO-1 (if operator chooses "addendum") |

**Estimated cost:** $0.10–$0.25 metered (doc changes + single verifier route to confirm restructure doesn't break instruction-file pointers).

---

### Set 021 Session 3 — Code refactoring (medium-risk, Python changes)

Depends on Session 2 (the module boundary for queue verification makes more sense once the doc restructure clarifies what's "core" vs. "platform-specific").

| Action | Primary file | HC/SO ref |
|---|---|---|
| Extract _wait_for_verifications() + queue helpers to ai_router/queue_verification.py | `ai_router/close_session.py` | HC-4 |
| Simplify --repair / --apply: merge into --repair + interactive confirmation (or --yes) | `ai_router/close_session.py` | HC-5 |
| Prune router-config.yaml task types (audit metrics first; remove zero-usage types) | `ai_router/router-config.yaml` | HC-7 |
| Add VS Code `when` clauses to hide Full-tier/outsource-last extension views | `tools/dabbler-ai-orchestration/package.json` + providers | HC-9 |

**Estimated cost:** $0.15–$0.35 metered (Python refactor needs end-of-session verification route + extension smoke test).

---

### Out-of-scope for Set 021 (operator decision required)

| Item | Reason |
|---|---|
| Remove ad-hoc UAT path entirely (SO-1, Gemini's cut) | Operator decides based on healthcare-accessdb migration timeline |
| Simplify NEXT_ORCHESTRATOR_REASON_CODES to 2+other (SO-2 partial accept) | Operator confirms whether adjudication metrics are being read |
| Memory system pruning (SO-3 cuts 1–3) | Operator decides which consumer-specific memories to migrate |

---

## Audit conclusions

Both verifiers reached identical overall scores (7/10) and similar diagnoses. The framework is sound but has accumulated complexity in three areas:

1. **Universal docs carry platform-specific content.** The workflow doc, authoring guide, and router config each include sections relevant only to `dabbler-platform` or to the outsource-last path, which all orchestrators must read past on every session.

2. **The close-out CLI has accreted modes.** Five invocation modes in one command is the natural result of iterative addition. The modes are all correct and reasoned; they just don't belong in the same file.

3. **The extension shows Full-tier features to Lightweight consumers.** A minor polish item but a visible signal of the broader pattern.

The framework's core architecture — event sourcing, gate-enforced close-out, adjudication logging, forced-model pins, adoption-tier choice — is well-designed and should not be touched. The cuts above are all at the surface (docs, config, module boundaries) not the core (event model, gate logic, routing algorithm, verification independence).

Set 021 implementation time estimate: 2–3 sessions, ~$0.30–$0.60 metered, no risk to the framework's core correctness.
