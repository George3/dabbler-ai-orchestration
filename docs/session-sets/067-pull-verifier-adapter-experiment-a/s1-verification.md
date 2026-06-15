# Set 067 S1 -- Cross-provider verification (gpt-5.4)

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Round 1.

Bottom line: **not verified**. The adapter gets several important things right, but I found one **critical** sandbox-confinenment defect and three **major** correctness holes.

The most important “right question differs from the posed one” point is this:

> `_safe()` in isolation is mostly fine.  
> The real confinement question is whether **every filesystem dereference** in every tool actually goes through that confinement check.

Here, `read_file` does, but `grep` does not for descendant files discovered during recursion.

## Focus review

### 1. Deterministic-servant guardrail

What is solid:

- `_guard_raw_ground_truth()` **does** reject a summarizing/paraphrasing servant on readable artifacts via exact content equality against `_CANONICAL[name](...)`.
- The explicit fake-`ERROR:` dodge on a readable file is correctly blocked by:
  ```python
  if result.content.startswith("ERROR: "):
      try:
          _CANONICAL[name](sandbox, args)
      except Exception:
          return
      raise DeterministicServantViolation(...)
  ```
  So “prefix `ERROR:` to a summary of a readable file” is **not** a hole.

What is **not** solid:

- The **error-result exemption is too broad**. If the canonical call raises, `_guard_raw_ground_truth()` accepts **any** `ERROR: ...` text. That means a servant can still inject model-authored text on failing probes and pass the guard.
  - Concrete case: missing file / invalid regex / non-directory `list_dir`.
  - Example bad servant result that currently passes:
    ```python
    ToolResult(
        content="ERROR: summary says the code probably has an auth bypass",
        raw=True,
        elided=False,
        bytes_total=0,
    )
    ```
    for a genuinely missing path.
- The elision path is also weaker than claimed because `_elide()` is not actually byte-capped; it is character-capped.

So the guardrail is **good against readable-content summaries**, but it is **not a full hard guarantee** over all tool results as claimed.

### 2. Sandbox confinement

`_safe()` itself correctly rejects:

- `../` escapes
- absolute escapes
- direct symlink escapes on the requested path

But overall confinement is **broken in `grep`**.

In `_canonical_grep()`:

```python
files = [root] if root.is_file() else [
    f for f in sorted(root.rglob("*")) if f.is_file()
]
...
for f in files:
    ...
    for i, ln in enumerate(
        f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
```

Only `root` is `_safe()`-checked. Each discovered `f` is then read directly.  
If the sandbox contains a symlinked file pointing outside the sandbox, `f.is_file()` will be true and `f.read_text()` will read the outside target.

Worse, this block:

```python
try:
    rel = f.resolve().relative_to(sandbox_real).as_posix()
except ValueError:
    rel = f.name
```

does not reject the escape; it silently relabels the leaked file with just its basename.

That is a real sandbox breakout.

### 3. Caps

What is correct:

- `max_turns` is enforced correctly by `for turn in range(caps.max_turns)`.
- Final-turn `force_verdict` is correct:
  ```python
  force_verdict = turn == caps.max_turns - 1
  ```
- `submit_verdict` is correctly excluded from `tool_call_count`.

What is **not** correct:

- `token_budget` and `cost_ceiling_usd` are only checked **before** the next call, using already-incurred totals:
  ```python
  if trace.input_tokens + trace.output_tokens >= caps.token_budget: ...
  if trace.cost_usd >= caps.cost_ceiling_usd: ...
  response = binding.request(...)
  ```
  So one more API call can always overshoot both ceilings.
- The tests explicitly pin that overshoot behavior (`test_cost_ceiling_cap` asserts `cost_usd > 0.01`).

That means these are not hard ceilings; they are post-hoc stop conditions.

Also: when `config=None`, `_provider_config()` lazily loads config, but `_pricing_for(model, config)` still gets the original `None`, so configured pricing is ignored on the default path.

### 4. Forced verdict parsing

Mostly good:

- `_parse_verdict()` does enforce:
  - non-empty `verdict`
  - findings as a list
  - non-empty `findings[i].description`

That matches the user’s cited Set 066 concerns.

Caveat:

- `_verdict_tool_schema()` marks `summary` as required, but `_parse_verdict()` does **not** reject a missing summary; it coerces it to `""`.
- From the excerpt you gave, I would not call this a definite Set 066 violation, but it is inconsistent with this module’s own declared tool schema.

### 5. Zero-tool-call accounting

Verified correct.

- `trace.tool_calls` is only appended for probe calls.
- `submit_verdict` is excluded.
- A no-probe verdict yields:
  - `zero_tool_calls == True`
  - `ok == False`

That matches the contract.

### 6. Seam correctness

Verified.

- `pull_route()` is a separate entrypoint.
- It does not call `route()` or `call_model()`.
- The loop driver is neutral over `ProviderBinding.request(...)`.
- `_BINDINGS` intentionally only contains Anthropic in S1; that is consistent with scope.

### 7. Test quality

The suite is not vacuous, but it misses several load-bearing cases:

- No symlink-in-tree confinement test for `grep`.
  - `TestSafe` only tests `_safe()` directly, not actual recursive tool behavior.
- No test for the **arbitrary `ERROR:` text** hole when canonical also fails.
- No multibyte UTF-8 test for the claimed **byte cap**.
- The cost-cap tests currently pin the overshoot behavior rather than forbidding it.

So the tests do **not** fully pin invariants 1–3 as claimed.

{"verdict":"ISSUES_FOUND","issues":[{"severity":"Critical","claim":"Sandbox confinement prevents symlink escapes","problem":"`_canonical_grep()` only applies `_safe()` to the root path. It then walks `root.rglob('*')` and reads each `f` via `f.read_text(...)` without re-checking that `f.resolve()` remains inside the sandbox. An in-sandbox symlink to an outside file will therefore be read. The later `relative_to(sandbox_real)` / `except ValueError: rel = f.name` logic even disguises the escape instead of rejecting it.","fix":"In `grep`, resolve and confine every candidate file before reading it. Prefer a traversal that does not follow symlinked directories (e.g. `os.walk(..., followlinks=False)`), and reject or skip any file whose real path is outside `sandbox.resolve()`. Add tests with symlinked files and symlinked directories inside the sandbox."},{"severity":"Major","claim":"The deterministic-servant guard makes summarizing/paraphrasing servants a hard failure","problem":"`_guard_raw_ground_truth()` has an overly broad error exemption: if `result.content.startswith('ERROR: ')` and the canonical tool also raises, it returns without validating the error text. That allows arbitrary model-authored `ERROR: ...` summaries to pass the guard on failing probes (missing file, invalid regex, wrong path type, etc.), which violates the claimed hard deterministic-servant property for all tool results.","fix":"Canonicalize error results too. Run the canonical tool under the same wrapper semantics as `DeterministicServant.run()` and require exact equality on `content`, `raw`, `elided`, and `bytes_total` for both success and error outcomes."},{"severity":"Major","claim":"Per-result elision is a real byte cap","problem":"`_elide()` computes `bytes_total` in UTF-8 bytes but decides whether to elide with `len(text) <= _RESULT_BYTE_CAP` and slices with `text[:_RESULT_BYTE_CAP]`. For multibyte content, a result can exceed the advertised 60,000-byte cap substantially, and the elision marker's dropped count is in characters, not bytes. This breaks the stated byte-cap contract and weakens token-budget protection.","fix":"Apply the cap to encoded bytes, then decode a codepoint-aligned prefix. Compute dropped bytes from actual byte lengths. Add tests using multibyte UTF-8 content."},{"severity":"Major","claim":"`token_budget` and `cost_ceiling_usd` are enforced as hard ceilings with correct accounting","problem":"In `pull_route()`, token and cost limits are only checked at the top of the loop against spend from prior turns, so one more `binding.request(...)` can exceed either ceiling before the stop condition fires. The tests explicitly encode this overshoot behavior. Separately, when `config=None`, `_provider_config()` lazily loads config but `_pricing_for(model, config)` still receives `None`, so configured model pricing is ignored on the default path.","fix":"Either relax the contract/tests to describe these as post-hoc soft ceilings, or add a preflight estimate (prompt/input-token estimate plus `max_output_tokens`) and refuse a call whose worst-case spend exceeds the remaining budget. Also pass the loaded top-level config through to `_pricing_for()` so configured pricing is used on the default path."}]}
