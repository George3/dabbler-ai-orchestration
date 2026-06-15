# aggregator

Builds the `unresolved` reference index over a parsed statement list.

## Contract

- `build_index(statements)` returns the index of UNRESOLVED references. It must
  be the SUPERSET of every reference the analyzer sees - assignment refs, call
  refs, AND return refs (`analyzer.all_refs`). The index size must equal the
  number of distinct unresolved references; nothing is silently dropped.
- A reference record is a dict `{"name": str, "line": int}` (see `analyzer`).
- `count_statements` counts statements, not blank lines.
