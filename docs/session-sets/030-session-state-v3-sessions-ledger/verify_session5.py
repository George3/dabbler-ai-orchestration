"""Session 5 verification driver — Set 030.

Round A bundles the AI-strategy surface — the highest-risk Session 5
addition. The other deliverables (scanState manager, loading
sentinel, viewsWelcome `when` clause, needs-migration badge, the
extension's migrateSet command) are visually exercised by the new
Layer 3 Playwright smokes (loading-state.spec.ts + migration-cta.spec.ts,
both green) and the Layer 2 ts-stub harness; they're not in this
bundle because the failure modes are observable in rendered text.

The AI strategy is structurally different: a model call inside a
migration writer with four distinct failure modes and a
RouteResult-handling invariant from memory
`feedback_ai_router_route_result_handling`. None of that surfaces as
rendered text — bugs would surface only as silent corrupt
state-file writes. That's exactly the kind of code review is for.

Per memory `feedback_split_large_verification_bundles`, the bundle
is sliced to keep it under 700 LOC. Per memory
`feedback_ai_router_route_result_handling`, the RouteResult is
dumped to JSON before any attribute access.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent


def read_lines(path, ranges):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rel = path.relative_to(REPO_ROOT).as_posix()
    chunks = []
    for start, end in ranges:
        section = "\n".join(
            f"{i+1:>5}  {lines[i]}" for i in range(start - 1, min(end, len(lines)))
        )
        chunks.append(
            f"--- {rel} lines {start}-{min(end, len(lines))} ---\n{section}"
        )
    total_lines = sum(min(e, len(lines)) - s + 1 for s, e in ranges)
    return (
        f"=== FILE: {rel} ({total_lines} LOC across {len(ranges)} slice(s)) ===\n"
        + "\n\n".join(chunks)
    )


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


def run_round(label, system_summary, code_block, focus_prompt, out_path):
    print(f"\n{'='*60}\n[{label}] sending verification call...\n{'='*60}")
    result = ai_router.route(
        content=focus_prompt,
        task_type="session-verification",
        context=f"{system_summary}\n\n--- FILES ---\n{code_block}",
        session_set="030-session-state-v3-sessions-ledger",
        session_number=5,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


SYSTEM_SUMMARY = """
Set 030 Session 5 shipped the in-extension v2->v3 migration UX plus
the AI-strategy wiring in the bulk migrator's `migrate_one_set`
public entry point. Both the in-extension lazy migrator (TS) and
the CLI subprocess into the same `migrate_one_set(set_dir,
strategy='ai')` Python entry point, so the route() call site lives
in Python (Option A per the cross-provider audit 2026-05-17 — GPT-5.4
chose this over an extension-side route() call after weighing
single-source-of-truth, future bulk-AI scenarios, and failure-handling
legibility).

GPT's audit produced four refinements which this session implements:

  1. Keep AI failures structured: no raw subprocess tracebacks
     bubbling up. Each failure mode is a distinct ACTION_FAILED_AI_*
     code with operator-actionable reason text.

  2. Keep AI explicitly opt-in: extension quickpick has a modal
     cost-confirmation; the CLI's `interactive` strategy never
     silently chooses AI.

  3. Distinct operator-facing reasons for invalid-AI-output vs
     malformed-input-state: ACTION_FAILED_AI_BAD_OUTPUT vs
     ACTION_SKIPPED_MALFORMED stay separate.

  4. Test the ugly cases first: tests cover missing credentials,
     401 unauthorized, 429 rate limit, non-JSON output, truncated
     response (RouteResult.truncated=True), wrong-shape JSON,
     count mismatch with no silent truncate, out-of-order
     numbering, zero-count state never-calls-route. Plus a happy
     path and markdown code-fence stripping.

The flow inside `migrate_one_set` STRATEGY_AI branch:

  1. Resolve expected_count from existing state + spec.md regex
     titles. Zero -> ACTION_FAILED_AI_BAD_OUTPUT (route never
     called).
  2. Call `_resolve_titles_via_ai(spec_md_path, expected_count)`.
  3. On AiNoCredentialsError -> ACTION_FAILED_AI_NO_CREDS (file
     unchanged).
  4. On AiProviderError -> ACTION_FAILED_AI_PROVIDER_ERROR (file
     unchanged).
  5. On AiCountMismatchError -> ACTION_FAILED_AI_COUNT_MISMATCH
     (file unchanged, NO silent truncate/pad).
  6. On AiBadOutputError -> ACTION_FAILED_AI_BAD_OUTPUT (file
     unchanged).
  7. On success, pass titles_override to `_migrate_state_dict`
     which uses them in place of regex spec_titles AND forces
     use_generic_titles=False so the override actually wins.

The helper `_resolve_titles_via_ai` flow:

  - Reads spec.md (empty string if missing — model can still
    generate plausible labels from the slug).
  - Deferred-imports `ai_router.route` (keeps the migrator's
    import lightweight when only regex/generic strategies run).
  - Builds the prompt via `_build_ai_title_prompt` (states the
    expected count explicitly; demands JSON; emits records in
    `{"number": int, "title": str}` shape).
  - Calls `route(content=prompt, task_type='spec-title-extraction')`.
  - Classifies provider exceptions: substrings "api key",
    "credential", "401", "unauthorized" -> AiNoCredentialsError;
    everything else -> AiProviderError.
  - Per memory feedback_ai_router_route_result_handling: dumps
    the RouteResult via `json.loads(json.dumps(dataclasses.asdict(result)))`
    BEFORE any attribute access. Field reads happen against the
    dumped dict, not the dataclass.
  - Refuses on `RouteResult.truncated=True` (AiBadOutputError).
  - Strips ```json/``` code fences if the model wrapped its
    answer.
  - Validates: must be a JSON array; length must equal
    expected_count (no silent truncate or pad); each entry must
    be a dict with `number == 1..N in order` and `title` a
    non-empty string.

Test results: pytest 592 passed + 1 skipped + 8 e2e deselected
(includes 10 new TestAIStrategy cases + 1 placeholder removal).
Mocha unit 376 passing + 2 pre-existing baseline failures
(unchanged from Session 4). Layer 3 Playwright 7/7 passing (5
existing treeView + 2 new — loading-state + migration-cta).
tsc --noEmit clean (after revert of an over-eager lowercase
import normalization that broke Linux CI on vsix-v0.14.0; vsix-
v0.14.1 ships with the correct capital-S casing).

Live releases:
  - dabbler-ai-router 0.4.0 on PyPI (uploaded via twine; the
    v0.4.0 tag's CI workflow got the idempotent "file already
    exists" rejection for the second upload attempt, which is
    not a real failure).
  - dabbler-ai-orchestration 0.14.1 on Marketplace (vsix-v0.14.1
    tag triggered the publish-vscode.yml workflow; operator
    approved the `marketplace` GitHub Environment to release).
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 5 AI-strategy wiring correctness.

The bundle below contains the AI-strategy slice of
ai_router/migrate_session_state.py: new constants (ACTION_FAILED_AI_*),
exception classes (AiTitleResolutionError + 4 subclasses), the
title-resolution helpers `_build_ai_title_prompt` +
`_resolve_titles_via_ai`, the updated `_migrate_state_dict` (with
its new `titles_override` parameter), and the STRATEGY_AI branch in
`migrate_one_set`.

Verify:

A. **RouteResult JSON-dump-before-access invariant (per memory
   `feedback_ai_router_route_result_handling`).** The migrator must
   dump the RouteResult via `dataclasses.asdict + json.dumps` BEFORE
   any attribute access, and all subsequent field reads must happen
   against the dumped dict, not the dataclass. Verify:
   1. Is the dump applied unconditionally on every route() return
      path (not just success)?
   2. Are `truncated`, `content`, and any other RouteResult fields
      read from `result_payload` (the dumped dict) rather than from
      `result` directly?
   3. If `dataclasses.asdict` raises (because route() returned a
      wrapper that's not a dataclass), is that caught as
      AiBadOutputError rather than escaping as an uncaught
      exception?

B. **Credential-vs-provider error classification.** The exception
   classifier compares the lowercased error message against
   substrings: "api key", "api_key", "apikey", "credential",
   "unauthorized", "401". Verify:
   1. Are there real provider error messages that contain
      "credential" but mean something else (e.g., "renewing
      credentials, please retry")? If so, should they classify
      as no-creds or provider-error?
   2. Is the 401 token sufficient? Some providers return HTTP
      "401" inside larger error messages — does the substring
      check fire correctly?
   3. Does any rate-limit error message (429) ever contain one of
      the credential tokens and get misclassified?
   4. Network errors (ConnectionError, TimeoutError) — does the
      handler catch these via the broad `except Exception` block
      and route them through AiProviderError?
   5. ImportError when `ai_router` module isn't importable —
      AiNoCredentialsError or a different class? The current
      code maps it to AiNoCredentialsError; is that semantically
      right (the operator action is "install ai-router," not
      "set API key")?

C. **Count-mismatch hard-stop, no silent truncate/pad.** The
   helper raises AiCountMismatchError when
   `len(parsed) != expected_count`. Verify:
   1. There is NO code path that pads with `Session N` fillers or
      truncates the parsed array to expected_count and proceeds.
   2. The mismatch reason includes both actual and expected counts.
   3. `migrate_one_set` translates AiCountMismatchError to
      ACTION_FAILED_AI_COUNT_MISMATCH with file unchanged on disk
      (no partial v3 write).

D. **Zero-count short-circuit.** Before any route() call,
   `migrate_one_set` computes expected_count from
   `_resolve_total(state, regex_spec_titles)`. If 0, returns
   ACTION_FAILED_AI_BAD_OUTPUT WITHOUT calling
   `_resolve_titles_via_ai`. Verify:
   1. Is route() truly never called in this path?
   2. Is the reason message operator-actionable (does it say
      something like "edit spec.md to include headings or use
      --strategy generic")?
   3. Is the file on disk untouched?

E. **`titles_override` threading through `_migrate_state_dict`.**
   When the AI helper returns a title map, that map must be the
   authoritative title source for the resulting sessions[].
   Verify:
   1. `_migrate_state_dict` uses `title_source = titles_override
      if titles_override is not None else spec_titles`.
   2. `_resolve_total` is called with `title_source` (not
      `spec_titles`) so AI-resolved titles' count drives total
      resolution.
   3. `use_generic_titles` is forced to False when override is
      provided (the AI-resolved titles must win over generic).
   4. The override map's keys are session numbers 1..N
      (post-validation in `_resolve_titles_via_ai` enforces this).
      If a hypothetical override map had a non-contiguous key set,
      would `_build_v3_sessions` fall back to `Session N` for
      missing keys cleanly?

F. **JSON parsing robustness.** The helper strips markdown code
   fences if present:
     ```json
     [...]
     ```
   Verify:
   1. The fence-stripping handles ``` and ```json equally.
   2. A response that is bare JSON (no fence) is parsed correctly.
   3. A response with leading/trailing whitespace is handled.
   4. A response with multiple fence blocks (model emitted both
      ```json and ``` somewhere in the middle) — does the strip
      drop only the OUTER fence, leaving inner ``` as literal
      content? If so, JSON parse fails -> AiBadOutputError, which
      is the right outcome.
   5. A response with a code fence but no closing ``` (truncated
      mid-stream) — does the truncation flag catch it first? If
      not, what does the fence-strip leave behind?

G. **Per-entry validation.** Each array entry must be a dict with
   `number == loop_index + 1` (1-indexed enumerate) and `title`
   a non-empty string. Verify:
   1. `number != i` is caught with a clear error message that
      includes both values.
   2. `title` of empty string, whitespace-only string, None, or
      non-string is caught.
   3. Extra keys in the entry (e.g., `{"number": 1, "title":
      "x", "description": "y"}`) are tolerated — the helper
      reads only `number` and `title`.

H. **Public exception class hierarchy.** AiTitleResolutionError
   is the base; AiNoCredentialsError, AiProviderError,
   AiBadOutputError, AiCountMismatchError are subclasses. Verify:
   1. All four are re-exported via `__all__`.
   2. The hierarchy supports `except AiTitleResolutionError` as
      a catch-all for library callers who don't care about the
      specific kind.
   3. No subclass shadows the base; the migrator's `migrate_one_set`
      catches each specifically to map to distinct ACTION codes.

I. **Reason-string forensic value.** Each ACTION_FAILED_AI_* result
   carries a `reason` string. Operator looks at this string to
   decide their next step. Verify:
   1. No-creds reason names the env vars to set (or the operator
      can derive them).
   2. Provider-error reason includes the underlying error so
      transient issues (timeouts, 429s) are diagnosable.
   3. Bad-output reason includes a snippet of the offending model
      output (first 200 chars) so the operator can see what
      went wrong.
   4. Count-mismatch reason includes both numbers.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have
    notes.)
  - REJECTED: <bulleted list of must-fix issues with line numbers>.

Cite specific line numbers when flagging issues. Skip stylistic
nits. Focus on correctness: does the AI strategy produce no-write
outcomes on every failure mode, surface the failure to the
operator in a kind-specific way, and never silently corrupt a v3
state file under any model misbehavior?
""".strip()


def _files() -> str:
    # Bundle just the new AI-strategy slice. Skip the v3-inference
    # core (Round A of Session 4 already verified it) and the CLI
    # argparse / output formatting (lower risk; doesn't affect
    # correctness of migrated state).
    migrator = read_lines(
        REPO_ROOT / "ai_router" / "migrate_session_state.py",
        [
            # ACTION_FAILED_AI_* constants + AiTitleResolutionError +
            # the 4 subclass exceptions + MigrationResult class header
            # (the dataclass populated by every action code).
            (114, 180),
            # _migrate_state_dict with the new titles_override parameter
            # — needs review because that's the threading from AI titles
            # into the v3 sessions[] build.
            (337, 405),
            # _build_ai_title_prompt (prompt shape; lines ~407-440) +
            # _resolve_titles_via_ai (the heart of the AI strategy:
            # route() call, RouteResult JSON-dump-before-access, four
            # failure classifications, count-mismatch hard-stop;
            # ~441-595).
            (407, 595),
            # migrate_one_set with the STRATEGY_AI branch including
            # zero-count short-circuit and the structured-failure
            # mapping that translates each AiTitleResolutionError
            # subclass into its ACTION_FAILED_AI_* code.
            (596, 805),
        ],
    )
    return migrator


def main():
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session5.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    if sub == "round-a":
        code_block = _files()
        run_round(
            "Round A",
            SYSTEM_SUMMARY,
            code_block,
            FOCUS_PROMPT,
            out_dir / "round-a-session-5-result.json",
        )
    elif sub == "round-b":
        code_block = _files()
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated migrator.\n\n"
            "For each Round-A issue, confirm:\n"
            "  - The fix is present at the cited location.\n"
            "  - The fix doesn't introduce a new contradiction.\n"
            "  - The fix is consistent with GPT's four refinements:\n"
            "    (1) structured failures, (2) explicit opt-in, "
            "(3) distinct reasons for invalid-AI vs invalid-input, "
            "(4) the ugly-cases coverage.\n"
            "  - The RouteResult JSON-dump-before-access invariant "
            "still holds.\n\n"
            "Format: VERIFIED if all issues addressed and no new ones "
            "found; REJECTED if any remain or new ones surfaced. Cite "
            "line numbers; skip stylistic nits."
        )
        run_round(
            "Round B",
            SYSTEM_SUMMARY
            + "\n\n--- Round B context ---\nRound A returned REJECTED "
            "with must-fix issues. The fixes are in place; Round B is "
            "the confirmation pass.",
            code_block,
            focus,
            out_dir / "round-b-session-5-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
