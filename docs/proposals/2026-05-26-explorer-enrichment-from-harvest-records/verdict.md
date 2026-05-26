# Set 046 Session 1 — Audit verdict

**Status:** AUDIT-LOCKED. Scope-locked spec.md rewrite landed at
[`docs/session-sets/046-explorer-enrichment-from-harvest-records/spec.md`](../../session-sets/046-explorer-enrichment-from-harvest-records/spec.md)
on 2026-05-26.

**Process:** Two-pass devil's-advocate consensus over [`proposal.md`](proposal.md)
per `feedback_devils_advocate_default_for_roadmap_decisions`.

| Pass | Primary read (route) | Cross-provider verify | Cost |
|---|---|---|---|
| **A** | gemini-2.5-pro → ENDORSE WITH REVISIONS | gpt-5-4-mini → ISSUES FOUND | $0.0487 |
| **B** (devil's-advocate) | gemini-2.5-pro → ENDORSE WITH BIAS FLIPS | gpt-5-4-mini → ISSUES FOUND | $0.0430 |
| **Total** | | | **$0.0917** |

Plus the initial debugging run before the field-capture fix: $0.0915. Session 1 routed cost: **$0.183** of $5 NTE (~3.7%).

## Bias resolution (proposal §7 → final disposition)

| Bias | Pass A primary | Pass A verify | Pass B primary | Pass B verify | **Final** |
|---|---|---|---|---|---|
| 1 — canonical vs harvested for (b) | endorse | (no comment) | FLIP | flip is wrong | **STAND BY** |
| 2 — router-ledger vs harvest cost | endorse | (no comment) | FLIP | flip is wrong | **STAND BY** |
| 3 — defer §3.3/§3.4 expansions | endorse | label fix only | STAND BY | (implicit endorse) | **STAND BY w/ label fix** |
| 4 — migrator bundled with §3.5 | FLIP | false positive | FLIP | (implicit endorse) | **FLIP (2-1-1)** |
| 5 — README screenshot scoping | (implicit stand-by via 7-session arc) | (no comment) | FLIP | (implicit endorse) | **PARTIAL: keep in close-out, recognize fixture work** |

## New leverage point added (Pass A primary §5)

**State-divergence pill** — when the canonical `orchestrator.engine` differs from the most-recent Harvest Record's `engine` for that set_slug, render a pill on the in-progress row. Becomes the *visible expression* of the canonical/harvested tension that Biases 1+2 stood by. Added to Session 3 scope alongside deliverable (b).

## Open questions (proposal §8 → final disposition)

| Q | Disposition | Source |
|---|---|---|
| Q1 — retroactive `totalSessions: null` migration? | **No, forward-only** | Pass B primary + Pass A verify both flagged |
| Q2 — second-line in `.row-text` vs new `.row-meta`? | **`.row-text` as proposed** | Pass B primary, no contest |
| Q3 — cross-tier consumer notice pattern? | **Current copy-paste + release-checklist** | Pass B primary, no contest |
| Q4 — README static PNG vs animated GIF? | **Static PNG** | Pass B primary, no contest |

## Terminology fix (Pass A verify §1)

§3.3 (writer-bypass) and §3.4 (multi-AI conflict) re-labeled in spec.md from "DEFER" → "ALREADY SHIPPED (expansion deferred)". The feature is shipped in 0.21.0; only the spec's refinement open-questions (sticky/dismissable, window-tuning) are deferred.

## Final scope (7 sessions)

| # | Title | Layer |
|---|---|---|
| 1 | Audit pass + scope-lock (this session) | docs |
| 2 | Writer-side `totalSessions: null` + Explorer pre-flight | router + ext |
| 3 | Second-line orchestrator badge (b) + state-divergence pill | ext only |
| 4 | Live cost surfacing per row | router + ext |
| 5 | Time-since-last-activity per row | ext only |
| 6 | "(needs migration)" expansion (migrator + triage + click action) | router + ext |
| 7 | README screenshot (c) + cross-tier docs + final verification + dual release (PyPI 0.9.0 + Marketplace 0.22.0) | docs + release |

## Deferred to follow-on sets

- §4.1 + §4.2 → new stub `047-state-file-schema-v4-audit` (audit-then-spec for substantial schema migration)
- §3.3 / §3.4 expansion refinements → deferred indefinitely until observed pain
- §6 Tool-touch histogram → deferred indefinitely (privacy + low marginal value)
