# Verdict — Structured Verification Issue Artifacts (S1 design-lock)

> **Set:** `055-structured-verification-issue-artifacts`, Session 1
> **Date:** 2026-06-02
> **Consensus input:** `proposal.md` (GitHub Copilot / GPT-5.4 dispositions)
> **Cross-provider reviewer:** `gemini-pro` (Google) — raw in `consensus-review.md`
> **Round-1 overall:** `CONSENSUS-AGREE`
> **Outcome:** design accepted as proposed. No disposition reversals.
> The reviewer raised three implementation risks; they are accepted as
> guardrails, not as reasons to change the core contract.
> This file is the **authoritative locked design**; where it differs from
> `proposal.md`, this file wins.

---

## How the consensus affected the design

The cross-provider reviewer agreed with **Q1-Q8** outright. There were no
recommended reversals on filename semantics, envelope-vs-array shape,
resolution-field policy, clean-round behavior, manual-flow treatment,
helper scope, runtime-reader scope, or release discipline.

That means the proposal's design stands as written. The only work for the
lock is to convert the reviewer's risks into explicit implementation
guardrails so Session 2 does not accidentally overstate the new artifact.

### Accepted guardrails from the reviewer's risks

**R1 — annotation drift is real, so the resolution fields are advisory
only.**

`resolution_status`, `resolution_notes`, and `resolved_in_round` remain in
scope for v1, but they are **append-only annotations**, not a second
authoritative workflow state. Session 2 docs must say clearly:

- the verification narrative remains the canonical prose record
- `disposition.json` remains the close-out handoff
- `sN-issues*.json` resolution fields are convenience metadata for
  issue-tracking and future automation only

No runtime reader in Set 055 may treat those fields as gate-driving or as
the final source of truth for whether a finding was actually resolved.

**R2 — schema under-utilization is acceptable only if the optional fields
stay truly optional.**

The v1 envelope keeps the optional resolution fields, but Session 2 must
avoid forcing them into every example or helper surface. A newly-written
artifact with just:

- `schemaVersion`
- `sessionNumber`
- `verificationRound`
- `verificationVerdict`
- `issues`

is fully valid. The optional fields exist to avoid repainting the schema
later if operators start annotating findings; they are not a required part
of the write path.

**R3 — inconsistent adoption is an intentional tradeoff, not a defect.**

Manual / `--no-router` workflows may emit the artifact when they have a
real structured issue list, but Set 055 deliberately does not force every
manual review into JSON. Session 2 docs must therefore preserve this
distinction:

- missing `sN-issues*.json` on a manual-flow set is not an error
- the artifact is required only when the workflow actually has a
  structured findings list to persist

This keeps the contract honest across engines and avoids fabricating data
from prose-only reviews.

---

## Locked invariant

> **The presence of `sN-issues*.json` means that verification round found
> issues.**

This invariant is why the lock keeps **no empty issue file for VERIFIED
rounds** and **no overwrite/latest-only mode**. A consumer or future tool
can safely treat artifact presence as "this round had structured findings"
without opening a second file or inspecting round history.

---

## Final locked dispositions

| Q | Decision |
|---|---|
| Q1 | **One file per findings-bearing verification round.** Round 1 uses `sN-issues.json`; later findings-bearing retries use `sN-issues-round-<M>.json`. Never overwrite. |
| Q2 | **Small envelope, not bare array.** `schemaVersion`, `sessionNumber`, `verificationRound`, `verificationVerdict`, and `issues[]` are the v1 top-level contract. |
| Q3 | **Preserve verifier issue objects verbatim and allow additive resolution fields.** `description` is the only reliable required issue field; `category` / `severity` stay loose strings; `resolution_*` fields are optional and advisory. |
| Q4 | **No empty issue file for VERIFIED rounds.** Only findings-bearing rounds get `sN-issues*.json`. |
| Q5 | **Manual / `--no-router` flows may write the same envelope when they genuinely have structured findings, but are not required to invent it from prose.** |
| Q6 | **No required helper.** Session 2 is docs/schema/example first; a helper is allowed only if it removes real duplication and remains convenience-only. |
| Q7 | **No runtime readers in Set 055.** `close_session`, gate checks, metrics, and the Explorer ignore the new artifact in this set. |
| Q8 | **Release only if code ships.** Docs/schema/example-only work needs no PyPI or Marketplace release; a Python helper would be PyPI-only. |

---

## Locked Session 2 scope

**Session 2 should ship:**

- a concrete schema/example for the root-level envelope
- workflow docs naming the root-level artifact and keeping
  `issue-logs/` retired
- at least one example fixture proving the JSON shape is real
- optional helper code only if it is obviously reducing repetition

**Session 2 must not ship:**

- any close-out gate dependency on `sN-issues*.json`
- Explorer/UI rendering or badges
- embedding the full issue array into `disposition.json`
- historical backfill of older sets
- a return to nested `issue-logs/`

---

## Out of scope (explicit)

- making resolution annotations authoritative over prose artifacts
- requiring manual workflows to fabricate structured issues from prose
- runtime aggregation/reporting surfaces
- TS/runtime consumer changes
- release/version work when no distributable code changes