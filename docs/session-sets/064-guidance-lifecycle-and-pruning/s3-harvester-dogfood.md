# Set 064 Session 3 — Harvester Backlog-Triage Dogfood (READ-ONLY)

> **Session:** 3 of 4. **Date:** 2026-06-14.
> **Orchestrator:** Claude Code (claude-opus-4-8), provider anthropic, effort high.
> **Deliverable:** D6 proof — run the backlog-remediation triage helper
> (`ai_router.guidance_triage`) against the real over-budget
> `dabbler-access-harvester` `lessons-learned.md` and record the proposed
> classification + projected post-remediation size.
> **Invariant honored:** **No edit was made to the harvester working
> tree.** This is a read-only proposal; executing the moves is a
> harvester-side follow-on set.

---

## 1. Method

```bash
python -m ai_router.guidance_triage \
  --file "<harvester>/docs/planning/lessons-learned.md" \
  --batch-size 100 --complexity-hint 90 --excerpt-chars 4000 \
  --out   s3-harvester-triage-raw.txt \
  --report s3-harvester-triage-report.txt \
  --session-set 064-guidance-lifecycle-and-pruning
```

- **One routed analysis call**, all 69 blocks in a single batch so the
  classifier had whole-file context for duplicate detection.
- `--complexity-hint 90` forced a **tier-3 model (opus)**, deliberately
  avoiding the tier-2 `gemini-pro` analysis profile's `thinking_budget:
  -1` unbounded-thinking JSON trap.
- **Model:** `opus` (claude-opus-4-8). **Routed cost: $0.6313.**
- Raw routed output and the rendered report are committed alongside this
  file (`s3-harvester-triage-raw.txt`, `s3-harvester-triage-report.txt`).

The full raw artifacts are the source of truth; this file is the
narrative summary.

---

## 2. Result

| Bucket | Count | Effect on the active tier |
|---|---:|---|
| keep-active | 44 | stays (full size) |
| archive | 20 | move to `lessons-archive.md` (grep-able, never deleted) |
| drop | 5 | boilerplate removed (How-To-Use, Entry-Template ×2, two bare section headers) |
| merge | 0 | — |
| promote | 0 | — |
| **unclassified** | **0** | every block was classified |

**Projected active-tier size:**

| | chars | ~tokens | vs 10,000-token ceiling |
|---|---:|---:|---|
| current | 154,780 | ~38,695 | **OVER (387%)** |
| projected (after applying the proposal) | 87,260 | ~21,815 | **still OVER (218%)** |
| reduction | | | **~44%** |

---

## 3. The headline finding: triage alone does NOT clear the ceiling

The single most important empirical result of this dogfood is that the
conservative triage pass cuts the harvester file by **~44%** — a real,
large win — **but still lands at ~2.18× the active-tier ceiling.** The 44
keep-active survivors are themselves substantial (most are 2,000–3,800
chars of genuinely live, single-context lessons that have not yet earned
promotion or archival).

This is exactly the precondition the recipe's **Step 5
(archive-bankruptcy)** is written for, and it validates *why* the recipe
is a multi-step operator-reviewed procedure rather than a one-shot
button. For the harvester specifically, the follow-on set will need some
combination of:

1. **Operator resolution of the near-duplicate pairs the model
   identified** (43/46, 21/47, 59/60, 5/29). The model classified 0
   `merge` because in each pair one member was already
   archive-bound/promoted, so no *live* merge target remained — but a
   human pass that consolidates the surviving members could recover
   further budget the conservative automated pass left on the table.
2. **A topic-file split** of `lessons-learned.md` — the harvester's own
   file header already anticipates this ("If this grows too large, split
   it into a `lessons-learned/` folder with a short index and topic
   files"). The 44 survivors are legitimately live; the file is simply
   carrying more genuine knowledge than a single always-loaded tier can
   hold under a 10k-token budget.
3. **Considering archive-bankruptcy** (Step 5) only with repo-owner
   sign-off, given that triage + dedup alone may not suffice.

Reporting this honestly is the point of a read-only dogfood: had the
projection come in under ceiling, the recipe would look complete; it
does not, so the recipe correctly carries the more-radical options.

---

## 4. Quality of the routed classification

The opus pass produced evidence-based reasoning, not guesses:

- **The primary budget win it found is `encoded`-class archival (20
  blocks).** Each archived lesson's *own body* records that its rule was
  already promoted to `project-guidance.md` (a "Promoted … on <date>"
  note inside the lesson). Once the binding rule lives in the
  always-loaded guidance tier, the verbose lesson prose is redundant in
  the always-loaded *lessons* tier — so the detail moves to the
  grep-able archive while the rule stays loaded via its one-line pointer.
  This is the `encoded-in`/supersession trigger working on real data.
- **It distinguished sibling-promoted from this-repo-promoted.** Blocks
  5–8 carry "promoted in a sibling repo" notes; the model kept them
  **active** because their rule is *not* in *this* repo's loaded
  guidance — a subtle, correct call.
- **It was conservative where automation is partial.** Blocks 14, 22, 32
  have some code/config encoding but retain live operational knowledge
  not captured by the automation, so they were kept active per the
  "when unsure, keep" rule.
- **It explained 0 promote / 0 merge** rather than silently omitting
  them (see the raw summary), which is the behavior the recipe wants — a
  promotion that is already noted in the body is an *archive* candidate,
  not a fresh promote.
- Only two non-promotion archives were proposed: block 27 (explicitly
  RESOLVED → `obsolete`) and block 59 (`superseded` by block 60's
  distilled lesson).

---

## 5. What this proves about the helper itself

- **Permissive extraction handles the real day-one shape.** The harvester
  file predates the D2 trailer scheme and mixes `##` and `###` headings
  (35 `###` lessons under `##` section headers, plus ~29 `##` lessons
  synced from the canonical repo, plus 5 structural `##` blocks). The
  extractor split all 69 correctly; the 5 structural blocks were the
  exact ones the classifier marked `drop`.
- **Robust response parsing.** The model wrapped its JSON in a prose
  summary and a ```` ```json ```` fence; the parser extracted the array
  cleanly (0 unclassified, no parse errors).
- **cp1252 safety proven end-to-end.** Real lesson titles carry
  em-dashes. The UTF-8 report file preserves them (`Notify The Human On
  route() Timeout —`); the ASCII-folded stdout copy shows `?` instead —
  i.e. the paid output was persisted to disk *before* any console print
  could crash (L-064-3 / L-064-4 in action).
- **No reference-conflict flags fired** — expected, because the harvester
  file has no D2 ids yet, so there is no active-guidance reference graph
  to violate. This is the day-one gap the recipe bridges, not a defect.

---

## 6. Invariant check

- **`docs/planning/lessons-learned.md` (the triage target) and all of
  `docs/planning/` in the harvester repo are unchanged by this session.**
  The helper reads the target file and writes only into *this*
  session-set directory (the raw + report artifacts). Verified via
  `git status --short` in the harvester repo: the only dirty paths are
  pre-existing, unrelated harvester-side session activity under
  `docs/session-sets/012-…` (an in-flight harvester session's state /
  log files) — nothing the dogfood produced and nothing under
  `docs/planning/`.
- The proposal is a **floor for operator review**, not an executed
  remediation. `archive != delete` throughout.
