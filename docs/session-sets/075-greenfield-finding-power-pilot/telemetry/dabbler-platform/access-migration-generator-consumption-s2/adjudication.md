# Greenfield matrix adjudication — access-migration-generator-consumption Session 2

> Adjudicated against the **fixed rubric**
> (`dabbler-ai-orchestration/docs/greenfield-adjudication-rubric.md`), working from the
> deduped, provider-blind `remediation-report.md`. Arm provenance (`pull:openai` vs
> `pull:google`) read mechanically off the per-cell `verification-matrix-report.json`
> (Cell 0 pull = openai/gpt-5.4; Cell 1 pull = google/gemini-2.5-pro; push =
> anthropic/claude-sonnet-4-6 in both). **Anti-bias rule applied:** TP/FP decided on
> substance before consulting provider identity.

- **Run:** `741b00d..WORKTREE`, pre-remediation, frozen.
- **Diff class:** `source-dominated` (the LEAD pilot signal — cohort §10). 8 files /
  432 lines / 22,028 bytes, `elided=false`. Composition leans packaging-plus-test
  (csproj `PackAsTool` metadata, `pack.ps1`, `.slnf`) but carries genuine C# logic
  (`TemplatePreflight` process-probing + version parse) and a substantial new
  consumer-validation gate test, so it is scored as source, not `packaging-small`.
- **Roster / arms:** `push:anthropic` (sonnet-4-6) × {`pull:openai` (gpt-5.4),
  `pull:google` (gemini-2.5-pro)} → 2 cells, 3 scored arms.

## Per-finding verdicts

The consolidated report listed 7 findings. README/helper-existence claims were
verified empirically (not assumed): `tools/Dabbler.CrudSlice/README.md` exists
(5,087 bytes, dated 2026-05-30, predates the session); `WriteLocalNugetConfig`
pre-exists at `PackagingSmokeTests.cs:651`; the session built green, packed 16
nupkgs, and the consumer gate + 29 CrudSlice tests passed — so every "will not
compile / cannot pack" claim is contradicted by a green build.

- **F1 — `WriteLocalNugetConfig` called but not defined in the diff** — verdict: **FP**
  (push-elision) — armsCaught: [push:anthropic]. The method pre-exists at line 651;
  the diff elided it. Build is green.
- **F2 — `README.md` declared in `.csproj` but absent from the diff** — verdict: **FP**
  (push-elision) — armsCaught: [push:anthropic]. `tools/Dabbler.CrudSlice/README.md`
  exists and predates the session; `pack.ps1` produced the `.Tool` nupkg successfully.
- **F3 — Missing `README.md` file** — verdict: **duplicate** of F2 (FP) —
  armsCaught: [push:anthropic]. Same claim, different wording.
- **F4 — prompt assumes `docs/session-sets/dabbler-platform` + a
  `path-aware-critique-schema.md`** — verdict: **FP** (irrelevant / not a diff defect)
  — armsCaught: [pull:openai]. The reviewer is complaining about its own
  prompt/harness paths, not about any code in the diff. No defect, no path to harm.
- **F5 — `AddDabblerPlatformStubs` conditionally registers stub services** — verdict:
  **FP** (pull-out-of-sandbox) — armsCaught: [pull:google].
  `src/Libs/Dabbler.Platform.Stubs/DabblerStubServiceCollectionExtensions.cs` is **not
  in this session's diff** (confirmed via `git diff --name-only 741b00d`). The rubric's
  out-of-sandbox example: a real-or-not issue in pre-existing code outside the review
  surface is FP for this measurement. (Substantively it is also likely intentional —
  conditional stub registration — but the out-of-sandbox call settles it.)
- **F6 — `.csproj` declares `README.md` as a pack artifact but the file is absent** —
  verdict: **duplicate** of F2 (FP) — armsCaught: [push:anthropic].
- **F7 — sequential synchronous pipe draining in `TemplatePreflight.IsTemplateInstalled`**
  — verdict: **FP** (pure nit, no plausible harm path) — armsCaught: [push:anthropic].
  The finding itself concludes "deadlock is practically impossible … nit-level"; `-h`
  output is far below any pipe buffer. Per the rubric, a style nit with no plausible
  path to harm is FP. (Noted as a known low-risk tradeoff in the code's own comment.)

## Adjudicated union

**|adjudicated_union_TP| = 0.** No matrix arm — and neither the session's standard
verification (green build + pack + 29 CrudSlice tests + the consumer-validation gate)
nor the end-of-set dogfood — surfaced a real defect in the frozen diff. The matrix
caught nothing the normal pass missed, and vice-versa; the union is empty.

## Per-arm scoring table (`source-dominated` stratum)

| arm (surface:provider) | TP | FP | precision        | share-of-union | unique-TPs | arm_cost_usd            | cost-per-TP        |
| ---------------------- | -- | -- | ---------------- | -------------- | ---------- | ----------------------- | ------------------ |
| `push:anthropic`       | 0  | 3  | 0.00             | 0.00           | 0          | not emitted (report v1) | n/a — 0 TP         |
| `pull:openai`          | 0  | 1  | 0.00             | 0.00           | 0          | not emitted (report v1) | n/a — 0 TP         |
| `pull:google`          | 0  | 1  | 0.00             | 0.00           | 0          | not emitted (report v1) | n/a — 0 TP         |

- **FP counts** use distinct consolidated findings credited to each arm; F3 and F6 are
  `duplicate` (folded into F2) and not double-counted, so `push:anthropic` carries
  3 distinct FPs (F1, F2, F7).
- **precision** = `TP/(TP+FP)` = `0/(0+FP)` = 0.00 for every arm with findings.
- **cost-per-TP** is undefined with TP=0; the matrix report (schemaVersion 1) carries
  no per-arm cost field, so absolute arm cost is recorded as "not emitted" rather than
  guessed. Either way the value is moot at TP=0.

## Reading (this run only — not a verdict)

On this small, clean, packaging-leaning source diff the matrix produced **0 TP / 7 FP
across all three arms (precision 0.00 each)**. Failure modes were the rubric's two
canonical FP classes: `push` elision (claiming pre-existing, diff-elided files/methods
are "missing" → 5 push FPs) and `pull` wandering out of the review sandbox / confusing
its own harness paths (2 pull FPs). This is one data point for the finding-power
corpus, not a comparative conclusion — the synthesis set scores the accumulated
telemetry.
