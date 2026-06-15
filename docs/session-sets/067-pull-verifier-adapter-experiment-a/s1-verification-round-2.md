# Set 067 S1 -- Cross-provider verification (gpt-5.4) ROUND 2

> Independent verifier: gpt-5.4 (openai). Post-remediation re-review.

Round-1 findings re-review:

- [Critical] grep sandbox breakout — RESOLVED: `_canonical_grep()` now gets candidates from `_walk_files(root, sandbox_real)`, and `_walk_files()` uses `os.walk(..., followlinks=False)` plus `_within_sandbox(f, sandbox_real)` before any `f.read_text(...)`.
- [Major] over-broad error exemption in the servant guard — RESOLVED: `_canonical_result()` canonicalizes both success and exception paths into a full `ToolResult`, and `_guard_raw_ground_truth()` now field-compares `content/raw/elided/bytes_total` against that canonical result.
- [Major] char-cap vs byte-cap elision — RESOLVED: `_elide()` now does `data = text.encode("utf-8")`, caps on `len(data)`, slices `data[:_RESULT_BYTE_CAP]`, decodes with `errors="ignore"`, and reports dropped bytes from encoded lengths.
- [Major] config=None pricing bug — RESOLVED: `pull_route()` now loads config once (`if config is None: config = _load_router_config()`) and passes that same resolved `config` to both `_provider_config(...)` and `_pricing_for(model, config)`.
- [Major, accepted overshoot] token/cost ceilings overshoot by one in-flight call — RESOLVED: the code still checks `trace... >= caps...` only before `binding.request(...)`, and `tool-contract.md` §5 now explicitly documents `token_budget`/`cost_ceiling_usd` as post-hoc stop conditions, matching the implementation.
- [Minor] tool-schema/parser summary inconsistency — NOT-RESOLVED: `_verdict_tool_schema()` still requires `"summary"`, but `_parse_verdict()` still coerces missing `summary` to `""` and accepts findings-bearing payloads, so schema and parser are still not aligned.

New defect introduced by the fixes:

- [Major] `_walk_files()` no longer restricts grep to regular files: it appends every `os.walk(...).filenames` entry after `_within_sandbox()` without checking `f.is_file()`/regular-file type, and `_canonical_grep()` then blindly does `f.read_text(...)`; a broken in-tree symlink now turns recursive grep into `ERROR`, and other non-regular entries would also be probed instead of skipped.

{"verdict":"ISSUES_FOUND","issues":[{"severity":"Major","claim":"Recursive grep only reads regular in-sandbox files after the sandbox hardening","problem":"`_walk_files()` now appends every `os.walk(...).filenames` entry after `_within_sandbox()` (`for name in sorted(filenames): ... found.append(f)`) without checking `f.is_file()`/regular-file type, and `_canonical_grep()` then blindly `f.read_text()`s each one. A broken in-tree symlink can now make a whole recursive grep return `ERROR`, and other non-regular entries would also be probed.","fix":"Filter `_walk_files()` to regular files only (e.g. `f.is_file()` or `stat.S_ISREG` after confinement) and/or catch per-file `OSError` in `_canonical_grep()` so broken/unreadable/non-regular entries are skipped instead of aborting the grep."},{"severity":"Minor","claim":"Tool schema and verdict parser are aligned on summary requirements","problem":"`_verdict_tool_schema()` still declares `required: ['verdict', 'summary']`, but `_parse_verdict()` still coerces missing `summary` to `''` and accepts findings-bearing payloads, so the declared tool schema and parser behavior remain inconsistent.","fix":"Either remove `summary` from `_verdict_tool_schema().parameters.required` or make `_parse_verdict()` reject missing/empty `summary` whenever the schema says it is required."}]}
