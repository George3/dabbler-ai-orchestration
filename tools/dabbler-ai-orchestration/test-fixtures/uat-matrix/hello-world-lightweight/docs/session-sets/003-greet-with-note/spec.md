# Greet with note

> **Purpose:** Add an exclamation-count option to the greeting.
> **Session Set:** `docs/session-sets/003-greet-with-note/`
> **Created:** 2026-06-07
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
verificationMode: out-of-band-or-none
totalSessions: 2
```

> Rationale: Lightweight Mode A, reviewed out of band. In the UAT
> fixture matrix this is the COMPLETE-WITH-NOTE Mode-A row: the set is
> done AND `external-verification.md` records the second-assistant
> review, so no marker renders — quiet is success.

---

## Project Overview

An `--excite N` option that appends N exclamation marks to the
greeting.

---

## Sessions

### Session 1 of 2: Parse the option

**Goal:** `--excite 3` is recognized and validated.
**Steps:**
1. Parse the integer option.
2. Reject negative or non-numeric values with a usage message.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Option parsing covered by a smoke check.
**Progress keys:** `session-001/option`

---

### Session 2 of 2: Excited output

**Goal:** `node hello.js --excite 3` prints `Hello, world!!!`.
**Steps:**
1. Append the requested punctuation.
2. Update the README usage table.
**Creates:** —
**Touches:** `hello.js`, `README.md`
**Ends with:** Output matches for several N; set closed.
**Progress keys:** `session-002/output`, `session-002/docs`

---

## End-of-set deliverables

- An `--excite N` option on the greeting CLI.
