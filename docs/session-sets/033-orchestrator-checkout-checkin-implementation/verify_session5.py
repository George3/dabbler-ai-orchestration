"""Session 5 verification driver — Set 033 (implementation cycle).

Round A bundles the artifacts produced by Session 5:

  - tools/dabbler-ai-orchestration/src/providers/CheckoutPollService.ts
    — NEW. State machine: directory-watch on
    ~/.dabbler/checkout-conflicts/, prompt dispatch (Poll / Force /
    Dismiss), polling with 5s debounce and H4 identity gate,
    force-override path, 30-min timeout default. Test seams
    (showInformationMessage + spawnStartSession injection) enable
    Layer-2 coverage without launching VS Code.
  - tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js
    — UPDATED. On `EXIT_CHECKOUT_CONFLICT` (4), emits a structured
    record at ~/.dabbler/checkout-conflicts/<ISO>-claude-<slug>.json.
    Existing stderr-log behavior preserved as a fallback.
  - tools/dabbler-ai-orchestration/src/codex/configWatcher.ts
    — UPDATED. resolveSingleInProgressSet now returns slug + model +
    checkedOutAt; dispatchCheckOut captures exit code via
    child.on('exit') (was: fire-and-forget) and writes the same
    sentinel format with `codex+openai` as the would-be holder.
  - tools/dabbler-ai-orchestration/src/extension.ts (excerpt)
    — service registration with pythonPath + timeout resolvers.
  - tools/dabbler-ai-orchestration/package.json (excerpt)
    — new dabblerSessionSets.checkoutPollTimeoutMinutes setting.
  - tools/dabbler-ai-orchestration/src/test/suite/checkoutPollService.test.ts
    — NEW. 25 tests across 8 suites covering parse, identity, key
    derivation, prompt dispatch, polling state machine (4 tests),
    sentinel ingest, conflictDirPath anchor, prompt-action constants.
  - tools/dabbler-ai-orchestration/src/test/playwright/checkout-polling.spec.ts
    — NEW. 1 passing Layer-3 scenario (sentinel consumed on
    activation) + 1 skipped with FIXME (the full polls-then-attaches
    happy path defers per the same notification-button brittleness
    that S4's release-checkout palette scenario documented).

Ground truth bundled alongside:

  - The H3 + H4 verdicts (§9 of proposal-addendum.md) — the
    hard-coordination + identity rules the polling identity gate
    enforces.
  - Set 033 spec.md Session 5 — the contract this session ships.
  - ai_router/start_session.py — EXIT_CHECKOUT_CONFLICT definition
    and the refusal-message contract the invokers map to sentinels.

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
from the six verdicts the Set 032 audit locked.

Sessions 1-4 (CLOSED):

  - S1 — Python writer side: orchestrator block on
    session-state.json is the authoritative check-out record;
    start_session enforces H3 hard coordination + --force override;
    +2 nested timestamps (checkedOutAt + lastActivityAt).
  - S2 — TypeScript reader-side migration: per-set marker
    (.dabbler/orchestrator.json) retired; MarkerWatchService class
    replaced by free functions in inProgressSetsService.ts; tree
    provider renders N in-progress accordions instead of one
    resolved active set; banner removed.
  - S3 — UI affordance migration (H1 + H3 + H4): hooks become
    invokers (Claude SessionStart shim spawns
    `python -m ai_router.start_session` rather than writing the
    marker directly); dabbler.setOrchestrator renamed to
    dabbler.checkOutOrchestrator; new dabbler.releaseCheckOut
    Command Palette action.
  - S4 — Layer-3 Playwright coverage: 4 passing scenarios
    (different-holder refusal, --force override + writer-log audit,
    same-holder re-attach, multi-in-progress bucket header).

Session 5 (THIS verification) ships the polling/queueing UX from
the spec:

  - When a SessionStart hook or Codex config-toml watcher invocation
    hits EXIT_CHECKOUT_CONFLICT (4 — H3 refusal because a different
    engine+provider holds the slot), the invoker writes a structured
    JSON conflict record to ~/.dabbler/checkout-conflicts/. Each
    record carries: schemaVersion (1), detectedAt, source, slug,
    sessionSetPath, sessionNumber, heldBy{Engine,Provider,Model},
    checkedOutAt, wouldBeHolder{Engine,Provider,Model,Effort}.
  - The in-extension CheckoutPollService scans the conflict
    directory at activation (for stale records from a prior
    extension lifetime), watches it via fs.watch for new records,
    and on each: reads, deletes the file, then shows a non-blocking
    information-message with three actions: "Poll for release",
    "Force override", "Dismiss".
  - Polling: watches the held set's session-state.json with a 5s
    debounce. When the file changes, re-reads, checks H4 identity
    (would-be holder's engine+provider matches the new orchestrator
    block OR the block is null), and spawns
    `python -m ai_router.start_session` without --force when the
    slot is free. If the writer refuses again (concurrent third-
    party claim), polling continues. If a third orchestrator joins
    mid-poll, the polling watcher does NOT yield — it continues
    waiting for the would-be holder that started the poll.
  - Force-override: spawns start_session with --force; the writer's
    existing _log_force_override path appends the audit line to
    ~/.dabbler/orchestrator-writer.log.
  - Timeout: dabblerSessionSets.checkoutPollTimeoutMinutes (default
    30, range 1..1440). On timeout, the service surfaces a one-time
    toast pointing at the "Dabbler: Release Check-Out" Command
    Palette action.
  - In-flight de-dup: a (slug, would-be holder identity) pair
    already being handled short-circuits duplicate sentinels (the
    Codex watcher fires on every config.toml save, and one prompt
    per distinct conflict is the operator UX).
  - Tests: Layer-2 — 25 tests across 8 suites; all pass.
    Layer-3 — 1 passing sentinel-consumption scenario + 1 skipped
    with FIXME (the toast-button-click happy path remains
    Playwright-brittle; covered at Layer 2).
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 5 implementation faithfulness for the
queueing/polling feature per the H3 hard-coordination + H4 identity
contract.

You are Gemini Pro, asked to verify that Session 5 of Set 033 ships
the polling UX consistent with the spec contract.

Verify:

A. **Conflict-record contract is faithful and complete.**

   1. parseConflictRecord (CheckoutPollService.ts) requires:
      schemaVersion === 1, sessionSetPath, sessionSetSlug,
      heldByEngine, heldByProvider, wouldBeHolderEngine,
      wouldBeHolderProvider, detectedAt, and source IN
      {"claude-invoker", "codex-watcher"}. Tolerates null/missing
      heldByModel, checkedOutAt, sessionNumber,
      wouldBeHolderModel, wouldBeHolderEffort. Confirm the
      strict-shape parser returns null on any required-field miss
      (the Layer-2 tests cover this — verify the contract
      end-to-end against the writer side).
   2. The Claude invoker (claude-session-start-invoker.js) writes a
      sentinel ONLY when result.status === 4
      (EXIT_CHECKOUT_CONFLICT). On other non-zero exits (boundary
      violations, usage errors) the invoker writes ONLY to stderr,
      not to the sentinel dir — the boundary is "different-holder
      refusal", not "any start_session failure".
   3. The Codex configWatcher's dispatchCheckOut now captures exit
      code via child.on('exit', ...) (was: fire-and-forget detached
      child). On exit 4, emitConflictRecord writes the same
      schema. The same-holder short-circuit (engine === "codex" &&
      provider === "openai") still elides the spawn entirely (no
      sentinel emission for the trivial re-attach case).
   4. Both emitters write to ~/.dabbler/checkout-conflicts/
      (homedir-anchored). Filename pattern: `<ISO-stamp>-<source>-<slug>.json`
      with ":" replaced for cross-platform filesystem safety
      (Windows can't have ":" in filenames).
   5. The four spec-named surface-contract fields (heldByEngine,
      heldByProvider, sessionSetPath, checkedOutAt) are all
      present in both emitters' records.

B. **CheckoutPollService state machine is faithful to the spec.**

   1. start() ensures the conflict directory exists
      (mkdirSync recursive), drains existing records (initial scan
      processes files written while the extension wasn't running),
      and registers fs.watch on the directory.
   2. processFile reads → deletes → parses → dispatches. The
      unlinkSync runs unconditionally after the read so a malformed
      record can't pin the directory full of unhandleable files.
      (Malformed records are silently dropped via parseConflictRecord
      returning null + processFile early-return.)
   3. handleConflict shows a non-blocking
      vscode.window.showInformationMessage with three actions:
      "Poll for release", "Force override", "Dismiss". In-flight
      de-dup is keyed on pollKey(record), which derives
      `<slug>::<would-be engine>+<would-be provider>`. A second
      sentinel for the same pair short-circuits without
      re-prompting.
   4. beginPolling registers fs.watch on the held set's
      session-state.json with a 5s debounce (POLL_DEBOUNCE_MS).
      tryRetry re-reads the file, applies isSlotFreeForHolder
      (H4 identity gate), and spawns start_session WITHOUT --force
      if the slot is free. An immediate tryRetry runs once at
      beginPolling so the slot-already-free-at-click case resolves
      without waiting for the next state-file change. retryInFlight
      prevents concurrent spawns from a watcher burst.
   5. forceOverride spawns start_session WITH --force. On success,
      shows a confirmation toast naming the slug + the new holder
      + the writer-log location. On failure, shows an error toast
      with the exit code + a hint at the CLI fallback.
   6. The timeout uses dabblerSessionSets.checkoutPollTimeoutMinutes
      (default 30, range 1..1440). resolvePollTimedOut shows a
      one-time information toast pointing at the
      "Dabbler: Release Check-Out" Command Palette action.

C. **H4 identity gate (engine + provider composite).**

   1. isSlotFreeForHolder(orchestrator, wouldBeEngine,
      wouldBeProvider) returns true ONLY when:
        (a) orchestrator is null OR undefined; OR
        (b) orchestrator.engine === wouldBeEngine AND
            orchestrator.provider === wouldBeProvider.
      It returns FALSE when a third orchestrator (different engine,
      or same engine + different provider) holds the slot. The
      spec's "if a third orchestrator joins mid-poll, the polling
      watcher does NOT yield to it — it continues for the holder
      that started the poll" maps to this exact predicate (a
      third-engine holder fails the gate; the watcher keeps
      waiting).
   2. pollKey composes the slug with the would-be holder identity,
      NOT the held-by identity. Two would-be holders racing for the
      same slot get distinct keys (Layer-2 covers this).

D. **Detection path correctness.**

   1. The Claude invoker emits a sentinel BEFORE writing to stderr
      so a race-condition between the extension reading the
      sentinel and the operator reading the stderr-log is benign
      (both paths surface independently).
   2. The Codex watcher's exit handler attaches to the spawned
      child object — verify the child.on('error') handler from S3
      is preserved (best-effort silent on spawn failure) AND the
      new child.on('exit') only emits when code === 4.
   3. Both emitters use os.homedir() (Node) / os.path.expanduser
      / equivalent to resolve ~/.dabbler/checkout-conflicts/, not
      a hard-coded path. Setting USERPROFILE / HOME in env should
      redirect the path (Layer-3 spec uses this for a hermetic
      test fixture).

E. **Service registration in extension.ts is robust.**

   1. The safeRegister('CheckoutPollService', ...) wrapper guards
      against a constructor throw — a failure here mustn't kill
      the rest of activation (same defensive pattern as the other
      safeRegister calls).
   2. pythonPathResolver mirrors the resolution chain used by
      checkOutOrchestrator.ts and configWatcher.ts (explicit
      setting → folder → workspace → global precedence; absolute /
      workspace-relative / bare-on-PATH cases).
   3. timeoutMinutesResolver reads the setting on each
      beginPolling() (not cached at construction). A setting change
      during a running extension takes effect on the next poll.
      Defensive clamp to [1, 1440].

F. **Test adequacy.**

   1. Layer-2 (25 tests) covers: parseConflictRecord (7),
      isSlotFreeForHolder H4 identity (5), pollKey (2),
      handleConflict dispatch incl. in-flight de-dup (3),
      beginPolling state machine (4 — immediate retry, third-
      holder no-spawn, session-number arg presence/absence,
      dispose semantics), processFile sentinel ingest (2),
      conflictDirPath, prompt-action constants.
   2. Layer-3: 1 passing — sentinel-consumption end-to-end via a
      pre-existing sentinel dropped before VS Code launches
      against a HOME-overridden fixture workspace. Sanity-check
      assertion: state-file's orchestrator block is unchanged
      (consume surfaces the prompt; it does NOT silently
      force-override). 1 skipped with FIXME — the toast-button-
      click happy path, deferred per the same Playwright brittleness
      S4 hit with the palette path.

G. **What's risky or missing.** Any edge case the implementation
   omits that would bite a real run?

   - The polling watcher uses fs.watch on a single file (the held
     set's session-state.json). fs.watch is best-effort on
     Windows (the spec already calls this out — Set 033 risk
     surface, R7-adjacent). What happens if the watch fails
     silently? The 5s debounce + the dirWatcher on the conflict
     dir together cover the "operator clicks Poll, then nothing
     happens" gap?
   - The retry path uses bare `python` on PATH (resolved via the
     workspace setting). If python is missing, the retry returns
     exit=null and the poll continues forever (until timeout). Is
     the failure mode acceptable, or does it need a guard?
   - The in-flight de-dup uses a Set<string> that's only cleared
     on poll resolution (success / timeout / dispose). If
     handleConflict throws AFTER adding to inFlight but BEFORE
     starting a poll, the key is stranded. Verify the finally
     block clears inFlight when beginPolling isn't called.
   - The Codex watcher spawn passes `cwd: opts.cwd` to
     cp.spawn, but the workspace cwd may differ from the
     session-set's parent dir. The writer is given the full
     session-set-dir path so this should be OK, but verify the
     cwd is consistent with what the Claude invoker passes (which
     omits cwd entirely — falling back to process.cwd()).
   - Force-override from the polling prompt does NOT explicitly
     confirm a second time (the prompt itself is the
     confirmation). Is the "single-modal force" UX consistent with
     the Release Check-Out command's "two-modal force" UX (S3
     intentionally double-confirmed for the operator-driven path)?
   - The Layer-3 spec relies on USERPROFILE/HOME override to
     redirect the conflict dir. Verify the override is honored by
     Node's os.homedir() on Windows (USERPROFILE precedence over
     SystemRoot/profile lookup) and on POSIX (HOME).

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits. S5 ships the queueing UX; a must-fix
here blocks S6 (which closes the migration with cross-tier
close-out + docs + PyPI release).
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverable — full file.
        read_file(EXT_ROOT / "src" / "providers" / "CheckoutPollService.ts"),
        # Updated Claude invoker — full file.
        read_file(EXT_ROOT / "scripts" / "claude-session-start-invoker.js"),
        # Updated Codex watcher — full file.
        read_file(EXT_ROOT / "src" / "codex" / "configWatcher.ts"),
        # extension.ts excerpt — service registration.
        read_section(
            EXT_ROOT / "src" / "extension.ts",
            "// Set 033 Session 5: CheckoutPollService",
            "// Set 030 Session 5: flip scanState to",
        ),
        # package.json excerpt — new setting.
        read_section(
            EXT_ROOT / "package.json",
            '"dabblerSessionSets.checkoutPollTimeoutMinutes"',
            "}\n      }\n    }\n  },",
        ),
        # Tests — ship in full so coverage assertions are checkable.
        read_file(EXT_ROOT / "src" / "test" / "suite" / "checkoutPollService.test.ts"),
        read_file(EXT_ROOT / "src" / "test" / "playwright" / "checkout-polling.spec.ts"),
        # Ground truth — H3 + H4 verdicts from the locked addendum.
        read_section(
            PROPOSAL_DIR / "proposal-addendum.md",
            "## 9. Audit resolution (Set 032 Session 1, 2026-05-19)",
            "## Round-2 questions (HISTORICAL — superseded by §9)",
        ),
        # Ground truth — Session 5 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 5 of 6:",
            "## Session 6 of 6:",
        ),
        # Ground truth — EXIT_CHECKOUT_CONFLICT + refusal-message body.
        read_section(
            REPO_ROOT / "ai_router" / "start_session.py",
            "EXIT_OK = 0",
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
        session_number=5,
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
        print("Usage: python verify_session5.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-5-result.json",
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
            out_dir / "round-b-session-5-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
