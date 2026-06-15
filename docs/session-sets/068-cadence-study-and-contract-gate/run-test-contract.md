# `run_test` Execution-Cage Contract (Set 068 S1)

> **Status:** Pinned design contract for the disposable-worktree `run_test`
> execution cage (`ai_router/run_test_sandbox.py`) and its wiring into the
> Set 067 pull-verifier adapter. This is the flagged prerequisite from
> Session 1, Step 2: it nails the worktree lifecycle, the bounded command
> surface, the raw result shape, the caps, and the deterministic-servant
> discipline **extended to execution** before the implementation, so the
> Experiment B harness (S3) binds to one stable surface.
> **Created:** 2026-06-15 (Session 1).

---

## 1. Why a new tool needs a new discipline

The Set 067 read-only probes (`read_file` / `grep` / `list_dir`) are governed by
the **byte-equality** deterministic-servant guard (`_guard_raw_ground_truth`):
the driver re-derives ground truth from a canonical pure function and asserts the
servant's bytes match. That works because a read is **idempotent and
re-derivable**.

`run_test` is not. Executing a command is **non-idempotent and
non-re-derivable** (timestamps, ordering, durations differ run to run), so the
byte-equality guard cannot apply to it. Its trustworthiness rests on a different,
equally code-enforced discipline:

1. **Deterministic servant, extended to execution.** The tool returns the **raw**
   command result — exit code + captured stdout/stderr — never a model-summarized
   view. There is no model in the loop between running the command and recording
   its bytes; the orchestrator runs the subprocess itself and records what it
   returns verbatim (capped/elided exactly like a Set 067 read result).
2. **Disposable-CWD isolation — and its precise scope (NOT an OS sandbox).** The
   command runs with `cwd` set to a **disposable, detached git worktree** — a
   separate checkout of a pinned ref — so the command's ordinary
   working-directory writes (build artifacts, temp files, even commits) land in a
   checkout that is **discarded at teardown** and never touch the real tree's
   working copy. The real tree is never the cwd. **This is the actual
   guarantee, and it is bounded:** the cage is **not** an adversarial OS sandbox
   — there is no chroot / mount namespace / UID restriction / env scrub /
   filesystem mediation. A command that *deliberately* writes an **absolute
   path**, follows a **symlink committed into the tree**, discovers the main
   worktree via **`git worktree list`**, or **spawns a detached child** that
   outlives the timeout can still reach the real filesystem. Confining genuinely
   untrusted code is an **explicit non-goal** (it is a far larger surface than a
   bounded verification cage warrants). The discipline rests on (3): the command
   is **operator-authored and trusted**, and this set's use is the project's
   **own** test command on the project's **own** pinned snapshots (Experiment B),
   so the threat model is *accidental / incidental* writes by a trusted command,
   not a malicious payload.
3. **Bounded command surface.** The model **cannot author an arbitrary shell
   command.** `run_test` runs an **operator-configured argv** (`shell=False`),
   the project's test command. The model can only *trigger* it (and, optionally,
   *select* among a small set of named configured commands); it can never inject
   `rm -rf` or an absolute-path write of its own. This is what makes the
   disposable-CWD isolation meaningful: the command itself is operator-authored
   and trusted, only the *decision to run it* is the model's. It is **not** a
   substitute for an OS sandbox against a hostile command body — see (2).
4. **A cage that cannot be torn down is a hard failure, not a degradation.**
   Mirrors Set 067's `_safe` / `DeterministicServantViolation` posture: if the
   cage cannot be created, or **teardown does not fully complete** (the worktree
   registration or the temp tree survives), the run reports an explicit `ERROR:`
   (surfaced in the tool result text and the trace error bit), never a silently
   normal-looking result. The leak is verified after teardown via
   `git worktree list`.

---

## 2. The disposable-worktree lifecycle

```
create  ->  run (write-confined)  ->  teardown (ALWAYS, incl. on exception)
```

- **create.** From a pinned `ref` (a commit SHA / tag / branch), the cage runs
  `git worktree add --detach <cage-path> <ref>` into a fresh temp directory. The
  worktree is **detached** — it is an ephemeral verification cage, **not** a
  session-set worktree, so the canonical `ai_router.worktree` CLI's
  `session-set/<slug>` branch discipline does **not** apply. This is exactly the
  "I need a worktree outside the canonical layout" case the layout doc
  (`docs/planning/repo-worktree-layout.md`) reserves for **raw `git worktree
  add`** as the intentional escape hatch. The cage path lives under the system
  temp dir (`tempfile.mkdtemp`), never inside the canonical
  `<repo>-worktrees/` container, so it cannot be mistaken for session work or
  tripped over by the worktree CLI's drift classifier.
- **run.** The configured argv runs with `cwd=<cage-path>`, `shell=False`, a
  clean/inherited env, a **hard wall-clock timeout** (kill on overrun), and an
  **output byte cap** (stdout and stderr each capped + elided to a raw head
  slice with an explicit ASCII marker, like Set 067 reads).
- **teardown.** In a `finally` block — runs on success, on a failed command, on a
  timeout-kill, and on **any** exception in create/run. **Order matters for leak
  recovery:** `git worktree remove --force <cage-path>`, then a best-effort
  recursive delete of the temp parent, and **only then** `git worktree prune` —
  so a registration whose directory is now gone is deregistered even when
  `remove --force` failed (e.g. on a Windows file lock). After pruning, the cage
  path is checked against `git worktree list`; a **surviving registration is a
  leak** → `worktree_removed=False`, which the result surfaces as a hard `ERROR:`
  (see §4). Teardown is non-raising (it never raises over the original outcome),
  but a leak is **not** silently downgraded to metadata.

---

## 3. The bounded command surface

The cage **never** accepts a free-form shell string from the model. The command
is resolved from configuration:

- `pull_verifier.run_test.command` — the default argv list (e.g.
  `["python", "-m", "pytest", "-q"]`). `shell=False` always; the list is passed
  verbatim to `subprocess`.
- (Optional) `pull_verifier.run_test.commands` — a name->argv map; the `run_test`
  tool's optional `name` input selects among them. An unknown / absent name falls
  back to the default command (or a raw `ERROR:` if neither is configured).

The `run_test` tool input schema is therefore intentionally tiny:

```jsonc
run_test({ "name": string })   // OPTIONAL; selects a configured command. No "command", no "args".
```

There is **no** `command` or `args` field. A model that wants to "run the tests"
calls `run_test({})` (or `run_test({"name": "unit"})`); it cannot express
anything the operator did not pre-authorize.

---

## 4. The raw result shape

`run_test` returns a `RunTestResult` (raw, capped/elided — never summarized):

| Field | Meaning |
|---|---|
| `ran` | True iff the cage was created and the command was executed (NOT whether tests passed). |
| `exit_code` | the command's raw exit code; `None` if it was killed (timeout). |
| `timed_out` | True iff the wall-clock cap fired and the process was killed. |
| `output` | combined raw stdout+stderr, each capped/elided with an explicit `[... elided N bytes ...]` ASCII marker; never paraphrased. |
| `wall_seconds` | measured wall-clock of the command. |
| `command` | the resolved argv actually run (provenance). |
| `worktree_created` / `worktree_removed` | cage-lifecycle provenance for the trace. |
| `error` | a raw error string when the cage could not be created/confined (e.g. not a git repo, bad ref), else `None`. |

When surfaced to the model as a tool result, it is rendered as raw ASCII text:
the exit code, the timeout flag, and the captured output — the same raw-ground-
truth discipline as a Set 067 read. **Two failure modes render as a leading
`ERROR:`** (so the loop's `is_error` flags them): a cage-setup `error`, and a
**teardown that did not complete** (`worktree_removed=False`) — the latter is a
possible leak and is treated as a hard failure, not a normal-looking result.

---

## 5. Caps (`RunTestCaps`)

| Cap | Default | Behavior |
|---|---|---|
| `wall_seconds` | 120 | hard wall-clock; the process (tree) is killed on overrun (`timed_out=True`, `exit_code=None`). |
| `output_byte_cap` | 60000 | per-stream (stdout, stderr) byte cap; over-cap output is elided to a raw head slice. Matches the Set 067 `_RESULT_BYTE_CAP`. |

`run_test` is a **bounded verification cage, not a CI runner** (spec non-goal): a
single configured command, hard-capped, disposable. Cost accounting for the
*agent* loop stays in `PullCaps` (Set 067); the cage's own cost is the subprocess
wall-clock, bounded by `wall_seconds`.

---

## 6. Wiring into the Set 067 adapter (additive, opt-in)

- `run_test` is added to `pull_verifier`'s tool vocabulary, but it is **only
  offered when a cage is configured** (a `run_test_config` is passed to
  `pull_route`, carrying `repo_root`, `ref`, the resolved command, and caps).
  **Absent that config, the loop is byte-for-byte the Set 067 read-only loop** —
  no new tool is offered, the read-only default is unchanged, and every existing
  Set 067 test still holds. This keeps S1 strictly additive (spec Non-goals: the
  set is additive; the read-only toolset is not removed).
- In the loop, a `run_test` tool call is dispatched to the cage
  (`run_test_in_cage`), **not** to the read-only servant, and therefore **not**
  through `_guard_raw_ground_truth` (which only governs re-derivable reads — see
  §1). It is recorded in the trace as a real probe (`raw=True`), so a verdict
  informed by a `run_test` is correctly **not** a `zero_tool_calls` run.
- The live, end-to-end use of `run_test` inside a metered loop (build + test per
  staged snapshot) is **Experiment B (S3)**. S1 ships the cage, the registry
  wiring, the dispatch seam, and the unit tests; it does not run a metered loop.

---

## 7. Full `grep` ReDoS isolation relocated onto the cage machinery

Set 067 0.21.1 shipped a portable nesting-aware **heuristic**
(`_has_nested_quantifier`) as a stopgap because Python's `re` has no step/time
bound and a catastrophic-backtracking pattern can hang the orchestrator process.
The heuristic cannot be complete (it approximates; a novel catastrophic shape it
does not model would slip through). Set 068 relocates the **real** defense onto
the same subprocess/timeout machinery this cage introduces:

- **`re2` fast path.** If a linear-time engine (`re2` / `google-re2`) is
  importable, compile and search with it **inline** — linear time means ReDoS is
  impossible by construction, no subprocess needed.
- **Subprocess + hard-timeout fallback** (the live path here, since `re2` is not
  installed). The regex match runs in a **separate process** with a hard
  wall-clock timeout (a thread cannot interrupt a catastrophic `re` match — it
  holds the GIL — so a true kill requires a separate process). On overrun the
  worker is killed and the grep returns a raw `ERROR: grep pattern timed out`
  result, which the model sees and can recover from. The walk + sandbox
  confinement stay in the parent (`_walk_files` / `_within_sandbox` are
  unchanged); only the regex evaluation is isolated.
- **The heuristic stays as a cheap pre-filter only.** `_has_nested_quantifier`
  and the length cap still run first to reject obvious catastrophic patterns
  without paying for a subprocess; the isolation is the backstop for everything
  the heuristic does not catch. Defense in depth, not heuristic-as-sole-defense.

The S1 suite asserts a pathological pattern that *defeats the heuristic* is still
bounded by the isolation (killed by timeout, raw error returned) rather than
hanging.
