# Set 068 S1 -- Cross-provider verification ROUND 2 (gpt-5.4)

> Remediation re-verify of the R1 Critical/Major/Minor findings.

Round 2 re-verification:

- **Critical (write-confinement overclaim): NOT RESOLVED.**  
  The contract text is now much more honest about the scope, but `ai_router/run_test_sandbox.py` still contains stale absolute language in both the module summary (`"The real tree is never ... mutated"`) and `run_test_in_cage()` docstring (`"write-confined"` / `"never mutated"`), which conflicts with the later explicit carve-outs for absolute-path writes, committed symlinks, `git worktree list` discovery, and detached children. So the re-scoped claim is **closer**, but not yet internally consistent across the updated code/docs.

- **Major 2a (prune ordering leak): NOT RESOLVED.**  
  `_teardown()` now has the right high-level order and it does verify post-teardown registration state, but it still runs plain `git worktree prune` with no `--expire now`; that does not guarantee immediate pruning of a freshly-stale registration. The new `_worktree_registered()` check detects the leak and flips `removed=False`, but it does not reliably prevent the registered-worktree leak.

- **Major 2b (leak not surfaced): RESOLVED.**  
  `RunTestResult.render()` now emits a leading `ERROR: run_test cage: ... teardown did NOT complete ...` when `ran=True` and `worktree_removed=False`, and `_dispatch_run_test()` classifies that as an error via `startswith("ERROR: ")`; the new tests directly cover this path.

- **Minor 3 (corrupted partial regex line): RESOLVED.**  
  `isolated_regex_search()` now trims to the pre-marker text and drops the final partial line on elided worker output, which fixes the corruption bug; the added regression test for partial-line elision matches the failure I called out. The extra `sys.stdout.buffer` change in `regex_worker.py` also correctly fixes the Windows `\r` contamination discovered during remediation.

**NEW issue introduced by remediation:**

- **New Minor: teardown-error rendering now drops the raw command result entirely.**  
  On the `ran=True and not worktree_removed` path, `RunTestResult.render()` returns only a generic `ERROR:` sentence and omits the raw exit code/stdout/stderr, which conflicts with the module/contract's stated “raw exit code + captured output, never paraphrased” discipline and reduces diagnosability exactly on the unsafe-leak path.

```json
{"verdict":"ISSUES_FOUND","issues":[{"severity":"Critical","issue":"Re-scoped write-confinement claim is still not internally consistent","details":"The contract now correctly narrows the guarantee, but ai_router/run_test_sandbox.py still says in the module summary and run_test_in_cage() docstring that the real tree is 'never mutated' / the command is 'write-confined', which contradicts the explicit non-sandbox carve-outs for absolute-path writes, symlink escapes, main-worktree discovery, and detached children."},{"severity":"Major","issue":"Teardown leak recovery is still not guaranteed","details":"_teardown() now deletes before pruning and checks registration state, but it still calls plain `git worktree prune` instead of forcing immediate stale-entry cleanup (e.g. `--expire now`). That means a freshly-stale registration may still remain registered; the code now detects/surfaces that leak, but does not reliably prevent it."},{"severity":"Minor","issue":"Teardown-error render now suppresses raw command output","details":"When `ran=True` and `worktree_removed=False`, RunTestResult.render() returns only a generic ERROR line and drops the raw exit code/stdout/stderr. That is a new observability regression against the stated 'raw exit code + captured output, never paraphrased' result contract."}]}
```
