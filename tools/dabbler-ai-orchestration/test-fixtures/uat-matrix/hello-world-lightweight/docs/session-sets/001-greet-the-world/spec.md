# Greet the world

> **Purpose:** Ship the hello-world CLI's greeting.
> **Session Set:** `docs/session-sets/001-greet-the-world/`
> **Created:** 2026-06-05
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

> Rationale: a tiny CLI on the Lightweight tier (router-off). In the
> UAT fixture matrix this is the NOT-STARTED Mode-A row: the `lw`
> marker renders, `Switch Tier…` is offered, and
> `Set Up Dedicated Verification…` is offered in both directions
> because no durable verification-mode record exists yet (there is no
> activity log at all).

---

## Project Overview

Build the `hello.js` greeting CLI: default greeting, then a `[name]`
argument.

---

## Sessions

### Session 1 of 2: Default greeting

**Goal:** `node hello.js` prints `Hello, world!`.
**Steps:**
1. Create `hello.js` with the default greeting.
2. Add the usage line to the README.
**Creates:** `hello.js`
**Touches:** `README.md`
**Ends with:** The default greeting prints.
**Progress keys:** `session-001/greeting`, `session-001/docs`

---

### Session 2 of 2: Name argument

**Goal:** `node hello.js Ada` prints `Hello, Ada!`.
**Steps:**
1. Read the optional name argument.
2. Cover the fallback when no name is given.
**Creates:** —
**Touches:** `hello.js`
**Ends with:** Both invocations print the right greeting.
**Progress keys:** `session-002/name-arg`, `session-002/fallback`

---

## End-of-set deliverables

- A greeting CLI with an optional name argument.
