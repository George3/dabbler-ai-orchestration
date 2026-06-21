# Greenfield matrix adjudication — Set 019 Session 2

- **Run:** `0fb87b8..WORKTREE` (pre-remediation snapshot), 2026-06-20
- **Diff class:** `packaging-small` (10 files / 186 lines / 11,149 bytes; not elided)
  — the CI publish workflow + csproj packaging/license + license/notice files +
  docs. This repo is the Set-075 SUPPORTING (diff-class-confounded) signal.
- **Roster (corpus continuity with S1):** `push:anthropic` (claude-sonnet-4-6),
  `pull:openai` (gpt-5.4), `pull:google` (gemini) → 2 dual-surface cells.
- **Arms that ran:** all three (skipped=0). Note: unlike S1, the `pull:google`
  arm did **not** trip a DeterministicServantViolation this run — both pull cells
  returned a clean `VERIFIED`.

## Verdicts (worked from the deduped consolidated `remediation-report.md`)

The consolidated report carried 5 push-only findings; both pull arms returned
`VERIFIED` (zero findings). Ground truth at adjudication time: the files the push
arm flags as "absent" **do exist** in the working tree — `THIRD-PARTY-NOTICES.txt`
was bundled into the packed `.nupkg` (verified: 2,809 bytes at the package root),
`docs/harvester/nuget-publish.md` exists and the `install.md` link resolves, and
`LICENSE` / `nuget-publish.yml` are present. They were **untracked** new files, so
`git diff 0fb87b8..WORKTREE` elided them from the slice the push surface saw —
the textbook push-elision FP from the rubric.

- **F1** — `THIRD-PARTY-NOTICES.txt` "packed but absent from the changeset / its
  existence is unverified" — **verdict: FP (push-elision)** — armsCaught: [push:anthropic]
  - The file exists and is bundled in the packed `.nupkg`. The push surface was
    given a diff that excluded the untracked new file; the "missing" claim is an
    artifact of that elided context (rubric FP example: *Push-Elision*). No defect.
- **F2** — `THIRD-PARTY-NOTICES.txt` "referenced in the build but absent from the
  diff" — **verdict: duplicate (of F1)** — armsCaught: [push:anthropic]
  - Substantively the same defect claim as F1, restated; folded into F1.
- **F3** — `docs/harvester/nuget-publish.md` "linked in install.md but absent from
  the diff" — **verdict: FP (push-elision)** — armsCaught: [push:anthropic]
  - Same root cause: the file is a new untracked file present in the tree; the
    `install.md` link resolves. Push saw an elided diff. No broken link, no defect.
- **F4** — `"S FOUND**\n\n###"` — **verdict: unclear (parse artifact)** — armsCaught: [push:anthropic]
  - A truncated fragment of the push arm's `ISSUES_FOUND` verdict line that the
    consolidator mis-parsed into a finding shell. Not a substantive finding;
    excluded from precision per the rubric (not silently defaulted to FP).
- **F5** — `"S FOUND"` — **verdict: unclear (parse artifact)** — armsCaught: [push:anthropic]
  - Same as F4 — a verdict-line fragment, not a finding. Excluded from precision.

## Adjudicated union

**adjudicated_union_TP = 0.** No matrix arm surfaced a real defect in the S2 work.
The standard cross-provider session-verification (Step 6, separate from this matrix)
is the authority for the merge decision; it is recorded in `s2-verification*.md`.

## Per-arm scoring (stratum: packaging-small)

| arm (surface:provider) | TP | FP | precision        | share-of-union | unique-TPs |
|------------------------|----|----|------------------|----------------|------------|
| `push:anthropic`       | 0  | 2  | 0.00             | 0.00           | 0          |
| `pull:openai`          | 0  | 0  | n/a (0 findings) | 0.00           | 0          |
| `pull:google`          | 0  | 0  | n/a (0 findings) | 0.00           | 0          |

(F2 = duplicate, folded into F1; F4/F5 = unclear, excluded from precision. So
`push:anthropic` is charged 2 FP for F1 + F3.)

## Signal note (counter to the packaging-small ⇒ favors-push prior)

This is the **second** Set-019 data point running counter to the "packaging-small
diffs are snippet-fittable and favor `push`" prior. In S1, the only TP (a cross-file
doc-staleness defect whose authoritative file was outside the diff) was caught
**only by pull** — push structurally could not see it. In S2, the inverse failure
mode appears: the push surface, fed a tracked-only diff that **elided the session's
new untracked files**, manufactured three false "missing file" findings, while both
pull arms — which read the actual repository — correctly returned clean. On this
packaging-small session the pull surface was both more precise (no FPs) and not
misled by the diff-slice's incompleteness. One confounded data point; both pull arms
present this run (no skipped google arm).
