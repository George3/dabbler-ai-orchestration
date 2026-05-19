# Orchestrator check-out / check-in — implementation (PLACEHOLDER)

> **⚠️ Placeholder spec.** This file exists so the session-set
> folder is visible in the Session Set Explorer's "Not Started"
> bucket. The real spec.md is the **deliverable** of Set 032's
> Session 2 (audit cycle) — produced after H1 / H2 / H3 / OQ1 / OQ2
> are resolved.
>
> **Do NOT run `start_session` against this set until Set 032 has
> closed.** Set 032's `close_session` is the gate that authors the
> real spec; until then, this placeholder reflects best-guess scope
> only.
>
> **Created:** 2026-05-19 (placeholder)
> **Session Set:** `docs/session-sets/033-orchestrator-checkout-checkin-implementation/`
> **Prerequisite:** Set 032 (`032-orchestrator-checkout-checkin-audit`)
> closed.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration (placeholder — subject to audit verdict)

```yaml
totalSessions: 6
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
```

> **`requiresE2E: true`** because multi-set rendering + check-out
> conflict scenarios warrant Layer-3 Playwright coverage. Final
> determination by Set 032.
>
> **`effort: high`** because the change touches Python writers
> (`start_session`, `close_session`), TypeScript reader
> (`MarkerWatchService`), all existing session-state.json files
> across this repo + three consumer repos, the workflow doc, and
> the per-agent instruction files. High coordination risk; high
> cost if a writer-side bug ships and breaks an in-flight session.

---

## Project Overview (placeholder)

Set 033 executes the implementation spec authored by Set 032's
audit cycle. The work implements:

- **Check-out / check-in state machine** in `session-state.json`
- **`start_session` as canonical writer** — refuses to write when
  held by a different orchestrator without operator override
- **Resolver refactor** — `resolveActiveSet()` → `listInProgressSets()`,
  enabling multi-in-progress rendering
- **Banner removal** — coupled to the resolver refactor
- **UI rename** — `dabbler.setOrchestrator` →
  `dabbler.checkOutOrchestrator` ("Check Out As…")
- **Writer Log narrows** to force-override + stalled-recovery +
  attach-conflict audit trail
- **Cross-orchestrator queueing / polling** feature (second
  orchestrator detects held check-out, offers poll / abort /
  force-override)
- **`close_session` check-in across all tiers** (Full + Lightweight
  per operator's "Lightweight doesn't excuse skipping the lock"
  clarification mid-Set-029-S6)
- **Workflow doc update** making the within-set sequential
  invariant explicit
- **Cross-repo notifications** — consumer repos' CLAUDE.md +
  `dabbler-platform`, `dabbler-access-harvester`,
  `dabbler-homehealthcare-accessdb`

---

## Tentative session split (placeholder — final shape by Set 032)

| # | Title (placeholder) |
|---|---|
| 1 | State machine in session-state.json + `start_session` refactor |
| 2 | Marker retirement (per H2 verdict) + resolver refactor (multi-set rendering) + banner removal |
| 3 | UI rename + ActionRegistry update + Command Palette release action |
| 4 | Playwright tests for multi-set rendering + check-out conflict scenarios |
| 5 | Queueing / polling feature |
| 6 | Cross-tier check-in + cross-repo notifications + within-set sequential invariant in workflow doc + PyPI release |

---

## Pre-audit basis

See [`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`](../../proposals/2026-05-19-orchestrator-tracking-architecture/)
for the full pre-audit artifacts:

- `proposal.md` (v1 design)
- `proposal-addendum.md` (operator clarifications + 2-state model
  sketch)
- `consensus-gemini-pro.{txt,json}` (R1 verdict, $0.015)
- `consensus-gpt-5-4.txt` (R1, manual paste)
- `consensus-gpt-5-4-round-2.txt` (R2, manual paste — surfaced
  the three Highs)
- `README.md` (decision trail + must-resolve items)

---

## Total estimated cost (placeholder — pre-spec forecast)

For ~6 sessions of implementation with end-of-session verification
and ~1 mid-set audit consult: **$0.20–$0.80 forecast.** Final shape
by Set 032.

For context: Set 029's 6 sessions totaled ~$1.70 (heavy audit + 3
verification rounds in Session 1). Set 033 benefits from the
pre-shipped design + Set 032's audit, so the per-session
verification spend should be lower.
