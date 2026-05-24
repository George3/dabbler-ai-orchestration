# Q1 — Bypass-rate self-observation log

> **Set 045 / Session 1 spike.** Schema + clock-start entry for the
> bypass-rate observation period. Set 044 proposal §6.1 raised the
> question: *what fraction of real-world AI sessions are
> Dabbler-launched vs. free-running?* This answer drives the
> investment split between the wrapper channel (Channel 2) and the
> native-log + narration channels (Channel 1) for Set 045 S3–S5.
>
> The log file lives **operator-local** at
> `~/.dabbler/bypass-observation-log.jsonl`. It is NOT committed to
> this repo. The clock-start entry was written 2026-05-24.

---

## 1. Schema (per JSONL line)

```jsonc
{
  "ts":              "2026-05-24T10:34:00-04:00",   // ISO 8601 with TZ; when the session started
  "entry_kind":      "session" | "clock-start" | "reflective" | "clock-end",
  "engine":          "claude" | "copilot" | "codex" | "gemini" | "other" | null,
  "launched_via":    "dabbler" | "manual" | "auto" | null,
  "workspace_cwd":   "C:/Users/denmi/source/repos/dabbler-ai-orchestration" | null,
  "set_slug":        "045-log-harvest-implementation" | null,
  "session_count":   1,                              // for reflective entries: rough N sessions in the window
  "window_hours":    null | 8,                       // for reflective entries: time window the count covers
  "notes":           "free-form"
}
```

### Field semantics

| Field | When required | Notes |
|---|---|---|
| `ts` | always | When the session *started* (best estimate; minute-precision is fine) |
| `entry_kind` | always | `clock-start` marks the start of an observation period; `session` is one observed AI session; `reflective` is a batched count for a recent window (e.g., end-of-day backfill); `clock-end` closes the period |
| `engine` | for `session` and `reflective` | Which AI |
| `launched_via` | for `session` and `reflective` | The bypass-rate signal: `dabbler` = went through extension command or future `dabbler-launch` wrapper; `manual` = operator opened terminal / IDE directly; `auto` = CI / script / hook-triggered |
| `workspace_cwd` | for `session` | Project the session worked in; informs whether bypass varies by repo |
| `set_slug` | for `session`, when known | Session set the AI was working on (often unknown for free-running sessions) |
| `session_count` | for `reflective` | Rough count of sessions in the reflective window |
| `window_hours` | for `reflective` | The time window the count covers (e.g., `8` for "since I started today") |
| `notes` | optional | Free-form |

## 2. Three capture mechanisms (in priority order)

Until Set 045 S3 ships the production `dabbler-launch` wrapper, the
operator must capture entries manually. Three paths:

1. **(Easiest, recommended baseline) Reflective end-of-day entry.**
   At the end of each work-day during the observation period, the
   operator writes ONE `entry_kind: "reflective"` line per engine
   used that day with a rough `session_count` and `window_hours`,
   and a coarse split into `dabbler` vs `manual` via two entries.
   Friction: ~30 seconds at day-end. Resolution: per-day, not
   per-session. **Acceptable for the bypass-rate question** because
   the question is a fractional-coverage estimate, not a
   per-session ledger.

2. **(Higher fidelity, optional) Per-session entry.** When the
   operator notices a clear "I'm starting an AI session right now"
   moment, write a single `entry_kind: "session"` line. Friction:
   ~10 seconds per session. Resolution: per-session.

3. **(Future, post-S3) Wrapper-automated capture.** When
   `dabbler-launch` ships in S3, every Dabbler-launched session
   automatically writes its `launched_via: "dabbler"` entry as a
   side-effect of the launch record. Manual entries are only
   required for the `launched_via: "manual"` cases. Friction: drops
   to ~near-zero for the dominant case post-S3.

The operator picks 1 or 2 (or both); the analysis at S5 takes
whatever's in the log at that point.

## 3. Observation period

- **Started:** 2026-05-24 (clock-start entry written today).
- **Minimum useful window:** 7 days of operator activity — yields a
  rough percentage estimate with N typically ~20–50 sessions.
- **Target window:** 14 days — narrows the confidence interval and
  captures weekend/weekday variation.
- **Analysis trigger:** at the start of Set 045 S5 (Explorer
  integration) the resolution doc reads the log and reports the
  bypass-rate fraction. If the log is short (< 7 days or < 10
  sessions), the analysis flags the limitation and proceeds with
  conservative defaults (assume bypass rate is 50% — both channels
  warrant equal investment regardless).

## 4. Clock-start entry written

The following JSONL line was appended to
`~/.dabbler/bypass-observation-log.jsonl` at the start of Session 1:

```json
{"ts":"2026-05-24T10:34:00-04:00","entry_kind":"clock-start","engine":null,"launched_via":null,"workspace_cwd":null,"set_slug":"045-log-harvest-implementation","session_count":null,"window_hours":null,"notes":"Set 045 S1 spike: bypass-rate self-observation period begins. Target 14 days through 2026-06-07. Analysis read at Set 045 S5 start."}
```

The clock is now running. The operator's commitment is one
reflective entry per work-day for the next 14 days, with optional
per-session entries when the operator notices a clear session-start
moment.

## 5. What the bypass-rate fraction will drive

At Set 045 S5 (Explorer integration), the resolution doc reads the
log and computes:

```
bypass_rate = (sessions where launched_via == "manual" or "auto") / total observed sessions
```

The decision rules:

| Bypass rate | Investment split implication |
|---|---|
| < 25% | Wrapper channel carries most coverage; Channel 1 (native-log + narration) is recoverability-focused |
| 25–60% | Both channels carry significant load; both must be production-grade (the proposal's locked dual-primary commitment is correct as-is) |
| > 60% | Native-log + narration carries most coverage; wrapper is a convenience channel that adds C3/A3 fidelity for Dabbler-launched sessions but is NOT the primary path |

Per the proposal §6.1 hypothesis, the operator's S1–S5 workflow
suggested most sessions are free-running. The actual fraction is
the empirical question this log answers. The locked dual-primary
architecture is correct regardless of the fraction — the question
only sharpens the *prioritization* of S3 (wrapper) vs S4 (Claude
parser) work, not the *existence* of either.
