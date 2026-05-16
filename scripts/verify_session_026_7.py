"""Session 7 (final) verification — wizard integration + test notification.

Single slice covering all Session 7 production-code changes:
  - wizard.html + WizardPanel.ts: openConfigEditor button wiring
  - notificationsSection.ts: button enabled
  - ConfigEditorPanel.ts: _handleTestNotification() implementation

CRITICAL: dumps RouteResult to JSON BEFORE any attribute access — per
the memory `feedback_ai_router_route_result_handling`.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_ai_router():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import ai_router
    return ai_router


SESSION_7_FILES = [
    "tools/dabbler-ai-orchestration/webview/wizard.html",
    "tools/dabbler-ai-orchestration/src/wizard/WizardPanel.ts",
    "tools/dabbler-ai-orchestration/src/configEditor/sections/notificationsSection.ts",
    "tools/dabbler-ai-orchestration/src/configEditor/ConfigEditorPanel.ts",
]


def main() -> int:
    parts = []
    for rel in SESSION_7_FILES:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        parts.append(f"=== {rel} ===\n{body}\n")
    bundle = "".join(parts)

    context = (
        "Set 026 Session 7 of 7 — wizard integration + test notification (final session).\n"
        "Reference: `docs/session-sets/026-router-config-editor-implementation/spec.md`\n"
        "Session 7 section.\n\n"
        "This slice covers the final integration and test-notification deliverables:\n"
        "  - wizard.html: added 'Configure AI Router' button → sends openConfigEditor message.\n"
        "  - WizardPanel.ts: new `case 'openConfigEditor'` in the message handler\n"
        "    → executes `dabbler.openConfigEditor`.\n"
        "  - notificationsSection.ts: removed `disabled` attribute and the\n"
        "    '(wired in Session 7)' placeholder from the test-notification button;\n"
        "    updated docblock.\n"
        "  - ConfigEditorPanel.ts:\n"
        "    - Added `import * as cp from 'child_process'`.\n"
        "    - Added `case 'sendTestNotification'` in onDidReceiveMessage switch.\n"
        "    - New `_handleTestNotification()` private method:\n"
        "      1. Checks for ai_router/ directory (returns early if missing).\n"
        "      2. Reads configured Pushover env-var names from local-overrides.yaml\n"
        "         (defaulting to PUSHOVER_API_KEY / PUSHOVER_USER_KEY if not configured).\n"
        "      3. Resolves env var values from process.env using the configured names.\n"
        "      4. Returns early with showErrorMessage if either key is absent.\n"
        "      5. Resolves pythonPath from dabblerSessionSets.pythonPath config (same\n"
        "         pattern as installAiRouterCommands.ts).\n"
        "      6. Spawns a Python subprocess with an inline `-c` script that calls\n"
        "         `send_pushover_notification('Dabbler test', '...')` from\n"
        "         `ai_router.notifications`, outputs JSON {ok, request_id} or\n"
        "         {ok:false, error}.\n"
        "      7. Passes PUSHOVER_API_KEY and PUSHOVER_USER_KEY in the subprocess env\n"
        "         (mapped from the configured names so ai_router/notifications.py's\n"
        "         hardcoded key names still work).\n"
        "      8. On child.on('close'), parses stdout JSON and surfaces result.\n"
        "    - Added §5 test-notification button click handler in _getHtml() script.\n\n"
        "Tests: tsc clean; pytest 427 passed, 1 skipped (no new unit tests for this\n"
        "session — wizard wiring and spawn-based button don't lend themselves to\n"
        "unit tests without @vscode/test-electron; correctness relies on code review).\n\n"
        "Verification asks:\n"
        "1. Wizard wiring: does the new 'openConfigEditor' message case correctly\n"
        "   execute `dabbler.openConfigEditor`? Any risk that the case falls through\n"
        "   to an unintended branch?\n"
        "2. _handleTestNotification — env-var resolution:\n"
        "   a. When local-overrides doesn't exist or has no notifications.pushover\n"
        "      block, does it default to the string 'PUSHOVER_API_KEY'?\n"
        "   b. Does the (typeof ... === 'string' ? ... : 'PUSHOVER_API_KEY') || 'PUSHOVER_API_KEY'\n"
        "      chain correctly handle null/undefined/empty-string values?\n"
        "   c. Is `process.env[apiKeyEnv]` safe if apiKeyEnv is an attacker-controlled\n"
        "      string (since it comes from a user-editable YAML)? Is there any injection\n"
        "      risk in the Python subprocess call?\n"
        "3. _handleTestNotification — Python subprocess:\n"
        "   a. The `-c` script is a multi-line string joined with '\\n'. Does this\n"
        "      work correctly on Windows (where line endings or quoting might differ)?\n"
        "   b. The script catches all exceptions and prints JSON — does it handle\n"
        "      `import errors` (e.g., ai_router not installed) correctly?\n"
        "   c. `child.on('close')` fires after stdout/stderr streams have ended. Is\n"
        "      there any race where stdout might not have flushed yet when 'close' fires?\n"
        "   d. If Python produces non-JSON stdout (e.g., deprecation warning before\n"
        "      the JSON line), does the `JSON.parse(stdout.trim())` fail cleanly?\n"
        "4. pythonPath resolution: the method reads inspect()?.workspaceFolderValue ??\n"
        "   workspaceValue ?? globalValue — same pattern as installAiRouterCommands.ts\n"
        "   `explicitConfigValue()`. Is this correct? Is there a case where the\n"
        "   resolution gives the wrong path?\n"
        "5. Button handler in _getHtml(): the id `s5-test-notification` must match the\n"
        "   HTML rendered by notificationsSection.ts. Does it?\n"
        "6. Any security or correctness issues not covered above?\n\n"
        "If you find no substantive issues, say VERIFIED. Otherwise list each\n"
        "finding with severity (Blocker / Major / Minor) and file:line references."
    )

    content = (
        "Review the Session 7 final-session bundle below against the criteria above.\n"
        "Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )

    ar = load_ai_router()
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="026-router-config-editor-implementation",
        session_number=7,
    )

    dump_path = REPO_ROOT / "scripts" / "verify_session_026_7_result.json"
    try:
        as_dict = dataclasses.asdict(result)
    except TypeError:
        as_dict = {k: v for k, v in vars(result).items()}
    cleaned = {}
    for k, v in as_dict.items():
        try:
            json.dumps(v)
            cleaned[k] = v
        except TypeError:
            cleaned[k] = repr(v)
    dump_path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"Dumped result to {dump_path.as_posix()}")

    data = json.loads(dump_path.read_text(encoding="utf-8"))
    print("=== VERIFIER RESPONSE ===")
    print(data.get("content", "<no content>"))
    print()
    print("=== COST ===")
    print(
        f"model={data.get('model_name')} "
        f"input_tokens={data.get('input_tokens')} "
        f"output_tokens={data.get('output_tokens')} "
        f"cost_usd={data.get('total_cost_usd')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
