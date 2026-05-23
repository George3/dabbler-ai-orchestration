"""Cross-provider verification for Set 036 Session 2.

Verifies the ``new_chat_id`` CLI + Claude Code SessionStart hook
invoker pass-through + installer-shim copy updates shipped in
Session 2. The work touches:

  * `ai_router/new_chat_id.py` (new) — the agent-facing token-source
    CLI for orchestrators with no native per-chat ID surface.
  * `ai_router/tests/test_new_chat_id.py` (new) — 22 unit tests.
  * `tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`
    — extended to parse `session_id` off the SessionStart payload and
    forward as `--chat-session-id <value>` to start_session.
  * `tools/dabbler-ai-orchestration/src/commands/newChatIdWorkflowToast.ts`
    (new) — shared one-time toast for the manual-only orchestrators.
  * `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts`
    + `installOrchestratorHookCopilot.ts` — invoke the toast before
    opening the check-out quickpick; documentation copy mentions the
    `python -m ai_router.new_chat_id` workflow.
  * `tools/dabbler-ai-orchestration/src/test/suite/claudeSessionStartInvoker.test.ts`
    (new) — 13 Layer-2 tests for the invoker's `session_id`
    extraction + `parsePayload` helper.

Total scope ~1200 LOC — split into two sub-rounds per
[[feedback_split_large_verification_bundles]] (>700 LOC bundles risk
gpt-5-4 timeout/429):

  * Round A (~580 LOC): Python CLI (new_chat_id.py + test).
  * Round B (~470 LOC): JS invoker + TS installer shims + toast
    helper + Layer-2 test. Opt-in unless Round A surfaces must-fix.

Usage:
    python scripts/verify_session_036_2.py [--round A|B]
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
    "Set 036 Session 2 of 7 — `new_chat_id` CLI + Claude Code\n"
    "hook-invoker pass-through. Reference:\n"
    "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/\n"
    "spec.md (Session 2 section).\n\n"
    "Prerequisite: Session 1 (CLOSED 2026-05-23, commit 2188744) shipped\n"
    "the chatSessionId writer migration + per-set lifecycle lock. The\n"
    "writer accepts `--chat-session-id <value>` and falls back to the\n"
    "$CHAT_SESSION_ID env var when omitted (precedence: explicit arg →\n"
    "env var → None). The H4 composite identity is now\n"
    "`engine + provider + chatSessionId`.\n\n"
    "Audit-locked verdict (proposal-addendum §Q1): there is NO env var\n"
    "that any first-class orchestrator (Claude Code, Codex CLI, Gemini\n"
    "Code Assist, GitHub Copilot) populates with a stable per-chat ID.\n"
    "Claude Code carries the identity in its SessionStart hook payload's\n"
    "`session_id` field. The other three orchestrators have no native\n"
    "surface — operators run the `new_chat_id` CLI to mint a UUID and\n"
    "export it as CHAT_SESSION_ID before invoking start_session.\n\n"
    "Goal of Session 2: ship that token-source plumbing. Claude Code's\n"
    "invoker shim forwards the SessionStart payload's `session_id`; the\n"
    "Python CLI provides the fallback for everyone else. Installer-shim\n"
    "updates for the manual-only orchestrators surface the workflow via\n"
    "a one-time toast + clipboard-copy of the canonical export command.\n\n"
    "Test results on this host:\n"
    "  * ai_router/tests/test_new_chat_id.py — 22 passed\n"
    "  * full ai_router pytest — 682 passed + 1 skipped\n"
    "  * extension Layer-2 (invoker test) — 13 passed\n"
    "  * extension Layer-2 (full suite) — 475 passed, 2 pre-existing\n"
    "    failures unrelated to Session 2 (configEditor-foundation +\n"
    "    notificationsSection scaffolding gaps).\n"
    "  * tsc --noEmit on extension — clean.\n\n"
    "Out of scope for Session 2 (deferred to later sessions per the\n"
    "7-session split):\n"
    "  * signalKind retirement + Codex config-toml watcher retirement\n"
    "    (Session 3).\n"
    "  * Takeover UX modal/CLI prompt + watcher-inventory test\n"
    "    (Session 4).\n"
    "  * Layer-3 Playwright coverage + cross-tier docs + cross-repo\n"
    "    notice (Session 5).\n"
    "  * Orchestrator-agnostic UI audit + empty-state refactor\n"
    "    (Session 6).\n"
    "  * Final test sweep + change-log + dual-registry release\n"
    "    (Session 7).\n\n"
    "Risk to call out (R2 in the spec): Claude Code hook payload schema\n"
    "drift. The audit identified `session_id` as the field name; if a\n"
    "future Claude Code update renames it, our extraction returns null\n"
    "and start_session falls through to the tolerant legacy branch.\n"
    "The invoker logs to stderr in that case (existing behavior).\n\n"
    "Risk R3: `new_chat_id` shell-flavor coverage. Initial scope is\n"
    "bash + PowerShell + fish. Operators on nu / tcsh / other shells\n"
    "fall back to manual `export CHAT_SESSION_ID=<uuid>`."
)


VERIFICATION_ASKS_A = (
    "Verification asks for Round A (Python CLI + test):\n\n"
    "1. ai_router/new_chat_id.py — module shape:\n"
    "   (a) `_resolve_chat_session_id` returns an existing non-empty\n"
    "       $CHAT_SESSION_ID value verbatim; mints a fresh\n"
    "       `uuid.uuid4()` when unset or set-to-empty. Mirrors\n"
    "       start_session.py's `_resolve_chat_session_id` empty-\n"
    "       collapse semantic (empty → None / mint). Is the symmetry\n"
    "       correct, or should the two helpers be merged into a single\n"
    "       canonical location to prevent future drift?\n"
    "   (b) `_detect_shell` returns one of {bash, powershell, fish} or\n"
    "       None. Windows short-circuits to powershell regardless of\n"
    "       $SHELL (the docstring justifies this: $SHELL on Windows is\n"
    "       either unset or a stale Git-Bash hand-off). Unix parses\n"
    "       the basename of $SHELL: bash/sh/zsh → bash; fish → fish;\n"
    "       pwsh/powershell → powershell; anything else → None. Is the\n"
    "       Windows short-circuit too aggressive — e.g., should a\n"
    "       Windows user with $SHELL=/usr/bin/bash (Git-Bash, WSL) get\n"
    "       bash routing? The current behavior privileges PowerShell\n"
    "       even when bash is explicitly named on Windows.\n"
    "   (c) `_format_bash` / `_format_powershell` / `_format_fish` —\n"
    "       single-quote the value; defensive single-quote escape for\n"
    "       embedded `'` characters (UUID v4 never contains one, but\n"
    "       the formatter is hardened against future callers passing\n"
    "       arbitrary strings). Are the per-shell escape rules\n"
    "       correct? PowerShell doubles `'` for literal interpretation;\n"
    "       bash uses `'\\''` to break-quote-quote-resume; fish\n"
    "       backslash-escapes. Any edge cases missed?\n"
    "   (d) Argparse exposes `--export` (flag) and `--shell` (choice).\n"
    "       Plain mode prints the UUID + newline only; export mode\n"
    "       prints the formatter line. Plain mode does NOT consult\n"
    "       `--shell` — is that the right contract, or should `--shell`\n"
    "       in plain mode error out as a usage mistake?\n"
    "   (e) Exit codes: 0 success, 1 shell-detect-failed, 2 argparse.\n"
    "       The shell-detect-failed branch's stderr message names\n"
    "       every entry of SUPPORTED_SHELLS so a future expansion\n"
    "       (e.g., adding nu) automatically updates the error text.\n"
    "       Defensive 'unsupported shell' branch is unreachable\n"
    "       through argparse but defended for programmatic callers.\n"
    "       Is that defense useful, or dead weight?\n\n"
    "2. ai_router/tests/test_new_chat_id.py — 22 tests:\n"
    "   (a) Plain-mode UUID v4 emission (regex + uuid.UUID round-trip).\n"
    "   (b) Distinct UUIDs across consecutive calls.\n"
    "   (c) Per-shell export shape: bash / powershell / fish.\n"
    "   (d) Auto-detect: Windows → powershell; bash / zsh / fish /\n"
    "       pwsh basenames → respective shells.\n"
    "   (e) Idempotency: existing $CHAT_SESSION_ID short-circuits the\n"
    "       mint in both plain and export modes.\n"
    "   (f) Empty $CHAT_SESSION_ID does NOT short-circuit (matches\n"
    "       writer-side semantics).\n"
    "   (g) Failure mode: --export without --shell on undetectable\n"
    "       shell → exit 1 with stderr mentioning --shell and every\n"
    "       SUPPORTED_SHELLS entry.\n"
    "   (h) Failure mode: --export with unrecognized $SHELL basename.\n"
    "   (i) Helper-level single-quote escape coverage.\n"
    "   (j) `_resolve_chat_session_id` direct invocation.\n"
    "\n"
    "   Autouse fixture `_isolate_env` strips $CHAT_SESSION_ID +\n"
    "   $SHELL before every test so leakage from the invoking shell\n"
    "   doesn't poison the test process.\n"
    "\n"
    "   Questions:\n"
    "   - Is there a branch missing? Specifically: an explicit\n"
    "     `--shell` value paired with an existing $CHAT_SESSION_ID\n"
    "     (export mode echoes the existing value, not a fresh UUID).\n"
    "     The current `test_export_mode_echoes_existing_chat_session_id`\n"
    "     covers this for bash; should fish + powershell variants also\n"
    "     be exercised, or is one shell sufficient?\n"
    "   - The defensive 'unsupported shell' branch in `run()` (when\n"
    "     `_EXPORT_FORMATTERS.get(shell)` returns None despite shell\n"
    "     being in SUPPORTED_SHELLS) is unreachable through argparse.\n"
    "     No test covers it. Is leaving it untested OK (dead code by\n"
    "     construction), or should a test directly drive `run()` with\n"
    "     a forged namespace to lock the defense?\n"
    "   - PID 999999 fixture pattern is not relevant here (no lock\n"
    "     contention), but the empty-string env-value test uses\n"
    "     monkeypatch.setenv with `''` — is that portable across\n"
    "     pytest versions? The pattern is consistent with Session 1's\n"
    "     test_explicit_empty_string_clears_env.\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references. Be concrete about the line numbers — the\n"
    "downstream Sessions 3–7 will reference this verdict."
)


VERIFICATION_ASKS_B = (
    "Verification asks for Round B (Round A fix confirmation + JS invoker + TS shims + Layer-2 test):\n\n"
    "0. ROUND A FIX VERIFICATION (light-touch — fixes are mechanical;\n"
    "   primary signal is the green test suite):\n"
    "   (a) MAJOR fix: `_detect_shell()` now checks `$SHELL` first on\n"
    "       every platform; Windows falls back to `powershell` only\n"
    "       when `$SHELL` is unset or has an unrecognized basename.\n"
    "       Three new tests in test_new_chat_id.py exercise:\n"
    "       Windows+SHELL=bash → bash; Windows+SHELL=fish → fish;\n"
    "       Windows+SHELL=nu → fallback powershell. The pre-existing\n"
    "       `test_export_auto_detect_picks_powershell_on_windows`\n"
    "       still passes (autouse fixture clears SHELL, so the\n"
    "       Windows fallback fires). All 26 tests pass on this host.\n"
    "   (b) MINOR fix: added `test_format_fish_escapes_embedded_\n"
    "       single_quote` covering the fish formatter's defensive\n"
    "       escape path.\n"
    "   The Round A bundle of these helpers is below the JS/TS\n"
    "   surface — assume the Python fixes hold based on the test\n"
    "   suite. Focus primary attention on the new surfaces below.\n\n"
    "1. tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js\n"
    "1. tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js\n"
    "   (a) New `extractSessionId(payload)` helper: returns the trimmed\n"
    "       string when payload.session_id is a non-empty string after\n"
    "       trimming; null otherwise. Covers missing, empty, whitespace-\n"
    "       only, non-string (number/object/null/undefined), and\n"
    "       non-object-payload inputs. Is the trim() correct, or could\n"
    "       Claude Code ever ship a session_id with deliberate leading/\n"
    "       trailing whitespace that we'd corrupt? (Assumption: UUIDs\n"
    "       don't have whitespace; defensive trim guards against payload\n"
    "       quirks.)\n"
    "   (b) `spawnStartSession(setDir, model, effort, chatSessionId)` —\n"
    "       new fourth arg; when non-null + non-empty, pushed onto args\n"
    "       as `--chat-session-id <value>`. Omitted entirely when null,\n"
    "       so start_session.py's `_resolve_chat_session_id` falls back\n"
    "       to $CHAT_SESSION_ID env or None. Is the omission the right\n"
    "       fallback, or should the invoker explicitly pass empty\n"
    "       string to force the strict-on-write 'None' path? (Argument\n"
    "       for omission: Session 1's CLI semantics treat empty-string\n"
    "       as 'deliberately clear, no env fallback' which is wrong\n"
    "       behavior for a hook that has no signal — better to omit.)\n"
    "   (c) `main()` calls `extractSessionId(payload)` once and threads\n"
    "       through. The bottom-of-file `require.main === module` guard\n"
    "       conditionally runs main() vs. exports {extractSessionId,\n"
    "       parsePayload} so the Layer-2 test can require() the module\n"
    "       without firing the hook side effects. Is the guard idiom\n"
    "       correct? Could `require.main` be undefined in some Node\n"
    "       ESM invocations?\n\n"
    "2. tools/dabbler-ai-orchestration/src/commands/newChatIdWorkflowToast.ts\n"
    "   (new) — shared 'READMEish snippet' surface invoked from the\n"
    "   Gemini / Copilot installer shims. One-time per (workspace,\n"
    "   orchestrator) via workspaceState; 'Copy bash command' /\n"
    "   'Copy PowerShell command' / 'Don't show again' actions.\n"
    "   Questions:\n"
    "   - The copy command is hard-coded:\n"
    "     `python -m ai_router.new_chat_id --export --shell bash | eval \"$(cat)\"`\n"
    "     Does the eval idiom actually work? `eval $(cmd)` is the\n"
    "     classic form; piping into `eval \"$(cat)\"` reads stdin into\n"
    "     eval as a string. Both should work but the former is more\n"
    "     idiomatic. Is the pipe form deliberate (so output stays in\n"
    "     one line) or a mistake?\n"
    "   - PowerShell command uses `Invoke-Expression` — also classic;\n"
    "     PSScriptAnalyzer flags it as a security risk in general but\n"
    "     it's the canonical way to run a generated export line.\n"
    "   - One-time-per-workspace via workspaceState — operator who\n"
    "     wants to see the toast again has to clear extension storage.\n"
    "     Is that acceptable, or should there be a 'Reset toast'\n"
    "     command? (Light-touch: probably leave it; if real friction\n"
    "     surfaces later, ship the reset.)\n\n"
    "3. installOrchestratorHookGemini.ts / installOrchestratorHookCopilot.ts\n"
    "   — both shims now invoke `maybeShowNewChatIdWorkflowToast` before\n"
    "   the existing `dabbler.checkOutOrchestrator` quickpick. The\n"
    "   `await` chains the toast before the quickpick so the operator\n"
    "   sees the workflow context first. Is the ordering right, or\n"
    "   should the quickpick open immediately and the toast surface\n"
    "   in parallel? (Argument for sequential: the toast is a learning\n"
    "   moment; making it block the quickpick ensures the operator\n"
    "   reads it.)\n\n"
    "4. tools/dabbler-ai-orchestration/src/test/suite/claudeSessionStartInvoker.test.ts\n"
    "   — 13 Layer-2 tests. Two suites (extractSessionId, parsePayload);\n"
    "   each loads the invoker module dynamically via\n"
    "   `await import(pathToFileURL(invokerPath).href)` in suiteSetup so\n"
    "   the file: URL works on Windows where bare paths confuse the\n"
    "   ESM loader. The shim's `module.exports = { ... }` surfaces as\n"
    "   the `default` export under CommonJS-interop; the fallback\n"
    "   `mod.default ?? mod` handles both shapes.\n"
    "   Questions:\n"
    "   - The dynamic-import workaround was necessary because Node's\n"
    "     ESM detector flips this `.ts` file to ESM scope at load\n"
    "     time (other test files trip the same warning). Is there a\n"
    "     cleaner pattern — e.g., a project-wide tsconfig adjustment\n"
    "     or a `.cjs` test file — that would avoid the trick?\n"
    "   - Trim-then-non-empty coverage: 'returns null when the field\n"
    "     is whitespace only' uses both `   ` and `\\t\\n`. Should\n"
    "     trailing-only / leading-only whitespace also have explicit\n"
    "     coverage, or is the 'trims surrounding whitespace before\n"
    "     returning' test sufficient to lock the contract?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity and file:line references."
)


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 2 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="036-chatsessionid-and-watcher-scope-implementation",
        session_number=2,
    )
    dump_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "036-chatsessionid-and-watcher-scope-implementation"
        / "verification-output"
        / f"round-{label.lower()}-session-2-result.json"
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

    ar_dir = REPO_ROOT / "ai_router"
    ext_dir = REPO_ROOT / "tools" / "dabbler-ai-orchestration"

    new_chat_id_text = (ar_dir / "new_chat_id.py").read_text("utf-8")
    test_new_chat_id_text = (
        ar_dir / "tests" / "test_new_chat_id.py"
    ).read_text("utf-8")

    invoker_text = (
        ext_dir / "scripts" / "claude-session-start-invoker.js"
    ).read_text("utf-8")
    toast_text = (
        ext_dir / "src" / "commands" / "newChatIdWorkflowToast.ts"
    ).read_text("utf-8")
    gemini_text = (
        ext_dir / "src" / "commands" / "installOrchestratorHookGemini.ts"
    ).read_text("utf-8")
    copilot_text = (
        ext_dir / "src" / "commands" / "installOrchestratorHookCopilot.ts"
    ).read_text("utf-8")
    invoker_test_text = (
        ext_dir / "src" / "test" / "suite" / "claudeSessionStartInvoker.test.ts"
    ).read_text("utf-8")

    rounds = {
        "A": (
            "Round A: Python CLI + unit tests",
            (
                f"=== ai_router/new_chat_id.py (full file — new) ===\n"
                f"{new_chat_id_text}\n\n"
                f"=== ai_router/tests/test_new_chat_id.py (full file — new) ===\n"
                f"{test_new_chat_id_text}\n"
            ),
            VERIFICATION_ASKS_A,
        ),
        "B": (
            "Round B: JS invoker + TS install shims + Layer-2 test",
            (
                f"=== scripts/claude-session-start-invoker.js (full file) ===\n"
                f"{invoker_text}\n\n"
                f"=== src/commands/newChatIdWorkflowToast.ts (full file — new) ===\n"
                f"{toast_text}\n\n"
                f"=== src/commands/installOrchestratorHookGemini.ts (full file) ===\n"
                f"{gemini_text}\n\n"
                f"=== src/commands/installOrchestratorHookCopilot.ts (full file) ===\n"
                f"{copilot_text}\n\n"
                f"=== src/test/suite/claudeSessionStartInvoker.test.ts (full file — new) ===\n"
                f"{invoker_test_text}\n"
            ),
            VERIFICATION_ASKS_B,
        ),
    }

    label, bundle, asks = rounds[args.round]
    print(f"Running {label} ...")
    _run_round(args.round, bundle, asks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
