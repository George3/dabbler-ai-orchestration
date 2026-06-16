# Automated Pull-Critique Capabilities Spec (Set 069)

> **Purpose:** Close the **automated-vs-manual pull-critique gap** the Set 068
> 0.22.x release exposed — the automated `pull_critique` producer ran read-only and
> missed two Major correctness bugs the operator's *manual* pull run caught by
> executing code. This set gives the automated critic a **constrained
> evidence-generation lane** (not arbitrary power), so its findings approach the
> manual run's at trusted-command risk, and a **quality-gated promotion path** so
> its best findings harden the deterministic floor instead of evaporating.
> **Design rationale (required reading):**
> [`docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md`](../../proposals/2026-06-16-pull-architecture-capabilities/proposal.md)
> (3-engine panel synthesis, operator-reviewed 2026-06-16) and the settled
> [`docs/verification-surface-strategy.md`](../../verification-surface-strategy.md).
> **Created:** 2026-06-16.
> **Session Set:** `docs/session-sets/069-automated-pull-critique-capabilities/`
> **Prerequisite:** Set 068 complete (it shipped `pull_verifier` / `pull_critique` /
> `contract_gate` / `run_test_sandbox` + the routed-gate cut-over this set extends).
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification (now
> **gated** per the Set 068 DEMOTE: run `python -m ai_router.routed_gate` on each
> session diff; this set's sessions touch the shared adapter + close-out, so they
> will trip the predicate — expect routed verification to be REQUIRED throughout).

---

## Session Set Configuration

```yaml
tier: full
requiresUAT: false
requiresE2E: false
uatScope: none
pathAwareCritique: required   # dogfood continues (Set 066/067/068 norm)
contractGate: advisory        # light dogfood of the S5-068 floor on this set's own probes
prerequisites:
  - slug: 068-cadence-study-and-contract-gate
    condition: complete
```

> Rationale: pure `ai_router` machinery + a PyPI release; **no UI surface** (the
> Explorer remains a Set-068 non-goal), so no UAT/E2E gate. **Full tier** — every
> session is cross-provider verified (gated). `pathAwareCritique: required`
> because this set touches the **shared pull adapter, the producer, and the
> close-out path** (the blast-radius predicate scores it `required`); it is
> additive — the read-only toolset and the manual flow remain.
>
> **A second, in-spec gate (not a `prerequisites:` entry):** the **Podman
> feasibility spike** (`docs/proposals/2026-06-16-pull-architecture-capabilities/podman-spike/`)
> must be **GREEN** before **Session 4** (the model-authored-probe lane) does any
> Podman work. Rungs 1–3 and 5–6 do **not** depend on it. If the spike is **red**
> (e.g. virtualization unavailable on the fleet), Session 4 records the **NO-GO**
> and the set ships rungs 1–3 + 5–6 only.

---

## Project Overview

### Background

Set 068 shipped the layered verification surface — a deterministic **contract-test
floor**, a repository-reading **path-aware critique ceiling**, and a
**blast-radius-gated** per-session routed check. The 0.22.x release then revealed
the ceiling's weak spot: the **automated** producer (`pull_critique.py`) drives its
critics **read-only** (`read_file` / `grep` / `list_dir`), so it is a *commentator*
where the **manual** critic (a frontier model in a Copilot editor with a terminal)
is an **evidence-producing probe runner**. The manual run reproduced two Major bugs
by executing code; the automated run could not. The fix is **constrained
evidence generation** under the deterministic-servant discipline, plus a
**ceiling -> floor ratchet** so reproduced probeable defects become permanent
falsifiers.

### The architecture (settled by the proposal panel)

- **The lever is execution-backed evidence, not more providers.** One critic that
  can *run* a probe and attach a **raw, replayed transcript** beats two read-only
  critics on correctness bugs. So this set adds execution lanes and an
  **evidence protocol**, and retunes (does not multiply) provider use.
- **Trigger / parameterize vs author.** The model may *trigger* operator-authored
  commands and *parameterize* operator-authored probe templates (both stay inside
  the trusted-command model); it may **author-and-run** code only inside a real
  **Podman** container (the boundary), severity-gated, behind a green spike.
- **The falsification reframe.** The floor does not make execution *safe*
  (containment does); it makes the agent's *claims* **re-runnable falsifiers**, so
  trust never rests on the agent's word. The executable ceiling's north star is
  "produce a re-runnable falsifier for the residual," not "narrate a bug."

### Scope (in)

- A **single execution-evidence protocol** for both manual and automated critics:
  evidence-tiered findings (`REPRODUCED` / `ASSERTED` / `HYPOTHESIS`),
  **orchestrator-tagged** (never agent-tagged), with a servant-captured transcript
  + **pristine replay** required for `REPRODUCED`, and the **meta-oracle rule**
  (an `EXECUTED` finding must drive a **real public entrypoint**, not an
  agent-built harness).
- Wiring **trusted-command execution** + **`get_diff`** + a **blast-radius-budgeted
  multi-turn** loop into `pull_critique`.
- The **probe-template lane**: operator-authored, versioned probe harnesses invoked
  with typed, validated args.
- The **Podman model-authored-probe lane** (graduating the spike harness into
  `ai_router/`), autonomous + severity-gated, with the AI-check as **triage only**
  — **gated on a green spike**.
- The **quality-gated ceiling -> floor ratchet** and the **measured replacement
  gate** (seeded + holdout benchmark scoreboard; folds in the Set 068 next-set
  recommendation to instrument the gated surface and reopen RETIRE on evidence).
- A synthesis update, focused tests, an `ai_router` **PyPI release**, dogfood,
  `change-log.md`.

### Non-goals (out)

- **Explorer / extension UI** for any of this; any **Marketplace** bump.
- A general CI runner; arbitrary shell; network egress during a probe; any write
  to the real working tree.
- **Retiring** the manual whole-set critique — it stays a backstop until the §S5
  scoreboard says otherwise (the human watching execution is the current defense
  against the meta-oracle problem).

### Standards

- **Deterministic servant, including for execution evidence.** Tools return raw
  ground truth; the **orchestrator** tags findings, never the agent; a
  summarizing/fabricating servant is a hard failure.
- **Containment is the cage's job, not the floor's.** Trusted commands run in the
  existing worktree cage; model-authored code runs only in Podman
  (`--network=none`, read-only repo, tmpfs scratch, `--cap-drop=ALL`, caps).
- **Pre-scripted, token-frugal surfaces.** The model emits a probe / typed args,
  never orchestration; token cost is bounded by construction, runtime by caps.
- **Flake-aware integrity.** Any "re-run and void on mismatch" uses an N-run
  majority before it can fire (no false accusations of honest critics).
- **Pre-registered, honest benchmarks** for the replacement gate (effect-size
  clarity; state when n is too small to resolve).

---

## Sessions

### Session 1 of 6: Execution-evidence protocol + evidence-tiered findings

**Steps:**
1. Register; read the proposal + `verification-surface-strategy.md`, `pull_verifier.py`,
   `pull_critique.py`, the Set 066 critique schema/validator, and L-066-1.
2. Define the **single evidence protocol** (manual + automated share it): the
   `REPRODUCED` / `ASSERTED` / `HYPOTHESIS` tiers; the **orchestrator-applied** tag
   rule; the transcript shape (pinned ref, command/template id + typed args,
   pristine-checkout status, exit, raw output, output hash); the **pristine-replay**
   requirement for `REPRODUCED`; and the **meta-oracle rule** (drive a real public
   entrypoint, not an agent harness).
3. Extend the critique artifact schema + the **pure-Python validator** (L-066-1
   parity: type-check optional fields, int-not-bool) to carry evidence-tiered
   findings; a finding tagged `REPRODUCED` without a valid transcript is **invalid**.
4. Tests (no metered calls); cross-provider verification (gated -> REQUIRED);
   `disposition.json`; commit + push; `close_session`.

**Ends with:** the evidence protocol + schema exist and reject a `REPRODUCED`
finding lacking a replayed transcript; session **VERIFIED**.
**Progress keys:** `evidence-protocol`, `evidence-schema`, `s1-verified`.

### Session 2 of 6: Trusted-command execution + diff-awareness + deeper probing

**Steps:**
1. Register; read the S1 protocol + the run-test-contract + `routed_gate`.
2. Wire **trigger-only** execution into `pull_critique`: the critic may trigger
   **operator-authored command ids** (declared falsifiers / vetted test entrypoints)
   in the existing `run_test` cage — **no model-authored argv**, fresh checkout,
   stripped env, caps. Add **`get_diff`** (raw unified diff + changed paths; no
   model-summarized symbol map). Add a **blast-radius-budgeted** multi-turn
   read->run->read loop (turn/token caps per set, not a magic constant).
3. Findings from a triggered run flow through the S1 protocol (orchestrator-tagged,
   transcript-backed).
4. Tests (the cage runs trivial deterministic commands; no metered calls);
   cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Ends with:** the automated producer can run existing trusted commands + see the
diff + probe in bounded turns, with evidence-tiered findings; session **VERIFIED**.
**Progress keys:** `trusted-exec-wired`, `diff-awareness`, `deeper-probing`, `s2-verified`.

### Session 3 of 6: The probe-template lane (the missing middle)

**Steps:**
1. Register; read S1–S2 + the proposal §1.4 / §3.3.
2. Build the **probe-template** surface: operator-authored, **versioned** probe
   harnesses (e.g. "invoke validator on this malformed-bytes artifact", "call X
   with a bad parent dir") the critic invokes with **typed, validated args**. The
   harness is human-authored (stays in the trusted-command model); the model
   supplies only typed inputs. Define the declaration + typed-arg validation +
   loop wiring; ship the templates that would have caught the 0.22.x bugs as the
   first library + regression coverage.
3. Tests; cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Ends with:** the critic can parameterize operator-authored probe templates to
find novel-but-local edge cases without authoring code; session **VERIFIED**.
**Progress keys:** `probe-template-lane`, `template-library`, `s3-verified`.

### Session 4 of 6: Podman model-authored-probe lane (GATED on a green spike)

**Steps:**
1. Register; **read `podman-spike/spike-result.json` + the spike README results
   table.** If the spike is **NOT GREEN**, record the **NO-GO** in this session's
   close-out (the lane is deferred; the set proceeds to S5 with rungs 1–3),
   and skip steps 2–3.
2. (Green spike only) **Graduate the spike harness into `ai_router/`** as
   `run_test_sandbox`'s sibling: a **digest-pinned**, no-secrets image; the
   `podman run` cage (`--network=none`, read-only repo, tmpfs scratch,
   `--cap-drop=ALL`, caps, crash-safe teardown); a **tiny typed tool surface** (the
   model supplies a probe / template args, never `podman` flags). Wire it as the
   **autonomous, severity-gated** rung-(b) lane (fire only on a critical/major
   claim unconfirmable via (a)/existing tests); the **AI safety check is triage
   only** (may reject/escalate, never approve); evidence flows through the S1
   protocol (drive a real entrypoint; replay).
3. Tests (cage mechanics against a trivial probe; the metered model loop is not in
   unit). Add a `--network=none` / read-only / teardown regression.
4. Cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Ends with:** model-authored probes run autonomously *inside Podman* (green spike)
or the lane is recorded NO-GO (red spike); session **VERIFIED**.
**Progress keys:** `spike-gate-checked`, `podman-lane` (or `podman-lane-nogo`), `s4-verified`.

### Session 5 of 6: Ceiling -> floor ratchet + measured replacement gate

**Steps:**
1. Register; read S1–S4 deliverables.
2. Build the **quality-gated ratchet**: a reproduced probeable defect yields a
   **candidate falsifier artifact** (never auto-merged); admission requires
   fails-on-old, passes-on-fixed, **drives a public contract** (not an incidental
   string/timing), survives an **N-run flake check**, has an owner, and carries
   **human sign-off**. Mandatory for reproduced probeable defects or an explicit
   waiver.
3. Build the **measured replacement gate**: a pre-registered **seeded + holdout**
   (recent real misses) benchmark scoring recall / precision / replay-success /
   **false-`REPRODUCED`** rate, and a telemetry record of the gated surface
   (escaped-defect rate, intro-stage vs end-of-set timing, rework saved,
   false-positive churn, predicate-should-have-fired misses) — the data the Set
   068 DEMOTE decision said **RETIRE** reopens on. The manual run's cadence is
   **decided by this scoreboard**, not retired on faith.
4. Tests; cross-provider verification; `disposition.json`; commit + push; `close_session`.

**Ends with:** reproduced probeable bugs can pay rent into the floor under a
quality gate, and a scoreboard measures the automated process against manual;
session **VERIFIED**.
**Progress keys:** `floor-ratchet`, `replacement-gate`, `s5-verified`.

### Session 6 of 6: Synthesis + docs + release + dogfood + close

**Steps:**
1. Register; read S1–S5 deliverables.
2. Update `docs/verification-surface-strategy.md` (the capabilities are now built;
   record the spike GO/NO-GO outcome) + `ai_router/docs/pull-verifier.md` + the
   proposal's status; promote a lesson if warranted.
3. Finalize tests; bump `ai_router`; ship the **PyPI release** per the publish
   runbook (green-`Test`-on-the-tagged-SHA prerequisite; **verify the tag's commit
   == the fixed SHA** — Set 068 lesson; operator pushes/approves the tag). Record
   the publish run id post-release.
4. `change-log.md`; route the next-session-set recommendation; cross-provider
   verification; **dogfood** (`pathAwareCritique: required`; `contractGate:
   advisory`) — and **dogfood the new lanes themselves** (run the now-execution-
   capable producer over this set's own diff); `close_session`; set closes.

**Creates:** the synthesis update, `change-log.md`, this set's dogfood artifacts.
**Ends with:** the automated pull-critique can generate execution-backed evidence,
promote reproduced bugs into the floor, and is measured against the manual run;
`ai_router` released; set closed.
**Progress keys:** `synthesis-updated`, `released`, `change-log-written`, `dogfooded`, `s6-verified`.

---

## End-of-set deliverables

- The single **execution-evidence protocol** + evidence-tiered findings schema (S1).
- **Trusted-command execution** + `get_diff` + bounded multi-turn probing in the
  producer (S2).
- The **probe-template lane** + the template library that catches the 0.22.x class (S3).
- The **Podman model-authored-probe lane** graduated into `ai_router/` (green spike)
  or a recorded **NO-GO** (red spike) (S4).
- The **quality-gated ceiling -> floor ratchet** + the **measured replacement gate /
  scoreboard** (S5).
- The synthesis update, an `ai_router` **PyPI release**, this set's dogfood
  artifacts, and `change-log.md` (S6).

An automated pull-critique that produces **execution-backed, replayable** evidence,
hardens the deterministic floor with every reproduced probeable defect, and is
**measured** against the manual run rather than assumed equal to it — closing the
gap the Set 068 release exposed, at trusted-command risk plus a contained,
spike-validated lane for the rest.
