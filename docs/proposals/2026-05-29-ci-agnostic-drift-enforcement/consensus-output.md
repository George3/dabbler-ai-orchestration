# Set 053 S1 — cross-provider consensus output (2026-05-29)

Two independent reviewers, each asked to evaluate AND adversarially
attack the proposal's load-bearing dispositions. Total routed cost
$0.0362 (gemini-pro $0.0121; gpt-5-4 $0.0241). Raw run:
[`run_consensus.py`](run_consensus.py).

## Convergence

- **CI is the centerpiece — CONFIRMED by both.** Since every writer
  already stamps from the constant, the residual vector is hand-editing,
  and CI is the only source-agnostic, non-bypassable choke point that
  sees the committed tree. Caveat (both): "CI as centerpiece" only holds
  if **branch protection is actually mandatory** — otherwise the real
  centerpiece is the policy configuration, not the job script.
- **Agree:** Q1/Q8 (centerpiece), Q3 (CI packaging), Q4 (writer audit →
  convention test), Q6 (required-for-merge docs), Q9 (opt-in `--fix`),
  Q13 (Azure specifics).

## The load-bearing disagreement: baseline allowlist (Q7/Q11/Q12)

**Both reviewers rejected the committed baseline-allowlist file** as the
wrong bet.

- **gemini-pro:** Q7/Q11/Q12 all *disagree*. "Worse than the
  alternatives… trades a one-time migration cost for a permanent
  maintenance burden. The baseline file itself becomes a new source of
  drift and review friction… A forced, one-time migration sweep is
  strategically superior — it eradicates the problem class and simplifies
  the reader codebase forever." Proposes instead an **inline,
  self-documenting directive inside the JSON file itself** (e.g. a
  `schema-pinned: "<reason>"` key) so the exception lives with the file,
  not in a disconnected manifest.
- **gpt-5-4:** Q7/Q11/Q12 all *modify*. "The proposal's load-bearing bet
  is not CI; it's the baseline allowlist… a durable exception registry
  that can rot, be padded to silence legitimate regressions, and drift
  from reality." Rates it "better than git-diff" (diff is underspecified
  across CI providers — merge-base, rename, squash/rebase, bot pushes)
  "but governance-heavy." If kept, it MUST add: a baseline-self-validator
  (fail if listed sets don't exist / are already current / duplicated),
  per-entry metadata (rationale/author/date/expiry), CODEOWNERS
  governance, rename/deletion handling, and a pruning workflow.

## Other modifications

- **Q5 advisory:** gemini — put a high-visibility warning **inside the
  JSON** (e.g. a `_warning` key readers ignore), not only external docs.
- **Q10 content-validation:** gemini — should be **default-on, not
  optional** ("a version/content mismatch IS drift"). gpt-5-4 — define
  precisely when it's required vs best-effort.
- **Q2 hooks:** gpt-5-4 — `core.hooksPath` is "operationally fragile and
  often ignored; treat as optional bootstrap, not a meaningful
  enforcement layer." (Reinforces hooks = secondary.)

## Missing (flagged for S2 if the relevant path is chosen)

Baseline-file self-validator; entry metadata + expiry; CODEOWNERS on the
exception mechanism; rename/stale-entry pruning; repo-wide-vs-touched-paths
scan cost/noise tradeoff; failure-message UX (migrate vs fix vs pin); bot
PR / merge-queue parity on GitHub *and* Azure; a scheduled audit job (not
just PR CI) to catch direct-to-branch writes.

## Synthesis going into the verdict

The reviewers agree the **separate baseline manifest is the weak link.**
Two clean replacements remain, and which one is right depends on a
**product-policy decision that is operator-locked** (Set 050's "old
schema is acceptable; no forced per-set migration"):

- **Keep the non-goal → inline per-file pin** (gemini's idea): a
  sub-current state file must carry an inline `schemaPinnedReason` field
  or CI fails it. Self-documenting, no separate manifest to rot, is
  simultaneously the escape hatch (Q12), the new-drift gate (Q7), and the
  non-goal mechanism (Q11). A new hand-authored stale file (no pin) fails.
- **Reverse the non-goal → one-time forced sweep** (both reviewers'
  strategic preference): migrate all ~46 historical sets to current once;
  then CI simply fails ANY sub-current file and the reader back-compat
  shim can eventually be retired. Simplest long-term, but reverses the
  operator's Set 050 directive.

This fork goes to the operator (see verdict).
