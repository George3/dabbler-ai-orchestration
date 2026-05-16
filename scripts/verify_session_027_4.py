"""Cross-provider verification for Set 027 Session 4.

Verifies the Playwright Electron rendering smoke layer + close-out
artifacts (version bumps, CHANGELOG entries, change-log.md, CLAUDE.md
test-commands section).

Split into two sub-rounds:
  * Round A: electronLaunch.ts + playwright.config.ts + package.json
    snippet (the launch / helper code).
  * Round B: treeView.spec.ts + change-log.md + the CHANGELOG / CLAUDE
    additions (the test scenarios + docs).

Total bundle stays well under the 700-LOC ceiling where gpt-5-4 starts
to time out (per the split-large-bundles memory).

Usage:
    python scripts/verify_session_027_4.py [--round A|B]

Default: both rounds sequentially.
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


SESSION4_CONTEXT = (
    "Set 027 Session 4 of 4 — Playwright Electron rendering smoke layer\n"
    "+ close-out. Reference: docs/session-sets/027-orchestrator-e2e-harness/\n"
    "spec.md (Session 4 section).\n\n"
    "Goal: ship a Layer 3 rendering smoke that launches a real VS Code\n"
    "Electron instance via Playwright's `_electron.launch`, opens the\n"
    "Session Set Explorer activity-bar view, and asserts on the\n"
    "rendered text in the tree. Five scenarios — fresh set, mid-session\n"
    "in flight, all done, cancelled, force-closed. Text-only assertions\n"
    "(Option B in the spec); no screenshot baseline committed.\n\n"
    "Why not use @vscode/test-electron's runTests? Session 3 found\n"
    "test-electron's runner broken on Windows 11 + VS Code 1.120 (the\n"
    "spawned Electron process exits before the in-process test runner\n"
    "can attach). Playwright's _electron.launch connects via CDP\n"
    "instead, sidestepping that path. We launch the cached Code.exe\n"
    "binary directly from .vscode-test/.\n\n"
    "Run result on this host (Windows 11 + VS Code 1.120):\n"
    "  All 5 tests PASS in 1m24s (well under the 3-min spec budget).\n"
    "  Single selector bug surfaced and fixed during the run:\n"
    "  `.activitybar [aria-label*=\"Dabbler AI Orchestration\"]` matched\n"
    "  two elements (action-icon + hidden badge); narrowed to\n"
    "  `.action-label[aria-label*=...]` for unambiguous match.\n\n"
    "Architecture chosen:\n"
    "  * `playwright.config.ts` — testDir=./src/test/playwright, 90s\n"
    "    per-test timeout, workers=1 (serial Electron launches).\n"
    "  * `electronLaunch.ts` — fixture API (mirrors Session 3's\n"
    "    e2eHarness.ts plumbing) + launchVSCode/closeVSCode/\n"
    "    openSessionSetsView/triggerRefresh helpers. Each launch gets\n"
    "    a fresh tmp user-data-dir + extensions-dir. Binary discovery\n"
    "    order: VSCODE_BIN env > latest .vscode-test/vscode-*/Code.exe\n"
    "    > throw.\n"
    "  * `treeView.spec.ts` — five scenarios using `treeitemTexts()`\n"
    "    helper that reads aria-label from every `[role='treeitem']`\n"
    "    inside the tree locator. Assertions are regex substring\n"
    "    matches against the joined aria-label text.\n\n"
    "Close-out work in this session:\n"
    "  * Version bumps: ai_router 0.3.0 -> 0.3.1; extension 0.13.15\n"
    "    -> 0.13.16.\n"
    "  * CHANGELOG.md entries in both packages.\n"
    "  * CLAUDE.md updated with Layer 1/2/3 commands + layer-choice\n"
    "    guidance.\n"
    "  * change-log.md for the set summarizes all four sessions.\n\n"
    "Out of scope for Session 4:\n"
    "  * Fixing the two drift classes Session 3 discovered (both still\n"
    "    pinned with explanatory test comments; reader/writer changes\n"
    "    deserve a dedicated set).\n"
    "  * Fixing the test-electron Windows runner — pre-existing.\n"
    "  * Pushing release tags (operator-driven post-merge step)."
)

VERIFICATION_ASKS_A = (
    "Verification asks for Round A (launch / helper code):\n"
    "1. `electronLaunch.ts`:\n"
    "   (a) `findCodeBinary()` — selects 'latest' from sorted dir names\n"
    "       and reverses. Is 'vscode-win32-x64-archive-1.120.0' > '1.119.1'\n"
    "       under default string sort? (Major-version >= 10 would break\n"
    "       lexicographic ordering; not a concern at v1.x but worth\n"
    "       flagging.)\n"
    "   (b) `_filteredEnv()` strips ambient GIT_* / PYTHONPATH — same\n"
    "       hygiene rule applied to the Layer 2 harness in Session 3.\n"
    "       Could anything else leak that would break the harness\n"
    "       (e.g., AI_ROUTER_ALLOW_FORCE_CLOSE_OUT for force tests,\n"
    "       LANG affecting Python stdout encoding)?\n"
    "   (c) `launchVSCode()` — passes `--user-data-dir` + `--extensions-dir`\n"
    "       per launch. `--disable-workspace-trust` allows the workspace\n"
    "       to activate the extension without trust prompt. Are any\n"
    "       launch flags missing that would cause the activity-bar icon\n"
    "       to be hidden by default (e.g., first-run welcome page\n"
    "       intercepting the workbench)?\n"
    "   (d) `openSessionSetsView()` uses\n"
    "       `.activitybar .action-label[aria-label*=\"Dabbler AI Orchestration\"]`\n"
    "       — case-sensitive substring match. Are there VS Code versions\n"
    "       that render the title in title-case differently? Should the\n"
    "       `*=` be `*= i` case-insensitive?\n"
    "   (e) `triggerRefresh()` opens command palette via Ctrl+Shift+P.\n"
    "       Will this work on macOS where the shortcut is Cmd+Shift+P?\n"
    "       The harness is currently Windows-only; should the helper\n"
    "       branch on platform?\n"
    "   (f) `closeVSCode()` swallows `app.close()` errors. Could a\n"
    "       lingering Electron process from a prior test leak into the\n"
    "       next, holding user-data-dir locks?\n"
    "2. `playwright.config.ts`:\n"
    "   * 90s timeout, workers=1, fullyParallel=false. Reasonable given\n"
    "     each test launches Electron cold (~10–15s per launch as\n"
    "     measured on the run that all passed)?\n"
    "3. `package.json` `test:playwright` script: `npm run compile &&\n"
    "    npx tsc --outDir out && npx playwright test`. Does Playwright\n"
    "    transpile the spec files via its own ts loader, or does it\n"
    "    need the compiled .js? (The `--outDir out` step compiles\n"
    "    everything to JS, but Playwright then reads .ts from\n"
    "    src/test/playwright/ directly.)\n"
    "4. Any race condition between the workbench finishing activation\n"
    "    and `openSessionSetsView()` clicking the activity icon? The\n"
    "    extension activates on `workspaceContains:docs/session-sets`\n"
    "    — that activation runs async; could the click land before the\n"
    "    view container is registered?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references."
)

VERIFICATION_ASKS_B = (
    "Verification asks for Round B (test scenarios + docs):\n"
    "1. `treeView.spec.ts`:\n"
    "   (a) Each test uses `triggerRefresh()` AFTER `openSessionSetsView()`.\n"
    "       But the view itself doesn't bind a file watcher when activated\n"
    "       from a workspace with no `docs/session-sets/` content at\n"
    "       startup, OR the harness writes state files BEFORE launch.\n"
    "       Is the refresh actually needed in all 5 scenarios, or only\n"
    "       in scenarios where state mutates after launch (none of these\n"
    "       — all state is prepared before launch)?\n"
    "   (b) `treeitemTexts()` returns aria-label for every treeitem and\n"
    "       falls back to textContent if aria-label is absent. Joining\n"
    "       with '\\n' and substring-matching is robust but could a\n"
    "       collapsed group hide the set node and cause the assertion\n"
    "       to fail (e.g., 'Not Started (3)' is rendered but the 3 set\n"
    "       children are hidden behind the collapsed group)?\n"
    "   (c) Scenario 5 (force-closed) asserts `In Progress (1)` AND\n"
    "       NOT `Done (1)`. This pins the truthful-display invariant\n"
    "       from Session 3. Is the assertion specific enough — does it\n"
    "       catch a regression where `isMidSetComplete` is 'fixed' in\n"
    "       a way that wrongly routes force-closed mid-set to Done?\n"
    "   (d) Each test has a `try { ... } finally { teardown(per) }`\n"
    "       block — good. Could the `teardown()` itself fail (e.g.,\n"
    "       Electron process still running on tmpdir delete) and\n"
    "       cause the next test's launch to inherit polluted state?\n"
    "   (e) No assertion on `description` separately — bucket header\n"
    "       count, `[FORCED]`, `N/N`, `in flight` all live in the same\n"
    "       joined aria-label text. Are any of these substrings\n"
    "       accidentally matchable from group headers or the welcome\n"
    "       text content (e.g., a hypothetical `(0)` appearing in a\n"
    "       non-bucket location)?\n"
    "2. `change-log.md`:\n"
    "   * Sessions 1–4 summaries accurate to the spec? Does it omit\n"
    "     any deliverable required by the acceptance criteria?\n"
    "   * Costs table is partial for Session 4 (verification cost not\n"
    "     yet known at write time). Document expectation that it gets\n"
    "     a final-cost amendment after verification?\n"
    "3. `CLAUDE.md` test-commands section:\n"
    "   * Layer 1/2/3 commands accurate? `pytest -m e2e` requires the\n"
    "     `e2e` marker — registered in pytest.ini in Session 1.\n"
    "     `npm run test:playwright` works as documented.\n"
    "   * 'Lowest layer that can see the regression' guidance — is\n"
    "     this captured well enough that a future contributor picks\n"
    "     the right layer?\n"
    "4. Version bumps:\n"
    "   * `pyproject.toml` 0.3.0 -> 0.3.1 — patch-version bump for\n"
    "     additive-only test infrastructure. Correct semver?\n"
    "   * `package.json` 0.13.15 -> 0.13.16 — patch-version bump,\n"
    "     same justification. Correct?\n"
    "5. `CHANGELOG.md` entries (both):\n"
    "   * Entries describe what changed accurately. Any factual errors\n"
    "     in the descriptions (e.g., wrong test count, wrong file\n"
    "     paths)?\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references."
)


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION4_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 4 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    result = ar.route(
        content=content,
        task_type="session-verification",
        context=context,
        session_set="027-orchestrator-e2e-harness",
        session_number=4,
    )
    dump_path = (
        REPO_ROOT / "scripts" / f"verify_session_027_4_result_{label.lower()}.json"
    )
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
    print(f"  Dumped to {dump_path.name}")
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
    parser.add_argument("--round", choices=["A", "B"], default=None)
    args = parser.parse_args()

    ext_root = REPO_ROOT / "tools/dabbler-ai-orchestration"
    electron_text = (ext_root / "src/test/playwright/electronLaunch.ts").read_text("utf-8")
    config_text = (ext_root / "playwright.config.ts").read_text("utf-8")
    spec_text = (ext_root / "src/test/playwright/treeView.spec.ts").read_text("utf-8")
    pkg_text = (ext_root / "package.json").read_text("utf-8")
    changelog_ext = (ext_root / "CHANGELOG.md").read_text("utf-8")
    changelog_router = (REPO_ROOT / "ai_router/CHANGELOG.md").read_text("utf-8")
    claude_md = (REPO_ROOT / "CLAUDE.md").read_text("utf-8")
    set_change_log = (
        REPO_ROOT / "docs/session-sets/027-orchestrator-e2e-harness/change-log.md"
    ).read_text("utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text("utf-8")

    # Round B bundle includes only the first 80 lines of each changelog
    # to keep size manageable (the older sections aren't being changed
    # and the verifier doesn't need them for context).
    def _head(text: str, n_lines: int) -> str:
        return "\n".join(text.splitlines()[:n_lines])

    rounds = {
        "A": (
            "Round A: electronLaunch.ts + playwright.config.ts + package.json scripts",
            (
                f"=== tools/dabbler-ai-orchestration/src/test/playwright/electronLaunch.ts ===\n"
                f"{electron_text}\n\n"
                f"=== tools/dabbler-ai-orchestration/playwright.config.ts ===\n"
                f"{config_text}\n\n"
                f"=== tools/dabbler-ai-orchestration/package.json (scripts only) ===\n"
                f"{_head(pkg_text, 360)}\n"
            ),
            VERIFICATION_ASKS_A,
        ),
        "B": (
            "Round B: treeView.spec.ts + change-log.md + CHANGELOG/CLAUDE/pyproject diffs",
            (
                f"=== tools/dabbler-ai-orchestration/src/test/playwright/treeView.spec.ts ===\n"
                f"{spec_text}\n\n"
                f"=== docs/session-sets/027-orchestrator-e2e-harness/change-log.md ===\n"
                f"{set_change_log}\n\n"
                f"=== CLAUDE.md (head 100 lines) ===\n"
                f"{_head(claude_md, 100)}\n\n"
                f"=== tools/dabbler-ai-orchestration/CHANGELOG.md (head 60 lines) ===\n"
                f"{_head(changelog_ext, 60)}\n\n"
                f"=== ai_router/CHANGELOG.md (head 50 lines) ===\n"
                f"{_head(changelog_router, 50)}\n\n"
                f"=== pyproject.toml ===\n"
                f"{pyproject}\n"
            ),
            VERIFICATION_ASKS_B,
        ),
    }

    to_run = [args.round] if args.round else ["A", "B"]
    all_ok = True
    for key in to_run:
        label, bundle, asks = rounds[key]
        print(f"\n{'='*60}")
        print(f"Running {label} ...")
        try:
            _run_round(key, bundle, asks)
        except Exception as exc:
            print(f"ERROR: {exc}")
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
