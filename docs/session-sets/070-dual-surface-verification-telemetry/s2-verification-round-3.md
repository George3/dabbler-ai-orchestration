## VERIFIED

- **R2 Issue 1:** Fixed.
  - `read_dual_surface_mode()` now rejects non-list `entries` before iteration, returning `off` instead of raising on `{"entries": 1}` / `{"entries": "oops"}`: `ai_router/dual_surface_verify.py:1471-1492`
  - `has_dual_surface_mode_record()` has the same non-list guard, so `record-mode` no longer blows up before repair: `ai_router/dual_surface_verify.py:1495-1515`
  - `record_dual_surface_mode()` no longer does `int(...)` on arbitrary prior `stepNumber` values; it filters with `_is_int_not_bool(...)` and ignores malformed values like `[]`: `ai_router/dual_surface_verify.py:1560-1594`
  - `main()` `record-mode` adds `TypeError` to the controlled-exit handler as fallback only: `ai_router/dual_surface_verify.py:1698-1721`

- **Remaining traceback paths for the scoped malformed-log cases:** None found.
  - `read-mode`:
    - unreadable file -> controlled exit `2` via `dual_surface_mode_record_unreadable()`: `ai_router/dual_surface_verify.py:1518-1534`, `1743-1747`
    - parseable malformed object/non-object (`entries: 1`, `entries: "x"`, top-level list) -> `read_dual_surface_mode()` returns default `off`, no traceback: `1471-1492`, `1743-1747`
  - `record-mode`:
    - unreadable file -> controlled exit `2`: `1698-1704`
    - parseable malformed `entries` non-list -> `has_dual_surface_mode_record()` returns `False`, then `record_dual_surface_mode()` repairs `entries` to `[]` and records successfully: `1495-1515`, `1560-1581`, `1705-1714`
    - parseable malformed prior `stepNumber` -> ignored during next-step computation, record still lands: `1579-1594`
    - parseable malformed top-level non-object -> controlled `ValueError` from writer, caught by CLI -> exit `2`: `1569-1577`, `1709-1714`
  - `resolve_and_record_dual_surface_mode()`:
    - with `entries: 1` / `entries: "x"` and a chosen mode, it flows through `has_dual_surface_mode_record()` -> `record_dual_surface_mode()` repair path, no uncaught traceback: `1630-1668`

- **Repair-vs-refuse behavior:** Defensible.
  - The malformed value is already unusable as an activity-log `entries` container.
  - The writer normalizes it to a valid list and lands the durable record atomically.
  - Readers are hardened to treat malformed `entries` as “no record” instead of crashing.
  - That is consistent, non-lossy for valid records, and strictly better than a traceback. No defect introduced by choosing exit `0` on successful repair.

- **R2 Issue 2:** Fixed.
  - Direct reader coverage for `entries=1` is present and exercises both hardened readers: `ai_router/tests/test_dual_surface_s2.py:619-629`
  - Direct writer coverage for malformed prior `stepNumber=[]` is present and exercises the former `int(...)` crash path: `ai_router/tests/test_dual_surface_s2.py:631-642`
  - CLI coverage for parseable malformed `entries=1` is present and necessarily traverses `main(["record-mode", ...]) -> resolve_and_record_dual_surface_mode() -> has_dual_surface_mode_record() -> record_dual_surface_mode()`: `ai_router/tests/test_dual_surface_s2.py:734-747`
  - CLI coverage for malformed prior `stepNumber=[]` is present and traverses the `record-mode` path into `record_dual_surface_mode()`: `ai_router/tests/test_dual_surface_s2.py:749-759`

- **Devil’s-advocate check:** The new tests do exercise the previously broken CLI path, not just the writer in isolation. If the old `has_dual_surface_mode_record()` iteration bug were still present, `test_record_mode_non_list_entries_does_not_crash` would fail before recording. If the old `int(e.get("stepNumber", 0))` path were still present, both malformed-stepNumber tests would fail. No net-new defect introduced in the scoped remediation.