# Set 066 — whole-set Path-Aware Critique prompt (dogfood instance)

> **Operator run instructions.** Open this repo in a **GitHub-Copilot** editor
> so each critic has real, path-aware workspace access. Paste everything below
> the `=== PROMPT ===` line **once under GPT-5.4** and **once under Gemini-Pro**
> — two independent passes from clean contexts. Save each raw verdict, then
> assemble both into `path-aware-critique.json` in this directory per
> `docs/path-aware-critique-schema.md` (one critique entry per provider; `>= 2`
> distinct providers; each entry content-non-trivial). This is the **dogfood**:
> Set 066 declares `pathAwareCritique: required`, so its own set-terminal
> `close_session` will not pass until this artifact is valid. Hand the verdicts
> back to the orchestrator (Claude) to fold into remediation before close.
>
> This is a concrete fill of the reusable template
> `ai_router/prompt-templates/path-aware-critique.md`.

---

=== PROMPT ===

You are an adversarial code-and-docs reviewer with **full read access to this
repository**. A session set — **Path-Aware Critique Policy** (Set 066, slug
`066-path-aware-critique-policy`) — has just finished its implementation work
across three sessions and is about to close and ship a PyPI release
(`dabbler-ai-router` 0.20.0). Your job is to find what is **wrong, risky,
incomplete, or internally inconsistent** in its changes — across code, tests,
and documentation — **before** it ships. Be a genuine devil's advocate: assume
the work is flawed and try to prove it. A rubber-stamp is a failure.

**Anti-bias instruction (load-bearing).** Do **not** rely on the summary below.
**Open and read the actual files yourself** and reason from what is on disk.
Where this description and the code/docs disagree, **the repository wins** —
call that out explicitly. For every claim of *current behavior* (what a function
reads/writes/enforces/defaults to; what a test asserts; what a doc says the code
does), verify it against the actual file before accepting it.

## What this set built (summary — verify it, do not trust it)

Set 066 ships a **tier-orthogonal** "Path-Aware Critique" per-set policy that
institutionalizes a manual, multi-provider, path-aware end-of-set review:

- **S1** — a `pathAwareCritique: none | advisory | required` per-set attribute
  (seeded in `spec.md`'s Session Set Configuration block, recorded **once at set
  start and immutable thereafter** as an `activity-log.json` entry with `kind:
  "path_aware_critique"`); a saved multi-provider critique-artifact contract
  (`path-aware-critique.json`) with a pure-Python runtime validator and a
  parallel JSON Schema; and a `P_set = any(P_task)` blast-radius predicate that
  *recommends* a level.
- **S2** — a **net-new**, tier-orthogonal content-aware **close-out gate** in
  `close_session` that, on the set-terminal close, enforces a valid
  multi-provider artifact when the recorded policy is `required` (hard-block in
  an interactive TTY, soft-warn headless) and warns when `advisory`.
- **S3** — the reusable prompt template, the workflow/guidance docs, this
  dogfood, and the 0.20.0 release.

The design source is `docs/proposals/2026-06-14-verification-surface-empirics/proposal.md`
(Candidate 1 + section 7 + its 2026-06-15 **Erratum**).

## Files to read (do not stop at the ones emphasized)

Code:
- `ai_router/path_aware_critique.py` — the attribute machinery (read/record/
  immutability), the artifact validator, and the S2 close-out gate validator.
- `ai_router/blast_radius.py` — the `P_set = any(P_task)` predicate + CLI.
- `ai_router/close_session.py` — the gate wiring (search for
  `path_aware_critique` / `validate_path_aware_critique_gate`); confirm it sits
  inside the fail-open guard and fires only on the set-terminal close.
- `ai_router/start_session.py` — the `--path-aware-critique` flag + the
  once-at-set-start capture wiring.
- `ai_router/dedicated_verification.py` — the **Lightweight-only** gate the S2
  gate deliberately mirrors but does **not** reuse (the erratum's basis).

Tests:
- `ai_router/tests/test_path_aware_critique.py`,
  `ai_router/tests/test_path_aware_critique_close_gate.py`,
  `ai_router/tests/test_path_aware_critique_schema.py`,
  `ai_router/tests/test_blast_radius.py`.

Docs + contract:
- `docs/path-aware-critique.schema.json`, `docs/path-aware-critique-schema.md`,
  `docs/path-aware-critique-schema-example.json`.
- `docs/ai-led-session-workflow.md` (the path-aware close-out gate section +
  *The end-of-set Path-Aware Critique stage*),
  `ai_router/docs/close-out.md`, `docs/planning/session-set-authoring-guide.md`,
  `docs/planning/project-guidance.md`, `docs/spec-md-schema.md`.
- `ai_router/prompt-templates/path-aware-critique.md`, `ai_router/CHANGELOG.md`,
  `pyproject.toml`, `ai_router/__init__.py`.
- This set's `spec.md`, `activity-log.json`, and `session-state.json`.

## Load-bearing claims to prove or disprove against the code

1. **Immutable once-at-set-start.** The durable `pathAwareCritique` record is
   written once and **cannot be silently downgraded** mid-set: after a record
   exists, a later `start_session --path-aware-critique none` is a no-op and
   cannot disarm a `required` gate. Verify `resolve_and_record_path_aware_critique`
   + `has_path_aware_critique_record` + the `start_session.py` wiring.
2. **Validator/Schema parity.** The pure-Python
   `validate_path_aware_critique_artifact` accepts exactly the same envelope as
   the JSON Schema `docs/path-aware-critique.schema.json` (closed top-level key
   set, required fields, types), with the **only** intended divergence being the
   `>= 2` **distinct**-providers rule JSON Schema cannot express. Find any real
   parity gap.
3. **Multi-provider is distinct-provider.** Two critique entries from the *same*
   provider are rejected (`single-provider`); only `>= 2` distinct providers
   pass. Verify the provider-distinctness logic.
4. **Gate posture + scope.** The close-out gate fires **only** on the
   set-terminal close; `required` → hard-block in an interactive TTY / soft-warn
   headless (and under `--accept-suggestions`); `advisory` → always warn, never
   block; `none` → skip. Verify in `close_session.py` and
   `validate_path_aware_critique_gate`.
5. **Fail-open.** The gate never wedges close-out: any import-time or internal
   error skips the gate (non-block direction) rather than crashing. Confirm the
   module import sits **inside** the broad try/except (the S2 round-1 fix).
6. **Net-new, not reuse.** The `dedicated_verification` gate is Lightweight-only
   (gates on `verificationMode`) and does not cover the Full-tier close path, so
   the S2 wiring is genuinely net-new — the proposal's original "reuse the
   dedicated gate" claim was false (the erratum). Verify against both files.
7. **Tier-orthogonal.** `validate_path_aware_critique_gate` consults only the
   tier-independent `pathAwareCritique` record and behaves identically on Full
   and Lightweight (no tier branch). Verify.
8. **Predicate is advisory-only.** `ai_router.blast_radius` implements
   `P_set = any(P_task)` and only **recommends**; nothing hard-auto-sets the
   attribute from it. Verify the module + CLI output.
9. **ASCII-only output.** Every gate/CLI/terminal string is cp1252-safe (no
   characters that crash a Windows console). Check the gate corrective text and
   the blast-radius CLI.
10. **The dogfood is real.** This set's `spec.md` declares
    `pathAwareCritique: required`, its `activity-log.json` carries the durable
    `required` record, and its own close is genuinely gated (not a dry-run).
    Confirm the spec config, the durable record, and that the gate reports
    `applicable=True` for this set.
11. **No doc/code drift.** The schema doc, authoring guide, workflow doc,
    close-out doc, and CHANGELOG describe the **actual** behavior — no claim of
    current behavior that the code does not implement (a known defect class:
    prose carried into a successor doc that the code never backed).
12. **Release coherence.** The version is bumped consistently
    (`pyproject.toml` + `ai_router/__init__.py` both `0.20.0`), the CHANGELOG
    entry matches what shipped, and the new prompt template is actually packaged
    (`[tool.setuptools.package-data]` includes `prompt-templates/*.md`).

## What else to attack

Correctness (off-by-one, wrong conditionals, fail-open/closed mistakes,
ordering), contract/cross-artifact drift, completeness (claimed-but-unimplemented
or wired-but-untested paths), false-confidence tests (a test that passes without
exercising the behavior it names), and anything unforeseen (hidden coupling,
cost/encoding hazards, a wrong default, a stale reference).

## Output format

Begin with a one-line **VERDICT**: `VERIFIED` (no significant issues) or
`ISSUES_FOUND`. Then:

- If `VERIFIED`: 1–3 sentences naming **which files you actually read** and
  **which of claims 1–12 you checked** and why you are confident. A bare "looks
  good" is a failed review.
- If `ISSUES_FOUND`: a **Findings** list. For each: **Severity**
  (Critical/Major/Minor), **Category** (correctness / contract-drift /
  completeness / false-confidence / other), **Location** (`file:line` or file +
  symbol), and **Description** (what is wrong, the ground truth you read that
  proves it, and the concrete fix).

Report only defects you can substantiate from files you actually opened.
