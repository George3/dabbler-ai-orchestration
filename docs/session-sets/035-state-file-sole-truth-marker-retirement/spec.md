# State-file sole truth — cancellation/restoration marker retirement

> **Purpose:** finish the H2 single-source-of-truth verdict that
> Set 033 Session 2 started. Retire the file-presence-based
> cancellation/restoration detection in favor of
> `session-state.json` as the canonical signal. Bundle a
> naming-glossary scrub for the marker-name string literals
> across the codebase.
> **Created:** 2026-05-21 (post-Set-033-close)
> **Session Set:** `docs/session-sets/035-state-file-sole-truth-marker-retirement/`
> **Prerequisite:** Set 033 (`033-orchestrator-checkout-checkin-implementation`) CLOSED.
> **Pattern:** audit collapsed into spec per operator's 2026-05-21
> adjudication. The architectural conclusion is unambiguous
> (Set 033 S2 H2 verdict + [[project_034_035_state_file_sole_truth_audit]]
> memory), so no separate cross-provider audit set is warranted.

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: medium
```

> **`requiresE2E: true`** — cancellation/restoration is an
> operator-visible behavior in the Session Set Explorer (tree
> bucketing, accordion rendering). Layer-3 Playwright coverage
> ensures the reader migration doesn't break the rendered
> experience.
>
> **`effort: medium`** — the writer side already updates
> `session-state.json` correctly (Set 008's
> `cancelLifecycle.ts` writes `status: "cancelled"` and
> `preCancelStatus`); the principal change is reader-side. Lower
> coordination risk than Set 033's multi-tier writer migration.

---

## Project Overview

### The architectural gap

Set 033 Session 2 locked the H2 verdict: **`session-state.json`
is the canonical source of truth for session-set state.** That
session retired the orchestrator-marker file
(`.dabbler/orchestrator.json`) and migrated the reader to consult
the state file's `orchestrator` block directly.

However, Set 033's scope was orchestrator-only. The *cancellation*
side of the lifecycle (`CANCELLED.md` and `RESTORED.md` audit-history
files, plus the file-presence-driven detection in `fileSystem.ts`)
was NOT migrated. Pre-H2 thinking — *"filename presence is what
matters"* — survived in two adjacent code paths:

- [`tools/dabbler-ai-orchestration/src/utils/fileSystem.ts:276`](../../../tools/dabbler-ai-orchestration/src/utils/fileSystem.ts) —
  the reader: `if (isCancelled(dir)) { state = "cancelled"; }`.
  `isCancelled()` checks `fs.existsSync(.../CANCELLED.md)`.
- [`docs/session-state-schema.md`](../../session-state-schema.md)
  "Cancel / restore" section — codifies the file-presence-first
  rule. Cites the same `CANCELLED.md present → Cancelled` as
  the canonical bucketing rule, regardless of `status`.

The writer ([`tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`](../../../tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts))
already keeps both signals in lockstep: it writes
`CANCELLED.md` AND sets `state.status = "cancelled"` /
`state.preCancelStatus = <prior>`. The state file has the data;
the reader just doesn't trust it.

### What this set ships

1. **Reader migration** — `fileSystem.ts:276` reads
   `state.status === "cancelled"` first; falls back to
   `isCancelled(dir)` only for legacy state files (no `status`
   field, schema v1, etc.).
2. **Writer alignment** — confirm the cancelLifecycle.ts writer
   and its Python mirror (`ai_router/session_lifecycle.py`)
   produce consistent state-file writes. The markdown files
   (`CANCELLED.md` / `RESTORED.md`) survive as **audit-trail
   artifacts**, no longer as state signals.
3. **Glossary harvest sub-task** — operator-flagged
   ([[project_034_035_state_file_sole_truth_audit]]): harvest all
   string literals across the solution that look like file/marker
   names, group by near-match (Levenshtein or shared-prefix),
   surface inconsistencies. The trigger was an AI engine writing
   `_cancelled.md` (lowercase, underscore-prefixed) while the
   reader expects `CANCELLED.md` — a Levenshtein-3 mismatch that
   should be caught systematically, not by operator eyes.
4. **Documentation alignment** — `session-state-schema.md` "Cancel
   / restore" section rewritten; `ai-led-session-workflow.md`
   cancellation/restoration flow updated to reflect state-file-
   first; `cancelLifecycle.ts` JSDoc updated.
5. **Layer-3 coverage** — Playwright scenario for cancellation
   bucketing driven by the state file (not the markdown file).
6. **Cross-tier doc + release** — minor `ai_router` release
   (0.6.1 patch) if the Python mirror in
   `session_lifecycle.py` changes; minor Marketplace release
   (0.18.1 patch) for the reader change.

### What stays unchanged (explicit non-scope)

- The `CANCELLED.md` / `RESTORED.md` audit-history markdown
  files are kept as operator-readable artifacts. They are not
  the source of truth post-035, but they are not retired.
- Per-session cancellation (a `"cancelled"` value in
  `sessions[].status`) remains reserved for a future schema —
  Set 030's invariants still apply.
- The pre-existing S2 (Set 033 Session 2) accordion-body
  rendering bug (rows ship `data-state="in-progress"` but
  `accordionHtml === null` reaches the webview) is **out of
  scope**. It's an adjacent UI bug; ship as a Set 034 fix or
  separate hotfix. Documented in
  [[project_034_035_state_file_sole_truth_audit]].
- A `SUPERSEDED.md` / `"superseded"` status is **not introduced**
  here — no current consumer writes one, and adding a status
  value without a use case is premature. If superseded
  semantics surface later, a follow-on set adds them.
- Set 034 (`034-session-set-explorer-styling-iteration`) runs
  **after** this set. The styling-iteration work is queued and
  doesn't interact with the cancellation lifecycle code paths.

---

## Session 1 of 4: Reader migration to state-file-sole-truth

**Goal:** flip the cancellation detection precedence in the
extension reader from file-presence-first to state-file-first.
The markdown markers stay on disk as audit artifacts; the reader
no longer uses their presence as the state signal.

**Steps:**

1. **Audit reader call sites.** Enumerate every place in the
   extension source that calls `isCancelled()` or `wasRestored()`
   (from `src/utils/cancelLifecycle.ts`). Document each call
   site's current behavior and target post-migration behavior.
2. **Add a state-file-first detector.** New function in
   `src/utils/cancelLifecycle.ts`:
   ```ts
   export function readCancellationState(sessionSetDir: string): "cancelled" | "restored" | "active" | "unknown"
   ```
   Returns:
   - `"cancelled"` if `state.status === "cancelled"`
   - `"restored"` if `state.status` is a non-cancelled value
     AND `RESTORED.md` exists (history-aware bucketing)
   - `"active"` if `state.status` is a non-cancelled value
     AND no `RESTORED.md`
   - `"unknown"` if no state file or unparseable state file →
     falls through to legacy `isCancelled()` / `wasRestored()`
3. **Refactor `fileSystem.ts:276`** to call
   `readCancellationState()` instead of `isCancelled()`. The
   legacy `isCancelled()` / `wasRestored()` helpers stay
   exported (some tests + Python-mirror parity comparisons use
   them) but are no longer the bucketing path.
4. **Schema-doc rewrite.** Replace `session-state-schema.md`
   "Cancel / restore" section with state-file-first language;
   note that the markdown files remain as audit artifacts and
   reads of legacy state files (no `status`, or schema v1)
   still tolerate the file-presence fallback.
5. **Unit tests.** Add to
   `src/test/suite/cancelLifecycle.test.ts`:
   - State file says `cancelled`, no `CANCELLED.md` → reader
     reports cancelled (the new behavior, would have been
     "active" pre-035).
   - State file says `complete`, `CANCELLED.md` present →
     reader reports cancelled (legacy fallback path; v1 state
     files with only file-presence cancellation).
   - State file says `complete`, `RESTORED.md` present →
     reader reports restored (history-aware).
   - State file missing → reader falls through to legacy
     `isCancelled()` behavior.
6. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- (no new files; `readCancellationState()` added to
  `cancelLifecycle.ts`)

**Touches:**
- `tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`
- `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`
- `tools/dabbler-ai-orchestration/src/test/suite/cancelLifecycle.test.ts`
- `docs/session-state-schema.md`

**Ends with:** Extension reads cancellation state from
`session-state.json` first; markdown markers serve as audit
artifacts and legacy-fallback signal only; unit tests pin both
paths.

**Progress keys:** `session-001/reader-call-sites-audited`,
`session-001/read-cancellation-state-implemented`,
`session-001/filesystem-refactored`,
`session-001/schema-doc-rewritten`,
`session-001/unit-tests-green`,
`session-001/round-a-verification`

**Estimated cost:** $0.03–$0.10.

---

## Session 2 of 4: Writer alignment + glossary harvest

**Goal:** confirm the cancelLifecycle.ts writer and its Python
mirror produce consistent state-file writes. Run the glossary-
harvest sub-task: find marker-name string literals across the
solution, surface inconsistencies, fix.

**Steps:**

1. **Writer parity check** — compare
   `src/utils/cancelLifecycle.ts` (TypeScript) and
   `ai_router/session_lifecycle.py` (Python mirror) line-by-line
   for byte-equivalent on-disk shape. Per the existing comment
   in `cancelLifecycle.ts:14-18`:
   > "The two writers must agree byte-for-byte on the on-disk
   > shape so a set cancelled on one platform reads identically
   > when the same repo is opened on another."
   Verify both writers:
   - Emit LF newlines and UTF-8 (no BOM)
   - Use second-precision ISO-8601 with local-offset timestamps
   - Write `state.status = "cancelled"` AND
     `state.preCancelStatus = <prior>` symmetrically
   - Write `CANCELLED.md` / `RESTORED.md` with identical
     `# Cancellation history` header + prepend-entry format
2. **Glossary harvest** — author a small one-shot script (Python
   or Node) that:
   - Recursively greps the solution (excluding `node_modules`,
     `.venv`, `out`, `dist`, `.git`) for string literals that
     look like file/marker names (heuristic: regex like
     `[A-Z][A-Za-z_-]*\.(md|json|toml|jsonl)` plus targeted
     patterns for known markers).
   - Groups matches by Levenshtein distance ≤ 3 within the
     same file extension.
   - Surfaces clusters where the operator might want
     consistency (e.g., `CANCELLED.md` vs `_cancelled.md` vs
     `cancelled.md`).
   - Outputs a Markdown report at
     `docs/session-sets/035-.../glossary-harvest.md`.
3. **Operator-driven fixes per glossary finding.** Each cluster
   is either (a) acceptable variance (e.g., test fixture file
   names that don't need to align with production code), (b) a
   real inconsistency to fix in-session, or (c) a
   follow-on candidate. Document the disposition for each
   cluster in `glossary-harvest.md`.
4. **`_cancelled.md` mismatch resolution** — the specific case
   that triggered this set: an AI engine wrote `_cancelled.md`
   while the reader expects `CANCELLED.md`. With Session 1's
   reader migration, the typo is moot (the state file is the
   source); but document the resolution so future contributors
   understand why a stray `_cancelled.md` in a session-set
   directory is harmless.
5. **Unit tests (writer side)** — add fixture-based tests that
   confirm:
   - Writer state-file output matches the Python mirror's
     output for the same input.
   - Cancellation + restoration round-trip preserves
     `preCancelStatus` correctly.
6. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `docs/session-sets/035-state-file-sole-truth-marker-retirement/glossary-harvest.md`
- `docs/session-sets/035-state-file-sole-truth-marker-retirement/scripts/harvest_glossary.py`
  (or `.js` per implementation preference)

**Touches:**
- `tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`
  (only if parity comparison surfaces a fix needed)
- `ai_router/session_lifecycle.py` (same condition)
- `tools/dabbler-ai-orchestration/src/test/suite/cancelLifecycle.test.ts`
  (writer round-trip tests)
- Any files surfaced by the glossary harvest as needing
  consistency fixes

**Ends with:** TypeScript and Python writers verified byte-
equivalent; glossary-harvest report committed; any in-session
fixes applied.

**Progress keys:** `session-002/writer-parity-verified`,
`session-002/glossary-harvest-script-authored`,
`session-002/glossary-harvest-report-committed`,
`session-002/in-session-fixes-applied`,
`session-002/writer-tests-green`,
`session-002/round-a-verification`

**Estimated cost:** $0.05–$0.15 (glossary harvest is the
medium-effort piece).

---

## Session 3 of 4: Documentation + Layer-3 coverage

**Goal:** align all canonical docs with the state-file-sole-truth
posture for cancellation/restoration. Add Layer-3 Playwright
coverage for the new reader behavior.

**Steps:**

1. **`session-state-schema.md`** — complete the rewrite started
   in Session 1: "Cancel / restore" section reframes the
   architectural model (state file is canonical; markdown files
   are audit artifacts + legacy-fallback signal). The
   `status` table on the schema doc is unchanged
   (`"cancelled"` was already a valid value).
2. **`ai-led-session-workflow.md`** — the cancellation /
   restoration narrative is documented in
   "Cancelling and restoring a session set". Update to reflect
   that the canonical signal is `status: "cancelled"`; the
   markdown files are the audit history.
3. **`tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`**
   JSDoc updates — the `isCancelled()` / `wasRestored()`
   functions get clearer docstrings explaining their legacy-
   fallback role; the new `readCancellationState()` becomes
   the primary documented entry point.
4. **Layer-3 Playwright scenario** at
   `tools/dabbler-ai-orchestration/src/test/playwright/cancellation-state-file.spec.ts`:
   - Scaffold a session set with `status: "cancelled"` and NO
     `CANCELLED.md` file.
   - Launch VS Code via Playwright's `_electron.launch`.
   - Assert the set renders in the **Cancelled** tree section
     (the state file wins; absence of the markdown file
     doesn't matter).
   - Companion scenario: legacy `CANCELLED.md`-present + state
     file says `complete` → still bucketed as Cancelled (the
     fallback path).
5. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `tools/dabbler-ai-orchestration/src/test/playwright/cancellation-state-file.spec.ts`

**Touches:**
- `docs/session-state-schema.md`
- `docs/ai-led-session-workflow.md`
- `tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts`
  (JSDoc only)

**Ends with:** Three canonical docs aligned; one new Layer-3
test green; Set 033's docs cited where the H2 verdict applies
beyond orchestrator state.

**Progress keys:** `session-003/schema-doc-finalized`,
`session-003/workflow-doc-aligned`,
`session-003/jsdoc-updated`,
`session-003/layer3-test-green`,
`session-003/round-a-verification`

**Estimated cost:** $0.03–$0.10.

---

## Session 4 of 4: Tests + change-log + dual-registry release

**Goal:** final test sweep, change-log aggregation, release the
patches.

**Steps:**

1. **Full test sweep** — run the complete Python + extension
   test surfaces:
   - `python -m pytest` (no regression from the
     `session_lifecycle.py` changes, if any).
   - `cd tools/dabbler-ai-orchestration && npm run test:unit`
     (Layer-2 stub harness for the reader migration).
   - `cd tools/dabbler-ai-orchestration && npm run test:playwright`
     (Layer-3, including the new
     `cancellation-state-file.spec.ts`).
   - `npx tsc --noEmit` clean.
2. **Set 035 change-log.md** — final-session aggregation per
   [[project_final_session_changelog_pre_close]]: top context
   block; one section per session; closing summary; deferred
   follow-ups (pre-existing S2 accordion-body bug → Set 034 or
   separate hotfix).
3. **Version bumps:**
   - `pyproject.toml` 0.6.0 → **0.6.1** (patch, only if the
     Python mirror in `session_lifecycle.py` changed).
   - `ai_router/CHANGELOG.md` 0.6.1 entry.
   - `tools/dabbler-ai-orchestration/package.json` 0.18.0 →
     **0.18.1** (patch).
   - `tools/dabbler-ai-orchestration/CHANGELOG.md` 0.18.1
     entry.
   - `CLAUDE.md` Extension versioning walk extended.
4. **End-of-session verification** (gemini-pro, Round A;
   budget for Round B given the reader-side change touches
   bucketing behavior).
5. **PyPI release** of `dabbler-ai-router` 0.6.1 (operator-gated
   per the established pattern; **skip if the Python mirror
   didn't change**).
6. **Marketplace publish** of `dabbler-ai-orchestration` 0.18.1
   (operator-gated; **does NOT bundle Set 034's styling work** —
   Set 034 ships its own 0.19.0 / 0.18.2 separately).
7. **`close_session` invocation** for Set 035 Session 4.

**Creates:**
- `docs/session-sets/035-state-file-sole-truth-marker-retirement/change-log.md`

**Touches:**
- `pyproject.toml` (conditional)
- `ai_router/CHANGELOG.md` (conditional)
- `tools/dabbler-ai-orchestration/package.json`
- `tools/dabbler-ai-orchestration/CHANGELOG.md`
- `CLAUDE.md`

**Ends with:** Reader migration complete; glossary harvest
done; canonical docs aligned; Layer-3 + Layer-2 tests green;
both registries published (PyPI conditional).

**Progress keys:** `session-004/test-sweep-green`,
`session-004/change-log-generated`,
`session-004/version-bumps-applied`,
`session-004/round-a-verification`,
`session-004/pypi-release-pushed`,
`session-004/marketplace-publish-completed`,
`session-004/close-session-succeeded`

**Estimated cost:** $0.05–$0.15 (verification + dual release).

---

## Risks

- **R1 — Reader fallback path silently masks state-file bugs.**
  The legacy `isCancelled(dir)` fallback fires when the state
  file is missing/unparseable. If a state-file write bug ever
  produces malformed JSON, the reader silently falls back to
  file-presence; the operator only notices when the markdown
  file isn't there either. Mitigation: log a `console.warn` on
  fallback so the diagnostic trail exists; document the
  behavior in the schema doc.
- **R2 — Pre-existing S2 accordion-body bug overlaps the
  reader code path.** The Set 033 S4 Playwright suite has two
  scenarios `test.skip`'d with FIXMEs for the multi-in-progress
  accordion rendering. Session 1 of this set touches the
  reader; if the bug is in the rendering pipeline, it might
  surface under the new reader. Mitigation: keep an eye on
  the Set 033 S4 skipped tests during Session 1's
  verification.
- **R3 — Glossary harvest produces too many findings to triage
  in-session.** If the harvest surfaces a hundred clusters,
  triaging them in Session 2 inflates the session cost.
  Mitigation: cap in-session triage at the top 10 clusters by
  edit-distance × file-count; defer the rest to a follow-on
  set or document them as acceptable variance.
- **R4 — Python/TypeScript writer drift goes undetected.**
  Session 2's parity check is manual eyeballing supplemented
  by round-trip tests. A subtle drift (e.g., a future Python
  patch changes timestamp precision) could slip past. Long-
  term mitigation (out of 035 scope): consider a shared spec
  + golden-file fixtures that both writers test against.
- **R5 — Marketplace 0.18.1 publish requires the operator's
  PAT being live.** The Set 033 PAT rotation incident closed
  cleanly with 0.18.0 publishing; 0.18.1 reuses the same
  rotated PAT. No new credential surface.

---

## Routing notes

- **Within-session verification (every session):** gemini-pro
  per [[feedback_ai_router_usage]] (end-of-session only).
  Round A first; Round B only if must-fix.
- **No routed mid-session API calls.** The architectural
  conclusion (state file is canonical) is settled by
  pre-existing Set 033 S2 H2 verdict + this set's spec.
- **Glossary harvest** is a code-side tool, not an AI
  routing concern.

---

## Total estimated cost

- Session 1: $0.03–$0.10
- Session 2: $0.05–$0.15
- Session 3: $0.03–$0.10
- Session 4: $0.05–$0.15
- **Total Set 035 forecast: $0.16–$0.50.**

For context: Set 033's 6 sessions totaled ~$0.20 of $1.25 NTE.
Set 035 is smaller scope (mostly reader-side + doc updates +
audit-trail markdown retention) and should land near the low
end of the forecast band.

---

## Cross-references

- **Prerequisite session set:** Set 033 (closed 2026-05-21) —
  shipped H2 (`session-state.json` is canonical) for the
  orchestrator side; this set extends H2 to cancellation.
- **Memory anchor:** [[project_034_035_state_file_sole_truth_audit]]
  — operator-approved 2026-05-20 mid-Set-033-S4.
- **Adjacent:** Set 034
  (`034-session-set-explorer-styling-iteration`) — runs AFTER
  this set; deferred per operator 2026-05-21. Marketplace
  publish for 034's styling work is separate from Set 035's
  0.18.1 patch.
- **Audit pattern:** [[feedback_audit_then_spec_for_substantial_features]]
  — audit-then-spec collapsed for this set; architectural
  conclusion is unambiguous, no separate cross-provider audit
  warranted.
- **Related architectural follow-on:** the audit-locked
  proposal at
  [`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/)
  is an independent direction (chatSessionId + watcher-scope
  discipline); it does not interact with Set 035's
  cancellation-marker-retirement work.
