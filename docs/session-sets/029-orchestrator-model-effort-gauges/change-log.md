# Set 029: Orchestrator Model & Effort Indicator Gauges

**Status:** Not started (4 of 4 sessions pending)
**Created:** 2026-05-17
**Cost:** TBD (estimated $0.55–$1.55 across the set)

---

## Context

The operator routinely switches the orchestrator model down for cheap
tasks (Claude Haiku for a quick rename) and sometimes forgets to
switch back up to Opus before starting substantive work. The failure
mode is silent: a new session opens on a lower-tier model, output
quality is wrong, and the session has to be aborted or salvaged.

Set 029 adds an always-on visual signal — two semi-circle CSS gauges
pinned above the Session Set Explorer — that makes the current
orchestrator model and effort level glance-readable at all times.

v1 supports all four of the operator's orchestrator surfaces (Claude
Code, Gemini Code Assist Agent, Codex, GitHub Copilot) with
auto-detection where viable and a manual-override quickpick command
as the universal fallback.

---

## Session 1: (pending — cross-provider design audit)

(populated at session close)

## Session 2: (pending — core webview + Claude detection)

(populated at session close)

## Session 3: (pending — non-Claude provider detection)

(populated at session close)

## Session 4: (pending — polish + marketplace publish)

(populated at session close)

---

## Final cost summary

(populated after Session 4 close-out)
