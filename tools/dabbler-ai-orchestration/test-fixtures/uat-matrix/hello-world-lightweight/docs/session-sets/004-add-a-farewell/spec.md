# Add a farewell

> **Purpose:** The CLI also says goodbye.
> **Session Set:** `docs/session-sets/004-add-a-farewell/`
> **Created:** 2026-06-08
> **Workflow:** lightweight
> **Prerequisite:** None

---

## Session Set Configuration

```yaml
tier: lightweight
requiresUAT: false
requiresE2E: false
uatScope: none
uatStyle: ad-hoc
verificationMode: dedicated-sessions
totalSessions: 2
```

> Rationale: Lightweight Mode B (`dedicated-sessions`) — a typed
> verification session will be appended after the work sessions
> complete. In the UAT fixture matrix this is the MID-WORK Mode-B row:
> session 2 is in flight, so the fraction reads `1/2+` (the `+` says
> the denominator can still grow) and no `v+` marker renders yet.

---

## Project Overview

A `--farewell` flag that prints `Goodbye, <name>!` after the greeting.

---

## Sessions

### Session 1 of 2: Farewell flag

**Goal:** `--farewell` prints the goodbye line.
**Steps:**
1. Parse the flag.
2. Print the farewell after the greeting.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Both lines print with the flag.
**Progress keys:** `session-001/flag`, `session-001/output`

---

### Session 2 of 2: Farewell-only mode

**Goal:** `--farewell-only` skips the greeting.
**Steps:**
1. Parse the second flag and make the two flags compose sensibly.
2. Update the README usage table.
**Creates:** —
**Touches:** `hello.js`, `README.md`
**Ends with:** All flag combinations print correctly.
**Progress keys:** `session-002/only-mode`, `session-002/docs`

---

## End-of-set deliverables

- Farewell flags on the greeting CLI, verified by a dedicated
  cross-engine verification session.
