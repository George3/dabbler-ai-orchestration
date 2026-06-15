# Change Log — 067-pull-verifier-adapter-experiment-a

> Ships the first-party, multi-provider **tool-loop "pull" verifier adapter**
> (`pull_route`) — the verifier drives a read-only tool loop and the
> orchestrator is a **deterministic servant** serving raw ground truth — runs
> **Experiment A** (which **confirmed** path-aware capability on identical
> frozen code), and wires the adapter as an **opt-in automated producer** of the
> Set 066 `path-aware-critique.json` artifact. Released as `dabbler-ai-router`
> **0.21.0**. The disposable-worktree `run_test` sandbox, the contract-test/CDC
> gate, **Experiment B** (cadence), and the routed keep/demote/retire decision
> are the sequenced follow-on **Set 068**. Routed per-session verification is
> unchanged.

## Sessions

### Session 1 — Adapter core + Anthropic binding (VERIFIED)

- `ai_router/pull_verifier.py`: the `pull_route()` agentic-loop driver — a
  `route()`-**parallel** seam (not a `route()` branch) with turn/token/cost
  caps, the **Anthropic** `tool_use` binding, sandbox-confined read-only tools
  (`read_file` / `grep` / `list_dir`), a forced `submit_verdict` shaped to the
  Set 066 critique entry, and a tool-call trace (a zero-probe run is a *failed*
  run).
- The **deterministic-servant** guardrail as code + test: a tool result is the
  raw artifact (success or error), independently re-derived and byte-compared; a
  summarizing servant raises `DeterministicServantViolation`.
- 54 tests, no metered calls in unit tests. Cross-provider verified (gpt-5.4,
  R1 1 Critical + 3 Major -> R3 VERIFIED).

### Session 2 — OpenAI + Gemini bindings + config wiring (VERIFIED)

- **OpenAI** binding on the **Responses API** (`previous_response_id` reasoning
  chaining; GPT-5.x rejects function tools + `reasoning_effort` on
  `/chat/completions`) and **Gemini** `function_declarations` binding (positional
  `functionCall` / `functionResponse`, bounded `thinkingBudget` per L-064-1),
  both behind the **same** provider-agnostic loop driver.
- The `pull_verifier:` executor block in `router-config.yaml` (per-provider model
  pins, shared caps, per-provider reasoning knobs) — distinct from the
  single-shot routing table.
- A 3-provider headless capability check (all three issue real tool calls and
  return schema-valid verdicts). Cross-provider verified (gpt-5.4, R1 -> R3
  VERIFIED).

### Session 3 — Experiment A: capability study (VERIFIED)

- A blind, frozen-tree **2×2 (context × provider)** capability test (Set 065
  `forward-ab-design.md`), K=3, **60 metered runs (~$1.38)**, graded against
  **pre-registered** criteria with a pre-registered manual audit of
  routed×cross-file catches. Instrument: 5 frozen trees, 20 seeded defects (all
  8 classes, 2 Critical, 2 novel controls), a pre-authored deterministic
  falsifier suite (19/20 discriminate).
- **Verdict (cross-provider verified): path-aware capability CONFIRMED.** H1
  context-access CONFIRMED (B1-A1 +0.31, B2-A2 +0.36, both >> noise band; gains
  100% cross-file incl. 2 Criticals routed missed); H3 routed unique-capability
  RULED OUT (only the cadence defense survives -> Set 068); H2 the edge is
  context-access not provider-multiplicity; H4 falsifier coverage 19/20.
- No production code; no release this session. Cross-provider verified of the
  analysis (gpt-5.4, R1 VERIFIED + 3 Minor wording fixes applied).

### Session 4 — Opt-in producer + synthesis + release (VERIFIED)

- **The producer** (`ai_router/pull_critique.py`). Experiment A confirmed
  capability, so the pre-registered S4 gate fired: `produce_path_aware_critique()`
  + the CLI `python -m ai_router.pull_critique <set-dir>` drive `pull_route`
  once per provider (default GPT-5.4 + Gemini-Pro) over a read-only repo sandbox,
  reuse the manual `path-aware-critique.md` template as the critique instruction,
  and write the Set 066 artifact the close-out gate validates. It **refuses to
  write a gate-failing artifact** (>= 2 distinct providers with usable verdicts;
  a failing provider is skipped, not fatal), **identity-stamps** `sessionSetName`
  + the recorded `pathAwareCritique` level, and validates the envelope with the
  same runtime validator the gate uses before writing. **Manual flow stays the
  default; the producer is strictly opt-in.**
- **Budget-aware forced verdict (`pull_verifier.py`).** The dogfood revealed
  that frontier reasoning models (GPT-5.4 at 28 probes, Sonnet at 18) over-probe
  and exhaust the token/cost budget **without ever submitting a verdict** — the
  final-turn force never fires because the hard ceiling breaks the loop first.
  Fix: `pull_route` now forces `submit_verdict` once **one more call of the last
  call's measured size** would breach either ceiling (an adaptive headroom
  reserve), so a verbose prober commits a verdict instead of being cut off empty.
  After the fix the default GPT-5.4 + Gemini-Pro pair both converge. (`L-067-1`.)
- Exported the public surface from `ai_router/__init__.py`
  (`produce_path_aware_critique`, `build_instruction`, `ProducerResult`,
  `PullCritiqueError`, `DEFAULT_PROVIDERS`). New tests (fake `run_pull` /
  `FakeBinding`, no metered calls); full Python suite green.
- Docs: new `ai_router/docs/pull-verifier.md`; opt-in "automated alternative"
  notes in `docs/path-aware-critique-schema.md` and the `path-aware-critique.md`
  template.
- **Release:** `ai_router` 0.20.0 -> **0.21.0** — **PUBLISHED to PyPI**
  2026-06-15 (tag `v0.21.0`, `release.yml` run `27562841610`, all jobs success
  incl. the green-`Test`-on-the-tagged-SHA gate; OIDC trusted publishing). No
  Marketplace bump (no extension change).
- **Dogfood (`pathAwareCritique: required`) — the headline of this session.**
  This set produced its own `path-aware-critique.json` via the **new producer**
  (a recursive dogfood: the opt-in automated path generated the very artifact its
  own `required` close-out gate validates). The path-aware critique (GPT-5.4 +
  Gemini-Pro reading the repo) **caught real producer/adapter defects the routed
  per-session verification (R1–R2) had passed**, all fixed before release:
  1. The **budget-exhaustion-with-no-verdict** flaw above (→ budget-aware forced
     verdict).
  2. `sessionSetName` stamped from an **unresolved** path (a `.` invocation
     yielded an empty name) → resolve the path first.
  3. `build_instruction` raised **`TypeError`** on a non-string disposition
     `summary` → `isinstance` guard.
  4. The CLI error path printed **un-sanitized** text → `_ascii()` wrap.
  5. A producer/gate **path-canonicalization asymmetry** (producer resolved,
     gate did not) could write an artifact the gate would reject on a
     non-canonical path → the gate now resolves identically.
  Regression tests added for all; the saved `path-aware-critique.json` records
  GPT-5.4 `ISSUES_FOUND` + Gemini-Pro `VERIFIED`. Cross-provider per-session
  verification: R1 `ISSUES_FOUND` (2) → fixed → R2 `VERIFIED`; the adapter +
  gate fixes re-verified R3→R5/R6 `VERIFIED`.

## Release

- `dabbler-ai-router` **0.21.0** — the pull-verifier adapter (3 bindings) + the
  opt-in path-aware-critique producer. No Marketplace bump (no extension change).

## Deferred to Set 068

- The disposable-worktree **`run_test`** tool + the **contract-test/CDC gate**
  (Experiment A H4: ~95% of defects are deterministically falsifiable).
- **Experiment B** (cadence) and the routed **keep / demote / retire** decision —
  routed's only surviving defense is cadence, which Experiment A holds constant.
