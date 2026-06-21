# Greenfield finding-power pilot — telemetry

This directory is the **canonical, committed aggregation home** (protocol decision
**D5**) for the greenfield finding-power pilot. The two source-bearing pilot repos
copy their **frozen** `matrix-run/` artifacts here at the end of a build session; a
future canonical **synthesis** set scores the accumulated corpus.

> Canonical contract: [`docs/greenfield-matrix-protocol.md`](../../../greenfield-matrix-protocol.md)
> (D5 telemetry layout + the required `metadata.json` fields, D3 freeze rule).
> Adjudication: [`docs/greenfield-adjudication-rubric.md`](../../../greenfield-adjudication-rubric.md).
> The per-session producer block: [`ai_router/prompt-templates/greenfield-matrix-addendum.md`](../../../../ai_router/prompt-templates/greenfield-matrix-addendum.md).

## Layout

```
telemetry/
  <repo>/
    <session>/
      verification-matrix-report.json    # frozen, immutable (D3)
      remediation-report.json            # frozen, immutable (D3)
      remediation-report.md              # frozen, immutable (D3)
      adjudication.md                    # per-finding TP/FP/dup/unclear + per-arm credit
      metadata.json                      # the required run metadata (below)
```

- `<repo>` is the pilot repo (`dabbler-platform`, `dabbler-access-harvester`).
- `<session>` is the consumer set/session id that produced the run.
- Telemetry is **committed and reviewable**, never gitignored — the pilot's purpose
  is a later synthesis. No CI / Git-PAT transport: the repos are co-located sibling
  worktrees, so the consumer session does a plain file copy.

## Required `metadata.json` fields

The canonical list lives in the protocol's **§6 (D5)**. Each run's `metadata.json`
MUST carry:

| field | meaning |
|---|---|
| `targetRepo` | the pilot repo name |
| `sessionId` | the consumer set/session that produced the run |
| `baseRef` / `headRef` | the measured diff range (`--base` / `--head`) |
| `matrixPackageVersion` | the `dabbler-ai-router` version that ran the matrix |
| `orchestratorProvider` / `orchestratorModel` | the session's orchestrator |
| `matrixArms` | a **list** of `{surface, provider, model}` for every scored arm — one push + two pull (§8), so a single pull field cannot name both |
| `diffStats` | `{bytes, lines, files, elided}` |
| `diffClass` | `source-dominated` \| `packaging-small` \| `docs-only-excluded` |
| `phase` | `pre-remediation` (the measurement snapshot) |
| `includedInFindingPower` | `true` for the two source repos; `false` for any docs-only sidecar |

## Cohort

| repo | role | included in finding-power aggregate? |
|---|---|---|
| `dabbler-platform` | **LEAD** (source-dominated generator tooling) | yes |
| `dabbler-access-harvester` | supporting (small/packaging diffs — confounded) | yes |
| `dabbler-access-migration-orchestrator` | **deferred** (docs-only) | no — pull-only sidecar at most, `includedInFindingPower=false` |

The migration-orchestrator repo is excluded from the aggregate (D4); it has no
subdirectory here unless it ships an optional, clearly-tagged pull-only sidecar run.

| `dabbler-great-psalms-scroll-font` | **candidate — to enable** (defect-dense algorithmic font-derivation) | yes (once enabled) — see Interim read |

## Interim read (2026-06-20, after the first 3 datapoints) — READ BEFORE PICKING THE NEXT TARGET

The first three runs (`dabbler-platform/…-s2`, `dabbler-access-harvester/019-s1`,
`019-s2`) are **TP-starved**: the adjudicated TP union across all three is **1**
(caught only by `pull:openai` — a cross-file doc-staleness defect the `push` arm is
structurally blind to). Every other finding was a false positive of the rubric's two
canonical classes (push elision; pull out-of-sandbox). **No finding-power conclusion
can be drawn from this** — with ~1 real defect total, share-of-union / unique-TP /
cost-per-TP are all degenerate. The cause is **defect density, not the instrument**:
these were small, clean, packaging/decision diffs — exactly the kind a deterministic
contract gate already covers, so there were no subtle defects left for the matrix to
catch.

**Implication for target selection — aim for defect-dense, oracle-poor source work.**
The next runs should be **algorithmic logic** sessions (numerically/geometrically
subtle, no cheap ground-truth oracle, interdependent steps), where real defects
survive naive testing and a path-aware adversarial review has unique value.

- **Lead target going forward: `dabbler-great-psalms-scroll-font` Stage B** (its
  `project-plan.md` §6.2–6.7): Procrustes/GPA alignment, centerline extraction,
  the ribbon width-profile / offset-Bézier reconstruction, outlier detection,
  kerning derivations, ligature/run detection, and the calamus-law stroke-uniformity
  models. **Skip** its setup/EDA/ingest sets (§7 steps 1–4) — low defect density.
  Enablement (router pin `>=0.26.0` + addendum wiring) is pending a deferred
  consumer-instruction sweep.
- **Retrospective sub-corpus (NOT greenfield finding-power):** applying the matrix to
  already-working code — the great-psalms `.scm` Script-Fu tools and the predecessor
  repo's image downloader — is the Sets 072–073 *already-built* mode, not a fresh
  pre-remediation run. Tag any such run `phase=retrospective` /
  `includedInFindingPower=false` so it never contaminates the greenfield aggregate.
  It is still useful scrutiny (those `.scm` tools were push-verified but **never**
  pull/path-aware-reviewed). Caveat: Script-Fu (TinyScheme) is a **new language** for
  this corpus (C#/.NET + Python so far) — record it so the synthesis does not compare
  Scheme FP-rates against Python ones as if they share an axis.

**Two methodology fixes the first runs surfaced (to fold into the addendum):**
1. **Stage new files before the matrix run.** Untracked files are elided from
   `git diff`, so the `push` arm hallucinates them as "missing" (the `019-s2`
   push-elision FPs) — the instrument penalizes push for an artifact of L-064-9.
2. **Commit *and push* the telemetry**, not just commit — the platform `…-s2`
   LEAD datapoint was committed but left unpushed (stranded on one checkout) until a
   later cross-check caught it. The addendum step 6 should say "commit **and push**."
