"""Session 1 verification driver — Set 035 (state-file sole truth).

Round A bundles the artifacts produced by Session 1, the opening
session of Set 035:

  - tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts —
    UPDATED. Adds readCancellationState() as the new state-file-
    first reader (returns "cancelled" | "restored" | "active" |
    "unknown"). Adds CancellationState type. Updates JSDoc on the
    legacy isCancelled() and wasRestored() predicates to mark them
    as legacy-fallback-only.
  - tools/dabbler-ai-orchestration/src/utils/fileSystem.ts —
    UPDATED. The bucketing read at line 276 now calls
    readCancellationState() first; the legacy isCancelled()
    file-presence check survives only as the fallback for the
    "unknown" return (state file missing/unparseable). A
    console.warn fires on the fallback path so the diagnostic
    trail exists.
  - tools/dabbler-ai-orchestration/src/test/suite/cancelLifecycle.test.ts —
    UPDATED. New "Set 035 state-file-first" test suite (10 cases)
    pinning the contract.
  - docs/session-state-schema.md — UPDATED. The "Cancel / restore"
    section is rewritten state-file-first; the status-table
    footnote and the bucketing table both updated.
  - tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts —
    UPDATED (bundled per operator directive 2026-05-21). The
    accordion empty-state no longer renders the two grey
    placeholder gauges above the "No signal — install Claude
    Code hook" CTA; the gauges read as "data we don't have" and
    were more confusing than useful.

Ground truth bundled alongside:

  - Set 035 spec.md Session 1 — the contract this session closes.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
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
EXT_ROOT = REPO_ROOT / "tools" / "dabbler-ai-orchestration"


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def read_section(
    path: Path, start_marker: str, end_marker: str | None = None
) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        return f"=== FILE: {rel} (SECTION MISSING: {start_marker!r}) ==="
    if end_marker is None:
        section = text[start:]
    else:
        end = text.find(end_marker, start + len(start_marker))
        section = text[start:end] if end > 0 else text[start:]
    return f"=== FILE: {rel} (from {start_marker!r}) ===\n{section}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 035 extends the H2 single-source-of-truth verdict that Set 033
Session 2 locked for the orchestrator block. H2 said
`session-state.json` is canonical for session-set state; Set 033
S2 retired the per-set orchestrator-marker file and migrated the
reader to consult the state file's `orchestrator` block.

Set 035's scope: extend H2 to the cancellation lifecycle. Pre-035
the reader at `tools/dabbler-ai-orchestration/src/utils/fileSystem.ts`
line 276 used file-presence-first detection — `CANCELLED.md` on
disk → bucket as Cancelled regardless of `status`. Set 008
established that convention; H2 makes it stale. The writer already
keeps `status: "cancelled"` and `preCancelStatus` in lockstep with
the markdown markers, so the state file already has the
authoritative signal.

Set 035 has 4 sessions. Session 1 (THIS verification) is the reader
migration:

  - New function `readCancellationState(sessionSetDir)` in
    `cancelLifecycle.ts` returns one of "cancelled" | "restored" |
    "active" | "unknown". State file's `status` field is the
    primary signal; `RESTORED.md` presence drives the history-
    aware "restored" return when status is non-cancelled.
  - `fileSystem.ts:276` switches to readCancellationState() first.
    The legacy isCancelled() file-presence check survives as the
    "unknown" fallback for legacy v1 snapshots, hand-edited files,
    or brand-new folders. The fallback emits `console.warn` so a
    diagnostic trail exists if a future state-file write bug ever
    masks a real cancellation.
  - `session-state-schema.md` rewritten state-file-first: the
    "Cancel / restore" section, the status-table footnote, and
    the bucketing rules table all updated.
  - Unit tests: 10 new cases in the cancelLifecycle suite pinning
    the four return values across all the contract corners
    (state says cancelled / state says complete with stray
    CANCELLED.md / RESTORED.md present / missing or unparseable
    state file / status-missing v1 / end-to-end cancel + restore).

Session 2 is writer parity + glossary harvest (TS vs Python writer
byte-equivalent + cross-solution marker-name consistency scan).
Session 3 is doc alignment + Layer-3 Playwright. Session 4 is
final test sweep + dual-registry release (PyPI conditional on
session-2 Python changes; Marketplace 0.18.1 patch).

Bundled in Session 1 per operator directive 2026-05-21: the
orchestrator-accordion empty-state in
`tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
previously rendered two grey placeholder gauges above the
"No signal — install Claude Code hook" CTA. The operator called
the gauges out as "more confusing than useful — we don't need to
show gauges when there is 'no signal'." The two SVG calls have
been removed; the CTA remains. The Layer-3 Playwright test
(session-sets-tree.spec.ts) checks `.acc-empty-cta` text only,
which still passes. The change is consistent with the
`feedback_dont_hide_behind_out_of_scope` rule (one-file fix while
warm beats a deferred follow-on).

All 10 new tests pass. The two pre-existing test failures
(configEditor `ViewColumn.One` stub gap; notificationsSection
"wired in Set 026 Session 7" assertion) are unrelated to
Session 1's code paths. Typecheck (`npx tsc --noEmit`) is clean.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 1 implementation faithfulness for the reader
migration to state-file sole truth + bundled empty-state simplification.

You are Gemini Pro, asked to verify that Session 1 of Set 035 ships
a correct, contract-faithful reader migration plus the
operator-directed empty-state polish.

Verify:

A. **readCancellationState contract.**

   1. Resolution order matches the spec verbatim:
      - `"cancelled"` iff `state.status === "cancelled"`.
      - `"restored"` iff `state.status` is a non-cancelled string
        AND `RESTORED.md` exists.
      - `"active"` iff `state.status` is a non-cancelled string
        AND no `RESTORED.md`.
      - `"unknown"` iff state file missing/unparseable, or
        `status` is non-string / empty.
   2. The "unknown" return path is reachable for ALL three legacy
      shapes: (a) state file absent, (b) state file unparseable,
      (c) state file present but lacking a `status` field. The
      reader does NOT silently inherit `isCancelled` semantics in
      the function itself — that's the CALLER's responsibility at
      fileSystem.ts:276.
   3. The function does NOT consult `CANCELLED.md` presence when
      the state file declares a non-cancelled `status`. A stray
      `CANCELLED.md` alongside `status: "complete"` is intentionally
      ignored — the state file wins, per the H2 verdict.

B. **fileSystem.ts:276 caller wires the fallback correctly.**

   1. The bucketing branch reads `readCancellationState(dir)`
      first. On `"cancelled"`, sets `state = "cancelled"` and
      skips the `readStatus` path.
   2. On `"unknown"` AND `isCancelled(dir)` true, sets `state =
      "cancelled"` and emits a `console.warn` naming the directory
      and pointing at `ensure_state_file` for repair. This is the
      ONLY remaining file-presence-first branch.
   3. On any other return ("active", "restored", or "unknown" with
      no `CANCELLED.md`), falls through to the existing
      `readStatus`/`isMidSetComplete` ladder unchanged. No
      regression on the in-progress / complete / not-started
      bucketing.

C. **Schema doc matches the reader behavior.**

   1. The status-table footnote on the `"cancelled"` value names
      `status: "cancelled"` as the CANONICAL signal (Set 035
      extending H2 from Set 033 S2); the CANCELLED.md marker is
      named as an audit-history artifact, not the bucketing
      signal.
   2. The "Cancel / restore" section reframes the architectural
      model state-file-first. It describes:
      - status: "cancelled" wins the bucketing read.
      - The markdown files (CANCELLED.md / RESTORED.md) are
        operator-readable audit artifacts.
      - The legacy-fallback path is explicit (missing /
        unparseable / status-less state file + CANCELLED.md on
        disk → fallback fires, console.warn emitted).
      - The contract does NOT silently let a stray CANCELLED.md
        override a non-cancelled status; that's an
        operator-resolvable inconsistency.
   3. The "Bucketing in the Session Sets Explorer (v3)" table's
      first bullet now reads "status === 'cancelled' →
      Cancelled (state file wins, Set 035)" with the legacy
      fallback noted via section link, not "CANCELLED.md present →
      Cancelled (filename wins)".

D. **Test pins.**

   1. The new "Set 035 state-file-first" suite has at least 10
      cases covering all four return values + legacy fallback +
      end-to-end. In particular:
      - One case where `status: "cancelled"` exists but no
        CANCELLED.md on disk → asserts "cancelled" (this is the
        Set 035 new behavior; would have been "active" pre-035).
      - One case where `status: "complete"` + CANCELLED.md
        present → asserts "active" (state file wins; the legacy
        predicate isCancelled() still reports true, which the
        test also asserts to document the asymmetry).
      - One case where state file is unparseable JSON → asserts
        "unknown".
      - One case where state file has no `status` field → asserts
        "unknown".
   2. The pre-existing test suites (predicates, cancelSessionSet,
      restoreSessionSet, session-state.json plumbing) are
      unchanged. The legacy predicates (isCancelled, wasRestored)
      remain exported and their existing tests still pass.

E. **Legacy export discipline.**

   1. isCancelled() and wasRestored() are still exported from
      cancelLifecycle.ts — they have legitimate callers (the
      fileSystem.ts fallback path; tests; future Python-parity
      comparisons). Their JSDoc now marks them as
      legacy-fallback-only and points at readCancellationState()
      as the primary entry point.
   2. The CancellationState type union is exported so any future
      caller outside cancelLifecycle.ts can branch on its values
      without re-declaring the union.

F. **Bundled empty-state simplification (operator directive
   2026-05-21).**

   1. `renderAccordionEmpty()` no longer emits the `<div class=
      "grey-gauges">` block with the two `renderGaugeSvg("unknown",
      "current", 0)` calls. The function now emits only the
      `<div class="acc-empty">` wrapper containing the
      `.acc-empty-cta` line ("No signal — <button>install Claude
      Code hook</button>"). The CTA button's `data-command`
      attribute and label-substitution logic are unchanged.
   2. The Layer-3 Playwright assertion in
      `session-sets-tree.spec.ts` (`expect(cta).toContainText(
      /No signal/)`) still applies — the assertion checks
      `.acc-empty-cta`, which is preserved. No test fails as a
      result of the gauge removal.
   3. The comment block above the function explains the removal
      in operator-language ("read as data we don't have", "more
      confusing than useful, 2026-05-21") rather than as a
      structural code-cleanup justification, so future readers
      understand the intent.
   4. The `renderGaugeSvg` function itself is still imported /
      defined and still called by `renderAccordionLoaded` (lines
      ~423 and ~430). The removal is scoped to the empty-state
      branch only.

G. **What's risky or missing.** Any edge case that would bite a
   real run?

   - Set 035's spec called out a pre-existing S2 (Set 033 S2)
     accordion-body rendering bug as out-of-scope: rows ship
     `data-state="in-progress"` but `accordionHtml === null`
     reaches the webview. That bug remains. The empty-state
     change in Session 1 does NOT modify the accordionHtml-
     pipeline plumbing, so the S2 bug is unchanged. Confirm the
     gauge-removal doesn't accidentally interact with the
     pipeline — it should be a pure render-output change.
   - The schema doc's older bucketing-table phrasing was used
     verbatim by external readers (the `feedback_default_not_started_evidence_to_escalate`
     rule is anchored on this section). The Session 1 rewrite
     preserves the architectural posture (default to lowest
     bucket, escalate only on evidence); confirm the rewrite
     doesn't accidentally weaken that.
   - The legacy fallback path's `console.warn` is the only
     observability for "state file is broken." That's
     intentional (the operator-resolvable inconsistency
     posture), but worth confirming no test silences
     console.warn in a way that would mask the warning during
     development.
   - Session 2 will do byte-parity verification of TS vs Python
     writers; if Session 1's reader migration accidentally
     touched writer semantics (it shouldn't — `cancelSessionSet`
     and `restoreSessionSet` are unchanged below the documented
     `readCancellationState` insertion), Session 2 will catch
     it. Worth a sanity check now.
   - The CSS in `tree.css` (`.acc-empty .grey-gauges { ... }`)
     and `indicator.css` (`.empty-state .grey-gauges { ... }`)
     still has dead rules for the removed `.grey-gauges`
     class. These are harmless (no element matches them
     anymore), but Session 3 (the doc + Layer-3 session) is a
     reasonable place to sweep them. Out of Session 1 scope.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits. Session 1 is the reader-migration
backbone of Set 035 — a must-fix here blocks the rest of the set's
sessions from building on the new contract.
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverable — new readCancellationState + updated JSDoc.
        read_section(
            EXT_ROOT / "src" / "utils" / "cancelLifecycle.ts",
            "/**\n * Legacy file-presence predicate. Returns ``true`` iff *sessionSetDir*",
            "// Atomic write via unique temp file",
        ),
        # Reader-caller refactor at fileSystem.ts:276.
        read_section(
            EXT_ROOT / "src" / "utils" / "fileSystem.ts",
            "// Set 035: state-file-first cancellation detection.",
            "let totalSessions: number | null = null;",
        ),
        # Updated import line.
        read_section(
            EXT_ROOT / "src" / "utils" / "fileSystem.ts",
            'import { isCancelled, readCancellationState } from "./cancelLifecycle";',
            "\n",
        ),
        # New test suite.
        read_section(
            EXT_ROOT / "src" / "test" / "suite" / "cancelLifecycle.test.ts",
            'suite("cancelLifecycle — readCancellationState (Set 035 state-file-first)"',
        ),
        # Schema doc — status-table footnote.
        read_section(
            REPO_ROOT / "docs" / "session-state-schema.md",
            '- `"cancelled"` — set was cancelled mid-flight.',
            "**Aliases tolerated on read",
        ),
        # Schema doc — full Cancel / restore section.
        read_section(
            REPO_ROOT / "docs" / "session-state-schema.md",
            "## Cancel / restore\n",
            "## Lazy synthesis",
        ),
        # Schema doc — bucketing table first bullet.
        read_section(
            REPO_ROOT / "docs" / "session-state-schema.md",
            "## Bucketing in the Session Sets Explorer (v3)",
            "The \"not mid-set\" guard",
        ),
        # Empty-state simplification.
        read_section(
            EXT_ROOT / "src" / "providers" / "OrchestratorAccordion.ts",
            "// Empty state for the accordion: marker not present",
            "// Loaded state: marker present.",
        ),
        # Ground truth — Session 1 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 1 of 4: Reader migration to state-file-sole-truth",
            "---\n\n## Session 2 of 4:",
        ),
        # Ground truth — full spec project-overview for context.
        read_section(
            SET_DIR / "spec.md",
            "## Project Overview",
            "---\n\n## Session 1 of 4:",
        ),
    ]
    return "\n\n".join(parts)


def run_round(label: str, code_block: str, focus_prompt: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{label}] sending verification call to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=focus_prompt,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE ---\n{code_block}",
        session_set="035-state-file-sole-truth-marker-retirement",
        session_number=1,
    )
    dumped = dump_route_result_to_json(result)
    out_path.write_text(json.dumps(dumped, default=str, indent=2), encoding="utf-8")
    cost = dumped.get("cost_usd") or dumped.get("cost") or "?"
    model = dumped.get("model") or dumped.get("model_name") or "?"
    tokens = (
        f"in={dumped.get('input_tokens', '?')}, "
        f"out={dumped.get('output_tokens', '?')}"
    )
    print(f"[{label}] model={model} cost=${cost} tokens={tokens}")
    print(f"[{label}] full response saved to: {out_path}")
    text = dumped.get("response") or dumped.get("text") or dumped.get("content")
    if isinstance(text, str):
        print(f"\n--- [{label}] VERIFIER OUTPUT ---\n{text}\n--- end [{label}] ---")
    return dumped


def main() -> None:
    out_dir = SET_DIR / "verification-output"
    out_dir.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python verify_session1.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-1-result.json",
        )
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated code.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round(
            "Round B",
            bundle,
            focus,
            out_dir / "round-b-session-1-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
