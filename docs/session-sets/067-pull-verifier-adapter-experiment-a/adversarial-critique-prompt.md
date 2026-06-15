# Adversarial critique prompt — Set 067 (pull-verifier adapter + Experiment A + producer)

> **For the operator.** Point a path-aware reviewer (GPT-5.4 and Gemini-2.5-Pro,
> each with **read access to this repository**) at the prompt in the
> `=== PROMPT ===` block below. Run it **once per provider, from a clean
> context**, and save each raw verdict as its own markdown file
> (e.g. `set-067-critique-gpt.md`, `set-067-critique-gemini.md`). This is a
> whole-**set** adversarial review (all four sessions), separate from the
> per-session routed verification and from this set's own
> `path-aware-critique.json` close-out artifact.
>
> **Scope:** the entire Set 067 body of work, at git `master` (S1–S4):
> the `pull_route` adapter + three provider bindings, the Experiment A capability
> study, and the S4 opt-in producer + the `ai_router` 0.21.0 release.

---

=== PROMPT ===

You are an adversarial code-, experiment-, and docs-reviewer with **full read
access to this repository**. A four-session body of work (**Set 067 —
first-party pull-verifier adapter + Experiment A capability study + opt-in
path-aware-critique producer**) has just finished and shipped an `ai_router`
0.21.0 release. Your job is to find what is **wrong, overclaimed, unsound,
incomplete, or internally inconsistent** in it — across code, the experiment,
and the documentation — and to do so **before** anyone trusts the result. Be a
genuine devil's advocate: assume the work is flawed and try to prove it. A
rubber-stamp is a failure.

**Anti-bias instruction (load-bearing).** Do **not** rely on the summaries
below. **Open and read the actual files yourself** and reason from what is on
disk. Where a summary, comment, or doc disagrees with the code or the data,
**the repository wins** — call it out explicitly. For every claim of *current
behavior* (what a function reads/writes/enforces/defaults to; what a test
asserts; what a result file reports), verify it against the actual file before
accepting it.

## What this set produced (verify each claim; do not trust this summary)

1. **The adapter (`ai_router/pull_verifier.py`, S1–S2).** A `route()`-parallel
   agentic seam `pull_route()` in which the verifier drives a read-only tool
   loop (`read_file` / `grep` / `list_dir`) and the orchestrator is a
   **deterministic servant** returning **raw ground truth**. Bindings for
   Anthropic (`tool_use`), OpenAI (Responses API, `previous_response_id`
   reasoning chaining), and Gemini (`function_declarations`). Caps
   (turn/token/cost), sandbox confinement (`_safe`, symlink-safe), a forced
   `submit_verdict`, and a tool-call trace (a zero-probe run is a *failed* run).

2. **Experiment A (S3, `experiment-a-results.md` + `experiment-a/`).** A blind,
   frozen-tree 2×2 (context × provider) capability study, K=3, 60 metered runs,
   graded against **pre-registered** criteria (`experiment-a-preregistration.md`)
   with a pre-registered **manual audit** of routed×cross-file catches. Headline:
   path-aware capability **CONFIRMED** (H1); routed unique capability **ruled
   out** (H3); the edge is **context-access not provider-multiplicity** (H2);
   falsifier coverage 19/20 (H4).

3. **The producer (`ai_router/pull_critique.py`, S4).** An **opt-in** automated
   producer (`python -m ai_router.pull_critique <set-dir>`) that drives
   `pull_route` once per provider over a read-only repo sandbox and writes the
   Set 066 `path-aware-critique.json` artifact the close-out gate validates. It
   **refuses to write a gate-failing artifact** (requires ≥2 distinct providers
   with usable verdicts), stamps `sessionSetName` + the recorded
   `pathAwareCritique` level, and validates the envelope before writing. Manual
   flow stays the default.

4. **Release.** `ai_router` 0.20.0 → 0.21.0 (`pyproject.toml`, `CHANGELOG.md`),
   docs (`ai_router/docs/pull-verifier.md` + automated-alternative notes in
   `docs/path-aware-critique-schema.md` and the `path-aware-critique.md`
   template). Routed per-session verification is **unchanged**; the `run_test`
   sandbox, contract-test gate, Experiment B (cadence), and the routed
   keep/demote/retire decision are deferred to Set 068.

## Load-bearing claims to check against the code and data (prove or disprove each)

- **Deterministic-servant guarantee is real, not decorative.** Does
  `_guard_raw_ground_truth` actually make a summarizing/fabricating servant a
  hard failure on *every* path — success **and** error results — or is there an
  error-shaped hole, an unguarded tool, or a result the guard never re-derives?
- **Sandbox confinement holds.** Can any of `read_file` / `grep` / `list_dir`
  (or the file walk) be coaxed to read outside the sandbox — via absolute paths,
  `..`, symlinked dirs/files, or a TOCTOU between walk and read?
- **Caps are enforced before spend.** Do the turn/token/cost ceilings actually
  bound a run, and is a zero-probe verdict really treated as a failed run
  (`PullResult.ok`)? Is `force_verdict` on the final turn correct?
- **The producer cannot emit a gate-passing-but-bogus artifact.** Trace
  `produce_path_aware_critique`: can it ever write an artifact that the close-out
  gate would *reject* (or, worse, *accept* when it shouldn't)? Check the
  distinct-provider keying (off the adapter-stamped provider, not the requested
  one), the identity stamping vs. `validate_path_aware_critique_gate`, the
  skip-not-fatal handling, and the pre-write validation. Does a single usable
  provider correctly refuse to write?
- **Experiment A's inference is sound.** Read `experiment-a-preregistration.md`,
  `catalogue.json`, `falsifier_suite.py`, `grade.py`, `audit.json`, and the
  `raw/` outputs. Does the **manual audit** (which removes 6 routed cross-file
  credits) follow its own pre-registered rule, or is it outcome-driven? Do H1/H2/
  H3/H4 actually follow from the data **under the pre-registered decision rule**,
  given the small n (5 trees, K=3) and the author-seeded defects? Is any effect
  reported as resolved that actually sits in the noise band?
- **No overclaim in the docs.** Do `experiment-a-results.md`, the CHANGELOG, and
  `ai_router/docs/pull-verifier.md` state the capability/limitations honestly
  (direction-not-magnitude; falsifier pre-authoring caveat; routed unchanged), or
  do they overstate what 60 runs on a mock repo establish?
- **Contract fidelity.** Does the producer's emitted envelope match
  `docs/path-aware-critique.schema.json` **and** the pure-Python validator
  (`validate_path_aware_critique_artifact`) — including `schemaVersion` integer
  typing and the ≥2-distinct-providers rule?

## What to attack

1. **Correctness.** Logic errors, wrong conditionals, off-by-one, mishandled
   edge cases, fail-open/fail-closed mistakes, ordering/atomicity bugs in the
   loop driver, the bindings, or the producer. Name the exact `file:line`.
2. **Security / confinement.** Any read outside the sandbox; any tool that
   mutates; any way the servant guarantee is bypassable.
3. **Experimental validity.** Pre-registration violations, grading subjectivity,
   an audit rule applied unevenly, an effect over-read at this n/K, a falsifier
   that doesn't discriminate, leakage between arms.
4. **Contract / cross-artifact drift.** Schema vs. validator vs. producer vs.
   docs disagreement; a doc claiming behavior the code does not implement.
5. **Completeness.** A claimed deliverable with no implementation; a wired-but-
   untested path; a stated invariant nothing enforces; a test that passes
   without exercising the behavior it names.
6. **Anything unforeseen** — cost/perf blowups, ASCII/encoding hazards on
   Windows `cp1252`, a wrong default, a stale reference, a release/packaging gap.

## Output format

Begin with a one-line **VERDICT**: `VERIFIED` (no significant issues) or
`ISSUES_FOUND`. Then:

- If `VERIFIED`: 2–4 sentences on **what you actually read** (which files, which
  claims, which data) and why you are confident. A bare "looks good" is a failed
  review.
- If `ISSUES_FOUND`: a **Findings** list. For each finding give:
  - **Severity:** Critical / Major / Minor
  - **Category:** correctness / security / experimental-validity / contract-drift / completeness / false-confidence / other
  - **Location:** the exact `file:line` (or file + symbol, or the result file)
  - **Description:** what is wrong, the ground truth you read (or the data point)
    that proves it, and the concrete fix.

Do NOT re-do the work. Only evaluate what was produced. Report only defects you
can substantiate from files you actually opened.
