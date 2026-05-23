"""Cross-provider verification for Set 036 Session 3.

Verifies the signalKind retirement + Codex config.toml watcher
retirement shipped in Session 3. The work is overwhelmingly a
delete/simplify pass:

  * `tools/dabbler-ai-orchestration/src/codex/configWatcher.ts`
    — DELETED (the watcher's check-out claims violated the D1
    watcher-scope discipline locked in the proposal-addendum).
  * `tools/dabbler-ai-orchestration/src/codex/` directory — gone.
  * `tools/dabbler-ai-orchestration/src/test/suite/codexConfigParser.test.ts`
    — DELETED (was the test pair for the watcher).
  * `tools/dabbler-ai-orchestration/src/extension.ts` — drop the
    `activateCodexConfigWatcher` import + `safeRegister` block.
  * `tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts`
    — retire the `signalKind` enum from `OrchestratorMarker` (both
    top-level + nested under `effort`); drop the clock-overlay span;
    drop the "(configured default)" qualifier from `describeMarker`;
    collapse `modelTooltip` / `effortTooltip` to the single
    live-signal branch; drop the `signalKind` parameter from
    `renderGaugeSvg` (and the `data-signal=` attribute); drop the
    `signal-${...}` class assembly from the gauge-cell class string;
    simplify the `accordionStateFromOrchestratorBlock` adapter so it
    no longer synthesizes `signalKind: "current"`.
  * `tools/dabbler-ai-orchestration/media/orchestrator-indicator/indicator.css`
    + `tools/dabbler-ai-orchestration/media/session-sets-tree/tree.css`
    — delete the `.signal-current` / `.signal-manual` /
    `.signal-last-observed` / `.signal-configured-default` rules
    and the `.clock-overlay` rule; update the visual-treatment
    header comments to record the retirement.

Plus comment-only updates in
  * `src/providers/CheckoutPollService.ts`
  * `src/providers/CustomSessionSetsView.ts`
  * `src/commands/openOrchestratorWriterLog.ts`
  * `src/commands/installOrchestratorHookClaudeCode.ts`
  * `src/commands/installOrchestratorHookGemini.ts`
  * `src/commands/installOrchestratorHookCopilot.ts`
  * `src/test/playwright/session-sets-tree.spec.ts`
  * `src/test/playwright/checkout-polling.spec.ts`

No new tests added (the spec called for updates to
`orchestratorAccordion.test.ts`, but that file doesn't exist —
Session 7's full test sweep + Layer-3 coverage in S5 is the
existing safety net). Test deltas:

  * extension Layer-2 suite: 484 → 474 passing (delta -10 = the
    `codexConfigParser.test.ts` deletion; same 2 pre-existing
    failures from Session 2).
  * ai_router pytest: 686 + 1 skipped (unchanged from Session 2).
  * `npx tsc --noEmit` on the extension — clean.

Total scope ~600 LOC of edits (mostly deletions + comment
rewrites). Single Round A; Round B only if must-fix surfaces.

Usage:
    python scripts/verify_session_036_3.py [--round A|B]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_router as ar  # type: ignore[import-not-found]


SESSION_CONTEXT = (
    "Set 036 Session 3 of 7 — `signalKind` retirement + Codex\n"
    "config-toml watcher retirement. Reference:\n"
    "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/\n"
    "spec.md (Session 3 section).\n\n"
    "Prerequisites:\n"
    "  * Session 1 CLOSED 2026-05-23 (commit 2188744) — chatSessionId\n"
    "    writer migration + per-set lifecycle lock.\n"
    "  * Session 2 CLOSED 2026-05-23 (commit 8cc0d2d) — new_chat_id\n"
    "    CLI + Claude invoker session_id pass-through.\n\n"
    "Audit-locked verdict (proposal-addendum §D1 — Watcher-scope\n"
    "discipline): the discipline applies to ORCHESTRATOR-STATE\n"
    "INFERENCE. Watchers that infer 'which orchestrator is claiming a\n"
    "session' from indirect signals (config.toml changes, MRU file\n"
    "ages, /think slash-command observations) are FORBIDDEN. Non-\n"
    "orchestrator UI refresh watchers (session-state.json,\n"
    "activity-log.json, CANCELLED.md) remain permitted. The system's\n"
    "sole orchestrator-claim path is the canonical writer\n"
    "(`python -m ai_router.start_session`); inference paths are dead.\n\n"
    "The Codex config.toml watcher was the most prominent inference\n"
    "violator (it computed a `codex + openai` claim from a TOML edit\n"
    "and dispatched start_session on the operator's behalf). The\n"
    "`signalKind` enum existed to communicate the quality/recency of\n"
    "the inferred signal to operators ('configured-default' for\n"
    "Codex-watcher claims, 'last-observed' for /think-derived effort,\n"
    "'manual' for quickpick claims, 'current' for live SessionStart\n"
    "writes). With the Codex watcher gone and the /think_*\n"
    "UserPromptSubmit hook dropped in Set 033 S3, every remaining\n"
    "signal is by construction 'current' — the enum has no remaining\n"
    "discriminator and its UI affordances (clock-overlay span,\n"
    "'(configured default)' qualifier, dashed-rim CSS treatment) are\n"
    "dead chrome. Session 3 retires the enum + its UI surface entirely.\n\n"
    "Test results on this host (no new tests added; test sweep\n"
    "confirms no regressions vs Session 2 baseline):\n"
    "  * ai_router pytest — 686 passed + 1 skipped (matches Session 2).\n"
    "  * extension Layer-2 (test:unit harness) — 474 passing\n"
    "    (Session 2 was 484; delta -10 = `codexConfigParser.test.ts`\n"
    "    deletion). Same 2 pre-existing unrelated failures as\n"
    "    Session 2 (configEditor-foundation panel lifecycle +\n"
    "    notificationsSection rendering scaffolding gaps).\n"
    "  * tsc --noEmit on extension — clean.\n\n"
    "Out of scope for Session 3 (deferred per the 7-session split):\n"
    "  * Takeover UX modal/CLI prompt + watcher-inventory test (S4).\n"
    "  * Layer-3 Playwright coverage + cross-tier docs + cross-repo\n"
    "    notice (S5).\n"
    "  * Orchestrator-agnostic UI audit + empty-state refactor (S6).\n"
    "  * Final test sweep + change-log + dual-registry release (S7).\n\n"
    "Risk to call out (R5 in the spec): `signalKind` retirement\n"
    "breaks legacy data readers. The reader-side tolerance is built\n"
    "into the OrchestratorMarker schema — older on-disk data with a\n"
    "`signalKind` field is silently dropped on read (TypeScript\n"
    "interface no longer carries the field; JSON.parse just discards\n"
    "extra keys). Marketplace download count is 5 as of 2026-05-21;\n"
    "external consumers negligible."
)


VERIFICATION_ASKS = (
    "Verification asks for Round A (single round; bundle is mostly\n"
    "deletions + comment updates, no behavioral additions):\n\n"
    "1. tools/dabbler-ai-orchestration/src/providers/OrchestratorAccordion.ts\n"
    "   (post-refactor full file — the only file with non-trivial\n"
    "   behavior changes in this session):\n"
    "   (a) `OrchestratorMarker` interface — both the top-level\n"
    "       `signalKind` field and the nested `effort.signalKind` +\n"
    "       `effort.observedAt` fields are gone. Is the loss of\n"
    "       `observedAt` correct? It was only ever populated by the\n"
    "       /think_* observation path; the orchestrator-block adapter\n"
    "       never set it. Confirm nothing in the renderer or in\n"
    "       downstream consumers still reads it.\n"
    "   (b) `describeMarker` — the '(configured default)' qualifier\n"
    "       branch is gone; the 'thinking on (last /think Xs ago)'\n"
    "       branch is gone. Did the refactor accidentally drop any\n"
    "       remaining-needed behavior? Specifically: the\n"
    "       `providerHasExtraCapacity` branch still chooses between\n"
    "       'thinking on' / 'thinking off' based on `marker.effort.\n"
    "       thinking`, which the adapter hard-codes to `false`. Is\n"
    "       that intentional? (Yes per Set 033 S2 — the adapter\n"
    "       doesn't track /think runtime state.)\n"
    "   (c) `renderGaugeSvg` signature dropped `signalKind: string`\n"
    "       and the SVG no longer emits `data-signal=`. CSS no longer\n"
    "       selects on the attribute, so the data-attr is dead.\n"
    "       Confirmed no test asserts the attribute's presence.\n"
    "   (d) `modelTooltip` collapsed from a 4-branch switch to a\n"
    "       single 'live signal' return. `effortTooltip` similarly\n"
    "       collapsed. The `marker.effort.observedAt` field that\n"
    "       used to feed the `last-observed` branch is gone with the\n"
    "       interface. Is the new tooltip text honest? (It says\n"
    "       'live signal' / '<effort> effort (<confidence>\n"
    "       confidence)' — both align with the writer's self-report\n"
    "       semantics.)\n"
    "   (e) `renderAccordionLoaded` — `modelClasses` / `effortClasses`\n"
    "       no longer include `signal-${...}` tokens; the\n"
    "       `clock-overlay` span is no longer interpolated; the\n"
    "       `renderGaugeSvg` calls pass only `(tier, needle)`. Did\n"
    "       any tests pin the `signal-current` class on a rendered\n"
    "       gauge? (Audit: no — the Playwright tests assert provider\n"
    "       sublabel text only, not signal class tokens.)\n"
    "   (f) `accordionStateFromOrchestratorBlock` — the synthesized\n"
    "       marker no longer carries `signalKind: 'current'` or the\n"
    "       nested `effort.signalKind: 'current'`. TypeScript would\n"
    "       have errored if any caller still expected those fields,\n"
    "       and `tsc --noEmit` is clean.\n\n"
    "2. tools/dabbler-ai-orchestration/src/codex/configWatcher.ts —\n"
    "   DELETED. The file was the sole producer of `codex + openai`\n"
    "   start_session claims via filesystem inference (TOML edit →\n"
    "   debounced subprocess spawn). The deletion takes the entire\n"
    "   `src/codex/` directory with it (it was the only file).\n"
    "   Knock-on:\n"
    "   (a) `tools/dabbler-ai-orchestration/src/extension.ts` lost the\n"
    "       import + the `safeRegister('activateCodexConfigWatcher',\n"
    "       ...)` block. The neighboring comment block was rewritten\n"
    "       to flag the deletion + record the rationale (Codex now\n"
    "       manual-only via Check Out As…).\n"
    "   (b) `tools/dabbler-ai-orchestration/src/test/suite/codexConfigParser.test.ts`\n"
    "       — DELETED (10 tests; was the unit-test pair for the\n"
    "       deleted TOML extractor + parser).\n"
    "   (c) `tools/dabbler-ai-orchestration/src/providers/CheckoutPollService.ts`\n"
    "       comment updated to drop the `configWatcher.ts` cross-\n"
    "       reference (the resolver-mirror comment).\n"
    "   (d) `tools/dabbler-ai-orchestration/src/test/playwright/checkout-polling.spec.ts`\n"
    "       comment updated — the sentinel-file scenario continues\n"
    "       to work (the Claude SessionStart invoker is still a\n"
    "       producer of conflict records on EXIT_CHECKOUT_CONFLICT).\n"
    "   Question: did any other code path call into the watcher\n"
    "   (e.g., a polling-mode reconciler that scanned codex/\n"
    "   subscriptions)? Audit says no — `activateCodexConfigWatcher`\n"
    "   was the sole entry point.\n\n"
    "3. CSS cleanup —\n"
    "   `tools/dabbler-ai-orchestration/media/orchestrator-indicator/indicator.css`\n"
    "   + `tools/dabbler-ai-orchestration/media/session-sets-tree/tree.css`:\n"
    "   the `.signal-*` rules and the `.clock-overlay` rule are\n"
    "   gone from both files. The visual-treatment matrix header\n"
    "   comment is rewritten to record the retirement. Question:\n"
    "   the orphaned `.grey-gauges` rules in both files were\n"
    "   ALREADY dead post-Set-035 (Set 035 Session 1 stopped\n"
    "   emitting grey gauges from `renderAccordionEmpty`). Spec\n"
    "   delegates their removal to Session 6's CSS sweep; this\n"
    "   session deliberately leaves them. Is that the right call,\n"
    "   or should they go in this session as part of the same CSS\n"
    "   pass? (Argument for deferring: keeps Session 3 focused on\n"
    "   the spec'd retirement; Session 6 already plans the sweep.)\n\n"
    "4. Documentation/comment updates (no behavior change):\n"
    "   * `src/providers/CustomSessionSetsView.ts` — the per-row\n"
    "     accordion-retirement rationale now reads neutrally\n"
    "     instead of pointing at `signalKind always \"current\"`.\n"
    "   * `src/commands/openOrchestratorWriterLog.ts` — module\n"
    "     comment + 'no writer log yet' info message rewritten to\n"
    "     describe the canonical writer's behavior (refusals +\n"
    "     force-overrides), not the deleted marker writer's.\n"
    "   * `src/commands/installOrchestratorHookClaudeCode.ts` —\n"
    "     comments updated to flag the signalKind retirement.\n"
    "   * `src/commands/installOrchestratorHookGemini.ts` /\n"
    "     `installOrchestratorHookCopilot.ts` — both file-level\n"
    "     comments extended to note that Codex now joins the\n"
    "     manual-only set.\n"
    "   * `src/test/playwright/session-sets-tree.spec.ts` — comment\n"
    "     header updated to reflect that the signalKind enum is gone\n"
    "     on the renderer side too.\n"
    "   Question: any place that still references signalKind /\n"
    "   configured-default / last-observed in a way that would\n"
    "   confuse a future reader? Grep audit shows the only remaining\n"
    "   hits are explanatory retirement comments and an audit-trail\n"
    "   reference in the CSS header. Confirm.\n\n"
    "5. Test posture: no new tests; `npx tsc --noEmit` clean;\n"
    "   `npm run test:unit` shows 474 pass / 2 pre-existing-failures\n"
    "   (matches Session 2 baseline minus 10 deleted\n"
    "   codexConfigParser tests); `python -m pytest` shows 686 + 1\n"
    "   skipped (unchanged from Session 2). Is a missing\n"
    "   `orchestratorAccordion.test.ts` (the spec called for it,\n"
    "   but the file never existed) a Blocker, or is the Playwright\n"
    "   coverage Session 5 will add the right place to lock the new\n"
    "   contract? (Argument for the latter: the simplified renderer\n"
    "   is mostly deletion; the contract change is best pinned by a\n"
    "   visual smoke that asserts no `signal-` class on a rendered\n"
    "   gauge.)\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references — sessions 4-7 will reference this verdict."
)


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 3 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="036-chatsessionid-and-watcher-scope-implementation",
        session_number=3,
    )
    dump_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "036-chatsessionid-and-watcher-scope-implementation"
        / "verification-output"
        / f"round-{label.lower()}-session-3-result.json"
    )
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        as_dict = dataclasses.asdict(result)
    except TypeError:
        as_dict = {k: v for k, v in vars(result).items()}
    cleaned: dict = {}
    for k, v in as_dict.items():
        try:
            json.dumps(v)
            cleaned[k] = v
        except TypeError:
            cleaned[k] = repr(v)
    dump_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"  Dumped to {dump_path.relative_to(REPO_ROOT)}")
    data = json.loads(dump_path.read_text(encoding="utf-8"))
    print("  === VERIFIER RESPONSE ===")
    print(data.get("content", "<no content>"))
    print()
    print(
        f"  model={data.get('model_name')} "
        f"input_tokens={data.get('input_tokens')} "
        f"output_tokens={data.get('output_tokens')} "
        f"cost_usd={data.get('total_cost_usd')}"
    )
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", choices=["A", "B"], default="A")
    args = parser.parse_args()

    ext_dir = REPO_ROOT / "tools" / "dabbler-ai-orchestration"

    accordion_text = (
        ext_dir / "src" / "providers" / "OrchestratorAccordion.ts"
    ).read_text("utf-8")
    indicator_css_text = (
        ext_dir / "media" / "orchestrator-indicator" / "indicator.css"
    ).read_text("utf-8")
    tree_css_text = (
        ext_dir / "media" / "session-sets-tree" / "tree.css"
    ).read_text("utf-8")
    extension_text = (
        ext_dir / "src" / "extension.ts"
    ).read_text("utf-8")
    custom_view_text = (
        ext_dir / "src" / "providers" / "CustomSessionSetsView.ts"
    ).read_text("utf-8")
    writer_log_text = (
        ext_dir / "src" / "commands" / "openOrchestratorWriterLog.ts"
    ).read_text("utf-8")
    claude_installer_text = (
        ext_dir / "src" / "commands" / "installOrchestratorHookClaudeCode.ts"
    ).read_text("utf-8")
    gemini_installer_text = (
        ext_dir / "src" / "commands" / "installOrchestratorHookGemini.ts"
    ).read_text("utf-8")
    copilot_installer_text = (
        ext_dir / "src" / "commands" / "installOrchestratorHookCopilot.ts"
    ).read_text("utf-8")
    pollservice_text = (
        ext_dir / "src" / "providers" / "CheckoutPollService.ts"
    ).read_text("utf-8")

    rounds = {
        "A": (
            "Round A: full post-refactor source bundle",
            (
                f"=== src/providers/OrchestratorAccordion.ts (full file — primary refactor) ===\n"
                f"{accordion_text}\n\n"
                f"=== media/orchestrator-indicator/indicator.css (full file — signal-* + clock-overlay rules removed) ===\n"
                f"{indicator_css_text}\n\n"
                f"=== media/session-sets-tree/tree.css (full file — signal-* + clock-overlay rules removed) ===\n"
                f"{tree_css_text}\n\n"
                f"=== src/extension.ts (full file — activateCodexConfigWatcher import + safeRegister removed) ===\n"
                f"{extension_text}\n\n"
                f"=== src/providers/CustomSessionSetsView.ts (full file — line 402 comment updated) ===\n"
                f"{custom_view_text}\n\n"
                f"=== src/providers/CheckoutPollService.ts (full file — configWatcher.ts cross-ref removed from comment) ===\n"
                f"{pollservice_text}\n\n"
                f"=== src/commands/openOrchestratorWriterLog.ts (full file — module comment + info message rewritten) ===\n"
                f"{writer_log_text}\n\n"
                f"=== src/commands/installOrchestratorHookClaudeCode.ts (full file — signalKind retirement noted) ===\n"
                f"{claude_installer_text}\n\n"
                f"=== src/commands/installOrchestratorHookGemini.ts (full file — Codex-now-manual-only note added) ===\n"
                f"{gemini_installer_text}\n\n"
                f"=== src/commands/installOrchestratorHookCopilot.ts (full file — Codex-now-manual-only note added) ===\n"
                f"{copilot_installer_text}\n"
            ),
            VERIFICATION_ASKS,
        ),
        "B": (
            "Round B: re-verify after Round A must-fix changes",
            (
                f"=== src/providers/OrchestratorAccordion.ts (full file — post-Round-A) ===\n"
                f"{accordion_text}\n"
            ),
            "Round B: confirm Round A blockers are addressed. See Round A "
            "verdict for the specific findings to re-check.",
        ),
    }

    label, bundle, asks = rounds[args.round]
    print(f"Running {label} ...")
    _run_round(args.round, bundle, asks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
