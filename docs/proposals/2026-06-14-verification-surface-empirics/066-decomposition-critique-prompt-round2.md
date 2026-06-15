# Path-Aware Critique — Set 066 Decomposition, ROUND 2 (resolve the scope fork)

> **How to run this (operator):** Same as round 1 — open the repo in a
> GitHub-Copilot editor (real path-aware repo access), paste everything below
> `=== PROMPT ===` **once under Gemini** and **once under GPT**. Save the
> verdicts as `066-critique-gemini-round2.md` and `066-critique-gpt-round2.md`
> in this folder. This round is narrow: it resolves the **one** disagreement
> round 1 left open. Do not re-open the settled points.

---

=== PROMPT ===

This is **round 2** of an adversarial design review for an upcoming session set
(**Set 066**). You have full read access to this repository — read the actual
files; the repo wins over any summary here.

**Round 1 already happened.** Two independent reviewers (you, under GPT,
and you, under Gemini) reviewed a proposed 066 decomposition. You **agreed** on
a set of code-grounded blockers (now accepted — do **not** re-litigate them) but
**disagreed** on one central question. This round resolves only that question.

## Settled in round 1 (accepted — do NOT re-argue; treat as constraints)

1. **Architecture:** the Mode-2 adapter must be a **first-class agentic-executor
   seam / parallel entrypoint** (e.g. `pull_route()`), NOT a "new provider kind"
   nested in `route()` / `providers.call_model` (which is single-shot
   text-in/text-out — verified at `ai_router/providers.py:43`,
   `ai_router/__init__.py` route/call_model sites).
2. **The forward A/B does not fit one session.** Experiment A (capability,
   seeded frozen trees) and Experiment B (cadence, staged-snapshot) are
   different harnesses and must be separate sessions; Experiment B may belong in
   a later set. (See `forward-ab-design.md`.)
3. **Provider bindings and the `run_test` sandbox are separate sessions.** OpenAI
   `tool_calls` and Gemini `function_declarations` differ and were never run
   (only Anthropic was, per `spike-report.md`); the disposable-worktree sandbox
   for `run_test` is **new** work (NOT reuse of `ai_router/worktree.py`, which is
   a long-lived session-set worktree CLI).
4. **Full-tier Path-Aware Critique close-out wiring is net-new work.** The
   `dedicated-sessions` content-aware gate is **inert on Full tier** (it fires
   only for Lightweight `verificationMode`; see `dedicated_verification.py`
   header ~L440 and `close_session.py` ~L1709). The proposal's claim that this
   gate can be "reused" was wrong — an erratum was appended to
   `proposal.md` (read the **Erratum** at its top).
5. **Do not bundle a PyPI release with an unsettled routed-fate decision.**

## The ONE open disagreement (resolve this)

What is **Set 066's purpose / first consumer**?

- **Round-1 GPT position:** Deferring the Path-Aware Critique *feature* to a
  later set is the wrong deferral. The approved proposal (read `proposal.md` §9
  and §1) says Path-Aware Critique is **justified now** ("steps 1–3 committable
  now; step 4 [routed-fate] is data-gated"). So 066 should build the adapter and
  **ship Path-Aware Critique as the real product consumer**; push Experiment B +
  routed keep/demote/retire + contract gate to 067.
- **Round-1 Gemini position:** 066 should build the adapter and run **Experiment
  A** (the A/B is the adapter's consumer/validator); defer the *feature
  integration*, Experiment B, the release, and routed-fate to 067 — don't ship a
  feature before the capability study validates the engine.

## Re-read before deciding (path-aware)

- `proposal.md` — especially the **Erratum**, §1, §7 (the `P_task`/`P_set`
  predicate), and §9 (sequencing + "steps 1–3 committable now").
- `forward-ab-design.md` — what Experiment A vs B each actually require.
- `docs/planning/session-set-authoring-guide.md` — the **sizing** band (2–4
  typical; 5+ needs clear synthesis points) and "set too broad" anti-pattern.
- `spike-report.md` §"Capability proof" and the manual path-aware practice the
  team already runs (it ships *today* without any adapter — relevant to whether
  the feature can ship before the adapter is fully proven).

## The three candidate decompositions — pick ONE and defend it

**Option A — product set + research set (separate the two tracks):**
- 066 = adapter engine (S1 executor seam + Anthropic core; S2 OpenAI; S3 Gemini;
  S4 `run_test` sandbox) + **S5 ship Path-Aware Critique** (Full-tier per-set
  attribute + net-new close-out wiring + docs) **+ PyPI release**. ~5 sessions.
- 067 = **all** experiments: S1 Experiment A, S2 Experiment B, S3 routed
  keep/demote/retire + scope contract gate. ~3 sessions.

**Option B — hybrid (keep Experiment A in 066):**
- 066 = engine + feature integration + **Experiment A** + release. ~6 sessions.
- 067 = Experiment B + routed-fate + contract gate. ~2 sessions.

**Option C — Gemini's round-1 split (validate before shipping):**
- 066 = adapter engine + **Experiment A**, **no feature, no release**. ~4 sessions.
- 067 = Experiment B + feature integration + release + routed-fate. ~3 sessions.

## Answer these explicitly

1. **Which option (A / B / C, or a better one you specify)?** One-paragraph
   justification.
2. **Engage the strongest counterargument to your pick.** If you pick A: is
   shipping the feature before *any* controlled capability study (Experiment A)
   reckless, given the manual path-aware practice already ships today and the
   S1/S2 evidence? If you pick C: does deferring a "justified now" feature
   contradict the proposal's own §9, and does 066 then ship *nothing*?
3. **Does shipping Path-Aware Critique actually require the adapter,** or can the
   feature ship with the **manual** flow (operator-run, like this very review)
   and the adapter as later automation? This may dissolve the fork — say so if
   it does.
4. **Where exactly is the 066/067 line,** and is each set inside the authoring
   guide's sizing band with a clear synthesis point?

End with a **Recommended decomposition** (session-by-session for 066 and 067,
what ships, what defers) and a one-line **BOTTOM LINE**.
