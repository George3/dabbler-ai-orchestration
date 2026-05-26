# Set 047 Session 6 — Cross-provider verification

You are an independent cross-provider verifier for a docs-and-release
close-out session of a 6-session AI-led-workflow session set. The set
(047-state-file-schema-v4-audit) migrates the on-disk session-state
file schema from v3 to v4, and Session 6 is the schema-doc + authoring-
guide revision + change-log generation + close-out + dual publish.

## What you are verifying

Three deliverables ship as the documentation surface of this set:

1. **`docs/session-state-schema.md`** — full rewrite. The canonical
   reference for `session-state.json` on the v4 schema. Previously
   documented the v3 schema (sessions[] ledger with top-level legacy
   triple); now documents v4 (per-session metadata records, derived
   top-level fields via reader shim).
2. **`docs/planning/session-set-authoring-guide.md`** — targeted edits
   adding the new `prerequisites:` field to the Session Set
   Configuration block documentation.
3. **`docs/session-sets/047-state-file-schema-v4-audit/change-log.md`**
   — new file summarizing all six sessions of the set.

Your job is to verify **accuracy** (does the documentation match the
shipped implementation?), **internal consistency** (do the doc's
claims agree with each other?), and **scope-lock fidelity** (does
the change-log faithfully summarize the spec-locked work that
shipped?).

## How to verify

Cross-reference the new docs against:

- The audit-locked spec
  (`docs/session-sets/047-state-file-schema-v4-audit/spec.md`), which
  is the single source of truth for what this set was supposed to
  ship.
- The Python writer source (`ai_router/session_state.py`,
  `ai_router/session_lifecycle.py`) and the read-side shim
  (`ai_router/progress.py`), which are authoritative for what the
  v4 writer actually emits and what the shim normalizes.
- The TypeScript writer mirror
  (`tools/dabbler-ai-orchestration/src/utils/sessionState.ts`,
  `cancelLifecycle.ts`) and the file-system reader
  (`fileSystem.ts`), authoritative for the TS side and the
  prerequisites cross-reference logic.

For internal consistency, sanity-check claims like:

- The schema doc claims the v4 writer emits a 7-field orchestrator
  block (engine/provider/model/effort/chatSessionId/checkedOutAt/
  lastActivityAt). Is that what the actual writer code emits?
- The schema doc claims rule 8 of the invariants is
  "sessions[N].orchestrator non-null IFF sessions[N].status ==
  in-progress". Is that what the writer code actually enforces or
  produces?
- The schema doc claims close_session clears `sessions[N].orchestrator`
  to null. Is that consistent with the s4-close-reason.md note that
  "per-session orchestrator is preserved as a historical record"?
- The change-log's per-session summaries — do they match the
  s1-s5-close-reason.md files in this session-set directory?

## What I want back

Apply your verifier prompt-template's verdict shape. Categories:

- **Critical** — factual errors in the docs that would mislead a
  user or downstream tool (claimed field names that don't exist,
  claimed invariants the writer doesn't enforce, missing reference
  to a major shipped feature).
- **Important** — accuracy issues that should be addressed but don't
  block publish (slightly mis-stated semantics, missing minor cross-
  references, change-log omissions of secondary deliverables).
- **Nice-to-have** — polish (wording, ordering, redundant text).

For each item, name the **file path + section heading** and a
**short fix recipe**. The closing orchestrator will address Critical
and Important items in-flight before close.

## Files bundled below

The bundle includes:

- The 3 new/edited docs (primary targets)
- The audit-locked spec (cross-check reference)
- The 5 prior close-reason files (cross-check for change-log accuracy)
- Key writer + reader source files (cross-check for schema doc
  accuracy)

The session-set's `session-state.json` is included as the
current-state example referenced by the schema doc's worked examples.
