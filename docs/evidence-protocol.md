# The execution-evidence protocol

> **What this is.** The single protocol both the **manual** and the
> **automated** pull-critique speak when a finding is backed by *running code*
> rather than just reading it. It defines the evidence tiers, the
> orchestrator-applies-the-tag rule, the servant-captured transcript shape, the
> pristine-replay requirement, and the meta-oracle rule.
>
> **Authoritative source.** The runtime implementation is
> `ai_router.evidence_protocol` (pure-Python, dependency-free). The on-disk
> shape is part of the `path-aware-critique.json` artifact — the JSON Schema
> `$defs/EvidenceTranscript` block in
> [`docs/path-aware-critique.schema.json`](path-aware-critique.schema.json) is
> the structural contract; this document is the narrative reference. If the doc
> and the code disagree, the code wins — update this doc.
>
> **Locked by** Set 069 Session 1
> (`docs/session-sets/069-automated-pull-critique-capabilities/`). The design
> source is the pull-architecture proposal
> ([`docs/proposals/2026-06-16-pull-architecture-capabilities/proposal.md`](proposals/2026-06-16-pull-architecture-capabilities/proposal.md))
> rung 1 and §3.5, and the settled
> [`docs/verification-surface-strategy.md`](verification-surface-strategy.md).

---

## Why this exists

Set 068's 0.22.x release exposed the **automated-vs-manual pull-critique gap**:
the automated `pull_critique` producer drove its critics **read-only**
(`read_file` / `grep` / `list_dir`), so it was a *commentator*, while the
**manual** critic (a frontier model in a Copilot editor with a terminal) was an
**evidence-producing probe runner**. The manual run reproduced two Major
correctness bugs by *executing code*; the automated run could not.

The fix is **constrained evidence generation** under the deterministic-servant
discipline. But the proposal panel insisted the evidence *protocol* ship
**first**, before any new execution lane, for one reason: more execution without
a shared evidence contract just enlarges the **bluff surface**, and a
human-watched terminal must not be allowed to mint *stronger* claims than
automated evidence. One protocol, both critics — that is the **two-standards**
fix.

The deeper reframe (proposal §2): the deterministic floor does **not** make
execution *safe* (containment does that — see the cage / Podman lanes). What it
buys is **epistemic**: it extends the deterministic-servant discipline to the
agent's *claims*. A finding that ships as a **re-runnable falsifier** requires
the human to trust the agent **not at all** — the servant re-executes it. So the
north star for the executable ceiling is not "narrate a bug" but **"produce a
re-runnable falsifier for the residual."**

---

## The three evidence tiers

Every finding carries an **effective tier**. The field is `evidenceTier` on a
finding object; it is **optional and additive** — a finding with no tier is
treated as `ASSERTED`, so every pre-069 artifact stays valid.

| Tier | Meaning | Backing required |
|---|---|---|
| `REPRODUCED` | The defect's failure was **reproduced by running a probe**. | A servant-captured **transcript** with a **pristine replay** through a **real public entrypoint** (a re-runnable falsifier). |
| `ASSERTED` | The critic claims the defect from **reading** the code; no execution. The natural tier of a read-only critique, and the **default** for an untagged finding. | The critic's reasoning / citations. No transcript. |
| `HYPOTHESIS` | A **suspected** issue flagged for follow-up; lowest confidence. | None; agent-proposed. |

`REPRODUCED` is the only tier with teeth: it is the only one that asserts an
*executed* reproduction, and therefore the only one that must be backed by an
artifact a third party can re-run.

---

## The orchestrator applies the tag — never the agent

The load-bearing trust rule. `REPRODUCED` is conferred by the **orchestrator**,
not the agent, and **only** when a valid transcript exists. The agent's proposed
tier is advisory:

- a **valid** transcript → `REPRODUCED` (trust rests on the artifact, not the
  agent's word — the servant re-ran it);
- **no** valid transcript → a `REPRODUCED` *claim* collapses to `ASSERTED` (the
  agent's un-executed word); `HYPOTHESIS` is preserved; anything else becomes
  `ASSERTED`.

In code this is `evidence_protocol.authoritative_tier(proposed_tier,
transcript)`. A producer calls it when assembling the artifact, so the on-disk
`evidenceTier` is **always** orchestrator-derived. The agent's `submit_verdict`
tool surface never exposes the authoritative tier — the agent cannot self-grant
`REPRODUCED`.

> **Why this matters.** Naive automation that lets the agent label its own
> finding `REPRODUCED` turns "reproduced by running" into a
> *hallucinated-reproduction* surface — stronger-looking than a read-only
> assertion but backed by nothing. The tag is trustworthy **iff** artifact-backed
> and independently replayed.

---

## The transcript shape (the falsifier contract)

A transcript backs a `REPRODUCED` finding only when **all** of the following
hold (`evidence_protocol.validate_transcript`):

| Field | Type | Rule |
|---|---|---|
| `pinnedRef` | string | The git ref / commit the probe ran against. Non-empty. |
| `commandId` **or** `templateId` | string | **Exactly one.** A **trusted, operator-authored** command id or probe-template id — **never model-authored argv**. |
| `args` | object / array | The typed, validated args (optional). |
| `pristineCheckout` | boolean | Must be `true` — the probe ran on a **fresh checkout**. |
| `exitCode` | integer / null | Present. `null` == the probe was killed / timed out (matches the `run_test` cage). |
| `rawOutput` | string | The raw captured stdout+stderr, **never summarized** (may be elided to a raw head slice). |
| `outputHash` | string | `sha256:<hex>` digest of the raw output — the unit the replay must match. Use `evidence_protocol.hash_output`. |
| `entrypoint` | object | The **public** entrypoint the probe drove (meta-oracle — below). |
| `replay` | object | The replay on a **second** pristine checkout (pristine-replay — below). |

### The pristine-replay requirement

A single run is "the agent says it ran." The **replay** is what makes it a
falsifier: the probe is run **again on a second, fresh checkout**, and the
replay's `outputHash` must **equal** the original `outputHash`. Only then is the
result deterministic and re-runnable by anyone.

```
transcript.replay.pristineCheckout == true
transcript.replay.outputHash       == transcript.outputHash
```

### The meta-oracle rule

Containment guarantees the *transcript* is real; it does **not** guarantee the
*probe tests the right thing*. A perfectly captured run can confidently
demonstrate a **non-bug** if the probe bakes in wrong assumptions or mocks its
way to a failure. So a `REPRODUCED` finding must demonstrate the failure
**through a real public entrypoint** — `entrypoint.kind` ∈ `{public_command,
public_api, cli, test_entrypoint}` — **never** an `agent_harness`. A transcript
whose entrypoint is an agent-built harness (or any non-public kind) is rejected.

```
transcript.entrypoint.kind  ∈ {public_command, public_api, cli, test_entrypoint}
transcript.entrypoint.kind  ≠ agent_harness    # the banned kind
transcript.entrypoint.ref   = e.g. "ai_router.contract_gate"
```

---

## How it is enforced

The Set 066 artifact validator
(`path_aware_critique.validate_path_aware_critique_artifact`) calls
`evidence_protocol.validate_finding_evidence` for every finding:

- no `evidenceTier`, or `ASSERTED` / `HYPOTHESIS` → **ok** (no transcript
  required; a transcript present on a non-`REPRODUCED` finding is optional
  supporting context, not deeply validated);
- an unknown `evidenceTier` → artifact **invalid** (`invalid-evidence`);
- `REPRODUCED` without a transcript, or with a transcript
  `validate_transcript` rejects → artifact **invalid** (`invalid-evidence`).

When the artifact is invalid, a set whose `pathAwareCritique` policy is
`required` cannot pass the close-out gate. A critique cannot **claim** a
reproduction it cannot back with a re-runnable transcript.

### What this protocol does NOT do (yet)

Session 1 ships the **protocol and the schema** only. The lanes that *generate*
the transcripts — trusted-command execution + `get_diff` + bounded probing (S2),
the probe-template lane (S3), and the Podman model-authored-probe lane (S4) —
land in later sessions and all feed findings through **this** protocol. The
ceiling→floor ratchet (S5) consumes a `REPRODUCED` transcript as a candidate
falsifier. Until those lanes land, every automated finding is `ASSERTED`
(read-only), exactly as before — the protocol is additive and changes no
existing behavior.
