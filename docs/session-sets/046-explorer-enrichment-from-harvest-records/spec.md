# Explorer Enrichment from Harvest Records

> **Purpose:** leverage the canonical Harvest Record stream that Set 045
> produces, plus the canonical `orchestrator` block that Set 033 produces,
> to surface richer per-row signals in the Session Set Explorer —
> orchestrator second-line badge, live cost surfacing, idle-time
> annotation, a state-divergence pill, and an actionable
> "(needs migration)" remediation path.
> **Status:** AUDIT-LOCKED 2026-05-26 (Set 046 Session 1). Replaces the
> 2026-05-23 stub. Audit artifacts at
> [`docs/proposals/2026-05-26-explorer-enrichment-from-harvest-records/`](../../proposals/2026-05-26-explorer-enrichment-from-harvest-records/).
> **Session Set:** `docs/session-sets/046-explorer-enrichment-from-harvest-records/`
> **Prerequisites (both CLOSED before this set runs):**
> - Set 045 (`045-log-harvest-implementation`) — CLOSED 2026-05-26. The
>   Harvest Record schema, joiner, wrapper, and parsers are production.
> - Set 036 (`036-chatsessionid-and-watcher-scope-implementation`) —
>   CLOSED 2026-05-24. Writer-side identity is solid.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification.
> **Cumulative Set 046 NTE:** $5.

---

## 1. What this set ships

Seven sessions. The set is **discretionary enrichment** of the existing
Session Set Explorer — no new UI surface, no new chat interface, no
schema changes to Harvest Records or `session-state.json` (the v4
schema audit is parked in Set 047).

| # | Title | Scope | Layer |
|---|---|---|---|
| **1** | **Audit pass + scope-lock** | *(this session)* — proposal, cross-provider verification, spec rewrite, open `047` stub. | docs |
| **2** | **Writer-side `totalSessions: null` + Explorer pre-flight** | Change `start_session` to keep `totalSessions: null` unless `--total-sessions` is passed. Backfill tests. Verify deliverable (a) renders `0/?` end-to-end on a fresh stub. Forward-only — no retroactive migration of existing not-started sets. | router + ext |
| **3** | **Second-line orchestrator badge (deliverable (b)) + state-divergence pill** | Insert `.row-second-line` between `.row-name` and `.harvest-badges` in [`media/session-sets-tree/client.js:271-273`](../../../tools/dabbler-ai-orchestration/media/session-sets-tree/client.js#L271-L273). Data source: canonical `orchestrator` block primary, most-recent harvest record fallback only when the orchestrator block is empty AND a single distinct triple exists across all records for the set_slug. Suppress silently otherwise. Long-name handling via `text-overflow: ellipsis` + `title` tooltip. **State-divergence pill** added in the same session: when `orchestrator.engine != most_recent_harvest_record.engine` for the set_slug, render a new conflict pill `state-divergence` alongside the existing `engine-mismatch` pill column. Layer-3 Playwright coverage of (b) + the new pill. | ext only |
| **4** | **Live cost surfacing per row** | Render `$X.XX` in a new column on in-progress rows. **Cost source: router metric ledger primary, harvest-estimated secondary** (consistent with the canonical-vs-evidence framing in S3). Compact display: `$X.XX` shows router-ledger only when no harvest activity exists; `$X.XX + $Y.YY` shows router-ledger + harvest-estimated when both exist. Hover-tooltip explains the breakdown explicitly per `feedback_user_facing_cost_messaging`. Cumulative-on-bucket-header is a nice-to-have if S4 runs short; otherwise out of scope. | router + ext |
| **5** | **Time-since-last-activity per row** | Third element on the second line: `active 2 min ago` / `idle 45 min` / `stale 4 h`. Data source: `orchestrator.lastActivityAt` (already populated by `start_session` — confirmed in this session's own state file), fallback to `max(ts)` over harvest records when the orchestrator block lacks `lastActivityAt`. Thresholds: live `< 5 min` (no color), idle `5–60 min` (default text color), stale `> 60 min` (muted/amber). Re-render piggybacks on the existing file-watcher; no new timer. Layer-3 coverage. | ext only |
| **6** | **"(needs migration)" expansion: migrator + triage + click action** | (Split from S5 per audit Bias 4 flip — Python migrator and TS UI work are distinct code surfaces.) Extend `python -m ai_router.migrate_session_state` to recognize non-canonical-v3 shapes (the `sessionLog[]` shape seen on `great-psalms-scroll-font`, plus any other near-conformant shapes surfaced by the triage). Idempotent. **Triage:** a one-page catalog at `docs/lightweight-tier-emission-drift.md` listing which Lightweight-tier consumers emit which non-canonical shapes (sweep over `dabbler-homehealthcare-accessdb`, `great-psalms-scroll-font`, and any other known Lightweight repos). **Click action:** add a left-click handler on the "(needs migration)" indicator that routes to the v2→v3 migrator (existing) for schemaVersion-absent files, and to the new expanded migrator for schemaVersion-3 non-canonical files. Confirmation modal before any write. | router + ext |
| **7** | **README screenshot (deliverable (c)) + cross-tier docs + cross-provider verification + close-out + dual release** | **README screenshot:** static PNG (per audit Q4) showing 1 in-progress half-completed row with the full enriched surface (second-line badge, idle-time annotation, cost figure, harvest-signal badge, conflict pill), 2 not-started rows (one stub `0/?`, one defined `0/5`), 2 completed rows (one collapsed bucket, one expanded). Mock-fixture lives at `tools/dabbler-ai-orchestration/test/fixtures/readme-screenshot/` so the screenshot can be regenerated. **Cross-tier consumer notice:** mirror the `docs/cross-repo-harvest-notice.md` pattern (per audit Q3); add a release-checklist line so the three consumer repos know to update their CLAUDE.md addenda. **Cross-provider verification** of the full set per the standard close-out flow (`feedback_split_large_verification_bundles` — slice to ≤500 LOC bundles). **Dual release:** `dabbler-ai-router 0.9.0` to PyPI + extension `0.22.0` to Marketplace. | docs + release |

## 2. Operator-locked deliverables (audit-confirmed)

The operator locked three deliverables at S1 start. The audit confirms they map cleanly onto the session plan above:

| # | Deliverable | Session(s) |
|---|---|---|
| (a) | "0/?" fraction icon for not-started session sets whose spec.md has no defined session breakdown | **S2** (writer-side change — Explorer's `fractionFor` already returns `N/?` when `totalSessions == null` per [`CustomSessionSetsView.ts:142-147`](../../../tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts#L142-L147); the fix is upstream) |
| (b) | Second line under In Progress rows showing `engine • model • effort` of the checked-out orchestrator; suppress silently when no data | **S3** (canonical `orchestrator` block primary; harvested fallback only as documented above) |
| (c) | Updated README.md with mocked screenshot of the Explorer (1 In Progress half-completed, 2 Not Started, 2 Completed) | **S7** |

## 3. Already shipped in 0.21.0 — expansion deferred

The original spec stub listed two candidate leverage points (§3 / §4 — writer-bypass warning surface and multi-AI conflict warning) as net-new. The audit confirms both **shipped in 0.21.0** as part of Set 045's joiner work:

- Writer-bypass is visible as **harvested-signal badge B** + **coordination-conflict pill `writer-bypass`** ([CLAUDE.md](../../../CLAUDE.md) 0.21.0 section).
- Multi-AI conflict is visible as **coordination-conflict pill `engine-mismatch`** (same section).

The spec stub's refinement open-questions (sticky-vs-live, dismissal flow, window-tuning) are real but defer until usage data shows the existing signals are being missed. With Marketplace download count near zero (`project_marketplace_download_count`), the cost of deferring expansion is near zero.

## 4. Deferred to follow-on sets

- **Set 047 — `state-file-schema-v4-audit`** (audit-pending). Bundles the parked v4 schema migration AND the "blocked-on-prereqs" lifecycle-state question. Per `feedback_audit_then_spec_for_substantial_features`, this is the class of change that wants its own audit set followed by a separate implementation set. Stub opened at Session 1 close-out (mirroring how Set 046 itself was opened at Set 044/S6 close-out).
- **Tool-touch histogram** (original spec §6) — deferred indefinitely. Privacy concern (file paths) + low marginal value vs. the operator's direct line-of-sight to tool calls.
- **§3.3 / §3.4 expansion refinements** — deferred until observed pain (see §3 above).

## 5. Data-source rules (for implementers)

These rules apply across S3, S4, S5 and capture the audit's resolved canonical-vs-evidence framing:

| Signal | Primary source | Fallback | Suppression |
|---|---|---|---|
| Second-line orchestrator badge (b) | `orchestrator` block from `session-state.json` | most-recent harvest record's `engine + model + effort` **only if** single distinct triple exists across all records for the set_slug | otherwise — render nothing |
| State-divergence pill | n/a — purely derived | n/a | suppress when no orchestrator block OR no harvest records (need both to detect divergence) |
| Live cost (S4) | router metric ledger (`ai_router/metrics/`) | harvest-estimated cost as additive secondary | suppress harvest-estimated `+ $0.00` clutter |
| Idle time (S5) | `orchestrator.lastActivityAt` | `max(ts)` over harvest records | suppress when neither exists |

Rule of thumb: **canonical primary, harvested fallback, suppress silently otherwise** (per operator's "no error, no missing data, just suppress" directive). The state-divergence pill is the *visible* expression of the rare case where canonical and harvested disagree — that's the high-value signal worth its own pill column.

## 6. Non-goals

- **A full Dabbler-owned chat replay UI.** Cancelled Sets 042-043 territory; this set should not drift there.
- **Modifying the Harvest Record schema.** Belongs in a Set 045 amendment or new parser-side set.
- **Modifying the `session-state.json` schema.** Belongs in Set 047.
- **Cross-provider cost reconciliation.** S4 ships router-primary + harvest-secondary side-by-side; reconciliation logic is its own future problem.
- **Retroactive `totalSessions: null` migration** (S2 forward-only per audit Q1).

## 7. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| S4 cost-source decision turns out to need reconciliation logic beyond side-by-side display | medium | Defer cumulative-on-bucket-header (already marked nice-to-have). Split into follow-on set if S4 runs long. |
| S6 migrator triage reveals more than 2-3 non-canonical shapes across Lightweight tier | low-medium | Migrator's recognition rules are pattern-based; per-shape recognition is cheap to add. Worst case: defer some shapes to a follow-on set, document them in the triage catalog. |
| S7 README screenshot mock-fixture work is larger than estimated (audit Bias 5 partial-flip) | medium | S7 is the close-out session and already has cross-provider verification + dual release packed in. If fixture work bloats, the cumulative-cost-on-bucket-header from S4 is the obvious deferral. |
| Cross-provider verifier 429 cascade on S7 verification bundle | medium-high (per `feedback_session_verification_gpt54_429_pivot_to_gemini`) | Pre-split S7 verification into ≤500 LOC slices per `feedback_split_large_verification_bundles`. Fall back to gemini-pro-as-verifier if gpt-5-4 cascades. |

## 8. Cumulative spend tracking

Set 045 closed at $0.39 of $5 NTE (~7.7%). Session 1 of Set 046 routed cost: **$0.183** of $5 NTE (~3.7%) — entirely on the audit cross-provider consensus. Each subsequent session's cross-provider verification is expected to cost $0.05–$0.30 per the empirical data in `project_verification_cost_empirical`. Projected total at S7 close-out: $0.5–$2 of $5 NTE (~10–40%).
