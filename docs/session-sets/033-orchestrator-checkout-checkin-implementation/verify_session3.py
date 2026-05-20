"""Session 3 verification driver — Set 033 (implementation cycle).

Round A bundles the artifacts produced by Session 3:

  - tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js
    — NEW shim that replaces the retired write-orchestrator-marker.js
    for the Claude SessionStart hook path. Reads the hook payload, walks
    up cwd to find the in-progress session set, and spawns
    `python -m ai_router.start_session` (per H1: hooks become invokers,
    not writers).
  - tools/dabbler-ai-orchestration/src/commands/checkOutOrchestrator.ts
    — RENAMED + REWRITTEN. Replaces the dabbler.setOrchestrator command
    + its marker-helper dispatch. New command id
    dabbler.checkOutOrchestrator; PROVIDER_TO_ENGINE map (H4 identity);
    listInProgressSetsAt resolver (reads session-state.json's
    orchestrator block, no marker file); dispatchCheckOut spawns
    `python -m ai_router.start_session`; force-override prompt fires
    on different (engine+provider) holder.
  - tools/dabbler-ai-orchestration/src/commands/releaseCheckOut.ts
    — NEW command. Confirmation-gated launcher of the renamed
    quickpick (H3's named release path alongside `start_session
    --force` on the CLI).
  - tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts
    — REFACTORED. Installs SessionStart hook pointing at the new
    invoker shim. Prunes any stale dabbler-managed UserPromptSubmit
    entries from operator settings.json (the signalKind path the old
    UserPromptSubmit served was retired with H2 in S2).
  - tools/dabbler-ai-orchestration/src/codex/configWatcher.ts
    — REFACTORED. On Codex config.toml change, walks up to find the
    in-progress session set and spawns `python -m ai_router.start_session`
    (was: spawned write-orchestrator-marker.js). Same-holder
    short-circuit to avoid spawning python on every editor save.
  - tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookGemini.ts
    + installOrchestratorHookCopilot.ts — small updates: executeCommand
    target renamed from dabbler.setOrchestrator to
    dabbler.checkOutOrchestrator.
  - tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts
    — id + label update; added dabbler.releaseCheckOut row action.
  - tools/dabbler-ai-orchestration/src/providers/detectOrchestrators.ts
    — Codex empty-state CTA command id updated; provider CTA labels
    updated to "check out as <provider>".
  - tools/dabbler-ai-orchestration/src/providers/CustomSessionSetsView.ts
    (excerpt) — id reference in the supported-commands allowlist.
  - tools/dabbler-ai-orchestration/src/extension.ts (excerpt)
    — import + safeRegister rename + new releaseCheckOut registration.
  - tools/dabbler-ai-orchestration/package.json (excerpt)
    — commands section: rename dabbler.setOrchestrator to
    dabbler.checkOutOrchestrator + add dabbler.releaseCheckOut.
  - tools/dabbler-ai-orchestration/src/test/suite/checkOutOrchestrator.test.ts
    — RENAMED + extended with providerToEngine tests.
  - tools/dabbler-ai-orchestration/src/test/suite/releaseCheckOut.test.ts
    — NEW. describeHolder unit tests.
  - tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts
    — updated for the rename + the new releaseCheckOut row.

Ground truth bundled alongside:

  - The H1, H3, H4 verdicts (§9 of proposal-addendum.md) — the audit
    decisions S3 traces to.
  - Set 033 spec.md Session 3 — the contract this session ships.
  - ai_router/start_session.py (CLI definitions only) — the writer
    surface every S3 invoker calls.

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
shipped the Python writer side (H1+H3+H4+OQ1). Session 2 (CLOSED)
shipped the TypeScript reader-side migration (H2): the per-set
`.dabbler/orchestrator.json` marker file was retired entirely, the
MarkerWatchService class was replaced by free functions in
inProgressSetsService.ts, and the tree provider renders N
in-progress accordions instead of a single resolved active set.

Session 2 closed knowingly with a writer-side breakage in place
(spec risk R1): the Claude SessionStart hook installer + Codex
configWatcher + manual-override quickpick all referenced the
deleted `scripts/write-orchestrator-marker.js` script via the
HELPER_REL string path. The references were compile-time clean but
runtime-broken (Node would emit "Cannot find module" on every
SessionStart fire). The breakage was scoped to S3.

Session 3 (THIS verification) closes that breakage and ships the
H1 + H3 UI affordance surface:

  - HELPER_REL references retired in all three offending files;
    the Claude hook now points at a NEW shim
    `scripts/claude-session-start-invoker.js` that invokes
    `python -m ai_router.start_session` directly. The Codex
    watcher and the manual quickpick also invoke start_session
    directly (no shim needed — they run inside the extension host
    and can spawn python themselves).
  - dabbler.setOrchestrator renamed to dabbler.checkOutOrchestrator
    (display label "Check Out As…"); the underlying file
    setOrchestratorManual.ts renamed to checkOutOrchestrator.ts via
    `git mv` (blame preserved).
  - NEW command dabbler.releaseCheckOut ("Release Check-Out") added
    as one of H3's two named release paths (the other is
    `start_session --force` on the CLI). It confirms intent, then
    delegates to the renamed quickpick.
  - The PROVIDER_TO_ENGINE map (anthropic→claude, openai→codex,
    google→gemini, github→copilot) is the H4-identity bridge from
    the operator-facing provider names to the engine brand the
    writer + reader read back. The H4 identity composite is
    (engine + provider), not (provider, model).
  - UserPromptSubmit hook entry retired entirely: the signalKind
    field it updated was removed alongside the per-set marker file
    in S2; with the orchestrator block on session-state.json having
    no signalKind, the hook had no behavior left. The installer
    additionally prunes any stale dabbler-managed UserPromptSubmit
    entries from existing operators' settings.json.
  - Tests: unit suite + lint pass cleanly (409 passing; 2 pre-
    existing unrelated failures — configEditor-foundation and
    notificationsSection — flagged in S2 disposition and unchanged
    by S3).

Sessions 4-6 are out of scope for THIS verification:
  - S4 is the Playwright Layer-3 spec coverage of multi-in-progress
    rendering + check-out conflict refusal + holder identity (the
    NAMED release-path visibility test in S4 will exercise the
    `dabbler.releaseCheckOut` command this session adds).
  - S5 is queueing / polling on detection of a held check-out.
  - S6 is close_session cross-tier check-in + canonical doc updates
    + cross-repo notifications + PyPI release.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 3 implementation faithfulness for the H1 invoker
refactor, the H3 release affordance, the H4 identity surface, and
the test coverage of the rename + new command.

You are Gemini Pro, asked to verify that Session 3 of Set 033 ships
the TypeScript UI affordance migration consistent with the H1, H3,
and H4 locked verdicts.

Verify:

A. **H1 invoker refactor is complete and correct.** "Hooks become
   invokers, not writers." Confirm:

   1. `scripts/claude-session-start-invoker.js` reads the Claude
      SessionStart hook payload from stdin (best-effort JSON parse),
      walks up cwd to find `docs/session-sets/<slug>/` with
      `status: "in-progress"`, and spawns `python -m ai_router.start_session`
      with arguments `--session-set-dir <abs path> --engine claude
      --provider anthropic --model <model> --effort <effort>` (no
      `--force` — hooks never auto-override). The shim NEVER writes
      to `session-state.json` directly. The shim NEVER touches the
      retired `.dabbler/orchestrator.json` marker path.
   2. The shim preserves the existing holder's `model` + `effort`
      when the holder is already `claude + anthropic` (the
      SessionStart payload has no model signal; falling back to
      `unknown` would degrade a more-accurate model recorded by the
      manual quickpick or configWatcher). Verify the
      `preserveExistingClaude` helper exists and is used.
   3. The shim is best-effort: spawn failure, JSON parse failure,
      walk-up failure, and writer-side conflict (`EXIT_CHECKOUT_CONFLICT
      = 4` from start_session.py) all surface via stderr but exit 0
      — Claude Code's hook chain is never broken by the shim.
   4. The Codex configWatcher (`src/codex/configWatcher.ts`) invokes
      `python -m ai_router.start_session` with engine=codex +
      provider=openai (NOT engine=openai). The configWatcher passes
      no `--force` (same hard-coordination rule as the Claude shim).
   5. The renamed quickpick command (`checkOutOrchestrator.ts`)
      dispatches via `dispatchCheckOut` which spawns
      `python -m ai_router.start_session`. The dispatch passes
      `--force` ONLY when the operator confirmed override via
      `maybeConfirmForceOverride` (different-holder modal prompt).
   6. The Gemini and Copilot installer shims still delegate via
      `vscode.commands.executeCommand` — the command id they target
      is updated to `dabbler.checkOutOrchestrator` (NOT
      `dabbler.setOrchestrator`). These remain UI-shim-only paths;
      neither installs a hook of its own.
   7. Confirm NO remaining references to
      `scripts/write-orchestrator-marker.js` exist in the bundled
      TypeScript source files (the S2 R1 breakage is closed).

B. **H3 release affordance is wired through the spec contract.**

   1. `dabbler.releaseCheckOut` is registered in package.json
      `contributes.commands` with `"category": "Dabbler"` so it's
      discoverable via "Dabbler: Release Check-Out" in the Command
      Palette.
   2. The command's implementation (`releaseCheckOut.ts`) walks up
      to find in-progress sets via the SAME `pickTargetInProgressSet`
      helper the quickpick uses (single source of truth — no
      divergent UX between Check Out As… and Release Check-Out).
   3. The flow is: confirm release → delegate to
      `dabbler.checkOutOrchestrator` with `{ targetSet: set }` arg
      so the operator picks the new holder in the same multi-step
      flow. The two-modal sequence (Release confirmation + the
      quickpick's own different-holder Override confirmation) is
      intentional — the first establishes intent, the second sanity-
      checks the identity handoff.
   4. The command is also exposed via ActionRegistry row 502 with
      label "Release Check-Out", gated on `state === "in-progress"`
      (same gate as Check Out As…).

C. **H4 identity surface (engine + provider composite, NOT
   engine alone, NOT engine+provider+model).**

   1. `PROVIDER_TO_ENGINE` in checkOutOrchestrator.ts maps:
      anthropic→claude, openai→codex, google→gemini, github→copilot.
      The `providerToEngine` function is exported (it's the H4
      identity bridge).
   2. `maybeConfirmForceOverride` compares (existing.engine,
      existing.provider) to (newEngine, tuple.provider) — NOT
      including model. Two different Claude models from anthropic
      (e.g., claude-opus-4-7 vs claude-sonnet-4-6) resolve to the
      same identity → no force prompt → same-holder re-attach (per
      Set 033 R3).
   3. The Claude shim's `preserveExistingClaude` compares engine
      AND provider — not just engine.
   4. The Codex watcher's same-holder short-circuit checks
      engine === "codex" AND provider === "openai" — not just
      engine.

D. **Rename completeness end-to-end.**

   1. package.json contributes.commands: `dabbler.setOrchestrator`
      is GONE; `dabbler.checkOutOrchestrator` is present with title
      "Check Out As…"; `dabbler.releaseCheckOut` is present with
      title "Release Check-Out".
   2. ActionRegistry: `dabbler.setOrchestrator` is GONE; the row
      now uses `dabbler.checkOutOrchestrator` with label
      "Check Out As…"; `dabbler.releaseCheckOut` row added.
   3. CustomSessionSetsView: the supported-commands allowlist
      includes `dabbler.checkOutOrchestrator` AND
      `dabbler.releaseCheckOut`; `dabbler.setOrchestrator` is GONE.
   4. detectOrchestrators: CODEX_CTA's commandId is now
      `dabbler.checkOutOrchestrator` (NOT `dabbler.setOrchestrator`).
   5. Gemini + Copilot installer shims: `executeCommand` targets
      `dabbler.checkOutOrchestrator` (NOT `dabbler.setOrchestrator`).
   6. extension.ts: import is from `checkOutOrchestrator` (NOT
      `setOrchestratorManual`); register function is
      `registerCheckOutOrchestrator`; `registerReleaseCheckOut` is
      called.
   7. The OrchestratorAccordion's user-facing string referencing
      "Set Orchestrator Model & Effort" is updated to reference
      "Check Out As…".

E. **UserPromptSubmit retirement is clean.**

   1. The Claude installer no longer ADDS a UserPromptSubmit entry.
   2. The installer PRUNES any existing dabbler-managed
      UserPromptSubmit entries (matched by `claude-session-start-invoker.js`
      OR `write-orchestrator-marker.js` substring in the command).
      The pruning is surgical: other UserPromptSubmit entries the
      operator may have installed at the same matcher are
      preserved verbatim.
   3. The pruning is idempotent: re-running the installer leaves a
      previously-cleaned settings.json unchanged.

F. **Test adequacy.**

   1. `checkOutOrchestrator.test.ts` (renamed): preserves the
      pre-existing MRU + formatTupleLabel tests; adds a new
      `providerToEngine` suite asserting the 4-element mapping.
   2. `actionRegistry.test.ts`: the expected-action set is updated
      (`dabbler.checkOutOrchestrator` + `dabbler.releaseCheckOut`
      replace `dabbler.setOrchestrator`); total ROW_ACTIONS length
      bumped from 16 to 17; the "appears only on in-progress rows"
      test covers BOTH new ids.
   3. `detectOrchestrators.test.ts`: the Codex CTA test expects
      `dabbler.checkOutOrchestrator` as the commandId.
   4. NEW `releaseCheckOut.test.ts`: covers the `describeHolder`
      helper's four shapes (full, model-absent, partial-identity,
      null orchestrator).

G. **What's risky or missing.** Any edge case the implementation
   omits that would bite a real run?

   - The Claude shim's `python` invocation uses bare `python` on
     PATH (no workspace pythonPath setting). The shim runs in
     Claude Code's hook context — outside VS Code — and so cannot
     read the dabblerSessionSets.pythonPath setting. Is this a
     known limitation, and is the failure mode (python not on
     PATH) graceful?
   - The Codex watcher's same-holder short-circuit ELIDES the
     lastActivityAt bump when codex+openai already holds. Is that
     intentional (yes — bumping on every config-file save would
     spam python invocations), or does it miss a useful liveness
     signal?
   - The renamed file `checkOutOrchestrator.ts` (was
     `setOrchestratorManual.ts`) — are there any stale string
     references to "setOrchestratorManual" anywhere bundled below
     that would still compile but indicate a missed update?
   - The D13 lint rule (`noLegacyFieldReads.test.ts`) flagged
     `state.currentSession` reads in checkOutOrchestrator.ts and
     configWatcher.ts; the fix was `// noqa: D13` annotations with
     justifying comments. Verify the carve-out is appropriate
     (these reads pass `currentSession` verbatim to the writer as
     `--session-number`; they don't re-derive legacy progress).

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits. Session 3 closes the S2-shipped
breakage AND ships the UI surface S4's Playwright scenarios will
exercise — a must-fix here blocks S4.
""".strip()


def _bundle() -> str:
    parts = [
        # NEW shim — ship in full.
        read_file(EXT_ROOT / "scripts" / "claude-session-start-invoker.js"),
        # Primary deliverable — full file.
        read_file(EXT_ROOT / "src" / "commands" / "checkOutOrchestrator.ts"),
        # New command — small, ship in full.
        read_file(EXT_ROOT / "src" / "commands" / "releaseCheckOut.ts"),
        # Refactored Claude installer — full.
        read_file(EXT_ROOT / "src" / "commands" / "installOrchestratorHookClaudeCode.ts"),
        # Refactored Codex watcher — full.
        read_file(EXT_ROOT / "src" / "codex" / "configWatcher.ts"),
        # Small installer shims — ship in full.
        read_file(EXT_ROOT / "src" / "commands" / "installOrchestratorHookGemini.ts"),
        read_file(EXT_ROOT / "src" / "commands" / "installOrchestratorHookCopilot.ts"),
        # ActionRegistry — full file is short enough.
        read_file(EXT_ROOT / "src" / "providers" / "ActionRegistry.ts"),
        # detectOrchestrators — full file (CTA updates).
        read_file(EXT_ROOT / "src" / "providers" / "detectOrchestrators.ts"),
        # CustomSessionSetsView excerpt — just the supported-commands allowlist.
        read_section(
            EXT_ROOT / "src" / "providers" / "CustomSessionSetsView.ts",
            "const SUPPORTED_ROW_COMMAND_IDS",
            "function contextValueFor(",
        ),
        # extension.ts excerpt — imports + registration block.
        read_section(
            EXT_ROOT / "src" / "extension.ts",
            "import { registerInstallOrchestratorHookGeminiCommand",
            "// Set 030 Session 5: flip scanState to",
        ),
        # package.json excerpt — commands section.
        read_section(
            EXT_ROOT / "package.json",
            '"command": "dabbler.installOrchestratorHook.claudeCode"',
            '"menus":',
        ),
        # OrchestratorAccordion excerpt — the user-facing copy update.
        read_section(
            EXT_ROOT / "src" / "providers" / "OrchestratorAccordion.ts",
            "function computeMismatch",
            "// ----- HTML escaping",
        ),
        # Tests — ship in full so coverage assertions are checkable.
        read_file(EXT_ROOT / "src" / "test" / "suite" / "checkOutOrchestrator.test.ts"),
        read_file(EXT_ROOT / "src" / "test" / "suite" / "releaseCheckOut.test.ts"),
        read_file(EXT_ROOT / "src" / "test" / "suite" / "actionRegistry.test.ts"),
        # detectOrchestrators test — small excerpt.
        read_section(
            EXT_ROOT / "src" / "test" / "suite" / "detectOrchestrators.test.ts",
            "Codex-only scenario",
            "Gemini-only scenario",
        ),
        # Ground truth — H1, H3, H4 verdicts from the locked addendum.
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # Ground truth — Session 3 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 3 of 6:",
            "## Session 4 of 6:",
        ),
        # Ground truth — start_session CLI definitions the invokers target.
        read_section(
            REPO_ROOT / "ai_router" / "start_session.py",
            "def _build_arg_parser",
            "def _identity_label",
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
        session_number=3,
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
        print("Usage: python verify_session3.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-3-result.json",
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
            out_dir / "round-b-session-3-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
