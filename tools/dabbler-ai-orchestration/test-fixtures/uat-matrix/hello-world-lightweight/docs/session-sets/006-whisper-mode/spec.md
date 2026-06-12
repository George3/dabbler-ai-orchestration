# Whisper mode

> **Purpose:** Add a `--whisper` flag that prints the greeting in
> parentheses.
> **Session Set:** `docs/session-sets/006-whisper-mode/`
> **Created:** 2026-06-10
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

> Rationale: Lightweight Mode B, fully verified. In the UAT fixture
> matrix this is the VERIFIED Mode-B row: a `type: verification`
> session was appended at runtime and completed with verdict VERIFIED,
> so no marker renders (quiet is success), the fraction reads `3/3`
> (the runtime-grown count), and the fraction tooltip carries
> "Verification: VERIFIED (session 3)".

---

## Project Overview

A `--whisper` flag: `(hello, world)` — lowercased and parenthesized.

---

## Sessions

### Session 1 of 2: Whisper flag

**Goal:** `--whisper` prints the parenthesized greeting.
**Steps:**
1. Parse the flag.
2. Lowercase and parenthesize the output line.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Whispered greeting prints.
**Progress keys:** `session-001/flag`

---

### Session 2 of 2: Precedence and docs

**Goal:** `--whisper` composes with the other tone flags.
**Steps:**
1. Implement the tone precedence (`--shout` > `--whisper` > `--quiet`).
2. Update the README usage table.
**Creates:** —
**Touches:** `hello.js`, `README.md`
**Ends with:** All combinations print correctly.
**Progress keys:** `session-002/precedence`, `session-002/docs`

---

## End-of-set deliverables

- A `--whisper` flag with documented tone precedence, verified by a
  completed cross-engine verification session.
