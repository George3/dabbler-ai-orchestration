# Set 064 Session 1 — Audit & Design-Lock

> **Session:** 1 of 4 (audit-only; touches no shipping code).
> **Date:** 2026-06-14
> **Orchestrator:** Claude Code (claude-opus-4-8), provider anthropic.
> **Goal:** Ground the design in the real state of every affected surface
> and lock D1–D8 with file-level evidence.
> **Companion:** `s1-consult/` (cross-provider mechanics consult +
> synthesis).

---

## 1. Measured overhead (Step 1)

Byte / line / estimated-token size of the always-loaded guidance files,
measured 2026-06-14 across every repo under `~/source/repos`. Token
estimate = `chars / 4` (the heuristic D1 will ship).

| Repo | File | Bytes | Lines | ~Tokens |
|---|---|---:|---:|---:|
| **dabbler-access-harvester** | lessons-learned.md | 154,713 | 2,468 | ~38,500 |
| | project-guidance.md | 60,411 | 1,011 | ~15,000 |
| | **combined** | **215,124** | **3,479** | **~53,500** |
| **dabbler-platform** | lessons-learned.md | 136,500 | 1,846 | ~34,000 |
| | project-guidance.md | 67,133 | 1,100 | ~16,700 |
| | **combined** | **203,633** | **2,946** | **~50,800** |
| dabbler-homehealthcare-accessdb | lessons-learned.md | 36,211 | 582 | ~9,000 |
| dabbler-pdf | lessons + guidance | 38,425 | 697 | ~9,600 |
| form-portal | lessons + guidance | 41,590 | 791 | ~10,400 |
| html-json-form-app | lessons + guidance | 40,823 | 767 | ~10,200 |
| dabbler-access-migration-orchestrator | lessons + guidance | 6,563 | 124 | ~1,600 |
| **dabbler-ai-orchestration (this repo)** | lessons-learned.md | 12,060 | 226 | ~3,000 |
| | project-guidance.md | 4,434 | 100 | ~1,100 |
| | **combined** | **16,494** | **326** | **~4,100** |

**Key findings:**

- **TWO repos are over budget, not one.** The spec named only the
  harvester (151 KB lessons). `dabbler-platform` is essentially tied at
  ~203 KB / ~50.8k tokens combined. The D7 cross-repo notice must target
  **both**.
- The cost lands in **consumer** repos, not here. This curator repo is
  ~4.1k tokens combined because curator work is low-volume; the harvester
  and platform pay ~50k tokens of context tax on **every** session start.
- `dabbler-access-harvester-old` (39 KB / 24 KB) is a stale legacy copy —
  excluded from the live set above.
- The spec's narrative figures (harvester "151 KB / 59 KB") are rounded
  earlier measurements; the table records the fresh 2026-06-14 values
  (154,713 / 60,411 bytes). Not an inconsistency — a measurement
  timestamp difference; the audit figures supersede.

**Collapsed-to-pointer vs. live prose:**

| Repo | File | Entries | Promotion/supersession markers |
|---|---|---|---|
| this repo | lessons-learned.md | 12 (`## H2`) | 3 promoted-pointers, rest live |
| harvester | lessons-learned.md | ~34 (`##`/`###` mix) | 25 "promoted" mentions, 2 "superseded" |
| harvester | project-guidance.md | 3 `##` + 14 `###` | 4 / 1 |
| platform | lessons-learned.md | **81** (`## H2`) | 9 / 0 |
| platform | project-guidance.md | 2 `##` + 16 `###` | 9 / 0 |

The platform's 81 distinct lessons in 1,846 lines (~22 lines each) with
only 9 promotion markers confirms near-monotonic growth. This grounds the
D6 triage-helper sizing: the helper must classify ~34–81 entries per file.

---

## 2. Read-path audit (Step 2)

Every instruction that names `lessons-learned.md` / `project-guidance.md`
as always-load (session-start) reading. **D4 must add an "exclude
`lessons-archive.md` from always-load" clause at each *set* site** (those
that list the files as a required-reading set).

**Always-load (must be touched by D4):**

| # | File | Lines | Context |
|---|---|---|---|
| 1 | `CLAUDE.md` | 112–114 | "When curator work runs as a session set" — names all three as required reading (a SET) |
| 2 | `AGENTS.md` | 111–113 | same (engine twin) |
| 3 | `GEMINI.md` | 111–113 | same (engine twin) |
| 4 | `docs/ai-led-session-workflow.md` | 35–37 | top-level "read before every session" |
| 5 | `docs/ai-led-session-workflow.md` | 53–54 | Overview diagram "reads ..." |
| 6 | `docs/ai-led-session-workflow.md` | 1042–1044 | Step 0 numbered read list |
| 7 | `docs/ai-led-session-workflow.md` | 2701–2703 | Rule 8 "mandatory pre-session context" |
| 8 | `docs/quick-start.md` | 152–153 | "happy path — Full tier" Step 0 |
| 9 | `docs/quick-start.md` | 225–226 | "Run your first session" Step 0 |
| 10 | `docs/planning/project-guidance.md` | 68–69 | Workflow Expectations preamble |

**Post-session (not always-load, but name both files — relevant to D5/D8
text, NOT to the exclude-from-always-load edit):**

- `docs/ai-led-session-workflow.md:84` — Overview diagram, Step 9
  reorganization candidates.
- `docs/ai-led-session-workflow.md:2041–2042` — Step 9 reorganization
  review (last-session-only). **This is where the "promote within N sets
  or archive" framing, if present anywhere, must be reconciled with D5's
  "promotion is orthogonal to archival."**

**Bundle note:** the consumer-bootstrap templates do **not** currently
name the guidance files (they point at external GitHub URLs for the tier
model / workflow). So D7's new templates introduce the always-load text
into new repos for the first time — they must carry the archive-exclusion
clause from birth.

---

## 3. Write-path audit (Step 3) — the D3 citation seam

How `close_session` runs today (file: `ai_router/close_session.py`):

- **Runs after commit+push.** Gate checks (`ai_router/gate_checks.py`)
  include `check_working_tree_clean` and `check_pushed_to_remote`,
  evaluated **before** the close completes.
- **Writes after the gates pass:** `session-state.json` via
  `_flip_state_to_closed` (`ai_router/session_state.py:1441`), and
  appends events to `session-events.jsonl` via `append_event`
  (`ai_router/session_events.py:203`): `closeout_requested`,
  optionally `closeout_force_used` / `verification_completed`, then
  `closeout_succeeded` (or `closeout_failed`). So the tree is **already**
  left dirty by one tracked-file write (`session-state.json`) post-gate
  today; the operator commits that separately.
- **Does NOT write `change-log.md`** — the work agent authors it before
  close; `check_change_log_fresh` only validates freshness on the final
  session.
- **`disposition.json`** (`ai_router/disposition.py`, schema
  `docs/disposition-schema.md`) is authored by the work agent before
  close and already round-trips fields (e.g. `verification_verdict`) into
  the `closeout_succeeded` event. **Adding a field here is the
  established extension pattern.**
- **Activity log:** `ai_router/session_log.py:165` `log_step(...)` is the
  append helper; there is a precedent for typed entries (`kind:
  "verification_mode"`).
- **TTY-vs-headless prompting exists** (Set 057 Q6 + Set 048 soft gate):
  hard-block on interactive TTY, soft-warn on non-TTY / `--accept-suggestions`
  (`close_session.py` ~1599–1730). D3 does **not** need it — citation is a
  passive disposition field, not a prompt.
- **Close is Python-CLI-only.** The VS Code extension does not invoke
  close_session (it only reads the resulting state).

**Locked seam (see D3 below):** the work agent runs a new
`cite_lessons` helper as part of the final commit (so the markdown
`last-used-set` edit lands inside the committed/pushed work and the tree
stays clean), records the same ids in `disposition.lessons_cited`, and
`close_session` reads that field only to record a `lessons_cited` entry
in the `closeout_succeeded` event (and validate the ids exist). No
post-gate markdown mutation by close_session.

---

## 4. Promotion convention + bootstrap bundle audit (Step 4)

**Promotion / collapse convention (current):**

- Rule lives in `docs/planning/lessons-learned.md:9–14`: *"When a lesson
  has proven itself in two or more different contexts, propose promoting
  it to `project-guidance.md` … Never delete a lesson; only move it."*
  (the "never delete; only move" rule is line 13).
- Current shrink mechanism = promotion collapse to a `- **Promoted.** …`
  pointer. It only fires on promotion and only ever collapses; it never
  evicts a stale / superseded / encoded-into-automation lesson.
- **Current lesson serialization:** `## H2 Heading`, then the four-bullet
  `Context / Failure or friction / Lesson / Action for future sessions`
  body. D2's metadata trailer must sit directly under the `##` heading
  without disturbing this body.
- **No "promote within N sets or archive" rule exists anywhere yet** —
  it was an operator first-draft proposal the consult rejected; D5 simply
  must not introduce it, and must add the "promotion is orthogonal to
  archival" statement.

**Consumer-bootstrap template bundle** (`docs/templates/consumer-bootstrap/`):

- Current files: `spec.md.template`, `session-state.json.template`,
  `start-here.md.template`, `getting-started.md.template`,
  `engine-file.shared-body.md`, `engine-file.{claude,agents,gemini}-tail.md`,
  `README.md`. **No `lessons-learned` / `project-guidance` / `archive`
  template exists yet.**
- Packaging: `tools/dabbler-ai-orchestration/esbuild.js` copies the bundle
  `docs/templates/consumer-bootstrap/ → dist/templates/consumer-bootstrap/`
  on every build, and **fails the build if a required file is missing**
  (the `required[]` list, esbuild.js ~19–32).
- Expansion: `tools/dabbler-ai-orchestration/src/utils/consumerBootstrap.ts`
  (`loadTemplateBundle` / `renderConsumerBootstrap` /
  `renderStructureBootstrap`), driven by three converging callers
  (`gitScaffold.ts`, the Getting Started form, `sessionGenPrompt.ts`).

**Consequence for D7/D8:** adding the three new templates means editing
`esbuild.js`'s `required[]` list AND `consumerBootstrap.ts`'s
`TemplateBundle` loader/interface — i.e. **an extension code change →
a Marketplace bump in S4**, even though the D3 citation keystone is
CLI-only. This refines the spec's "extension touched only if S1 finds the
citation step needs a command surface": the citation step does **not**,
but the D7 template bundle work **does**.

---

## 5. Locked design — D1–D8

Direction was locked by the prior 2026-06-14 consult (summarized in the
spec). Mechanics locked here, confirmed by the S1 cross-provider consult
(`s1-consult/`, no DISAGREE on any deliverable). Items marked **[+consult]**
were added/strengthened by the S1 consult.

### D1 — Guidance cost reporter
- CLI: `python -m ai_router.guidance_report`. ASCII-only output.
- Token estimator: `ceil(chars / 4)` heuristic — zero deps, deterministic;
  framed as a tokens-read-per-session proxy, not a billing number.
- Reports per-file + combined bytes / lines / est-tokens. **Ceilings are
  enforced per active file** (the D5 `lessons-learned` and
  `project-guidance` values); the combined total is informational only.
- **[+consult] Header stamping is opt-in (`--write-headers`); the default
  invocation is a read-only report.** Prevents every run from dirtying
  tracked docs. The freshness header is a single stable marker block
  (one format, one placement: top of the file under the purpose preamble)
  recording last-pruned set, current bytes/tokens, configured ceiling,
  generated date.
- **[+consult] `--check` mode** returns non-zero when a file is over its
  ceiling (for any consumer who wants a hard CI gate).
- Config: a new `guidance:` block in `router-config.yaml`
  (ceilings + disuse window).

### D2 — Per-lesson metadata schema
- Serialization: an **HTML-comment trailer** immediately under each `##`
  heading, **double-quoted** values, fixed canonical field order,
  omit-empty:
  ```
  <!-- lesson: id="L-064-1" added-set="064" last-used-set="064" status="active" scope="portable" -->
  ```
- Fields: `id`, `added-set`, `last-used-set`,
  `status` (`active|archived|promoted`), `superseded-by`, `encoded-in`,
  `scope` (`portable|repo-specific`). Multi-value fields comma-separated
  inside the quotes.
- **[+consult] ID governance:** `id` = `L-<set>-<seq>` (e.g. `L-064-1`),
  assigned once, **permanent across heading renames**. On **merge** the
  survivor keeps its id; absorbed entries get `status="archived"` +
  `superseded-by="<survivor>"` and move to the archive. IDs never
  regenerated casually.
- Ship a **parser + formatter** (round-trips the trailer, normalizes
  order/spacing) and **[+consult] a validator**
  `python -m ai_router.validate_guidance_meta` (CI / pre-commit wireable)
  that rejects malformed trailers.
- Rationale: invisible in rendered markdown, grep-able, human-editable.
  YAML block (too heavy/indentation-fragile) and visible trailer (prose
  clutter) both rejected by both providers.

### D3 — Citation-at-close keystone (THE keystone)
- The work agent lists instrumental lesson ids in a new
  `disposition.json` field `lessons_cited: ["L-064-1", ...]`.
- The markdown `last-used-set` update is applied by a helper the agent
  runs as part of the final commit:
  `python -m ai_router.cite_lessons --set <N> <id> <id> …`. The metadata
  edit therefore lands **inside the committed/pushed work** and the tree
  stays clean (git blame on a metadata line points at the commit that
  used the lesson).
- `close_session` reads `disposition.lessons_cited` only to record a
  `lessons_cited` field in the `closeout_succeeded` event. **No markdown
  mutation by close_session.**
- **[+consult] close_session validates** that each cited id exists in a
  guidance file; an unknown id is recorded as a non-blocking mismatch in
  the event (not silently accepted).
- **No-citation default is fully inert** — empty/absent list does
  nothing; silence never auto-evicts.
- **[+consult] Reactivation loop:** `cite_lessons` on an `archived` id
  updates its `last-used-set` in the archive **and** warns "cited id X is
  archived — consider reactivating," surfacing it for operator move-back.
- No close-time TTY prompt (passive field). Stays Python-CLI-only.

### D4 — Active / archive split
- `lessons-learned.md` = always-load **active** tier, capped to the D5
  ceiling. New sibling `lessons-archive.md` = **never auto-loaded**,
  grep-on-demand (+ `guidance_search --archive`).
- Move rule redefined: **"never delete; move active → archive."**
- Add an explicit "`lessons-archive.md` is NOT in the always-load set"
  clause at the **10 always-load sites** in §2.
- `project-guidance.md` gets a **ceiling + freshness header only — no
  archive sibling** (smaller, higher-signal by design; revisit only if
  it later breaches its ceiling).

### D5 — Steady-state triggers + backstop ceiling
- Archive a lesson when **ANY** of: `superseded-by` set; `encoded-in`
  names a live test/lint/guard/template; subsystem retired; OR no
  `last-used-set` activity for **N sets AND not referenced by active
  guidance**.
- **Disuse window N = 20 (default, configurable).** The S1 consult split
  (gpt 12 / gemini 20); locked at 20 because the trigger is gated by
  "not referenced," is operator-reviewed (never automatic), and
  rare-but-critical lessons can fire once in ~50 sets — and the
  over-budget case is D6's job, not the steady-state window's. Operators
  can lower it without a code change.
- **[+consult] "Referenced by active guidance"** = the lesson's `id`
  appears in `project-guidance.md`, or in another active lesson's
  `superseded-by` / `encoded-in`, or in active prose. The sweep / triage
  tooling builds this id dependency graph across **both** files before
  proposing any archive.
- Ceilings (hard backstop only): active `lessons-learned.md` **10,000
  tokens (~40 KB)**, `project-guidance.md` **6,000 tokens (~24 KB)** —
  both confirmed by both providers. Over ceiling ⇒ a sweep is **required
  before adding** new content; the sweep archives by the evidence rules
  above, not by raw length.
- **[+consult] Backstop enforcement seam (non-blocking, mirrors the Set
  053 drift advisory):** (a) `start_session`/`close_session` print a soft
  over-ceiling advisory (fail-open, never changes exit status); (b)
  `guidance_report --check` is the opt-in hard CI gate.
- **DELETE** the "promote within 10 sets or archive" rule (it does not
  exist yet — D5 must not introduce it) and state that **promotion is
  orthogonal to archival.**

### D6 — Backlog-remediation recipe (one-time, over-budget repos)
- Portable doc under `docs/` + a **routed-triage helper** (warranted:
  two repos at ~150–200 KB). Recipe combines:
  - (a) routed **bulk triage** classifying every entry
    keep-active | archive | promote | merge, operator-reviewed;
  - (b) a **supersession-merge dedup** pass;
  - (c) **archive-bankruptcy as an explicit, heavily-gated opt-in**
    (**[+consult]**: requires opt-in + projection-first + repo-owner
    signoff; not a co-equal default) — wholesale move to archive,
    re-surface on citation;
  - (d) **seed `last-used-set`** for survivors so the steady-state
    mechanism inherits a baseline.
- S3 dogfoods it **read-only** against the harvester's 154 KB
  `lessons-learned.md`, producing a projected post-remediation size; no
  edit to the harvester tree.

### D7 — Ship to consumers
- Add to the bundle: metadata-aware `lessons-learned.md.template` +
  `project-guidance.md.template` + empty `lessons-archive.md.template` +
  the lifecycle-doc reference. Update `esbuild.js` `required[]` and
  `consumerBootstrap.ts` loader/interface → **Marketplace bump in S4.**
- New templates carry the always-load text **with the archive-exclusion
  clause from birth.**
- Cross-repo notice (established pattern) pointing **both** over-budget
  consumers (harvester **and** platform) at the D6 recipe.

### D8 — Docs + release
- New canonical **engine-agnostic** lifecycle doc under `docs/` (per the
  Documentation-authority principle).
- Update authoring guide, `ai-led-session-workflow.md`,
  `project-guidance.md` rule text, quick-start, bootstrap docs.
  CLAUDE/AGENTS/GEMINI reference the canonical doc only (no sole-sourced
  fact).
- **PyPI bump** (keystone lands in `ai_router`) + **Marketplace bump**
  (D7 touches the extension build). Through the green-Test gate.

---

## 6. S2 ship-ordering (adopted from the consult)

Build tools before policy/docs so repos never hand-edit inconsistent
metadata. **S2 order:** D2 parser/formatter/validator → D3 cite path →
D1 reporter + `--check` + `guidance_search` → D4 split → D5 policy text.

---

## 7. Discrepancies surfaced (for the operator)

1. **Two over-budget repos, not one** — `dabbler-platform` (~50.8k
   tokens) is essentially tied with the harvester. D7 notice targets both.
2. **The spec's referenced 2026-06-14 consult was not in the repo** —
   `s1-consult/` did not exist before this session. The S1 mechanics
   consult (this session) is the consult of record; the direction is
   re-summarized from the spec, unchanged.
3. **D7 forces a Marketplace bump** the spec treated as "not expected" —
   the citation keystone is CLI-only, but the template-bundle work is an
   extension change. S4 carries both PyPI and Marketplace bumps.
4. **Pre-existing uncommitted change:** `docs/planning/lessons-learned.md`
   carried 3 post-063 lessons (added, not committed) at session start —
   not produced by this session. They are legitimate 063 lessons that an
   063 close-out left uncommitted. The working-tree-clean close gate
   cannot pass with them dirty, so this session commits them (clearly
   labeled). One of them ("A Replacement Doc Inherits The Retired Doc's
   Claims At Its Peril") tripped the `drift_guard` stale-framing check via
   the bigram "no Python" in `(no Python runtime reader exists)` — a false
   positive (about `ai_router` having no budget.yaml reader, unrelated to
   the Lightweight tier). Reworded to "no `ai_router` runtime reader
   exists" (same remediation pattern as commit 05ca267); `test_drift_guard`
   is green again.

---

## 8. End state

D1–D8 answered with file-level evidence and a cross-provider mechanics
consult (no DISAGREE). No shipping code touched (audit-only — the only
non-artifact edit is the one-bigram drift-guard reword in §7.4). Suite
baseline at close: **Python 1221 passed / 1 skipped / 0 failed**
(`pytest -q`, 2026-06-14); TS suite unchanged by S1 (no TS touched; the
2 tracked Set-026 failures are the known baseline).
