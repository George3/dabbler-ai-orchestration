# Set 064 S3 Verification (gpt-5-4)

- Verifier model: gpt-5-4
- input_tokens: 18875, output_tokens: 15188
- cost_usd: 0.2750, total_cost_usd: 0.2750
- truncated: False

---

## Deliverable 1 — `ai_router/guidance_triage.py`

- **Major**
  - **Issue** → Block/preamble size accounting is not exact; it drops one newline at every segment boundary, so `current_chars` / `projected_chars` can be low and are not reliably comparable to the source file length or `guidance_report`.
  - **Location** → `extract_blocks()`: `preamble = "\n".join(lines[:first])` and `block_text = "\n".join(block_lines)`.
  - **Fix** → Stop reconstructing segments with `split("\n")` + `join()`. Compute exact character offsets in the original `text` and slice substrings directly, or otherwise preserve the boundary newline that precedes the next heading. Add an invariant test that `extraction.preamble_char_size + sum(b.char_size) == len(source_text)`.

- **Major**
  - **Issue** → Malformed `merge` entries still remove blocks from the active-tier projection. A response with `classification="merge"` and no valid `merge_target` is flagged as an error, but the returned `Classification` is still `MERGE`, and `project_size()` counts it as 0 retained chars. That makes the projected savings too optimistic.
  - **Location** → `parse_triage_response()` keeps invalid merges; `project_size()` removes every `MERGE` unconditionally.
  - **Fix** → Reject malformed merges from the returned classification list so they remain unclassified and are retained conservatively, or coerce them to `keep-active`. Also validate `merge_target` is in-range, different from `index`, and ideally points to a surviving `keep-active`/`promote` block before counting it as removable.

- **Minor**
  - **Issue** → The reference-conflict guard does not fully match the documented “referenced by active guidance” behavior. It counts trailer references from any block, even if that referring block is itself being removed, and `project_guidance_text` matching is raw substring search, which can false-positive on ID prefixes.
  - **Location** → `build_reference_graph()` / `flag_referenced_archives()`.
  - **Fix** → Match IDs as exact tokens in `project-guidance.md`, and only treat references from blocks that remain active after triage as conflicts.

## Deliverable 2 — `ai_router/tests/test_guidance_triage.py`

- **Major**
  - **Issue** → The tests do not catch either of the two real helper correctness bugs above.
  - **Location** → Missing coverage in `test_guidance_triage.py`; `test_parse_merge_without_target_is_flagged()` currently locks in the malformed-merge behavior by expecting the invalid merge to remain a returned classification.
  - **Fix** → Add:
    1. an aggregate-length invariant test (`current_chars == len(source_text)` and all-KEEP projection matches the source length), and  
    2. a projection test proving invalid/missing `merge_target` leaves the block retained conservatively.

- **Minor**
  - **Issue** → The cp1252/ASCII safeguard is not actually exercised. `test_render_report_is_ascii_only()` uses ASCII-only input and never tests the real fold-to-ASCII display path.
  - **Location** → `test_render_report_is_ascii_only`.
  - **Fix** → Use a non-ASCII title/body and assert the stdout-facing path (`_to_ascii` / `_safe_print`, or `main()` stdout capture) folds it safely while the UTF-8 report content remains intact.

## Deliverable 3 — `docs/guidance-backlog-remediation.md`

- **Minor**
  - **Issue** → Step 2 claims the raw routed output is persisted “before any parse or console print,” but the shipped helper parses inside `run_triage()` before `main()` writes `--out`.
  - **Location** → `docs/guidance-backlog-remediation.md`, Step 2 bullet; same mismatch also appears in the module docstring/design notes in `guidance_triage.py`.
  - **Fix** → Either change the implementation to persist each raw batch before parsing, or narrow the documentation to the behavior the code actually guarantees: persisted before any console display.

## Deliverable 4 — `s3-harvester-dogfood.md`

- No artifact-to-artifact contradiction found. The dogfood summary matches the supporting rendered report on counts, projected chars/tokens, reduction, and the “still over ceiling” conclusion.

VERDICT: ISSUES_FOUND
