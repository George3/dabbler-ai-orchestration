"""Cross-provider verification for Set 036 Session 4.

Verifies the Q3 Takeover-UX modal + CLI prompt + Q7 watcher-inventory
convention test shipped in Session 4. Scope:

  * NEW
    `tools/dabbler-ai-orchestration/src/providers/chatSessionMismatchModal.ts`
    — Q3-locked modal helper (3 buttons; pure helpers; injectable
    surface).
  * NEW
    `tools/dabbler-ai-orchestration/src/providers/ReadOnlyIntentService.ts`
    — transient in-memory map (Set<path>) of read-only-intent flags;
    singleton accessor + test-reset helper.
  * `tools/dabbler-ai-orchestration/src/providers/CheckoutPollService.ts`
    — ConflictRecord schema extended (heldByChatSessionId +
    wouldBeHolderChatSessionId, optional/backward-compatible);
    isChatSessionMismatch predicate added; handleConflict branches
    on the predicate to the new handleChatSessionMismatch helper that
    drives the modal; spawnRetry now forwards --chat-session-id for
    the take-over write.
  * `tools/dabbler-ai-orchestration/src/commands/checkOutOrchestrator.ts`
    — maybeClearReadOnlyIntent() gate runs before
    maybeConfirmForceOverride() so an extension-side write on a
    read-only-flagged set surfaces an explicit clear-intent prompt.
  * `tools/dabbler-ai-orchestration/src/extension.ts` — registers
    the ReadOnlyIntentService singleton's dispose() with
    context.subscriptions.
  * `tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`
    — emitConflictRecord now populates heldByChatSessionId +
    wouldBeHolderChatSessionId.
  * `ai_router/start_session.py` — new _is_interactive_tty() +
    _prompt_takeover_choice() helpers; H3 refusal branch now gates
    the prompt on (chatSessionId mismatch AND interactive TTY);
    EXIT_READ_ONLY=6 added for the read-only choice.
  * NEW
    `tools/dabbler-ai-orchestration/src/test/suite/watcherInventory.test.ts`
    — Q7-locked allowlisted convention test (3 entries in the
    initial WATCHER_ALLOWLIST + 3 sanity assertions).

Plus new test files (chatSessionMismatchModal.test.ts,
readOnlyIntentService.test.ts, test_start_session_takeover_prompt.py)
and extended checkoutPollService.test.ts. Test totals: ai_router
pytest 693 + 1 skipped (was 686 + 1); extension Layer-2 519 (was 474;
+45), 2 pre-existing failures unchanged. tsc --noEmit clean.

Total scope ~1100 LOC (implementation + tests). Split into Round A
only; Round B fires only if must-fix surfaces.

Usage:
    python scripts/verify_session_036_4.py [--round A|B]
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
    "Set 036 Session 4 of 7 — Takeover UX (Q3) + watcher-inventory\n"
    "convention test (Q7). Reference:\n"
    "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/\n"
    "spec.md (Session 4 section).\n\n"
    "Prerequisites:\n"
    "  * Session 1 CLOSED 2026-05-23 (commit 2188744) — chatSessionId\n"
    "    writer migration + per-set lifecycle lock (Q5).\n"
    "  * Session 2 CLOSED 2026-05-23 (commit 8cc0d2d) — new_chat_id\n"
    "    CLI + Claude SessionStart invoker session_id pass-through\n"
    "    (Q1).\n"
    "  * Session 3 CLOSED 2026-05-23 (commit 7dcf039) — signalKind\n"
    "    enum + Codex config-toml watcher RETIRED (D1).\n\n"
    "Audit-locked verdicts in scope this session:\n\n"
    "  * Q3 Takeover UX — In the VS Code IDE: modal at the takeover\n"
    "    boundary naming the held chatSessionId + proposing\n"
    "    orchestrator + three actions: Take Over (start_session\n"
    "    --force), Open in Read-Only Mode (no claim; state mutations\n"
    "    via extension surfaces refused), Cancel. In a CLI-only flow:\n"
    "    same three actions via stdin single-char selection when\n"
    "    interactive; EXIT_CHECKOUT_CONFLICT when non-interactive\n"
    "    (operator should re-run with --force if takeover intended).\n"
    "    Toast notifications are SECONDARY only (not primary\n"
    "    resolution path).\n\n"
    "  * Q6 (REJECTED) — No persistent `requireExplicitTakeover`\n"
    "    off-switch. The modal does NOT ship a 'Remember this choice'\n"
    "    checkbox. Each takeover gets its own decision.\n\n"
    "  * Q7 Watcher-scope enforcement — allowlisted watcher-inventory\n"
    "    unit test. Every fs.watch / createFileSystemWatcher callsite\n"
    "    must be in a hand-maintained allowlist with a D1 rationale.\n"
    "    New watchers without an allowlist entry fail the test.\n\n"
    "Implementation pattern (per spec):\n"
    "  * The modal is a pure helper (chatSessionMismatchModal) with\n"
    "    an injectable ShowModal surface so Layer-2 tests can drive\n"
    "    each branch without booting vscode.window.\n"
    "  * Read-only intent is in-memory only (ReadOnlyIntentService),\n"
    "    singleton-scoped to the extension host's lifetime. NO\n"
    "    persistence (Q6 REJECTED).\n"
    "  * CheckoutPollService routes chatSessionId-mismatch conflicts\n"
    "    to the modal via isChatSessionMismatch(record) — engine+\n"
    "    provider mismatches stay on the existing poll/force/dismiss\n"
    "    prompt (polling would never resolve on a same-engine\n"
    "    different-chat case, so the modal is the right UX there).\n"
    "  * The CLI prompt in start_session.py is gated on TTY AND chat-\n"
    "    id mismatch — engine+provider mismatches at the CLI stay on\n"
    "    the non-interactive refusal path per Q3 scope.\n"
)


VERIFICATION_ASKS = (
    "Specific things to check:\n\n"
    "1. Q3 modal contract — chatSessionMismatchModal.ts:\n"
    "   * Three buttons in the locked order (Take Over / Open in\n"
    "     Read-Only Mode / Cancel)?\n"
    "   * modal: true option passed (operator must dismiss\n"
    "     explicitly)?\n"
    "   * truncateChatSessionId truncates at 8 chars + ellipsis,\n"
    "     renders <none> for null/empty (per Q3 audit-locked\n"
    "     verdict)?\n"
    "   * resolveChoice maps unknown/undefined labels to 'cancel'\n"
    "     (safe default — never silently take-over)?\n"
    "   * Q6 REJECTED contract: no 'Remember this choice' checkbox\n"
    "     or any other persistent off-switch?\n\n"
    "2. CheckoutPollService routing — does isChatSessionMismatch\n"
    "   correctly route ONLY chatSessionId conflicts (same engine+\n"
    "   provider, both chatSessionIds non-null and different) to the\n"
    "   modal? engine+provider mismatches must stay on the legacy\n"
    "   poll/force/dismiss prompt. null/null and one-null/one-string\n"
    "   collapse to the engine+provider case (tolerant-on-read\n"
    "   alignment with start_session.py's H3 predicate). The take-\n"
    "   over branch must forward --chat-session-id to start_session\n"
    "   --force so the H4 composite is correctly populated for the\n"
    "   new holder (not left as null which would invite a tolerant-\n"
    "   on-read fallback on the next SessionStart).\n\n"
    "3. CLI prompt — start_session.py:\n"
    "   * _is_interactive_tty() requires BOTH stdin AND stderr to be\n"
    "     TTYs (a script capturing stderr would otherwise swallow\n"
    "     the prompt without the operator seeing it)?\n"
    "   * Prompt fires ONLY for the chatSessionId-mismatch case\n"
    "     (engine+provider mismatch stays on the non-interactive\n"
    "     refusal — the modal/CLI prompt is locked to the chat-id\n"
    "     scope per Q3)?\n"
    "   * Empty input / EOF / garbage all default to 'cancel'\n"
    "     (explicit operator confirmation required for take-over)?\n"
    "   * Take Over routes through the existing _log_force_override\n"
    "     → register_session_start path (no new write path)?\n"
    "   * Read-Only exits EXIT_READ_ONLY=6 with a stderr note; no\n"
    "     state mutation?\n\n"
    "4. ReadOnlyIntentService contract — set/clear/isReadOnly are\n"
    "   idempotent (second setReadOnly on the same path does NOT\n"
    "   double-fire onDidChange; clearReadOnly on an unflagged path\n"
    "   is a no-op). Empty paths are ignored. dispose() clears all\n"
    "   intents AND disposes the emitter. Singleton via\n"
    "   getReadOnlyIntentService() shared across\n"
    "   checkOutOrchestrator + CheckoutPollService. Q6-aligned: no\n"
    "   serialization to disk anywhere?\n\n"
    "5. checkOutOrchestrator.ts wiring — maybeClearReadOnlyIntent()\n"
    "   fires BEFORE maybeConfirmForceOverride()? On 'Cancel', the\n"
    "   intent stays set (no write). On 'Clear & Check Out', the\n"
    "   intent is cleared AND the check-out proceeds. The modal\n"
    "   uses { modal: true } so the operator must dismiss\n"
    "   explicitly.\n\n"
    "6. Q7 watcher-inventory test — watcherInventory.test.ts:\n"
    "   * Hand-maintained WATCHER_ALLOWLIST with {file, line, target,\n"
    "     purpose} tuples?\n"
    "   * Scanner walks src/ for fs.watch / createFileSystemWatcher\n"
    "     and asserts each callsite is in the allowlist (orphan test\n"
    "     fails loudly with the D1 rationale-required message)?\n"
    "   * Stale-line-number test catches refactor drift?\n"
    "   * Baseline count of 3 watchers (extension.ts:147 +\n"
    "     CheckoutPollService.ts:249 + CheckoutPollService.ts:426)?\n"
    "   * Test file itself excluded from the scan (via the test/\n"
    "     prefix carve-out)?\n\n"
    "7. ConflictRecord schema extension — additive backward-\n"
    "   compatible (schemaVersion stays 1; new fields are optional;\n"
    "   pre-Set-036 records that omit the fields parse to null on\n"
    "   both new keys). Claude invoker populates both new fields\n"
    "   from existing.chatSessionId and the caller's chatSessionId.\n\n"
    "8. Test posture: are the 9 new test suites correctly placed\n"
    "   (Layer-2 for the TS surfaces; pytest for the CLI)? Any\n"
    "   load-bearing branch not covered (especially the tolerant-on-\n"
    "   read collapse to engine+provider routing in\n"
    "   isChatSessionMismatch)?\n\n"
    "9. Q3 audit-locked toast contract — are the existing\n"
    "   CheckoutPollService toasts ('Check-out on \"X\" was claimed\n"
    "   for Y after polling.', 'Forced check-out on \"X\" for Y.',\n"
    "   timeout notice) preserved AS secondary surfaces? The modal\n"
    "   is the new primary; toasts must not be elevated to primary\n"
    "   resolution path.\n\n"
    "10. Are any forwards-incompatible changes missing? For instance,\n"
    "    a future consumer on a pre-Set-036 ai_router (without the\n"
    "    chatSessionId composite) producing a conflict record:\n"
    "    the new Claude invoker keeps emitting the new fields; the\n"
    "    parser tolerates pre-Set-036 records missing them. Is the\n"
    "    matrix complete?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references — sessions 5-7 will reference this verdict."
)


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 4 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="036-chatsessionid-and-watcher-scope-implementation",
        session_number=4,
    )
    dump_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "036-chatsessionid-and-watcher-scope-implementation"
        / "verification-output"
        / f"round-{label.lower()}-session-4-result.json"
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
    parser.add_argument("--round", choices=["A", "B", "C"], default="A")
    args = parser.parse_args()

    ext_dir = REPO_ROOT / "tools" / "dabbler-ai-orchestration"

    modal_text = (
        ext_dir / "src" / "providers" / "chatSessionMismatchModal.ts"
    ).read_text("utf-8")
    intent_text = (
        ext_dir / "src" / "providers" / "ReadOnlyIntentService.ts"
    ).read_text("utf-8")
    poll_service_text = (
        ext_dir / "src" / "providers" / "CheckoutPollService.ts"
    ).read_text("utf-8")
    checkout_cmd_text = (
        ext_dir / "src" / "commands" / "checkOutOrchestrator.ts"
    ).read_text("utf-8")
    invoker_text = (
        ext_dir / "scripts" / "claude-session-start-invoker.js"
    ).read_text("utf-8")
    start_session_text = (
        REPO_ROOT / "ai_router" / "start_session.py"
    ).read_text("utf-8")
    watcher_test_text = (
        ext_dir / "src" / "test" / "suite" / "watcherInventory.test.ts"
    ).read_text("utf-8")
    modal_test_text = (
        ext_dir / "src" / "test" / "suite" / "chatSessionMismatchModal.test.ts"
    ).read_text("utf-8")
    intent_test_text = (
        ext_dir / "src" / "test" / "suite" / "readOnlyIntentService.test.ts"
    ).read_text("utf-8")
    poll_test_text = (
        ext_dir / "src" / "test" / "suite" / "checkoutPollService.test.ts"
    ).read_text("utf-8")
    cli_test_text = (
        REPO_ROOT / "ai_router" / "tests" / "test_start_session_takeover_prompt.py"
    ).read_text("utf-8")

    rounds = {
        "A": (
            "Round A: full post-implementation source bundle",
            (
                f"=== NEW src/providers/chatSessionMismatchModal.ts ===\n"
                f"{modal_text}\n\n"
                f"=== NEW src/providers/ReadOnlyIntentService.ts ===\n"
                f"{intent_text}\n\n"
                f"=== src/providers/CheckoutPollService.ts (full file — chatSessionId fields + isChatSessionMismatch + handleChatSessionMismatch wiring + spawnRetry forwarding) ===\n"
                f"{poll_service_text}\n\n"
                f"=== src/commands/checkOutOrchestrator.ts (full file — maybeClearReadOnlyIntent gate added) ===\n"
                f"{checkout_cmd_text}\n\n"
                f"=== scripts/claude-session-start-invoker.js (full file — emitConflictRecord chatSessionId fields) ===\n"
                f"{invoker_text}\n\n"
                f"=== ai_router/start_session.py (full file — _is_interactive_tty + _prompt_takeover_choice + EXIT_READ_ONLY wiring in H3 branch) ===\n"
                f"{start_session_text}\n\n"
                f"=== NEW src/test/suite/watcherInventory.test.ts (Q7 allowlisted convention test) ===\n"
                f"{watcher_test_text}\n\n"
                f"=== NEW src/test/suite/chatSessionMismatchModal.test.ts ===\n"
                f"{modal_test_text}\n\n"
                f"=== NEW src/test/suite/readOnlyIntentService.test.ts ===\n"
                f"{intent_test_text}\n\n"
                f"=== src/test/suite/checkoutPollService.test.ts (full file — chatSessionId fixtures + isChatSessionMismatch suite + modal-routing suite) ===\n"
                f"{poll_test_text}\n\n"
                f"=== NEW ai_router/tests/test_start_session_takeover_prompt.py ===\n"
                f"{cli_test_text}\n"
            ),
            VERIFICATION_ASKS,
        ),
        "B": (
            "Round B: re-verify after Round A must-fix changes",
            (
                f"=== src/providers/CheckoutPollService.ts (post-Round-A — pollKey + isSlotFreeForHolder now include chatSessionId) ===\n"
                f"{poll_service_text}\n\n"
                f"=== src/commands/checkOutOrchestrator.ts (post-Round-A — confirm/commit split for read-only intent timing) ===\n"
                f"{checkout_cmd_text}\n\n"
                f"=== src/test/suite/checkoutPollService.test.ts (post-Round-A — added pollKey + isSlotFreeForHolder chatSessionId branches) ===\n"
                f"{poll_test_text}\n\n"
                f"=== NEW src/test/suite/readOnlyIntentTiming.test.ts (Round A Minor regression test) ===\n"
                + (REPO_ROOT / 'tools' / 'dabbler-ai-orchestration' / 'src' / 'test' / 'suite' / 'readOnlyIntentTiming.test.ts').read_text('utf-8')
            ),
            (
                "Round B: confirm the three Round A findings are addressed.\n"
                "Specifically:\n\n"
                "1. Round A Major 1 (pollKey chatSessionId): the would-be\n"
                "   holder's chatSessionId is now included in pollKey() via\n"
                "   a `<no-chat-id>` sentinel for null. Two chats on the\n"
                "   same engine+provider with distinct chatSessionIds now\n"
                "   produce distinct keys (no in-flight de-dup leak).\n"
                "   Two pre-Set-036 records (both null) still collapse,\n"
                "   preserving the Set-033 dedup contract. New tests pin\n"
                "   both branches.\n\n"
                "2. Round A Major 2 (isSlotFreeForHolder chatSessionId):\n"
                "   the predicate now takes an optional\n"
                "   wouldBeChatSessionId and applies the tolerant-on-read\n"
                "   rule from start_session.py's H3 predicate. When the\n"
                "   parameter is omitted (back-compat for legacy callers),\n"
                "   the behavior is unchanged. beginPolling() now forwards\n"
                "   record.wouldBeHolderChatSessionId so a third chat\n"
                "   joining mid-poll no longer misclassifies as 'free for\n"
                "   holder'.\n\n"
                "3. Round A Minor (read-only intent timing):\n"
                "   maybeClearReadOnlyIntent was split into\n"
                "   confirmRevertReadOnlyIntent (returns the operator\n"
                "   decision, does NOT mutate state) and\n"
                "   commitClearReadOnlyIntent (clears the intent).\n"
                "   executeCheckOut now invokes the commit only AFTER\n"
                "   dispatchCheckOut returns 0 (post-pushMru). An\n"
                "   operator who picks 'Clear & Check Out' but then\n"
                "   cancels the force-override modal (or sees the\n"
                "   subprocess fail) retains the read-only protection.\n\n"
                "Confirm each fix lands cleanly. Surface any net-new\n"
                "issues only — do NOT re-litigate the Round A findings\n"
                "themselves."
            ),
        ),
    }

    if args.round == "C":
        chat_mismatch_test = (
            ext_dir / "src" / "test" / "suite" / "checkOutOrchestratorChatSessionMismatch.test.ts"
        ).read_text("utf-8")
        label = "Round C: re-verify after Round B Major fix (manual-checkout chatSessionId routing)"
        bundle = (
            f"=== src/commands/checkOutOrchestrator.ts (post-Round-B — InProgressSet.state.orchestrator.chatSessionId added; maybeShowChatSessionMismatchOnManualCheckout helper; executeCheckOut routes chat-id mismatch BEFORE engine+provider prompt) ===\n"
            f"{checkout_cmd_text}\n\n"
            f"=== NEW src/test/suite/checkOutOrchestratorChatSessionMismatch.test.ts (Round B Major regression — 9 tests) ===\n"
            f"{chat_mismatch_test}\n\n"
            f"=== src/providers/chatSessionMismatchModal.ts (unchanged since Round A — included for context) ===\n"
            f"{modal_text}\n"
        )
        asks = (
            "Round C: confirm the Round B Major fix is implemented "
            "correctly. Specifically:\n\n"
            "1. maybeShowChatSessionMismatchOnManualCheckout: does it\n"
            "   correctly detect ONLY the same-engine/provider/prior-\n"
            "   string-chatSessionId case? null/key-absent priors must\n"
            "   collapse to no-mismatch (tolerant-on-read alignment\n"
            "   with start_session.py's H3 predicate and\n"
            "   CheckoutPollService.isChatSessionMismatch).\n\n"
            "2. executeCheckOut ordering: the chat-id mismatch check\n"
            "   fires BEFORE maybeConfirmForceOverride. The two are\n"
            "   mutually exclusive (chat-id mismatch requires engine+\n"
            "   provider match; maybeConfirmForceOverride only prompts\n"
            "   on engine+provider mismatch); if the chat-id path\n"
            "   ran AFTER, the engine+provider helper would short-\n"
            "   circuit to {proceed: true, force: false} and dispatch\n"
            "   would hit EXIT_CHECKOUT_CONFLICT with no UX.\n\n"
            "3. Take-over → force=true → dispatchCheckOut succeeds →\n"
            "   commitClearReadOnlyIntent fires (the Round A Minor fix\n"
            "   ordering is preserved). Read-only → setReadOnly on the\n"
            "   intent service → executeCheckOut returns BEFORE\n"
            "   dispatch (no spawn). Cancel → abort, no intent\n"
            "   mutation.\n\n"
            "4. ChatSessionId is now on the InProgressSet schema. The\n"
            "   reader (listInProgressSetsAt) passes state.orchestrator\n"
            "   through unchanged, so the chatSessionId field flows\n"
            "   naturally without a new transform.\n\n"
            "5. The forceNote in the success toast now uses the\n"
            "   `force` local (was decision.force pre-fix) — wire\n"
            "   correctness check.\n\n"
            "6. Toast contract: the new read-only path silently sets\n"
            "   the intent and returns. Should it surface a\n"
            "   confirmation toast like the CheckoutPollService path\n"
            "   does? The Q3 audit-locked verdict says toasts are\n"
            "   secondary-only; this is a borderline case where an\n"
            "   info toast might prevent operator confusion about\n"
            "   'why did nothing happen?'. Flag as Minor if you\n"
            "   think so.\n\n"
            "7. Any net-new gaps surfaced. Do NOT re-litigate the\n"
            "   Round A / Round B findings — those are pinned by\n"
            "   regression tests. Focus on whether the new code\n"
            "   path is correct + complete."
        )
        print(f"Running {label} ...")
        _run_round("C", bundle, asks)
        return 0

    label, bundle, asks = rounds[args.round]
    print(f"Running {label} ...")
    _run_round(args.round, bundle, asks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
