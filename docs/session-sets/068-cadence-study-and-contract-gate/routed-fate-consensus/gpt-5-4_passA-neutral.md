# Consensus consult -- gpt-5-4 -- passA-neutral

> model_used=None cost_usd=0.06296 chars=2715

## Recommended outcome

**DEMOTE — make the `contract-test/CDC gate + end-of-set path-aware critique` the Full-tier default, and require per-session cross-provider routed verification only for high-coupling/high-blast-radius sessions or when deterministic coverage is absent.**

## Right question check

This is slightly misframed as a permanent keep/demote/retire choice. The evidence supports a phased policy: **demote now**, then reopen **retire** only after Set 068 S5 is live and telemetry shows routed is no longer catching unique severe defects.

## Assessment

Experiment A removes the main capability case for routed as the default verifier: the decisive lever is **repository context**, not provider diversity. Path-aware catches severe cross-file defects that snippet-fed routed structurally cannot see, and adding a second routed provider buys nothing. Experiment B also fails the pre-registered **every-session cadence defense**: R’s edge over end-of-set review is real, but it mostly decomposes into context coverage and generic earliness, not a clean, unique cadence effect that survives controls.

## Why DEMOTE, not KEEP or RETIRE

**KEEP** is too strong because the evidence does not justify every-session mandatory routed as the primary verification surface; at set close, **E materially outperforms R**, and R’s unique value collapses to one narrow class: early detection of migrating coupling defects. **RETIRE** is too strong because that narrow value is real, S5 is not yet operational, and the live workflow has repeatedly seen routed catch real pre-commit defects that the toy study does not fully bound.

## Concrete changes

- **Config default:** Full tier = mandatory `contract-test/CDC gate` once S5 lands, plus one mandatory `end-of-set path-aware critique`; `per-session cross-provider routed = conditional`, not universal.
- **Workflow-doc rule:** require per-session routed only if a session:
  - changes a shared API/schema/contract,
  - touches both sides of a dependency or producer/consumer edge,
  - performs cross-module refactors, file moves/renames, or wiring/build/config changes,
  - lacks deterministic probes for the changed surface, or
  - is marked high-blast-radius or hotfix.
- **Temporary fallback:** until S5 exists, or whenever the contract gate is unavailable/red, escalate that set back to per-session routed for the affected sessions.

## What not to change

Do **not** remove routed capability entirely, do **not** add a second routed provider, and do **not** remove the end-of-set path-aware/manual flow. Revisit **RETIRE** only after live S5-era telemetry shows routed is no longer finding unique high-severity issues or producing meaningful rework savings.
