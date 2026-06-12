# Greet quietly

> **Purpose:** Add a `--quiet` flag that lowercases the greeting.
> **Session Set:** `docs/session-sets/002-greet-quietly/`
> **Created:** 2026-06-06
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

> Rationale: Lightweight Mode A. In the UAT fixture matrix this is the
> COMPLETE-WITHOUT-NOTE Mode-A row: the set is done but nothing records
> an out-of-band review, so the `v?` marker renders, the row menu
> offers `Open External Verification Note`, and the completed-set
> `Set Up Dedicated Verification…` path (the blessed Python writer) is
> eligible.

---

## Project Overview

A `--quiet` mode for the greeting CLI.

---

## Sessions

### Session 1 of 2: Parse the flag

**Goal:** `--quiet` is recognized.
**Steps:**
1. Parse `--quiet` ahead of the name argument.
2. Keep the default behavior unchanged without the flag.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Flag parsing covered by a smoke check.
**Progress keys:** `session-001/flag`

---

### Session 2 of 2: Quiet output

**Goal:** Quiet mode prints `hello, world.`.
**Steps:**
1. Lowercase the greeting under `--quiet`.
2. Update the README usage table.
**Creates:** —
**Touches:** `hello.js`, `README.md`
**Ends with:** Both modes print correctly; set closed.
**Progress keys:** `session-002/quiet-output`, `session-002/docs`

---

## End-of-set deliverables

- A `--quiet` flag on the greeting CLI.
