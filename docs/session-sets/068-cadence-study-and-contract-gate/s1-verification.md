# Set 068 S1 -- Cross-provider verification (gpt-5.4)

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Round 1.

I would **not** sign off this session as-is.

What looks solid:
- `run_subprocess_capped()` does use temp-file capture, so normal stdout/stderr flooding does not blow orchestrator memory before timeout/readback.
- The additive wiring in `pull_verifier.pull_route()` looks correct from the diff: `run_test` is only offered when `run_test_config` is non-`None`, and the read-only tools still go through `_guard_raw_ground_truth`.
- The regex fallback is genuinely moved into a killable subprocess, so catastrophic backtracking no longer hangs the parent on the normal fallback path.

But I found three real issues.

### 1) Core safety claim is false: this is **not** write-confined against untrusted code
The contract claims “the real tree is never mutated” because:
- cwd is the disposable worktree, and
- the model cannot author an arbitrary shell command.

That is not enough.

In `run_test_in_cage()`, the only confinement is:

```python
run = run_subprocess_capped(
    cmd,
    cwd=cage,
    timeout_seconds=caps.wall_seconds,
    output_byte_cap=caps.output_byte_cap,
)
```

There is **no OS sandbox**: no chroot/container/mount namespace, no restricted UID, no path mediation, no env scrub. The fixed argv is operator-authored, but that argv is specifically a test/build command that executes **repository code and tests**, which are the untrusted thing under verification.

So a repo under test can:
- write to absolute paths directly,
- follow symlinks committed into the repo/worktree to escape,
- run `git worktree list --porcelain` to discover the main worktree path and write into it,
- spawn a detached child and continue writing after timeout.

This means the important question is not “can the model inject a shell string?” but “can the fixed test command execute untrusted code that writes outside the worktree?” The answer is **yes**.

The existing test `test_write_cannot_escape_real_tree_untouched()` only checks a trivial relative write (`open('escaped.txt', 'w')`). It does **not** pin the actual claimed safety property.

### 2) Teardown can leak a registered worktree, and leak is not surfaced as a hard error
`_teardown()` currently does:

```python
rm = _git(repo_root, "worktree", "remove", "--force", str(cage))
...
_git(repo_root, "worktree", "prune")
shutil.rmtree(parent, ignore_errors=True)
if parent.exists():
    removed = False
return removed
```

Two problems here:

#### 2a) Prune ordering is wrong for leak recovery
If `git worktree remove --force` fails, but the subsequent `shutil.rmtree(parent)` does delete the directory, `git worktree prune` has already run **too early**. That stale registration is never pruned in this function.

So yes: a worktree can leak registered with git.

#### 2b) Teardown failure is silently downgraded to metadata
`run_test_in_cage()` returns:

```python
return dataclasses.replace(base, worktree_removed=removed)
```

But `RunTestResult.render()` ignores `worktree_removed`; it only emits `ERROR:` when `error` is set. Then `_dispatch_run_test()` classifies failure with:

```python
is_error = content.startswith("ERROR: ")
```

So a teardown failure can produce an apparently normal successful tool result with `worktree_removed=False` hidden only in structured state, not in the tool text or trace error bit. That contradicts the stated “cage escape is a hard failure” posture.

Tests miss this: `test_teardown_on_exception()` proves `finally` runs when `run_subprocess_capped` raises, but there is **no** test for `git worktree remove` failure or for “teardown failure must surface as an error”.

### 3) `isolated_regex_search()` can return a corrupted truncated match line
In the elided-worker-output path:

```python
lines = run.stdout_text.split("\n")
if run.stdout_elided:
    lines = [ln for ln in lines if not ln.startswith("[... elided ")]
    if lines:
        lines = lines[:-1]
return lines
```

This does **not** reliably drop the partial trailing match line.

Why: `_ELISION_MARKER` ends with a trailing newline, so `split("\n")` usually yields a final `""`. The `lines[:-1]` drops that empty string, not the truncated match line before it.

Result: a worker stdout cut mid-line can leak a corrupted `rel:lineno:par...` entry back to the caller, violating the contract’s “no corrupted match line” claim.

There is no test covering this partial-line elision case.

---

### Focus-by-focus summary
1. **Crash-safe teardown:** `finally` is present, but teardown can still leak git registration; failure is not escalated.
2. **Write confinement:** not airtight; fixed command surface does not sandbox untrusted repo code.
3. **Timeout kill:** normal process-group kill is fine for ordinary children, but detached children can outlive it; this compounds issue #1.
4. **Output cap:** normal subprocess output cap is genuinely bounded via temp files + capped readback.
5. **ReDoS isolation:** timeout backstop is real, but elided output post-processing is buggy.
6. **Wiring correctness:** opt-in offering/dispatch looks correct from the diff.
7. **Tests:** good happy-path coverage, but they do not pin the real confinement claim, teardown-remove failure, or corrupted partial regex-line handling.

{"verdict":"ISSUES_FOUND","issues":[{"severity":"Critical","claim":"`run_test` write-confinement means the real tree is never mutated","problem":"`run_test_in_cage()` only changes `cwd` to the disposable worktree and runs a fixed argv. That argv executes untrusted repository code/tests with full filesystem access and inherited environment. Such code can write absolute paths, follow symlinks out of the worktree, enumerate `git worktree list` to find the main worktree, or spawn detached children. So the implementation does not actually confine writes to the disposable worktree.","fix":"Either add a real OS sandbox (container/chroot+mount namespace/read-only binds/separate UID/landlock, etc.) around the test command, or narrow the contract/docs to explicitly say this is only command-selection control, not filesystem confinement. Add tests for absolute-path/symlink/main-worktree discovery escapes."},{"severity":"Major","claim":"Crash-safe teardown prevents git worktree leaks and treats cage escape as a hard failure","problem":"`_teardown()` runs `git worktree prune` before `shutil.rmtree(parent)`. If `git worktree remove --force` fails but the directory is later deleted, the stale registration is never pruned. Also `run_test_in_cage()` only records `worktree_removed=False`; `RunTestResult.render()` ignores that field, so `_dispatch_run_test()` does not surface teardown failure as an error probe. A registered worktree can therefore leak, and the caller may still see an apparently normal result.","fix":"On teardown failure paths, delete the directory first if needed, then run `git worktree prune`, and verify unregistration via `git worktree list --porcelain` or equivalent. If teardown does not complete, set `error`/render `ERROR:` so the cage escape is a hard failure. Add a test that forces `git worktree remove` to fail and asserts both no registration leak and error surfacing."},{"severity":"Minor","claim":"Elided regex-worker output never returns a corrupted partial match line","problem":"In `isolated_regex_search()`, when `run.stdout_elided` is true, the code filters out the marker line and then does `lines = lines[:-1]`. Because the elision marker itself ends with a newline, `split(\"\\n\")` usually leaves a final empty string, so `[:-1]` drops the empty element rather than the partial trailing match line. A truncated `rel:lineno:...` line can therefore be returned.","fix":"Strip the elision marker before splitting, or inspect the pre-marker text and explicitly drop the final real line when the capture ended mid-line. Add a test that forces worker stdout elision in the middle of a match line and asserts no partial line is returned."}]}
