## pass-b — openai (model=gpt-5-4, in=4363 out=8000 cost=$0.1309)

Below is the strongest case **against** the author’s most consequential choices, with a hard final call on each.

## 1) Q1/Q3 — network-fetched GitHub manifest on every session start

### Strongest counter-argument
As proposed, this is **over-engineering on the hot path**.

- **You’re adding a network dependency to every session start for a non-fatal fact.** Old schema is explicitly acceptable. That alone kills the case for a live fetch in the startup path.
- **It does not actually solve the incident path cleanly.** The incident was:
  1. no hook, and
  2. ancient pinned router.
  
  A manifest fetch only helps if the repo already has the new checker/hook installed. A repo pinned to `ai_router 0.1.1` does not magically gain `check_migrations` because GitHub is reachable.
- **The constant already exists in code.** A constant + release/CI guard is boring, but robust. For runtime behavior, boring wins.
- **You are creating new failure modes for negligible operational benefit:** latency, GitHub outages, raw.githubusercontent throttling, enterprise/firewalled environments, privacy leakage, and nondeterministic startup behavior.
- **“Authoritative when reachable” is a trap.** If the manifest says schema `5` before the router/migrators/docs are actually released everywhere, clients learn about a future they cannot handle. Best case: noise. Worst case: wrong guidance.
- **`raw` on `master` is the wrong source.** Not because GitHub serves a “half-merged file” — it won’t. The real risk is **branch-head skew**:
  - manifest merged before package release
  - manifest ahead of migrators/docs
  - CDN/cache inconsistency by ref
  - mutable branch tip, not an immutable release artifact

In short: this is runtime complexity to patch over release/versioning discipline.

### Why it **isn’t** over-engineering
There is one real argument for it:

- **A remote manifest is the only way to teach stale installs about newer schema without first upgrading code.** A local constant + CI only protects this repo; it does nothing for consumer repos pinned to old router versions.
- If the actual product goal is **“surface canonical schema currency to pinned consumers without requiring a dependency bump”**, then some out-of-band artifact is justified.

That said: even if you buy that goal, it still does **not** justify a live fetch on every session start from `raw/master`.

### Raw-on-master vs tag
- **“Half-merged manifest” is the wrong fear.** GitHub won’t hand you a physically torn file.
- **The real danger is mutable HEAD getting ahead of releases.**
- If a manifest exists, it should be tied to an **immutable release boundary**:
  - release asset
  - immutable tag
  - package metadata published with the router release

### FINAL call
**Compromise X.**

- **Do not fetch a manifest on every session start.**
- Runtime truth for the checker should be the **installed router constant**.
- If you keep a manifest, make it **advisory**, **cached/off-hot-path**, and **release-coupled**:
  - explicit refresh command
  - daily cache
  - CI/release verification
  - Explorer/manual “check for newer schema”
- **Never use raw `master` as authoritative runtime input.**

So: **Q1 and Q3 should change.**  
Q2 then becomes subordinate: any advisory fetch should be fail-open and cached, not on the startup path.

---

## 2) Q6 — folding drift check into existing `start_session` SessionStart invoker

### Strongest counter-argument
This is bad coupling.

- **`start_session` is a write-path/orchestration concern.** Drift detection is a read-only hygiene/audit concern. They are not the same thing.
- **A repo should be able to adopt the guard without adopting the orchestrator-writer hook.** The proposal denies that.
- **You’re tying the guard to the exact mechanism implicated in the incident.** If the router is stale/missing, `python -m ai_router.check_migrations` is unavailable. A separate lightweight hook could still work.
- **It muddies failure modes and ownership.**
  - Did startup fail because session scaffolding failed?
  - because drift check failed?
  - because Python env is broken?
  - because router version is old?
  
  One hook now multiplexes unrelated responsibilities.
- **It blocks clean rollout.** Some repos will want “warn me about schema drift” but not “install the full orchestrator writer flow.”
- **It hurts testability and ops.** Separate tools can have separate exit codes, telemetry, and adoption paths.

The strongest architectural point: **the drift check is trivial deterministic filesystem logic. It does not need to be entangled with the writer path at all.**

### FINAL call
**Compromise X.**

- Make drift detection a **separate single-purpose command/hook**.
- The installer may still generate **one SessionStart wrapper script** if the host only allows one hook entry, **but that wrapper must chain two independent concerns**:
  1. orchestrator/session-start
  2. schema-drift check
- They must be **independently installable/configurable**.
- Strongly prefer a **JS-side fallback** for the drift scan so stale/no-router repos still get protection.

So: