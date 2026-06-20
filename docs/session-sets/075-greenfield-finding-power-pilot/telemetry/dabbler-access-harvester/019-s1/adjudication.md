# Greenfield matrix — adjudication (Set 019, Session 1)

- **target:** `dabbler-access-harvester` (greenfield pilot **supporting / confounded** signal)
- **committed ref (measured diff):** `60490e6..WORKTREE`
- **diffShape:** 2 files, 175 lines, 9205 bytes, `elided=false`
- **diffClass:** `packaging-small` (the S1 diff is `AccessHarvester.Cli.csproj` packaging
  props + `docs/harvester/install.md` — snippet-fittable; favors `push` for the wrong
  reason → confounded, Validity Threat 1)
- **phase:** `pre-remediation` (this snapshot was frozen BEFORE the F2 doc fix)
- **orchestrator:** anthropic / `claude-opus-4-8`
- **matrix package:** `dabbler-ai-router 0.26.1`
- **adjudicator:** orchestrator (Opus 4.8), each finding checked against repo ground truth

## Arms that ran

| arm (surface:provider) | model | framing | verdict | status |
|---|---|---|---|---|
| `push:anthropic` | `claude-sonnet-4-6` | adversarial-devil's-advocate | VERIFIED (1 inconclusive nit, self-resolved) | scored |
| `pull:openai` | `gpt-5.4` | adversarial-devil's-advocate | ISSUES_FOUND (2 Major) | scored |
| `pull:google` | (n/a) | adversarial-devil's-advocate | — | **SKIPPED** — `DeterministicServantViolation` (Gemini grep servant altered bytes; a Gemini tool-fidelity failure unrelated to the diff). Per the D3 freeze rule the range was **not** re-run; the dropped arm is recorded here, not silently elided. |

> Provenance is **incomplete** (`pushUnkeyed=1, pullUnkeyed=2`): no finding was keyed,
> so no cross-surface dedup occurred. With only one pull arm scoring, no `pull∩pull`
> agreement is observable this run.

## Per-finding verdicts

- **F1 — completeness: "S2 nuget publish pipeline + first-push guardrails absent"** —
  verdict: **FP** (out-of-scope) — armsCaught: `[pull:openai]`
  - Ground truth: accurate — `.github/workflows/release.yml` has only the zip release;
    no `dotnet pack` / `nuget push` / validation guardrails exist yet.
  - Why FP: those are **explicitly Session 2 deliverables**, correctly deferred by
    `spec.md` (the set is 2 sessions; S1's contract is "packs + installs locally"). It is
    not a defect in the S1 diff or S1's scope. Retained as a valid S2 tracking reminder
    (already in the session plan), not a defect against this merge.
- **F2 — contract-drift: "consumer docs state stale schema version (v1.0)"** —
  verdict: **TP (Minor)** — armsCaught: `[pull:openai]`
  - Ground truth confirmed: `docs/harvester/install.md:379` says schema "Current value:
    `1.0`"; `README.md:97` says `validate` checks "harvester-schema v1.0 that is embedded
    in the binary" — both stale. Actual current schema is **v1.1** (`validate` supports
    `["1.0","1.1"]`; `--version` emits "schema v1.1"; HHC golden validates against v1.1).
  - Severity: **Minor**, not the pull arm's "Major" — the harvester keeps v1.x
    backward-compatible (v1.0 manifests still validate) and the **runtime** `--version`
    output already tells the truth, so the harm path (a consumer pinning v1.0 from the
    doc) is real but low. Pre-existing staleness, not introduced by the S1 diff, but it
    lives in a file S1 edits (`install.md`) and a load-bearing sibling doc (`README.md`).
  - **Remediated** post-freeze (see "Remediation" below).
- **F3 — (push-only, uncategorized): EnableCompressionInSingleFile musing + SQLite-removal
  note** — verdict: **FP** (report artifact) — armsCaught: `[push:anthropic]`
  - The push arm's own inconclusive reasoning ("I cannot confirm it was previously
    present… I'll flag it as a nit/minor") plus a confirmation that the install.md SQLite
    removal is consistent — captured as a pseudo-finding by the consolidator. The push
    arm's actual verdict is **VERIFIED**. Ground truth: `EnableCompressionInSingleFile`
    is **still present**, merely RID-gated; nothing was removed. Not a real defect.

## Adjudicated union (proxy denominator)

| | count |
|---|---|
| **Unique TPs (adjudicated union)** | **1** (F2) |
| FPs | 2 (F1 scope, F3 artifact) |
| duplicate / unclear | 0 |

## Per-arm scoring — stratum `packaging-small`

| arm | TP | FP | precision | share-of-union | unique-TPs | arm_cost_usd | cost-per-TP |
|---|---|---|---|---|---|---|---|
| `push:anthropic` (claude-sonnet-4-6) | 0 | 1 | 0.00 (0/1) | 0.00 | 0 | not emitted by tool | n/a (0 TP) |
| `pull:openai` (gpt-5.4) | 1 | 1 | 0.50 (1/2) | 1.00 | 1 | not emitted by tool | n/a |
| `pull:google` | — | — | skipped | — | — | — | — |

> Per-arm `costUsd` is **not surfaced** in the matrix/remediation reports for this
> `dabbler-ai-router 0.26.1` run, and router-metrics does not tag the matrix-arm calls
> distinctly; cost columns are therefore recorded as "not emitted" rather than estimated.

## Observation (for the synthesis set)

On this `packaging-small` diff the pilot's stated prior is that small/snippet-fittable
diffs favor `push`. This run runs **counter** to that prior: `push:anthropic` returned a
clean VERIFIED (0 TP), while the sole real TP was caught by `pull:openai`. The mechanism
is informative rather than contradictory — the only real defect (F2) is a **cross-file doc
inconsistency** where the authoritative `README.md` is **not in the diff**; the push arm,
which sees only the diff, structurally **cannot** observe it, while the pull arm's
whole-repo access can. A single confounded data point with one pull arm missing — do not
over-read; recorded for the corpus.

## Remediation (post-freeze, pre-commit)

F2 (the one TP) fixed after this report was frozen: `install.md` "Current value: `1.0`"
→ `1.1`, and `README.md` `validate` schema wording updated from "v1.0" to the actual
"v1.0 / v1.1 (current v1.1)" behavior. F1 carried forward to Session 2 (its rightful
owner); F3 requires no action.
