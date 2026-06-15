# Path-Aware Critique Policy Spec

> **Purpose:** Ship **Path-Aware Critique** as a first-class, **tier-orthogonal**
> per-set policy — a `pathAwareCritique: none | advisory | required` attribute, a
> blast-radius predicate that *recommends* `required`, a saved multi-provider
> critique-artifact contract, and a **net-new** content-aware close-out gate —
> institutionalizing the **manual** operator-run path-aware review (GitHub Copilot
> driving GPT-5.4 + Gemini-Pro over the repo) the team already practices, and
> shipping it via an `ai_router` PyPI release. The automated tool-loop adapter and
> the forward A/B are deliberately **later sets** (067, 068).
> **Created:** 2026-06-15
> **Session Set:** `docs/session-sets/066-path-aware-critique-policy/`
> **Prerequisite:** Set 065 (`065-verification-surface-empirics`) complete — its
> cross-provider-verified proposal is the design source.
> **Workflow:** Orchestrator → AI Router → Cross-provider verification

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
pathAwareCritique: required   # Set 066 S3: this set dogfoods its own gate (see rationale)
prerequisites:
  - slug: 065-verification-surface-empirics
    condition: complete
```

> Rationale: `ai_router` tooling + workflow gate + docs; **no UI surface in this
> set** (surfacing the attribute in the Session Set Explorer is deferred), so no
> UAT/E2E gate. **Full tier** because each session is cross-provider verified —
> and, fittingly, this set *dogfoods* the very manual path-aware practice it
> institutionalizes. It ships a **PyPI `ai_router` release** so consumer repos
> get the new close-out gate; **no Marketplace bump** (no extension change).
>
> **`pathAwareCritique: required` (added Session 3).** The set that ships the
> Path-Aware Critique gate eats its own dogfood: its set-terminal close enforces
> the very gate it builds. The blast-radius predicate scores this set
> `required` (it touches `close_session.py` wiring and shared schema docs), and
> S1/S2 started before the attribute existed, so the durable record was `none`;
> Session 3 records `required` directly via the sanctioned writer
> (`record_path_aware_critique`) as an **operator-initiated arming** — an upgrade
> (none -> required), the safe direction the immutability rule protects (it
> blocks silent *downgrades* that would disarm a gate, not an explicit arming).
> S3 therefore cannot close until a valid multi-provider `path-aware-critique.json`
> exists at this set's root — the first real instance of the practice.

---

## Project Overview

### Background

Set 065 produced a cross-provider-verified proposal recommending Path-Aware
Critique adoption (`docs/proposals/2026-06-14-verification-surface-empirics/proposal.md`).
A pre-spec **round-2 path-aware panel** (GPT-5.4 + Gemini-Pro + an independent
Opus, run manually through Copilot — artifacts in that proposal dir as
`066-critique-*.md`) **dissolved** the central scoping fork and converged on a
**three-set roadmap**:

- **066 (this set)** — ship the **manual** Path-Aware Critique policy/feature.
- **067** — build + capability-validate the first-party tool-loop **adapter**
  (read-only `pull_route()` seam + Anthropic/OpenAI/Gemini bindings) and run
  **Experiment A** (capability).
- **068** — `run_test` sandbox + **Experiment B** (cadence) + the routed
  **keep/demote/retire** decision + the **contract-test/CDC gate**.

### The reframe that scopes this set

**Shipping Path-Aware Critique does *not* require the adapter.** The feature is a
per-set attribute + a close-out gate + the **manual operator flow** — the very
flow that produced *this set's own* design critiques (and the 065 proposal's
erratum). It is proven (12 unique real defects incl. two Criticals in the S1
bake-off) and already practiced by the harvester repo. 066 makes it **canonical,
enforceable, and releasable**; the adapter is later *automation behind an
already-shipped surface* (067).

### The erratum correction (load-bearing for scope)

The 065 proposal claimed Path-Aware Critique could "reuse the `dedicated-sessions`
content-aware close-out gate." Verified false: that gate is **inert on Full tier**
(`ai_router/dedicated_verification.py` ~L441; `ai_router/close_session.py` ~L1709
wires it only for Lightweight `verificationMode`). So the close-out wiring here is
**net-new**, not free reuse. The feature itself is **tier-orthogonal** (valid on
both tiers); the wiring is net-new because the existing gate never covered the
Full-tier close path — not because the attribute is Full-tier-specific.

### Scope (in)

- The tier-orthogonal `pathAwareCritique: none | advisory | required` per-set
  attribute (seeded in spec config, recorded once at set start, immutable after).
- A `P_set = any(P_task)` **blast-radius predicate** helper that *recommends* a
  value (advisory recommendation; the operator confirms — not a hard auto-set).
- A saved **multi-provider critique-artifact** contract + validator (≥2 providers,
  content-non-trivial; raw verdicts, never edited after written).
- A **net-new**, tier-orthogonal **content-aware close-out gate** that enforces
  `required`.
- Canonical **manual-workflow docs** + a reusable **prompt template**.
- Focused **tests**, a **dogfood** pass on this set, and a **PyPI release**.

### Non-goals (out — explicitly deferred)

- The first-party tool-loop **adapter** / `pull_route()` seam, and the
  OpenAI/Gemini tool-loop **bindings** → **067**.
- The disposable-worktree **`run_test` sandbox** → **068**.
- **Experiment A** (capability) → **067**; **Experiment B** (cadence) → **068**.
- The routed **keep / demote / retire** decision → **068** (066 leaves
  per-session routed verification **unchanged**).
- The **contract-test / CDC gate** → **068**.
- **Explorer / extension UI** for the attribute, and any **Marketplace** bump →
  future / optional.

### Standards

- **Tier-orthogonal:** the attribute and gate work on both Full and Lightweight.
- **Routed verification stays UNCHANGED** — 066 does not touch routed's status.
- **ASCII-only** CLI/terminal output (project-guidance Code Style).
- The saved critique artifact follows verification-artifact discipline: **raw,
  multi-provider, never edited after written**.
- Close-out fail-posture mirrors the Set 057 Q6 pattern: **hard-block in an
  interactive TTY, soft-warn headless**.

---

## Sessions

### Session 1 of 3: Policy surface + blast-radius predicate + artifact contract

**Steps:**
1. Register session start; read `project-guidance.md`, `lessons-learned.md`,
   `session-set-authoring-guide.md`, the 065 proposal (§1, §5 Candidate 1, §7,
   **Erratum**), and this roadmap's `066-critique-*.md` panel records.
2. Add the tier-orthogonal **`pathAwareCritique: none | advisory | required`**
   per-set attribute: extend the Session Set Configuration schema + the
   spec-config parser; implement the **seed → record-once-at-set-start** pattern
   (spec seed recorded to `activity-log.json` / state at first `start_session`;
   **immutable** after first record), mirroring `verificationMode`. Document in
   `session-set-authoring-guide.md` and the spec-config schema doc.
3. Implement the **`P_set = any(P_task)`** blast-radius predicate helper in
   `ai_router`: classify a set's changed/planned surface (cross-artifact /
   shared-schema / wiring / index changes) and **recommend** a `pathAwareCritique`
   value — advisory recommendation, ASCII output, **not** a hard auto-set.
4. Define + validate the saved **multi-provider critique artifact** contract
   (e.g. `path-aware-critique.json`): per-provider entries (provider / model /
   verdict / findings), ≥2 providers, content-non-trivial; a validator + schema
   doc.
5. Unit tests: attribute parse / seed / record / immutability; predicate
   classification; artifact validator (accept valid, reject single-provider /
   trivial).
6. Cross-provider verification; author `disposition.json` (routed
   `next_orchestrator`); commit + push; `close_session`.

**Creates:** the predicate helper module, the artifact schema + validator, the
schema doc, the new tests.
**Touches:** the spec-config parser, `session-set-authoring-guide.md`, the
session-config / state-schema docs.
**Ends with:** the attribute parses and records once (immutable); the predicate
recommends a value; the artifact validator accepts valid / rejects invalid; tests
green; session cross-provider **VERIFIED**.
**Progress keys:** `attribute-added`, `predicate-implemented`,
`artifact-contract-defined`, `s1-verified`.

---

### Session 2 of 3: Net-new content-aware close-out wiring

**Steps:**
1. Register; read S1 deliverables, `ai_router/close_session.py` structure, and
   the existing `dedicated_verification` gate (to **mirror its shape, not reuse
   it** — it is Lightweight-only).
2. Implement the **tier-orthogonal content-aware close-out check**: at a
   **set-terminal** close, when the recorded `pathAwareCritique == required`,
   confirm a **valid multi-provider critique artifact** exists and is
   content-non-trivial; `advisory` → non-blocking warn; `none` → skip. **Fail
   posture:** hard-block in an interactive TTY, soft-warn headless. This is
   **net-new** wiring reaching the Full-tier close path.
3. Wire the check into the `close_session` gate list; confirm it composes with
   the existing gates; ASCII output.
4. Tests: gate fires / passes / skips per attribute value **×** tier; fail-posture
   (TTY vs headless); a missing or trivial artifact blocks a `required` terminal
   close; `advisory` never blocks.
5. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Creates:** the close-out gate function + its tests.
**Touches:** `ai_router/close_session.py`, `ai_router/docs/close-out.md`,
`docs/ai-led-session-workflow.md`.
**Ends with:** a `required` terminal close is blocked without a valid
multi-provider critique artifact; `advisory` warns; `none` and both tiers behave
correctly; tests green; session **VERIFIED**.
**Progress keys:** `gate-implemented`, `gate-wired`, `fail-posture-tested`,
`s2-verified`.

---

### Session 3 of 3: Docs, prompt template, dogfood, release

**Steps:**
1. Register; read the S1 + S2 deliverables.
2. Author the **canonical manual Path-Aware Critique workflow** docs and a
   **reusable prompt template** (`ai_router/prompt-templates/path-aware-critique.md`,
   generalized from this roadmap's `066-decomposition-*-prompt*.md`): operator
   runs the Copilot-driven GPT + Gemini review over the repo and saves the
   multi-provider verdicts as the artifact. Update
   `docs/ai-led-session-workflow.md` (new end-of-set stage), `project-guidance.md`,
   and `session-set-authoring-guide.md`.
3. **Dogfood:** run the manual path-aware critique on **this set's own** changes,
   save it as a real critique artifact, and confirm the S1 validator + S2 gate
   accept it (exercised via the gate's test path / a dry-run — this set is the
   first real instance of the practice).
4. Finalize tests; bump `ai_router` version; ship the **PyPI release** following
   the publish runbook (incl. the green-`Test`-workflow release prerequisite on
   the tagged SHA). Routed verification stays **unchanged**. Record the publish
   run id post-release.
5. Author `change-log.md`; route the **next-session-set recommendation** (expected
   **067** = adapter + Experiment A); cross-provider verification; `close_session`;
   set closes.

**Creates:** the prompt template, the workflow docs, the dogfood critique
artifact, `change-log.md`.
**Touches:** `ai_router` version + CHANGELOG, the workflow / guidance docs.
**Ends with:** the manual Path-Aware Critique is canonical, tested, and released;
this set dogfooded its own gate; PyPI published; the set is closed.
**Progress keys:** `docs-written`, `prompt-template-shipped`, `dogfooded`,
`released`, `change-log-written`, `s3-verified`.

---

## End-of-set deliverables

- The tier-orthogonal `pathAwareCritique` attribute + the `P_set` blast-radius
  predicate helper (S1).
- The multi-provider critique-artifact contract + validator + schema doc (S1).
- The net-new tier-orthogonal content-aware close-out gate + tests (S2).
- The canonical manual-workflow docs + reusable prompt template (S3).
- The dogfood critique artifact for this set (S3).
- A `ai_router` **PyPI release** carrying the gate (S3).
- `change-log.md` (S3).

A shipped, tested, tier-orthogonal Path-Aware Critique policy enforceable at
close-out via the proven manual flow — with the automated adapter (067) and the
routed-fate / cadence study (068) sequenced as the follow-on sets.
