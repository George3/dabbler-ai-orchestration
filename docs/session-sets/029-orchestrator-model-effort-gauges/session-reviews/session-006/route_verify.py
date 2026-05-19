"""End-of-session verification for Set 029 Session 6.

Pinning: gemini-pro per the S3 / S4 / S5 pattern. Verification covers
the relegate-buttons refactor (ActionRegistry, OrchestratorAccordion,
tree.css), the async refactor of readCurrentMarkerForWorkspace, and
the corresponding test updates. Docs / CHANGELOG / README / CLAUDE.md
text changes are excluded from the verification bundle — those are
self-evident in the diff and don't warrant routed review.

Per memory `feedback_split_large_verification_bundles`: this bundle
is ~14k chars / ~270 lines diff, well under the 700-LOC threshold.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# session-006 -> session-reviews -> 029-... -> session-sets -> docs -> repo
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


PROMPT_TEMPLATE = """\
# Set 029 Session 6 — end-of-session verification

Verifier: gemini-pro (S3/S4/S5 pin).

## Context

Session 6 of Set 029 is the polish + publish session for the
multi-provider orchestrator indicator that shipped in v0.17.0 from
Session 5. The expected scope was: HTML-preview styling iteration,
README/CHANGELOG/CLAUDE.md updates, Marketplace publish. During the
session the operator flagged the "Set Orchestrator…" and "Writer Log"
accordion-body buttons as confusing affordances (the former declares
an orchestrator without setting one). A mid-session cross-provider
consensus call (GPT-5.4 + Gemini Pro) endorsed migrating to a
check-out / check-in architecture as a follow-on session set, and
relegating the two buttons in v0.17.1 as the immediate UI fix.

The architecture migration is NOT in this session's scope — it's
deferred to a follow-on session set `030-orchestrator-checkout-checkin`
with audit-input artifacts preserved at
`docs/proposals/2026-05-19-orchestrator-tracking-architecture/`. Three
High items + two open questions are pre-captured for that audit
cycle's must-resolve list.

This session's actual source-code scope:

1. **Relegate two commands from accordion-body buttons to
   right-click context menu + Command Palette.** Source files:
   `src/providers/ActionRegistry.ts` (new group-5xx entries),
   `src/providers/OrchestratorAccordion.ts` (remove `acc-actions`
   HTML in both empty and loaded states), `media/session-sets-tree/tree.css`
   (remove dead `.acc-actions` + `.acc-action` rules), and
   `src/test/suite/actionRegistry.test.ts` (update the 14-action set
   assertion to 16 + add applicability test for the new actions).

2. **Async refactor of `readCurrentMarkerForWorkspace`** in
   `src/commands/setOrchestratorManual.ts`. Per S5 Round-B Gemini
   SUGGEST #2, converted from sync `fs.statSync` / `fs.readdirSync` /
   `fs.readFileSync` to `fs.promises.*`. Caller `maybeConfirmForceOverride`
   was already `async`; the await chain is well-contained. The
   function is not exported, so no public surface change.

3. **Skipped S5 Round-B Gemini SUGGEST #1** (pushMru race) with
   documented analysis: the race claim assumes the function is
   async, but the current sync implementation has no in-process race
   (JS event loop is single-threaded; `fs.writeFileSync` is atomic
   from the JS perspective). Cross-process races on the file need
   file-level locking, which the proposed promise-chain mutex
   doesn't provide. Both items are folded into the Set 030 module
   rewrite where the surface changes anyway.

Tests run post-change: `npm run test:unit` reports 398 passing, 2
failing (both pre-existing: configEditor-foundation vscode-stub
`ViewColumn.One` miss + notificationsSection placeholder test). The
new ActionRegistry test passes. Compile is clean.

## Diff under review

The diff below covers `src/`, `media/session-sets-tree/tree.css`, and
the test file. Docs / CHANGELOG / package.json / README / CLAUDE.md
text changes are NOT included — those are obvious from inspection
and don't warrant routed review.

```
__DIFF__
```

## Questions

Provide a verdict per question. Format: VERIFIED / SUGGEST / MUST-FIX +
1–3 sentence reasoning. If MUST-FIX, name the file + line and the
specific fix.

**Q1 — ActionRegistry correctness.** Are the two new actions
(`dabbler.setOrchestrator` at group 501, `dabbler.openOrchestratorWriterLog`
at group 502) wired correctly? Specifically: do the `when` predicates
match the intent (setOrchestrator only on in-progress rows; writer
log always available)? Does the ordering by group keep the menu
deterministic? Is the test's new applicability case correct?

**Q2 — OrchestratorAccordion HTML cleanup.** Are the `acc-actions`
blocks removed from BOTH `renderAccordionEmpty` and
`renderAccordionLoaded` without breaking the surrounding HTML
structure? The `acc-link` (smart-CTA install link) in
`renderAccordionEmpty` must still render; the `staleAnnotation +
modelSections` flow in `renderAccordionLoaded` must still emit
without the removed `actionsRow` template. Verify the template
literal closes cleanly.

**Q3 — Dead-CSS removal in `tree.css`.** Are the `.acc-actions` and
`.acc-action` rules removed without taking adjacent rules with them?
The `.acc-link` rule below them must still exist and parse.

**Q4 — `readCurrentMarkerForWorkspace` async correctness.** Verify
the conversion: every `fs.statSync` / `fs.readdirSync` /
`fs.readFileSync` is replaced with the corresponding `fs.promises.*`
+ `await`. The walk-up loop's control flow is preserved (no early
return that should have stayed; no `return empty` collapsed
incorrectly). The function is `async` and returns `Promise<...>`.
The single caller `maybeConfirmForceOverride` awaits it.

**Q5 — Test correctness.** Does the updated
`actionRegistry.test.ts` correctly assert the 16-action set? Does
the new `"setOrchestrator appears only on in-progress rows"` test
cover the matrix (in-progress: yes; not-started/complete/cancelled:
no) for `setOrchestrator`, and (all four states: yes) for the
writer log?

**Q6 — Anything else risky.** Any other concern in this diff —
imports, exception handling that should have changed but didn't,
breaking changes to exported types, etc.?
"""


def _dump(result, label: str) -> dict:
    if dataclasses.is_dataclass(result):
        d = dataclasses.asdict(result)
    else:
        d = {
            "content": getattr(result, "content", None),
            "model_name": getattr(result, "model_name", None),
            "model_id": getattr(result, "model_id", None),
            "input_tokens": getattr(result, "input_tokens", None),
            "output_tokens": getattr(result, "output_tokens", None),
            "cost_usd": getattr(result, "cost_usd", None),
            "total_cost_usd": getattr(result, "total_cost_usd", None),
        }
    (HERE / f"verify-result-{label}.txt").write_text(
        d.get("content") or "", encoding="utf-8"
    )
    (HERE / f"verify-result-{label}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return d


def main() -> int:
    diff = Path("c:/tmp/s6-source-diff.txt").read_text(encoding="utf-8")
    content = PROMPT_TEMPLATE.replace("__DIFF__", diff)
    spec_dir = REPO_ROOT / "docs" / "session-sets" / "029-orchestrator-model-effort-gauges"
    print(f"Gemini Pro prompt size: {len(content):,} chars")
    result = ai_router.query(
        model="gemini-pro",
        content=content,
        task_type="session-verification",
        session_set=str(spec_dir),
        session_number=6,
    )
    d = _dump(result, "round-a")
    cost = d.get("total_cost_usd") or d.get("cost_usd")
    print(
        f"Gemini Pro: cost ${cost} / "
        f"{d.get('input_tokens')} in / {d.get('output_tokens')} out"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
