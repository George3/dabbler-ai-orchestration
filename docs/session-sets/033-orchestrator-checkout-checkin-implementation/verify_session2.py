"""Session 2 verification driver — Set 033 (implementation cycle).

Round A bundles the artifacts produced by Session 2:

  - tools/dabbler-ai-orchestration/src/providers/inProgressSetsService.ts
    — renamed module, listInProgressSets() + extractRecommendation()
    + recommendationFor() (the per-set ai-assignment lookup that
    replaces MarkerWatchService's private findActiveRecommendation).
  - tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts
    — added the accordionStateFromOrchestratorBlock() helper that
    synthesizes a RenderState from the orchestrator block on
    session-state.json (Set 033 Session 1 schema).
  - tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts
    — refactored postSnapshot + buildBuckets + buildBucket + buildRow
    to render N in-progress accordions; banner removed; suppression
    key field renamed.
  - tools/dabbler-ai-orchestration/src/types/sessionSetsWebviewProtocol.ts
    — protocol changes (ambiguityBanner dropped, isResolvedSet
    dropped, markerUpdatedAt → accordionUpdatedAt rename).
  - tools/dabbler-ai-orchestration/media/session-sets-tree/client.js
    — webview-side: banner rendering gone; isExpandable predicate
    simplified to "accordionHtml !== null"; suppression check uses
    accordionUpdatedAt.
  - tools/dabbler-ai-orchestration/src/extension.ts (relevant block)
    — MarkerWatchService construction removed.
  - tools/dabbler-ai-orchestration/src/test/suite/inProgressSetsService.test.ts
    — 7 preserved extractRecommendation tests + 3 new
    listInProgressSets tests.
  - tools/dabbler-ai-orchestration/src/test/playwright/session-sets-tree.spec.ts
    — pre-Set-033 marker-seeded scenarios removed; orchestrator-block
    + multi-in-progress scenarios added.

Ground truth bundled alongside:

  - The H2 verdict (§9 of proposal-addendum.md, line item H2 only) —
    the audit decision the implementation must trace to.
  - Set 033 spec.md Session 2 — the contract this session ships.
  - Set 033 schema check-out / check-in section — the data shape
    the new reader consumes.

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
PROPOSAL_DIR = (
    REPO_ROOT / "docs" / "proposals" / "2026-05-19-orchestrator-tracking-architecture"
)


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
Set 033 implements the orchestrator check-out / check-in migration
from the six verdicts the Set 032 audit locked. Session 1 (CLOSED)
shipped the Python writer side (H1+H3+H4+OQ1) — register_session_start
now writes checkedOutAt + lastActivityAt under the orchestrator block;
start_session enforces hard coordination with a --force override; the
schema doc captures the contract.

Session 2 (THIS verification) ships the TypeScript reader-side
migration (H2): the per-set `.dabbler/orchestrator.json` marker file
is retired entirely. The MarkerWatchService class with its
`resolveActiveSet()` walk-up resolver, marker file watcher, polling
backstop, and "multi-in-progress ambiguity banner" is replaced by:

  - A free function `listInProgressSets(all?)` in the renamed module
    `inProgressSetsService.ts` that returns the array of in-progress
    SessionSets sorted by startedAt ascending.
  - A `recommendationFor(set)` helper for the per-row mismatch lookup
    (the pre-Set-033 `findActiveRecommendation` is now a thin
    per-set wrapper around the unchanged `extractRecommendation`).
  - An `accordionStateFromOrchestratorBlock(block, recommendation)`
    helper in OrchestratorAccordion.ts that synthesizes the old
    `RenderState` shape from the new orchestrator block — preserving
    the gauge geometry, mismatch logic, and CSS class hooks. The
    synthesizer always emits `signalKind = "current"` and
    `confidence = "high"` (the writer is the authority; the retired
    last-observed / configured-default / manual signal kinds no
    longer apply).
  - CustomSessionSetsView refactored so every in-progress row gets
    its own accordion (not just the resolver's single "active set"),
    and the multi-in-progress ambiguity banner is removed from the
    protocol + client.

Sessions 3-6 are out of scope for THIS verification. The bundle
includes only Session 2 deliverables.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 2 implementation faithfulness for the H2 reader-
side migration, contract coverage of the spec's nine steps, and
test adequacy across Layers 2 and 3.

You are Gemini Pro, asked to verify that Session 2 of Set 033 ships
the TypeScript reader-side check-out / check-in migration consistent
with the H2 locked verdict.

Verify:

A. **H2 retirement of the per-set marker file is complete and
   correct.** Confirm:

   1. The bundled `inProgressSetsService.ts` exports
      `listInProgressSets()` and NO API named `resolveActiveSet()`
      (the H2 replacement is total, not additive).
   2. The bundled `inProgressSetsService.ts` does NOT read or write
      `.dabbler/orchestrator.json`. No fs.readFileSync /
      vscode.workspace.createFileSystemWatcher reaches into the
      retired marker path.
   3. `listInProgressSets()` returns SessionSet records sorted by
      `startedAt` ascending (the spec's "oldest in-flight ranks
      first" intent — verified directly by the third unit test
      "tolerates missing startedAt").
   4. The protocol type `SnapshotPayload.ambiguityBanner` field is
      gone. The protocol type `RowPayload.isResolvedSet` field is
      gone. The replacement `accordionUpdatedAt` field is present
      and documented.
   5. The CustomSessionSetsView's buildRow renders an accordion for
      EVERY in-progress row (not just one). Non-in-progress rows
      still skip the accordion entirely (per S4 Q3 = a — preserved
      from the pre-Set-033 design).

B. **accordionStateFromOrchestratorBlock synthesis correctness.**
   The helper takes the Set 033 Session 1 schema's orchestrator
   block (engine, provider, model, effort, checkedOutAt,
   lastActivityAt) and returns a RenderState the unchanged renderer
   can consume.

   1. Null / partial block → `{ kind: "empty" }`. Specifically:
      block === null/undefined → empty; block lacking both provider
      AND model → empty (the synthesizer refuses to fabricate
      identity).
   2. Loaded block → `{ kind: "loaded", marker, stale, ageSec,
      mismatch }`. Verify the synthesized marker:
      - `signalKind` is always "current".
      - `confidence` is always "high".
      - `tier` is `classifyRecommendationTier(provider, model)`.
      - `thinking` is always `false`.
      - `stalenessMaxSec` is the default.
      - `updatedAt` falls back through:
        `lastActivityAt` ?? `checkedOutAt` ?? now.
   3. Age calculation uses `lastActivityAt` (preferred) then
      `checkedOutAt` then 0; stale predicate is the same threshold
      the prior renderer used.
   4. Mismatch computation uses the existing `computeMismatch`
      function unchanged.

C. **Suppression-state continuity.** Pre-Set-033 the suppression
   key was (slug, marker.updatedAt). The new key is (slug,
   orchestrator.lastActivityAt) flowing through the same
   `suppressionState` reducer functions (suppressionState.ts is
   unchanged). The wire-protocol field renamed from
   `markerUpdatedAt` to `accordionUpdatedAt` end-to-end:
   - CustomSessionSetsView's `handleToggle` accepts
     `accordionUpdatedAt: string | null`.
   - The protocol type `ToggleRowMsg.accordionUpdatedAt` matches.
   - The client.js posts `accordionUpdatedAt` and reads
     `data-accordion-updated-at`.
   - The DOM attribute name on `<div role="treeitem">` is
     `data-accordion-updated-at` (not `data-marker-updated-at`).

D. **Banner removal end-to-end.**
   1. Protocol type `SnapshotPayload` has no `ambiguityBanner` field.
   2. CustomSessionSetsView's `postSnapshot` builds no
      `ambiguityBanner` payload object.
   3. client.js no longer renders `.ambiguity-banner` div.
   4. The Playwright multi-in-progress scenario asserts
      `.ambiguity-banner` has count 0.

E. **Test adequacy (Layer 2).**
   - 7 preserved `extractRecommendation` tests — confirm the import
     points at `inProgressSetsService` (not the retired
     MarkerWatchService) and the test bodies are unchanged.
   - 3 new `listInProgressSets` tests — confirm coverage of
     (i) filter+sort, (ii) empty result, (iii) tolerance of null
     `startedAt`.

F. **Test adequacy (Layer 3).**
   - Pre-Set-033 marker-seeded scenarios ("configured-default Codex"
     + "manual Gemini") are removed (the signalKind affordance they
     covered is retired).
   - A new scenario seeds the orchestrator block on session-state
     and asserts the provider sublabel renders.
   - A new multi-in-progress scenario seeds TWO in-progress sets
     with distinct orchestrator identities and asserts BOTH rows
     carry the `data-expandable="1"` attribute AND the ambiguity
     banner has count 0.

G. **What's risky or missing.** Any edge case the implementation
   omits that would bite a real run?
   - An in-progress set with `orchestrator: null` (pre-Set-033
     workspace migrating mid-flight). Does the accordion render an
     empty-state CTA correctly?
   - A session-state.json with `orchestrator.provider` missing but
     `engine` present (a pre-Set-033 state file populated by a
     hook that pre-dated the provider field). Does the synthesizer
     fall back to `engine` as the provider display value?
   - The file rename from MarkerWatchService.ts →
     inProgressSetsService.ts — are there any stale string
     references to the old name anywhere bundled below that would
     still resolve at compile time but indicate a missed update?
   - The `extension.ts` excerpt: was the `MarkerWatchService` import
     fully removed, and is the `provider` instance no longer
     receiving a marker constructor argument?

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits. Session 2 ships the reader-side
foundation Sessions 3-5 build on (Session 3's UI rename presumes
the per-row accordion exists; Session 4's Playwright scenarios
exercise the multi-in-progress rendering; Session 5's queueing
polls for orchestrator-block changes the new reader observes) —
a must-fix here will block downstream work.
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverables — full files where the change is wholesale.
        read_file(EXT_ROOT / "src" / "providers" / "inProgressSetsService.ts"),
        # OrchestratorAccordion full — verifier needs to see the
        # types (OrchestratorMarker, RenderState) AND the new
        # synthesizer in one place.
        read_file(EXT_ROOT / "src" / "providers" / "OrchestratorAccordion.ts"),
        # CustomSessionSetsView full — the buildBucket/buildRow
        # rewrite is the structural heart of the change.
        read_file(EXT_ROOT / "src" / "providers" / "CustomSessionSetsView.ts"),
        # Protocol — small file, ship in full.
        read_file(EXT_ROOT / "src" / "types" / "sessionSetsWebviewProtocol.ts"),
        # client.js — webview-side, ship in full so the verifier
        # can cross-check the DOM attribute name + suppression flow.
        read_file(EXT_ROOT / "media" / "session-sets-tree" / "client.js"),
        # Layer-2 tests — ship full so coverage assertions are
        # checkable directly.
        read_file(EXT_ROOT / "src" / "test" / "suite" / "inProgressSetsService.test.ts"),
        # Layer-3 spec — ship full so the new/removed scenarios are
        # visible end-to-end.
        read_file(EXT_ROOT / "src" / "test" / "playwright" / "session-sets-tree.spec.ts"),
        # Extension.ts excerpt — just the marker-construction removal.
        read_section(
            EXT_ROOT / "src" / "extension.ts",
            "export function activate(",
            "const evaluateContextKeys =",
        ),
        # Ground truth — H2 verdict from the locked addendum.
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # Ground truth — Session 2 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 2 of 6:",
            "## Session 3 of 6:",
        ),
        # Ground truth — the Session 1 schema doc section that
        # describes the orchestrator block the new reader consumes.
        read_section(
            REPO_ROOT / "docs" / "session-state-schema.md",
            "### Check-out / check-in (Set 033)",
            "### Dual-write legacy fields",
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
        session_set="033-orchestrator-checkout-checkin-implementation",
        session_number=2,
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
        print("Usage: python verify_session2.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-2-result.json",
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
            out_dir / "round-b-session-2-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
