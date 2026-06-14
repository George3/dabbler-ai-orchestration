# Guidance Backlog Remediation — One-Time Recipe

> **Audience:** Any AI-led-workflow repo whose always-loaded
> `lessons-learned.md` has grown **over its active-tier ceiling** and
> needs a one-time pass to get back under budget. Engine-agnostic
> (Claude Code / Codex / Gemini all follow the same recipe).
>
> **Status:** Portable canonical procedure (Set 064 D6).
> **Companion:** the steady-state lifecycle — per-lesson metadata (D2),
> citation-at-close (D3), the active/archive split (D4), and the
> evidence-based archive triggers + ceiling backstop (D5) — is what
> *keeps* a file under budget once this recipe has brought it back.
> This recipe is the one-time **interim** strategy that the steady-state
> mechanism cannot perform on its own.

---

## Why a separate one-time recipe at all

The steady-state lifecycle is **forward-looking**. It records
`last-used-set` from the moment it ships and archives a lesson on
evidence (superseded, encoded-into-automation, subsystem retired, or no
demonstrated reuse for the disuse window **and** not referenced by active
guidance). That works the day it lands and gets stronger as usage history
accumulates.

It is **useless on day one for a repo that is already over budget.**
Every existing lesson has no `last-used-set` history, so the disuse
trigger can only see "no recorded usage" for *all* of them — it would
either archive everything (catastrophic) or, with the "not referenced"
guard, nothing. A repo sitting at three to four times its ceiling (the
`dabbler-access-harvester` file was ~38.7k tokens against a 10k ceiling;
`dabbler-platform` was comparable) needs a **deliberate, evidence-driven
sweep** to get back under budget *before* the steady-state mechanism has
anything to measure.

That sweep is this recipe. It is **operator-reviewed at every step** and
**archive never means delete** — archived entries move to the grep-able,
never-auto-loaded `lessons-archive.md` and stay reachable
(`python -m ai_router.guidance_search --archive`).

---

## Preconditions

- The steady-state mechanism (Set 064 S2) is available in the repo's
  `ai_router` (the helpers below ship with it).
- `lessons-archive.md` exists as the sibling archive tier (created when
  the active/archive split lands; if it does not exist yet, create it
  empty with a one-line purpose header first).
- You have confirmed the file is actually over budget:

  ```bash
  python -m ai_router.guidance_report --check
  ```

  A non-zero exit means at least one active file is over its ceiling. If
  it exits zero, you do **not** need this recipe — the steady-state
  triggers are sufficient.

---

## The recipe

### Step 1 — Measure the baseline

```bash
python -m ai_router.guidance_report
```

Record the current bytes / lines / estimated tokens and the configured
ceiling. This is the number the remediation must beat. The token estimate
is the same `ceil(chars / 4)` proxy the projection in Step 2 uses, so the
"before" and "projected after" numbers are directly comparable.

### Step 2 — Routed bulk triage (produces a PROPOSAL)

```bash
python -m ai_router.guidance_triage \
  --file docs/planning/lessons-learned.md \
  --batch-size 100 \
  --complexity-hint 90 \
  --excerpt-chars 4000 \
  --out   <session-dir>/triage-raw.txt \
  --report <session-dir>/triage-report.txt
```

This routes one analysis pass that classifies **every** heading-delimited
block into exactly one bucket:

| Bucket | Meaning | Effect on the active tier |
|---|---|---|
| `keep-active` | a live, still-relevant lesson | stays (full size) |
| `archive` | real lesson, no longer worth loading every session (superseded / obsolete / subsystem retired / already encoded into a test/lint/guard so the prose is redundant) | **moved** to `lessons-archive.md` |
| `promote` | proven across multiple contexts; belongs in `project-guidance.md` | collapses to a one-line pointer here |
| `merge` | near-duplicate of, or subsumed by, another block | folded into the survivor (`merge_target`) |
| `drop` | not a lesson at all (boilerplate, section header, template, usage note) | removed |

The helper then prints a **projected post-remediation size** and whether
that projection clears the ceiling. Key properties:

- **It never edits the target file.** The output is a *proposal*. No move
  happens until the operator applies it (Step 3+).
- **Permissive block extraction.** Real over-budget files predate the D2
  metadata scheme and mix `##` and `###` lesson headings (a section
  header with `###` lessons under it, plus `##` lessons synced from the
  canonical repo). The extractor splits on every heading in
  `--min-level`..`--max-level` (default 2–3) and lets the classifier mark
  structural blocks `drop`; deeper `####` sub-points stay inside their
  lesson's block.
- **Tier-3 model on purpose.** `--complexity-hint 90` forces a tier-3
  model. This is deliberate: the tier-2 `gemini-pro` analysis profile
  runs with `thinking_budget: -1` (unbounded), which has been observed to
  consume the entire output budget on thinking and return empty/truncated
  JSON. A high-stakes one-time pass should pay for a tier-3 model.
- **Raw routed output is persisted to UTF-8** (`--out`) before the
  rendered report is printed, so a cp1252 console cannot lose the paid
  result mid-line. Terminal output is ASCII-folded; the report file keeps
  full fidelity.
- **Reference-graph guard.** If the file already carries D2 ids, the
  helper flags any block proposed for `archive`/`merge`/`drop` that is
  *referenced by active guidance* (`project-guidance.md`, or another
  lesson's `superseded-by` / `encoded-in`). Pass `--project-guidance` to
  feed that signal. On a day-one no-id file there are no ids, so nothing
  is flagged — that gap is exactly why this recipe exists.

The classifier is instructed to be **conservative**: when unsure whether
a lesson is still live, prefer `keep-active`; a rare-but-critical disaster
lesson that fires once in many sets is **not** archived for apparent
disuse.

### Step 3 — Operator review (the proposal is a floor, not a command)

Read `triage-report.txt`. The classification is a **starting point**, not
an instruction to execute blindly. Overrule any call that the routed
model got wrong — especially:

- anything proposed `archive`/`drop` that you know is still live;
- any `merge` whose `merge_target` would lose a distinction that matters;
- any rare-but-critical lesson the model down-weighted for disuse.

Resolve every `FLAGGED` reference conflict before proceeding.

### Step 4 — Supersession-merge dedup pass

Work through the `merge` group. For each near-duplicate cluster, pick the
**survivor** (usually the most complete / most recent), fold the unique
content of the absorbed entries into it, then mark each absorbed entry
`status="archived"` with `superseded-by="<survivor-id>"` and move it to
the archive. The survivor keeps its id (D2 ID-governance: ids are
permanent across renames; on a merge the survivor's id wins).

### Step 5 — Archive-bankruptcy (heavily gated opt-in — NOT the default)

The most radical option: move the **whole** active file to the archive
and let entries re-surface only when a future session cites them
(`python -m ai_router.cite_lessons` on an archived id updates its
`last-used-set` in the archive and prints a `RECONSIDER` line). This is a
clean reset for a file that is mostly dead weight.

It is **opt-in, projection-first, and requires repo-owner sign-off** — it
is **not** a co-equal default alongside the triage pass. Only consider it
when:

1. the Step 2 triage projection shows the keep-active survivors *alone*
   still cannot get the file under ceiling, **and**
2. the repo owner has explicitly approved a wholesale reset, **and**
3. you have a committed snapshot of the pre-bankruptcy file so nothing is
   irrecoverable.

Most over-budget files do **not** need this; the triage + dedup passes
are normally sufficient. Archive-bankruptcy is the escape hatch, recorded
here so the option is explicit rather than improvised.

### Step 6 — Apply the surviving moves and seed the steady-state baseline

For the entries you are keeping (`keep-active` and the `promote`
pointers):

1. **Mint a D2 metadata trailer** for each survivor that lacks one
   (`<!-- lesson: id="L-<set>-<seq>" added-set="…" status="active"
   scope="…" -->`). Use the current set number for `id` minting on
   genuinely new ids; preserve any existing id.
2. **Seed `last-used-set`** for survivors so the steady-state disuse
   window has a baseline rather than treating every survivor as
   never-used on the day after remediation. A reasonable seed is the
   remediation set number (the survivors demonstrably mattered enough to
   keep *this* set), or the set in which each lesson was last genuinely
   applied if you can determine it.
3. **Move** the `archive`/`merge`-absorbed entries to
   `lessons-archive.md` (full text preserved) and **delete** only the
   `drop` boilerplate.
4. Validate the result:

   ```bash
   python -m ai_router.validate_guidance_meta
   ```

### Step 7 — Re-measure and confirm under ceiling

```bash
python -m ai_router.guidance_report --check
```

A zero exit confirms the active tier is back under budget. Stamp the
freshness header (`--write-headers`) recording this set as the
`last-pruned-set`. From here, the steady-state lifecycle keeps the file
under budget on its own.

---

## Non-goals / invariants

- **Archive ≠ delete.** Every `archive`/`merge` move preserves the full
  text in `lessons-archive.md`; only `drop` boilerplate is removed, and
  only after operator review.
- **No unattended deletion.** Every step is operator-reviewed; the routed
  triage only ever *proposes*.
- **No vector-DB / embedding retrieval.** Markdown + `grep` (and
  `guidance_search --archive`) is the floor; embedding retrieval over the
  archive was considered and rejected as over-engineered at this scale.
- **Promotion stays orthogonal to archival.** A lesson can be kept active
  for many sets without ever being promoted; promotion moves a lesson
  *up* to `project-guidance.md`, archival moves it *out* of the
  always-load set. They are independent axes.

---

## Proof case

This recipe was dogfooded **read-only** against the
`dabbler-access-harvester` `lessons-learned.md` (~38.7k tokens against a
10k ceiling) in Set 064 Session 3. The triage proposal and the projected
post-remediation size are recorded in that set's
`s3-harvester-dogfood.md`. No edit was made to the harvester working
tree — executing the proposed moves is a harvester-side follow-on, not
the canonical set's job.
