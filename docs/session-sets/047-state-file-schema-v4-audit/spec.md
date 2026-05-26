# State File Schema v4 — Audit Pass

> **Purpose:** audit-then-spec a v4 evolution of the canonical
> `session-state.json` schema that derives top-level state from a
> per-session `sessions[]` array, eliminating the
> denormalization-driven bugs the v3 schema generates.
> **Created:** 2026-05-26 (stub — Set 046 / S1 close-out).
> **Status:** STUB — AUDIT PENDING. Pre-audit material below is the
> v4 motivation captured at the time the v3→v4 deferral was
> decided. A fresh cross-provider audit pass should run before
> the spec is detailed.
> **Session Set:** `docs/session-sets/047-state-file-schema-v4-audit/`
> **Prerequisite:**
> - Set 046 (`046-explorer-enrichment-from-harvest-records`) CLOSED.
>   Set 046 ships forward-only `totalSessions: null` writer behavior;
>   the v4 audit should observe whether that forward-only fix
>   eliminates enough of the v3-bug pain to change the v4 cost/benefit
>   calculus.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification.

---

## Why this is a STUB

Per `feedback_audit_then_spec_for_substantial_features`: a schema
migration that touches every writer, every reader, every Explorer
consumer, every test, and every Lightweight-tier consumer repo's
ad-hoc emission shape is exactly the class of change that wants:

1. A dedicated cross-provider design audit (this set's S1).
2. A separate implementation set authored *after* the audit
   scope-locks.

Set 046's audit (`docs/proposals/2026-05-26-explorer-enrichment-from-harvest-records/`)
explicitly chose **not** to absorb the v4 work, on the grounds that it
would balloon Set 046 beyond its discretionary-enrichment character.

---

## Pre-audit material (lifted from Set 046's original stub)

### v4 motivation — derive top-level state from `sessions[]`

The current v3 schema denormalizes a half-dozen fields that are
derivable from the `sessions[]` array if per-session timestamps and
orchestrator are promoted into it. Concretely:

| Top-level field | Derivation |
|---|---|
| `totalSessions` | `len(sessions)` |
| `completedSessions` | `[s.number for s in sessions if s.status == "complete"]` |
| `currentSession` | the (singleton) session with `status == "in-progress"`, else `null` |
| `status` | all complete → `complete`; all not-started → `not-started`; any in-progress → `in-progress`; explicit cancellation marker remains |
| `lifecycleState` | drop entirely; sub-states (`closeout_pending`, `closeout_blocked`) move to the events ledger |
| `startedAt` (set) | `min(session.startedAt for s in sessions if s.startedAt)` |
| `completedAt` (set) | `null` unless `status == "complete"`, else `max(session.completedAt)` |
| `orchestrator` (set) | the orchestrator of the in-progress session (per-session field) |
| `verificationVerdict` (set) | composite over per-session verdicts (today the top-level field is overwritten each close, losing history) |

The redundancy is mostly historical baggage from the v0→v3 migration.
Today it generates real bugs:

- **Set 036 S7** had to add a `fractionFor() → N/?` fallback because the
  writer can leave `totalSessions` null.
- **Set 045 S3's** final VERIFIED clobbered S2's VERIFIED in the
  snapshot (events ledger has both; snapshot doesn't).
- **Set 046 S2** is shipping a forward-only `totalSessions: null` writer
  fix — but that's a workaround for the same denormalization, not a fix.

### Blocked-on-prereqs lifecycle question (parked from Set 046)

Question:

> Should the canonical state-file `status` field gain a "deferred" or
> "blocked" value distinct from "not-started" and "cancelled" for sets
> whose prerequisites are unmet? Or is that better modeled as a derived
> Explorer property over machine-readable prerequisite declarations on
> existing "not-started" specs?

This question genuinely belongs in the v4 audit because it touches the
same `status` enum that v4 reshapes. Surfacing it standalone wastes
audit cycles; bundling it lets the audit treat the whole status-token
set holistically.

### Touch surface (impact assessment)

- **ai_router writers:** `start_session`, `close_session`,
  `mark_session_complete`, `cancel_lifecycle`, `register_session_start`.
- **ai_router readers:** `gate_checks`, `reconciler`,
  `session_lifecycle`, `joiner.parsers`.
- **Extension consumers:** `fileSystem.ts:readSessionSets`,
  `fractionFor`, the cancellation reader from Set 035, the orchestrator
  block readers from Set 033.
- **Tests:** every layer (pytest, Layer-2 tree-provider, Layer-3
  Playwright).
- **Lightweight-tier consumer repos:** currently invent ad-hoc shapes
  (`sessionLog[]` seen on `great-psalms-scroll-font`; catalog from
  Set 046 S6 will surface others). A v4 spec must canonicalize a
  natural emission pattern the Lightweight tier can adopt.

---

## Cross-provider audit topics (audit-pending)

1. **Is the "promote timestamps + orchestrator + verdict to per-session"
   shape the right v4 shape, or is there a different normalization
   worth considering?** (e.g., should `verificationVerdict` history be
   a separate ledger like events, rather than a per-session field?)
2. **Cancellation marker:** explicit set-level `cancelled: true` flag,
   or every-session-cancelled-or-not-started inference?
3. **Migration sequencing:** reader-first (accept both v3 and v4)
   then writer-second (emit v4) — or atomic flip with a v3→v4
   migrator?
4. **One-shot migrator for non-canonical v3 files** emitted by
   Lightweight orchestrators. Set 046 S6 ships expanded recognition
   for `sessionLog[]`-shaped files; the v4 migrator should subsume
   that work AND add v3-canonical → v4 transformation.
5. **Blocked-on-prereqs lifecycle:** status-enum value vs derived
   Explorer property. Which is the right separation of concerns?

---

## Non-goals (audit-pending)

- **Set 046's enrichment work.** Set 046 ships Explorer second-line
  badges, cost surfacing, idle-time annotation, etc. None of those
  depend on v4 — they all work against the v3 surface (with the
  forward-only `totalSessions: null` writer fix Set 046 ships in S2).
- **Harvest Record schema changes.** Those belong in a Set 045
  amendment, not here.
- **New Explorer features beyond what v4 enables.** This set is a
  schema migration; it does not ship UI enrichment.

---

## Note on this stub

The audit pass should treat the v4 motivation above as a prompt for
thinking, not a checklist to implement. The session count, effort
estimate, and exact migration sequencing are deliberately NOT
specified here — those are audit deliverables.
