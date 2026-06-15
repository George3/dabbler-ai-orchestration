# Path-Aware Critique — reusable operator prompt template

> **What this is.** The canonical, reusable prompt for the **manual
> Path-Aware Critique** stage (Set 066): an end-of-set, **multi-provider**
> review in which each critic has **real, path-aware access to the
> repository** and pulls ground truth itself rather than reviewing a snippet
> the (biased) author pasted. It institutionalizes the operator flow that
> the team already practices — GitHub Copilot driving **GPT-5.4** and
> **Gemini-Pro** over the repo — and that produced this very feature's design
> critiques.
>
> **When to run it.** At the end of a session set whose recorded
> `pathAwareCritique` policy is `advisory` or `required` (see the authoring
> guide and `docs/path-aware-critique-schema.md`). The blast-radius predicate
> (`python -m ai_router.blast_radius <paths…>`) *recommends* the level; the
> operator confirms it at set start.
>
> **Why path-aware + multi-provider.** The Set 065 bake-off proved a
> path-aware, multi-provider critique catches a class of high-severity defects
> a snippet-fed single-shot verifier structurally cannot see (fabricated data,
> index undercounts, cross-artifact contract drift). A single provider is
> insufficient (the 010-vs-C3 split implied opposite single-provider fixes),
> so the saved artifact **requires >= 2 distinct providers**.
>
> **Automated alternative (opt-in, Set 067).** This manual flow is the
> default and always available. As of Set 067 you can also produce the same
> artifact automatically with `python -m ai_router.pull_critique
> <session-set-dir>`, which drives the first-party tool-loop pull verifier
> (`ai_router.pull_verifier`) once per provider over a read-only repo sandbox
> and writes `path-aware-critique.json` directly — using *this very prompt*
> as its critique instruction. Set 067 Experiment A confirmed the automated
> path catches the same class of real cross-file defects. The producer is
> strictly opt-in; nothing in the normal session flow invokes it.

---

## How to run this (operator)

1. Open the repository in an editor with **GitHub Copilot** (so the reviewer
   has real, path-aware workspace access — this is a Mode-2 *pull* review, the
   kind the routed `route()` path cannot do).
2. Fill the `{...}` placeholders in the `=== PROMPT ===` body below with this
   set's specifics (slug, change summary, the file list, the load-bearing
   claims to check).
3. Paste the filled prompt into Copilot Chat **once under GPT-5.4** and **once
   under Gemini-Pro** — two independent passes, each from a clean context.
4. Save each critic's raw verdict, then assemble them into
   `docs/session-sets/{session_set_slug}/path-aware-critique.json` per
   `docs/path-aware-critique-schema.md`. The artifact is **raw and never
   edited after written** (verification-artifact discipline). One critique
   entry per provider; `>= 2` distinct providers.
5. Hand the verdicts back to the orchestrator to fold into remediation, then
   run `close_session` — on a `required` set the close-out gate confirms the
   saved artifact is valid before the set-terminal close.

> A clean review still produces an artifact: every provider records what it
> reviewed and its verdict. Unlike `sN-issues.json` (whose presence *means*
> issues were found), this artifact's presence means *the critique ran*. Never
> fabricate a provider entry to satisfy the gate.

---

=== PROMPT ===

You are an adversarial code-and-docs reviewer with **full read access to this
repository**. A session set (**{set_title}**, slug `{session_set_slug}`) has
just finished its implementation work and is about to close. Your job is to
find what is **wrong, risky, incomplete, or internally inconsistent** in its
changes — across code, tests, and documentation — **before** it ships. Be a
genuine devil's advocate: assume the work is flawed and try to prove it. A
rubber-stamp is a failure.

**Anti-bias instruction (load-bearing).** Do **not** rely on my summary below.
**Open and read the actual files yourself** and reason from what is on disk.
Where my description and the code/docs disagree, **the repository wins** — call
that out explicitly. Pull ground truth; do not trust a flattering paraphrase.
In particular, for every claim of *current behavior* (what a function reads,
writes, enforces, or defaults to; what a test asserts; what a doc says the code
does), verify it against the actual file before accepting it.

## What this set changed (my summary — verify it, do not trust it)

{change_summary}

## Files changed (read these; do not stop at the ones I emphasize)

{files_changed}

## Load-bearing claims to check against the code (prove or disprove each)

{claims_to_check}

## What to attack

1. **Correctness.** Logic errors, wrong conditionals, off-by-one / index
   miscounts, mishandled edge cases, fail-open/fail-closed mistakes, ordering
   bugs. Name the exact file and line.
2. **Contract / cross-artifact drift.** A schema, validator, doc, and test that
   are supposed to describe the same contract but disagree. A doc claiming a
   behavior the code does not implement (or vice versa). A pure-Python validator
   that has drifted from its JSON Schema twin.
3. **Completeness.** A claimed deliverable with no actual implementation, a
   wired-but-untested path, a stated invariant nothing enforces, an edge case
   the tests skip.
4. **False confidence.** A test that passes without exercising the behavior it
   names; a "VERIFIED" claim the evidence does not support.
5. **Anything unforeseen** — hidden coupling, cost/perf blowups, ASCII/encoding
   hazards on Windows `cp1252`, a wrong default, a stale reference.

## Output format

Begin with a one-line **VERDICT**: `VERIFIED` (no significant issues) or
`ISSUES_FOUND`. Then:

- If `VERIFIED`: 1–3 sentences on **what you actually read** (which files, which
  claims you checked) and why you are confident. A bare "looks good" is a failed
  review.
- If `ISSUES_FOUND`: a **Findings** list. For each finding give:
  - **Severity:** Critical / Major / Minor
  - **Category:** correctness / contract-drift / completeness / false-confidence / other
  - **Location:** the exact `file:line` (or file + symbol)
  - **Description:** what is wrong, the ground truth you read that proves it, and
    the concrete fix.

Do NOT re-do the work. Only evaluate what was produced. Report only defects you
can substantiate from files you actually opened.
