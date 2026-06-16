# Contract-Test / CDC Gate — design note (Set 068 S5)

> **Status:** Pinned design for the deterministic contract-test floor
> (`ai_router/contract_gate.py`) and its close-out wiring. The gate is the
> **deterministic floor** Experiment A's H4 finding supports (~95% of seeded
> defects are deterministically falsifiable; see
> [`experiment-a-regrade.md`](experiment-a-regrade.md) and the Set 067
> `experiment-a-results.md` H4) and the **replacement floor** the Set 068 S4
> routed keep/demote/retire decision's transition guard waits on:
> [`routed-fate-decision.md`](routed-fate-decision.md) §4 — *"the demotion does
> not take effect until the Set 068 S5 contract-test / CDC gate is live and
> stable."* This session builds the floor; **S6** wires the blast-radius gating
> predicate and flips the workflow default (it does not happen here).
> **Created:** 2026-06-15 (Session 5).

---

## 1. What the gate is (and is not)

The contract-test / CDC gate is a **deterministic, per-set, opt-in floor** that
confirms a set's **contract / falsifier tests** (the cheap, reproducible check)
actually ran and passed at set close, and that they **cover every probeable
defect class the set declares** — reserving the (expensive) path-aware agent for
the **non-probeable residual**. It operationalizes the layered defense the S4
decision named:

- **Floor (this gate):** deterministic contract tests carry the ~95%-probeable
  bulk. Cheap, reproducible, no model in the loop.
- **Ceiling (path-aware critique, Set 066/067):** the agent is reserved for the
  ~5% non-probeable residual and for *authoring* falsifiers.

It is **not** a CI runner and **not** a general test harness (spec non-goal). It
runs **one** operator-declared contract command in the Set 068 S1 disposable
`run_test` cage, hard-capped and crash-safe, and records the raw result.

## 2. Why it mirrors the path-aware critique gate (produce → validate)

The gate deliberately reuses the **Set 066 path-aware-critique shape** so an
operator who knows one knows the other, and so the close-out path stays
deterministic and fast:

| Concern | Path-aware critique (Set 066/067) | Contract gate (this set) |
|---|---|---|
| Per-set policy attribute | `pathAwareCritique: none\|advisory\|required` | `contractGate: none\|advisory\|required` |
| Durable record | activity-log entry, once at set start, immutable | identical machinery (own `kind`) |
| Producer (runs the work) | `python -m ai_router.pull_critique` (drives the agents) | `python -m ai_router.contract_gate run` (drives the S1 cage) |
| Saved artifact | `path-aware-critique.json` | `contract-floor-result.json` (+ declared `contract-manifest.json`) |
| Close-out gate | validates the saved artifact, posture-aware | validates the saved result + manifest, posture-aware |

**Why produce-then-validate, not run-at-close:** running a full contract suite
inside `close_session` would make close-out a multi-minute, network-and-flake-
exposed operation that must *never wedge* (the fail-open contract). Instead the
**producer** runs the floor in the S1 cage and saves the raw result; the
**close-out gate** validates that saved result (it passed, it matches this set,
it covers every probeable class). The producer is where the tests *run*; the gate
is the deterministic *check* that they ran and carried the bulk. This also gives
the S1 `run_test` cage its first production consumer.

## 3. The declaration surface — `contract-manifest.json`

A set that opts into `contractGate: advisory|required` declares, at the set root:

```jsonc
{
  "schemaVersion": 1,
  "sessionSetName": "068-cadence-study-and-contract-gate",
  "contractGate": "required",
  "command": ["python", "-m", "pytest", "-q", "tests/contract"],
  "defectClasses": [
    { "id": "DC1", "description": "...", "probeable": true,  "coveredBy": ["test_dc1"] },
    { "id": "DC2", "description": "...", "probeable": false, "coveredBy": [] }
  ]
}
```

- `command` — the operator-authored contract/falsifier argv (`shell=False`,
  passed verbatim to the S1 cage). Bounded command surface — the model never
  authors it (run-test-contract §3).
- `defectClasses[]` — the seeded / known defect classes and how they are covered:
  - `probeable: true` ⇒ a deterministic contract test **can** falsify this class,
    so it **must** name ≥1 covering test in `coveredBy` (the floor carries it).
  - `probeable: false` ⇒ the **residual** reserved for the path-aware agent;
    `coveredBy` is expected empty and the gate reports it as agent-reserved, not
    a failure.

## 4. The floor result — `contract-floor-result.json`

The producer runs `command` in the S1 cage and writes the **raw** result
(mirroring the deterministic-servant discipline — exit code + captured output,
never summarized):

```jsonc
{
  "schemaVersion": 1,
  "sessionSetName": "068-...",
  "contractGate": "required",
  "ref": "<git ref the cage checked out>",
  "command": ["python", "-m", "pytest", "-q", "tests/contract"],
  "ran": true, "passed": true, "exitCode": 0, "timedOut": false,
  "wallSeconds": 12.3, "worktreeCreated": true, "worktreeRemoved": true,
  "output": "<raw, capped/elided>"
}
```

## 5. The close-out gate — pass condition + posture

`validate_contract_gate(session_set_dir)` (posture-agnostic, never raises):

- `contractGate == none` ⇒ `applicable=False, ok=True` (no-op; default).
- `advisory` / `required` ⇒ gate is applicable; **ok** iff **all** hold:
  1. a valid `contract-manifest.json` exists (schema + identity: its
     `sessionSetName` / `contractGate` match this set);
  2. a valid `contract-floor-result.json` exists whose `command` matches the
     manifest and `sessionSetName` matches this set;
  3. the floor result **passed** (`ran` and `exitCode == 0`, not `timedOut`,
     worktree torn down) — a leaked/timed-out/failed run is **not** a floor;
  4. **every** `probeable: true` defect class names ≥1 `coveredBy` test (the
     floor genuinely carries the probeable bulk). An uncovered probeable class
     is a gate failure.
- The **non-probeable residual** (probeable=false classes) is **reported**
  (`reason` + a structured count) as agent-reserved — never a failure.

**Posture** (the *caller's* decision, mirroring Set 066): `required` HARD-blocks
in an interactive TTY and SOFT-warns headless / `--accept-suggestions`;
`advisory` ALWAYS soft-warns and never blocks; `none` skips. Fires **only** on
the set-terminal close, and is **fail-open** in the non-block direction — any
internal error never wedges close-out.

## 6. Scope this session (S5)

- `ai_router/contract_gate.py`: the `contractGate` policy attribute machinery
  (mirror of `path_aware_critique`), the manifest + floor-result pure-Python
  validators (L-066-1 discipline: type-check optional fields; `int`-not-`bool`
  for `schemaVersion`), the floor **producer** (drives the S1 cage), the coverage
  computation, the close-out `validate_contract_gate`, and the `python -m
  ai_router.contract_gate` CLI (`run` / `validate`).
- `docs/contract-manifest.schema.json`, `docs/contract-floor-result.schema.json`,
  `docs/contract-gate.md` (the canonical schema + doc).
- Close-out wiring in `ai_router/close_session.py` (posture model, set-terminal,
  fail-open) + a `router-config.yaml` comment anchor.
- Tests (no metered calls; the cage runs trivial deterministic commands against a
  real temp git repo).

**Out of scope (S6 / future):** wiring the blast-radius gating predicate that
flips per-session routed to gated (S4 §4) and any Explorer/extension UI. This set
ships the floor; S6 flips the default and synthesizes.
