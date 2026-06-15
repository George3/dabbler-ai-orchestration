# Change Log — Set 068 (Cadence Study + Contract-Test Gate)

## Session 1 of 6 — `run_test` disposable-worktree sandbox + tool (+ ReDoS isolation)

**Status:** CLOSED, VERIFIED (gpt-5.4 R1→R3). No release (Session 6 ships the
PyPI bump). Full `ai_router` suite green.

### Shipped

- **`ai_router/run_test_sandbox.py`** — the execution cage:
  - `run_subprocess_capped()` — shared `shell=False` subprocess primitive: hard
    wall-clock timeout that **kills the process tree** on overrun (Windows
    `taskkill /T`, POSIX `killpg`), temp-file-bounded per-stream output cap with
    raw head-slice elision (bounded memory even under a flood).
  - `run_test_in_cage()` — creates a **disposable, detached** git worktree from a
    pinned ref (raw `git worktree add` — the intentional escape hatch from the
    worktree-layout doc — under the system temp dir, never the canonical
    container), runs the operator-configured argv with `cwd` = the throwaway
    checkout, and tears the worktree down on **every** exit path (success /
    failed command / timeout-kill / exception) via `finally`:
    `remove --force` → `rmtree` → `git worktree prune --expire now` → verify no
    registration leaked. A teardown leak (`worktree_removed=False`) renders as a
    leading raw `ERROR:` (flagged as an error probe) while **preserving** the raw
    exit + output for diagnosis.
  - `run_test_caps_from_config()` — reads the new `pull_verifier.run_test.caps`
    block.
- **`ai_router/regex_worker.py`** + **`isolated_regex_search()`** — the relocated
  `grep` ReDoS defense: an `re2` inline fast path when available, else the regex
  evaluation runs in a **killable subprocess** bounded by the cage's hard timeout,
  so a catastrophic pattern that **defeats** the 0.21.1 nesting-aware heuristic is
  killed, not hung. The heuristic is demoted to a cheap **pre-filter** only; the
  walk + sandbox confinement stay in `_canonical_grep` (only the regex eval is
  isolated).
- **`pull_verifier.py` wiring** — `RunTestConfig`, `_run_test_tool_schema()`,
  `_dispatch_run_test()`. `run_test` is **offered only when a `RunTestConfig` is
  passed** to `pull_route()`; absent that, the offered tools are byte-for-byte the
  Set 067 read-only set (additive). It is dispatched to the cage **outside** the
  byte-equality guard (execution is non-re-derivable) and recorded as a real
  probe (so a verdict informed by it is not a `zero_tool_calls` run).
- **`router-config.yaml`** — `pull_verifier.run_test.caps` (wall-clock + output
  cap). **`__init__.py`** — exports for the new surface.
- **`run-test-contract.md`** — the pinned design contract.

### Scope correction (verification-driven)

The cage is **disposable-CWD isolation of a TRUSTED command** (the project's own
test command on its own pinned snapshots — Experiment B's threat model), **not an
OS sandbox**. It does not confine absolute-path writes, committed symlinks,
`git worktree list` main-worktree discovery, or detached children; confining
untrusted code is an explicit non-goal. The module docstring, contract, and tool
description were re-scoped to state this precisely (R1 Critical, per L-064-8).

### Tests

29 new tests (25 in `test_run_test_sandbox.py` + 4 `run_test` wiring tests in
`test_pull_verifier.py`): cage lifecycle + always-teardown (incl. on exception),
timeout-kill, output cap, write-confinement (real tree untouched), teardown-leak
detection + ERROR surfacing + raw-output preservation, caps-from-config, ReDoS
isolation of a heuristic-defeating pattern, elided-output partial-line drop, and
the Windows `\r` multi-match regression. No metered calls in the suite.

### Verification

gpt-5.4 (openai, high effort), cross-provider: **R1** ISSUES_FOUND (Critical
write-confinement overclaim + Major teardown prune-order / leak-surfacing + Minor
elision partial-line; **also** caught a latent Windows `\r` multi-match grep bug
while writing the Minor test) → **R2** ISSUES_FOUND (Critical re-scope echoes
still in two docstrings per L-065-1; Major `prune --expire now`; new Minor
leak-render dropped raw output) → **R3 VERIFIED**. ~$0.436.

### Deferred to later sessions

The live metered build-and-test-per-snapshot use of `run_test` is **Experiment B
(Session 3)**. The symmetric Experiment A re-grade + Experiment B pre-registration
are **Session 2**. No release until **Session 6**.
