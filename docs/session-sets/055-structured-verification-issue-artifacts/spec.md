# Structured Verification Issue Artifacts Spec

> **Purpose:** The modern workflow now writes root-level
> `sN-verification.md` narratives and `disposition.json`, but it has no
> canonical machine-readable persistence for verifier findings. The
> structured `issues` list already exists at verification time; older
> `issue-logs/` persistence survives only in legacy `SessionLog`
> helpers. Introduce a small, root-level per-session JSON artifact
> (`sN-issues.json`) so findings stay queryable without reviving
> `issue-logs/` or re-coupling engines to Python-only scaffolding.
> **Created:** 2026-06-02
> **Session Set:** `docs/session-sets/055-structured-verification-issue-artifacts/`
> **Prerequisite:** Set 054 (`verificationVerdict` persistence) should
> land first; this set builds on the same Step-6 / Step-8 handoff
> surface but does not expand Set 054's scope.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
```

> Rationale: this is an additive artifact-format / helper / docs pass.
> No browser-visible UI, no E2E surface, and no close-out gate change.

---

## Project Overview

### Motivation

The repo now has a split artifact story:

- The live workflow preserves the verifier's prose in root-level files
  such as `sN-verification.md` and the session outcome in
  `disposition.json`.
- The verifier parser already produces structured
  `{"verdict": ..., "issues": [...]}` data in memory, so the
  machine-readable issue list exists transiently at verification time.
- The old `issue-logs/` directory is not part of the modern required
  layout; it appears only through legacy `SessionLog` helpers and a few
  one-off scripts.
- That leaves no canonical, durable, machine-readable issue artifact for
  later analysis, auditing, or follow-up automation.

The goal of this set is to restore structured issue persistence without
bringing back the old folder contract. The new artifact should live at
the session-set root, be writable by any orchestrator that can emit
plain JSON, and remain optional from the close-out machinery's point of
view.

### What this set delivers

1. A canonical root-level issue filename convention:
   `sN-issues.json` for round-1 findings, then
   `sN-issues-round-2.json`, `sN-issues-round-3.json`, and so on for
   later findings-bearing retries.
2. A small JSON schema documenting the persisted finding shape,
   including which fields come from the verifier and which optional
   fields the orchestrator may append while resolving findings.
3. Workflow/docs updates so the current instructions point at the new
   root-level artifact and explicitly keep `issue-logs/` retired.
4. Docs/schema/example-first delivery, with an optional `ai_router`
   helper only if S1 judges that a real duplication point exists. Any
   helper must stay convenience-only, not a required dependency for
   Copilot/Codex/Gemini flows.

### Non-goals

- **No resurrection of `issue-logs/` or `session-reviews/`.** The new
  artifact lives beside `sN-verification.md`, not in a nested folder.
- **No close-out gate dependency.** `close_session` should not block on
  `sN-issues.json` in this set.
- **No embedding the full issues array into `disposition.json`.** The
  disposition remains the close-out handoff, not the long-lived per-round
  findings archive.
- **No Explorer/UI surface.** No badges, panels, or dashboard work.
- **No historical backfill.** Old sets keep their existing artifacts.

### Open design questions (S1 audit)

1. **Per-round vs latest-only files.** Should each findings-bearing
   retry get its own JSON file, or should the latest run overwrite the
   previous one? Recommendation: one file per findings-bearing round,
   never overwrite.
2. **Schema shape.** Should the artifact preserve the verifier issue
   objects verbatim, or add optional orchestrator-side resolution fields
   such as `resolution_status`, `resolution_notes`, and
   `resolved_in_round`? Recommendation: preserve verifier fields intact
   and allow additive optional resolution fields.
3. **Clean final round behavior.** If a later retry returns `VERIFIED`,
   should the workflow emit an empty `sN-issues-*.json` file? Recommendation:
   no; only findings-bearing rounds get issue files. The clean round is
   already preserved in `sN-verification.md`.
4. **Manual / `--no-router` flows.** May a human-authored external
   verification produce an `sN-issues.json` file by hand when structured
   findings exist? Recommendation: yes, as long as the file matches the
   documented schema.
5. **Helper surface.** Should this set ship a small Python helper for
   tests and scripts, or stay docs-only for writing? Recommendation:
   docs remain engine-agnostic; a helper is acceptable only as an
   optional convenience wrapper.
6. **Runtime readers.** Should any runtime path consult
   `sN-issues.json` in this set? Recommendation: no. This set is about
   persistence and documentation, not gate logic or UI behavior.

---

## S1 Audit Lock (2026-06-02)

Session 1 re-verified the current tree and captured the design record at
`docs/proposals/2026-06-02-structured-verification-issue-artifacts/`
(`proposal.md`, raw `consensus-review.md`, authoritative `verdict.md`).
**`verdict.md` is the locked design; this block is its summary.**

**Headline outcome:** the cross-provider reviewer (`gemini-pro`)
returned `CONSENSUS-AGREE`. No design reversals were recommended. The
reviewer's risks were accepted as implementation guardrails, not as
reasons to change the contract.

**Locked dispositions:**

- **Filename convention** — round 1 findings use `sN-issues.json`;
   later findings-bearing retries use `sN-issues-round-<M>.json`.
   Never overwrite a prior findings artifact.
- **JSON shape** — the artifact is a small envelope, not a bare array:
   `schemaVersion`, `sessionNumber`, `verificationRound`,
   `verificationVerdict`, `issues`.
- **Issue object policy** — preserve verifier fields verbatim
   (`description` required; `category` / `severity` loose optional
   strings), and allow optional append-only resolution fields
   (`resolution_status`, `resolution_notes`, `resolved_in_round`).
- **Clean rounds** — no empty issue file for VERIFIED rounds. The
   presence of `sN-issues*.json` means that verification round found
   issues.
- **Manual / `--no-router`** — may write the same envelope when a
   structured issue list exists, but are not required to fabricate JSON
   from prose-only review.
- **Helper** — docs/schema/example first; helper remains optional and
   must stay convenience-only.
- **Runtime scope** — no runtime readers or gate logic in this set.
- **Release scope** — only release if Session 2 ships Python code.

**Accepted guardrails:**

- Resolution fields are advisory annotations, not authoritative workflow
   state.
- A minimal envelope without any `resolution_*` keys is fully valid.
- Missing issue JSON on a manual-flow set is not an error when the
   review existed only as prose.

---

## Sessions

### Session 1 of 2: Audit & design-lock

**Steps:**
1. Re-verify the current state: where structured verifier issues exist in
   memory, where recent sets persist only prose, and where legacy
   `issue-logs/` helpers still linger.
2. Lock the filename convention, schema scope, resolution-field policy,
   and the explicit "no nested folder" rule.
3. Run cross-provider consensus on the open questions above,
   especially per-round persistence vs overwrite, and whether any helper
   should ship at all.
4. Capture the audit record in a proposal / verdict pair and update this
   spec with the locked design.

**Creates:** proposal + verdict under `docs/proposals/`.
**Ends with:** a design-locked artifact contract for `sN-issues.json`.
**Progress keys:** naming locked; schema policy locked; helper yes/no locked.

### Session 2 of 2: Implement + docs + tests

**Steps:**
1. Add the blessed schema/example and, only if real duplication justifies
   it, a small optional helper for writing structured issue artifacts.
2. Update `docs/ai-led-session-workflow.md`,
   `docs/planning/session-set-authoring-guide.md`, and any other
   canonical references so they point to `sN-issues.json` and continue
   to treat `issue-logs/` as legacy compatibility only.
3. Add tests for the helper/schema path if code ships; otherwise add at
   least a fixture/example that proves the documented envelope shape is
   concrete.
4. Cross-provider verification, close-out, and held release notes if the
   implementation touches the packaged `ai_router` surface.

**Ends with:** a documented, root-level, machine-readable issue artifact
that future sessions can rely on without reviving `issue-logs/`.
**Progress keys:** schema/doc landed; helper/tests landed if justified;
release note written if needed.

---

## End-of-set deliverables

- Canonical root-level structured issue artifact naming:
  `sN-issues.json` and `sN-issues-round-<M>.json`.
- A schema reference for the persisted issue shape.
- Workflow/authoring docs updated to use the root-level artifact and to
  keep `issue-logs/` retired.
- Optional helper/tests only if they improve consistency without making
  Python importability a requirement.