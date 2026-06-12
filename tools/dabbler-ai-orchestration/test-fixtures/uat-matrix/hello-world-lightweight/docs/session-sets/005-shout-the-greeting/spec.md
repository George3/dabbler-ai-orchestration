# Shout the greeting

> **Purpose:** Add a `--shout` flag that uppercases the output.
> **Session Set:** `docs/session-sets/005-shout-the-greeting/`
> **Created:** 2026-06-09
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

> Rationale: Lightweight Mode B. In the UAT fixture matrix this is the
> WORK-COMPLETE Mode-B row: both work sessions are closed but the typed
> verification session has not been appended yet, so the fraction reads
> `2/2+` AND the `v+` marker renders — the actionable "verification is
> owed" moment, with `Verification Kickoff` on the row menu. (The
> per-session counts come from `session-events.jsonl`; the top-level
> status is still `in-progress` because the set is in the
> awaiting-verification window.)

---

## Project Overview

A `--shout` flag: `HELLO, WORLD!` instead of `Hello, world!`.

---

## Sessions

### Session 1 of 2: Shout flag

**Goal:** `--shout` uppercases the greeting.
**Steps:**
1. Parse the flag.
2. Uppercase the assembled output line.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Shouted greeting prints.
**Progress keys:** `session-001/flag`

---

### Session 2 of 2: Compose with other flags

**Goal:** `--shout` composes with `--quiet` precedence rules.
**Steps:**
1. Define and implement the precedence (`--shout` wins).
2. Update the README usage table.
**Creates:** —
**Touches:** `hello.js`, `README.md`
**Ends with:** All combinations print correctly.
**Progress keys:** `session-002/precedence`, `session-002/docs`

---

## End-of-set deliverables

- A `--shout` flag with documented flag precedence, verified by a
  dedicated cross-engine verification session.
