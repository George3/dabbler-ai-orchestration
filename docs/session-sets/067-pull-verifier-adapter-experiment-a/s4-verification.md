ISSUES_FOUND

- **Severity:** Medium  
  **Category:** Correctness  
  **Location:** `ai_router/pull_critique.py:252-256, 295-296, 356-363`  
  **Description:** `produce_path_aware_critique()` does not always stamp the **recorded** `pathAwareCritique` level. The public `level` / CLI `--level` override lets a caller write a structurally valid artifact whose `pathAwareCritique` disagrees with the set's durable policy record, because only `validate_path_aware_critique_artifact()` is checked before write. Ground truth: a set recorded as `required` can be written as `"pathAwareCritique": "advisory"` (`test_explicit_level_overrides_recorded` codifies this), and `validate_path_aware_critique_gate()` should then reject it for this set/policy. This breaks the claimed "recorded ... level" / "refuses to write a gate-failing artifact" guarantee and leaves the docs/changelog overstating behavior. **Fix:** for write mode, always use `read_path_aware_critique(set_dir)` or run the full gate identity check against `set_dir` before writing and reject mismatches; if an override is still needed, restrict it to dry-run only and document that explicitly.

- **Severity:** Low  
  **Category:** CLI/Encoding  
  **Location:** `ai_router/pull_critique.py:441-455`  
  **Description:** The CLI claims ASCII-only status output, but it prints unsanitized dynamic text: provider names, `result.skipped`, `result.reasons`, and `written_to`. Ground truth: any non-ASCII path, provider/model string, or exception message will be emitted verbatim, violating the Windows `cp1252` ASCII-only terminal convention. **Fix:** sanitize every dynamic field before printing, e.g. `s.encode("ascii", "backslashreplace").decode("ascii")`.