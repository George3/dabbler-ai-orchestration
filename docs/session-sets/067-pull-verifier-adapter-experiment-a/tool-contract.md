# Pull-Verifier Tool Contract (Set 067 S1)

> **Status:** Pinned design contract for the first-party tool-loop "pull"
> verifier adapter (`ai_router/pull_verifier.py`). This is the flagged
> prerequisite from Session 1, Step 2: it nails the read-only toolset
> signatures, the deterministic-servant return shapes, the forced verdict
> schema, and the caps/trace contract **before** the implementation so the
> S2 OpenAI/Gemini bindings and the S3 experiment harness all bind to one
> stable surface.
> **Created:** 2026-06-15 (Session 1).

---

## 1. The seam — `pull_route()` is parallel to `route()`, not nested in it

`route()` / `ai_router.providers.call_model` is a **single-shot,
text-in/text-out** path (verified at `ai_router/providers.py`: one
`client.post`, one `APIResult`, no tool loop). A "pull" verifier is an
**agentic executor**: the verifier drives a multi-turn tool-use loop and the
orchestrator answers tool calls. These are different control structures, so
the adapter is a **new first-class entrypoint** (`pull_route()` in
`ai_router/pull_verifier.py`), **not** a new "provider kind" inside `route()`.

The two share the provider *config* (`router-config.yaml` `providers:` block:
`api_key_env`, `base_url`, `api_version`, `timeout_seconds`, `retry`) but not
the call path.

```
pull_route(
    sandbox_dir,        # the read-only review sandbox (repo root / frozen tree)
    instruction,        # the critique task (what to review, what to look for)
    *,
    provider="anthropic",
    model=None,         # defaults from the executor config block (S2); S1 pins a model
    caps=None,          # PullCaps; defaults below
    config=None,        # loaded router config; loaded on demand if None
    binding=None,       # ProviderBinding override (tests inject a fake)
    servant=None,       # DeterministicServant override (tests inject a bad servant)
) -> PullResult
```

`pull_route()` **never** mutates the sandbox and **never** routes the loop
through `route()`. It is read-only by construction (Section 3).

---

## 2. The deterministic-servant guardrail (load-bearing)

The single property that makes a "pull" review trustworthy: **every tool
result is raw ground truth — file bytes, raw `grep` lines, a directory
listing — never a model-summarized or paraphrased view.** This is the
anti-bias property. The whole point of path-aware critique (Set 065 C9/C3
evidence) is to remove the biased context-assembler; a servant that
summarized would re-introduce exactly the bias the design exists to kill.

**Enforcement is code, not aspiration.** The canonical deterministic
functions (`_canonical_read_file` / `_canonical_grep` / `_canonical_list_dir`)
are the source of truth for what ground truth *is*. The pluggable
`DeterministicServant` produces each candidate `ToolResult`; the loop driver
then independently re-derives ground truth from the canonical function and
**asserts byte-equality** (or, for an elided result, that the content is a raw
contiguous slice of ground truth). A servant that paraphrases, summarizes, or
otherwise touches the bytes fails the assert and raises
`DeterministicServantViolation` — a **hard failure**, not a warning. The S1
test suite injects a summarizing servant and asserts the violation fires.

Elision is the one permitted transform and it is still raw: when an artifact
exceeds the per-result byte cap, the canonical function returns a raw
head slice with an explicit `[... elided N bytes ...]` ASCII marker and sets
`elided=True` and `bytes_total` to the full size. Elision is deterministic
(same input → same slice) and visible in the trace; it never paraphrases.

---

## 3. Read-only toolset (this set) — signatures and return shapes

Three probe tools, all sandbox-confined and read-only. The `run_test`
execution tool (the only one needing a disposable-worktree cage) is **Set
068** and is deliberately absent here.

| Tool | Input schema | Returns (raw ground truth) |
|---|---|---|
| `read_file` | `{ "path": string }` (required) | the file's full raw UTF-8 text (decode errors replaced), elided to a raw head slice if over the byte cap |
| `grep` | `{ "pattern": string (required), "path": string (optional, default ".") }` | raw matching lines, one per line, formatted `relpath:lineno:line` (the line text is verbatim); `(no matches)` when none |
| `list_dir` | `{ "path": string (optional, default ".") }` | newline-joined sorted entry names (`name/` suffix marks a directory) |

**Sandbox confinement (`_safe`).** Every `path` is resolved against the
sandbox and must remain inside it. The hardened `_safe()` rejects: absolute
paths that escape, `..` traversal that escapes, and symlinks whose real target
escapes (`Path.resolve()` collapses symlinks, then a real-prefix check). A
rejected path returns a raw `ERROR: path escapes sandbox: <p>` tool result
(the servant surfaces errors as raw text, never hides them) — it does **not**
crash the loop, so the model can recover. The S1 suite asserts a `../`-escape
and an absolute-path escape are both refused.

**Confinement covers *every* dereference, not just the requested path.**
`grep` walks the tree, so confining only its root would leak any in-sandbox
symlink pointing outside. The canonical grep walks with
`os.walk(followlinks=False)` (symlinked *directories* are never descended) and
confines every discovered *file* with a real-path check before reading it
(`_within_sandbox`) — a symlinked file whose target leaves the sandbox is
**skipped**, never read or relabelled. The S1 suite asserts an in-sandbox
symlink to an outside file does not leak through `grep`.

All three tools are **read-only**: there is no write/edit/delete tool in the
registry, so the loop cannot mutate the sandbox even in principle.

---

## 4. The forced verdict — matches the Set 066 critique-entry shape

The loop terminates when the verifier emits a structured verdict, forced via a
**control tool** `submit_verdict`. Its input schema is the Set 066
`path-aware-critique.json` **critique entry** (`docs/path-aware-critique.schema.json`
`$defs/Critique`), so an adapter-produced critique drops straight into the
artifact the close-out gate already validates (the S4 producer wiring):

```jsonc
submit_verdict({
  "verdict": string,            // required, non-empty (e.g. "VERIFIED", "ISSUES_FOUND")
  "summary": string,            // the prose verdict / what was reviewed
  "findings": [                 // 0+ structured findings
    {
      "description": string,    // required, non-empty
      "severity": string,       // optional loose string
      "category": string        // optional loose string
    }
  ]
})
```

`provider` and `model` are stamped by the adapter (the verifier never reports
its own identity), completing the full critique entry
(`provider`/`model`/`verdict`/`summary`/`findings`). The adapter validates the
forced verdict against this shape and raises if the verdict is missing/empty;
a single critique entry it emits is guaranteed to satisfy the per-entry
structural rules of `validate_path_aware_critique_artifact` (the multi-provider
≥2-distinct-providers rule is satisfied by S2 running ≥2 providers and S4
assembling their entries into one artifact).

`submit_verdict` is a **control** tool, not a probe — it is **not** counted in
`tool_call_count`, so a run that submits a verdict without ever probing the
repo is correctly recorded as a `zero_tool_calls` (failed) run.

---

## 5. Caps + trace (capped and instrumented)

**Caps (`PullCaps`).** Every run is bounded on four axes; the loop stops at the
first ceiling reached and records which one in `trace.stop_reason`:

| Cap | Default | Stop reason |
|---|---|---|
| `max_turns` | 12 | `max-turns` |
| `max_output_tokens` (per API call) | 4096 | (bounds each call) |
| `token_budget` (cumulative in+out) | 200000 | `token-budget` |
| `cost_ceiling_usd` (cumulative metered) | 1.00 | `cost-ceiling` |

`max_turns` and `max_output_tokens` are **hard** pre-call bounds. `token_budget`
and `cost_ceiling_usd` are **post-hoc stop conditions**, checked at the top of
each turn against spend already incurred: a single in-flight call may overshoot
its ceiling by its own cost, because token usage is not known until the call
returns (this matches `route()` / the spike and is the realistic floor for a
metered loop). They bound the *number* of further calls, not the exact spend of
the current one. On the final permitted turn the binding is asked to **force**
`submit_verdict` (provider `tool_choice`) so a capped run still yields a verdict
where possible.

**Trace (`PullTrace`).** Instrumentation proving probes actually run, not
merely afforded (Set 065 signature):

- `tool_calls`: per call `{ turn, name, args, raw, elided, result_chars, error }`
  for every probe (the raw/elided flag is the proof the servant returned
  ground truth);
- `api_turns`, `input_tokens`, `output_tokens`, `cost_usd`, `wall_seconds`;
- `tool_call_count` (probe calls only), `zero_tool_calls`
  (True when a verdict was produced with **no** probe — a **failed run, not a
  fast one**), `stop_reason`.

`PullResult.ok` is True **iff** a schema-valid verdict was forced **and** at
least one probe ran (`not zero_tool_calls`).

---

## 6. Provider-agnostic driver, per-provider binding (S1 = Anthropic)

The loop driver is provider-neutral: it operates on a neutral transcript
(`user` / `assistant`+tool_calls / `tool` results) and a `ProviderBinding`
translates that transcript to/from the provider wire format and reports a
neutral `BindingResponse(text, tool_calls, input_tokens, output_tokens,
stop_reason)`. S1 ships `AnthropicBinding` (`tool_use` blocks). S2 adds
`OpenAIBinding` (`tool_calls` / Responses API) and `GeminiBinding`
(`function_declarations`) behind the **same** driver — the driver does not
change. The binding registry (`_BINDINGS`) raises a clear `NotImplementedError`
for providers not yet bound, so S2 is a pure addition.
