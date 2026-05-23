"""Cross-provider verification for Set 036 Session 5.

Verifies the Layer-3 Playwright coverage + cross-tier doc updates +
cross-repo notice update shipped in Session 5. Scope:

  * NEW Layer-3 Playwright specs:
    * `tools/dabbler-ai-orchestration/src/test/playwright/chatsessionid-takeover.spec.ts`
      — two-chat takeover end-to-end: chatSessionId-mismatch refusal
      with both IDs in stderr, --force handoff updating state +
      writer log, same-chat re-attach preserves checkedOutAt.
    * `tools/dabbler-ai-orchestration/src/test/playwright/chatsessionid-missing-tolerance.spec.ts`
      — tolerant-on-read: legacy state (no chatSessionId key) AND
      Set-036-null state both tolerate a new chat and populate the
      field strictly on first write; subsequent different chats
      refused.
    * `tools/dabbler-ai-orchestration/src/test/playwright/new-chat-id-cli-flow.spec.ts`
      — `python -m ai_router.new_chat_id` plain-mode UUID v4 mint;
      env-fallback flow into orchestrator block; idempotency against
      existing $CHAT_SESSION_ID.

  * Helper extensions:
    * `electronLaunch.ts` — attemptStartSession gains chatSessionId
      + env opts; seedOrchestratorBlock distinguishes omitted-key vs
      null-value vs string for chatSessionId (Set 036 three-shape
      contract).

  * Cross-tier doc updates:
    * `docs/session-state-schema.md` — chatSessionId added to
      orchestrator block JSON shape + field table; H4 holder
      identity refined to `engine + provider + chatSessionId`
      composite; new paragraphs on chatSessionId source (Claude
      Code hook / new_chat_id CLI), tolerant-on-read semantics,
      strict-on-write contract, takeover prompt at the H3 boundary,
      writer log fields, per-set lifecycle lock (Q5); block-null
      invariant extended to note chatSessionId clears with the
      block; mid-set worked example updated with chatSessionId.
    * `ai_router/docs/close-out.md` — Section 0 close-side protocol
      table extended with orchestrator clear + closeout_succeeded
      Q4 payload (chatSessionId + engine + provider + model); Section
      2 "Orchestrator check-in" paragraph notes chatSessionId lives
      inside the block; Section 3 step 9 mark_session_complete
      bullet notes Q4 payload snapshot ordering; Section 4 stranded-
      checkout recovery extended to chatSessionId case + writer log
      composite line + TTY takeover prompt mirror.
    * `docs/ai-led-session-workflow.md` — "Orchestrator check-out /
      check-in (Set 033)" subsection: H4 refined to triple;
      chatSessionId source paragraph; H3 refusal mentions chat-id
      and TTY prompt; tolerant-on-read paragraph; force-override
      writer log now logs both chatSessionIds; closeout_succeeded
      Q4 payload note; per-set lifecycle lock paragraph; tier
      symmetry restated for Lightweight (new_chat_id paste).

  * Cross-repo notice update:
    * `docs/cross-repo-checkout-notice.md` — UPDATE of the snippet
      from the Set 033 base composite to the Set 036 refinement.
      Holder identity now triple; chatSessionId source by
      orchestrator; refusal example carries chat-id; takeover modal
      / CLI prompt added as third resolution path; tolerant-on-read
      paragraph; close-out clears chat-id with block; lifecycle
      lock paragraph; Lightweight tier reminder mentions
      new_chat_id paste. Header notes the update + diff-based swap
      guidance for consumers that already pasted the Set 033
      version.

Test posture (Layer-3): three new specs add 9 tests; all 9 pass.
Full Playwright suite: 21 passed + 3 skipped + 5 pre-existing
failures in session-sets-tree.spec.ts + multi-in-progress.spec.ts
that are explicitly Session 6's scope to fix per the Set 036 spec
(Session 6 step 5 — "Layer-3 Playwright update" — and the orphaned
`.grey-gauges` CSS sweep). `npx tsc --noEmit` clean.

Total scope ~875 LOC (375 doc/helper insertions + ~500 LOC new
specs). Round A bundled; Round B fires if must-fix or if the
cross-tier doc reach surfaces a doc/code drift.

Usage:
    python scripts/verify_session_036_5.py [--round A|B]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai_router as ar  # type: ignore[import-not-found]


SESSION_CONTEXT = (
    "Set 036 Session 5 of 7 — Layer-3 Playwright coverage +\n"
    "cross-tier doc updates + cross-repo notice update. Reference:\n"
    "docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/\n"
    "spec.md (Session 5 section).\n\n"
    "Prerequisites:\n"
    "  * Session 1 CLOSED — chatSessionId writer migration + per-set\n"
    "    lifecycle lock (Q5).\n"
    "  * Session 2 CLOSED — new_chat_id CLI + Claude SessionStart\n"
    "    invoker session_id pass-through (Q1).\n"
    "  * Session 3 CLOSED — signalKind enum + Codex config-toml\n"
    "    watcher RETIRED (D1).\n"
    "  * Session 4 CLOSED — Takeover UX modal/CLI prompt (Q3) +\n"
    "    watcher-inventory convention test (Q7).\n\n"
    "Audit-locked verdicts the docs must reflect (cumulative):\n\n"
    "  * Q1 chatSessionId source — Claude Code: hook-payload\n"
    "    session_id; all others: new_chat_id CLI.\n"
    "  * Q3 Takeover UX — modal in IDE; CLI prompt in terminal; toast\n"
    "    secondary only.\n"
    "  * Q4 chatSessionId on close — cleared from session-state.json;\n"
    "    persisted in closeout_succeeded event payload alongside engine\n"
    "    + provider + (optional) model.\n"
    "  * Q5 Hybrid migration tolerance — explicit cross-process\n"
    "    serialization (shared per-set lifecycle lock).\n"
    "  * H4 holder identity — refined from `engine + provider` to\n"
    "    `engine + provider + chatSessionId`.\n"
    "  * Tolerant-on-read — prior block missing chatSessionId entirely\n"
    "    OR with key present and null both tolerated for engine+\n"
    "    provider matches; strict-on-write populates on first new\n"
    "    write.\n\n"
    "Layer-3 test posture: 5 pre-existing failures in\n"
    "session-sets-tree.spec.ts + multi-in-progress.spec.ts assert\n"
    "against the per-row accordion (`data-expandable`) + 'No signal'\n"
    "CTA that Set 034 retired; they are explicitly Session 6's scope\n"
    "to fix per the spec (Session 6 step 5 — 'Layer-3 Playwright\n"
    "update' replaces the /No signal/ assertion + the orphaned\n"
    ".grey-gauges CSS sweep). Out of scope for Session 5.\n"
)


VERIFICATION_ASKS = (
    "Specific things to check:\n\n"
    "1. Layer-3 spec correctness — chatsessionid-takeover.spec.ts:\n"
    "   * Three tests exercise the right boundary? (a) chatSessionId-\n"
    "     mismatch refusal with EXIT_CHECKOUT_CONFLICT (4) + both\n"
    "     chatSessionIds named in stderr + the `chatSessionId=<value>`\n"
    "     composite label format; (b) --force handoff updates state\n"
    "     to new chat AND writer log has both IDs + session=N +\n"
    "     force-override + ISO timestamp; (c) same-chat re-attach\n"
    "     preserves checkedOutAt and bumps lastActivityAt.\n"
    "   * Does the spec correctly stay at the process boundary (not\n"
    "     drive the VS Code modal directly)? Per the established\n"
    "     pattern in checkout-conflict.spec.ts the modal is acknowl-\n"
    "     edged-brittle and the Layer-2 suite covers it; Layer-3 is\n"
    "     the writer-side end-to-end the modal's Take Over button\n"
    "     ultimately hits.\n"
    "   * homeOverride pattern is used correctly (HOME + USERPROFILE\n"
    "     both set so the writer log lands in tmpdir, not the dev's\n"
    "     real home)?\n\n"
    "2. Layer-3 spec correctness — chatsessionid-missing-tolerance.spec.ts:\n"
    "   * Three tests cover the three branches? (a) legacy state\n"
    "     (chatSessionId key ABSENT — verified via `'chatSessionId'\n"
    "     in orchestrator === false` sanity check) tolerates new chat\n"
    "     + populates strictly; (b) Set-036 null state (chatSessionId\n"
    "     key present, value null — verified via `.toBeNull()`)\n"
    "     tolerates + populates strictly; (c) post-population, a\n"
    "     different chatSessionId is refused with exit 4 + both IDs\n"
    "     in stderr + state unchanged.\n"
    "   * Does seedOrchestratorBlock correctly produce the three\n"
    "     shapes (omitted-key / null-value / string)? The 'in' check\n"
    "     on the overrides distinguishes omitted from explicit-null;\n"
    "     the post-spread delete is the safety net so an accidental\n"
    "     default key doesn't slip in.\n\n"
    "3. Layer-3 spec correctness — new-chat-id-cli-flow.spec.ts:\n"
    "   * Three tests cover (a) plain-mode UUID v4 emission against\n"
    "     a strict regex; (b) minted UUID flows through $CHAT_SESSION_ID\n"
    "     env into orchestrator.chatSessionId when start_session is\n"
    "     invoked WITHOUT --chat-session-id (env-fallback branch);\n"
    "     (c) idempotency — a second mint in an env that already\n"
    "     carries $CHAT_SESSION_ID re-emits the same value.\n"
    "   * REPO_ROOT derivation is correct (5 `..` hops from\n"
    "     src/test/playwright/ to the repo root, matching\n"
    "     electronLaunch.ts's EXTENSION_ROOT (3 hops) + REPO_ROOT\n"
    "     (2 more) chain).\n"
    "   * The local _filteredEnv helper mirrors electronLaunch's\n"
    "     hygiene without unnecessarily widening the exported API\n"
    "     surface for a single caller.\n"
    "   * UUID v4 regex correctly enforces the version (4-prefix) +\n"
    "     variant (8/9/a/b) nibbles? `/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i`.\n\n"
    "4. electronLaunch.ts helper extensions:\n"
    "   * attemptStartSession's new chatSessionId opt: null vs string\n"
    "     vs undefined behavior is correct? (`typeof === 'string'`\n"
    "     gate means null does NOT push --chat-session-id, which is\n"
    "     the intended fall-through-to-env behavior). The empty\n"
    "     string CLI value (which would otherwise look like a no-op)\n"
    "     would now push --chat-session-id '' to the writer — is\n"
    "     that the right call given start_session's documented\n"
    "     'empty string explicitly clears env' branch?\n"
    "   * seedOrchestratorBlock's chatSessionId distinction:\n"
    "     - overrides has no chatSessionId key → key absent on disk\n"
    "       (legacy shape)\n"
    "     - overrides has chatSessionId: null → key present, value\n"
    "       null (Set 036 no-ID write)\n"
    "     - overrides has chatSessionId: 'abc' → key present, value\n"
    "       string\n"
    "     The post-spread delete only fires on the 'no key in\n"
    "     overrides' branch, so the other two shapes survive\n"
    "     intact. Confirm.\n"
    "   * Are existing callers (checkout-conflict.spec.ts,\n"
    "     multi-in-progress.spec.ts, etc.) backward-compatible?\n"
    "     They omit chatSessionId from overrides, so the post-spread\n"
    "     delete is a no-op and the resulting block matches the\n"
    "     pre-Session-5 shape.\n\n"
    "5. session-state-schema.md doc accuracy:\n"
    "   * JSON shape correctly lists chatSessionId with type\n"
    "     `string | null`?\n"
    "   * Field table includes chatSessionId in the orchestrator-\n"
    "     row description?\n"
    "   * H4 paragraph refined to `engine + provider + chatSessionId`\n"
    "     with the discriminator explanation (two distinct chats on\n"
    "     same engine + provider are different holders)?\n"
    "   * chatSessionId source paragraph correctly differentiates\n"
    "     Claude Code (hook payload) from all-other-orchestrators\n"
    "     (new_chat_id CLI)?\n"
    "   * Tolerant-on-read paragraph covers BOTH the key-absent and\n"
    "     key-present-null branches with the strict-on-write contract?\n"
    "   * H3 refusal paragraph mentions the TTY takeover prompt as\n"
    "     the inline CLI mirror of the extension modal?\n"
    "   * Force-override paragraph notes the writer log carries both\n"
    "     chatSessionIds?\n"
    "   * Per-set lifecycle lock paragraph covers the dual-acquire\n"
    "     contract + 30s poll for start_session + exit codes (5 for\n"
    "     start, 3 for close)?\n"
    "   * Block-null invariant paragraph extended to note\n"
    "     chatSessionId clears with the rest of the block?\n"
    "   * Mid-set worked example shows a populated chatSessionId?\n\n"
    "6. ai_router/docs/close-out.md accuracy:\n"
    "   * Section 0 close-side protocol table includes the\n"
    "     orchestrator-clear row?\n"
    "   * Section 0 closeout_succeeded paragraph correctly lists the\n"
    "     four Q4 payload fields (chatSessionId, engine, provider,\n"
    "     model) AND the legacy-degradation behavior (no orchestrator\n"
    "     block → fields omitted, not emitted as empty strings)?\n"
    "   * Section 2 'Orchestrator check-in' paragraph notes that the\n"
    "     chatSessionId lives inside the orchestrator block (no\n"
    "     separate field-level wipe needed)?\n"
    "   * Section 3 step 9 mark_session_complete bullet notes the\n"
    "     payload snapshot ordering (taken BEFORE the block-clear so\n"
    "     the payload reflects the released holder)?\n"
    "   * Section 4 stranded-checkout paragraph extended to cover\n"
    "     stale chatSessionId case + writer log composite line\n"
    "     including both chat-IDs + TTY takeover prompt as inline\n"
    "     mirror?\n\n"
    "7. docs/ai-led-session-workflow.md accuracy:\n"
    "   * 'Orchestrator check-out / check-in (Set 033)' subsection:\n"
    "     - Holder identity now triple (engine + provider +\n"
    "       chatSessionId)?\n"
    "     - chatSessionId source paragraph (Claude Code hook /\n"
    "       new_chat_id CLI for everyone else)?\n"
    "     - H3 refusal paragraph mentions TTY takeover prompt?\n"
    "     - Tolerant-on-read paragraph covers both branches?\n"
    "     - Force-override writer log mentions both chatSessionIds?\n"
    "     - closeout_succeeded Q4 payload note?\n"
    "     - Per-set lifecycle lock paragraph (Set 036 Q5)?\n"
    "     - Tier symmetry: Lightweight humans paste their\n"
    "       new_chat_id-generated UUID into the chatSessionId field?\n\n"
    "8. docs/cross-repo-checkout-notice.md update:\n"
    "   * Header notes the Set 036 update + diff-based swap guidance\n"
    "     for consumers that already pasted the Set 033 version?\n"
    "   * Version numbers bumped to dabbler-ai-router 0.7.0 +\n"
    "     extension 0.19.0?\n"
    "   * H4 holder identity triple + chatSessionId discriminator\n"
    "     explanation?\n"
    "   * chatSessionId source by orchestrator (Claude Code\n"
    "     automatic; others via new_chat_id)?\n"
    "   * Refusal example carries chat-id?\n"
    "   * Resolution paths include the takeover modal / CLI prompt?\n"
    "   * Tolerant-on-read paragraph?\n"
    "   * Close-out clears chat-id with block + closeout_succeeded\n"
    "     Q4 payload note?\n"
    "   * Per-set lifecycle lock paragraph?\n"
    "   * Lightweight tier reminder mentions new_chat_id paste?\n"
    "   * 'Notes for the paster' updated for the swap path?\n\n"
    "9. Cross-tier doc/code drift check — anywhere a doc claim\n"
    "   contradicts the actual code shipped in Sessions 1-4?\n"
    "   Specifically:\n"
    "   * Does the close-out doc's payload field-list match what\n"
    "     close_session.py actually writes (Session 1 step 4 added\n"
    "     `_peek_orchestrator_identity` and the **-unpack into the\n"
    "     payload)?\n"
    "   * Does the workflow doc's 'TTY takeover prompt' description\n"
    "     match start_session.py's _is_interactive_tty + _prompt_takeover_choice\n"
    "     contract (both stdin AND stderr must be TTYs; empty input\n"
    "     defaults to cancel)?\n"
    "   * Does the schema doc's lifecycle-lock 30s poll claim match\n"
    "     close_lock.py's acquire_lock_with_timeout default?\n\n"
    "10. Out-of-scope check: confirm Session 5 did NOT touch the\n"
    "    session-sets-tree.spec.ts or multi-in-progress.spec.ts\n"
    "    failures (those are Session 6's planned scope). The git\n"
    "    diff should show only the four docs + electronLaunch.ts +\n"
    "    the three new spec files.\n\n"
    "If you find no substantive issues, say VERIFIED. Otherwise list\n"
    "each finding with severity (Blocker / Major / Minor) and\n"
    "file:line references — Sessions 6-7 will reference this verdict."
)


def _git_diff(path: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "HEAD", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text("utf-8")


def _run_round(label: str, bundle: str, asks: str) -> dict:
    context = f"{SESSION_CONTEXT}\n\n{asks}"
    content = (
        f"Review the following Session 5 work ({label}) against the\n"
        f"criteria above. Be specific about file paths and line numbers.\n\n"
        f"{bundle}"
    )
    # task_type="verification" + complexity_hint=60 → tier 2 → gemini-pro
    # per the Set 036 spec's "gemini-pro" routing note (the
    # cross-provider intent for a Claude orchestrator is preserved:
    # Anthropic → Google verifier). The session-verification task type
    # is hard-pinned to gpt-5-4 in router-config.yaml's
    # task_type_overrides, but OpenAI's TPM/RPM limit on gpt-5-4 has
    # been saturated since Session 4 (Round C also 429'd) and the
    # 15-min cooldown contract is insufficient per
    # [[feedback_split_large_verification_bundles]]. Using
    # "verification" (the unpinned variant of the same workflow shape)
    # routes by complexity tier and lands on gemini-pro at tier 2.
    result = ar.route(
        content=content,
        task_type="verification",
        complexity_hint=60,
        context=context,
        session_set="036-chatsessionid-and-watcher-scope-implementation",
        session_number=5,
    )
    dump_path = (
        REPO_ROOT
        / "docs"
        / "session-sets"
        / "036-chatsessionid-and-watcher-scope-implementation"
        / "verification-output"
        / f"round-{label.lower()}-session-5-result.json"
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
    # A1/A2 split — Round A is bundled large enough to trip OpenAI's
    # 429 after sustained reasoning workload from prior sessions (per
    # [[feedback_split_large_verification_bundles]]). Splitting into
    # code (A1) + docs (A2) halves the per-call payload while keeping
    # the verifier's coverage intact: A1 sees the executable surface
    # (Layer-3 specs + helper) and A2 sees the doc claims that surface
    # makes about chat-id behavior. Net coverage equals the original
    # Round A; per-call cost is roughly the same totals split across
    # two requests with a cooldown in between.
    parser.add_argument(
        "--round", choices=["A", "A1", "A2", "B"], default="A"
    )
    args = parser.parse_args()

    pw_dir = "tools/dabbler-ai-orchestration/src/test/playwright"

    # New spec files: full content (not in HEAD yet, so git diff is
    # all-additions; sending the file content is clearer for review).
    spec_takeover = _read(f"{pw_dir}/chatsessionid-takeover.spec.ts")
    spec_tolerance = _read(f"{pw_dir}/chatsessionid-missing-tolerance.spec.ts")
    spec_cli = _read(f"{pw_dir}/new-chat-id-cli-flow.spec.ts")

    # Modified helper + docs: git-diff hunks keep the bundle compact
    # while preserving the new prose in context (added lines are
    # prefixed `+`).
    diff_electron = _git_diff(f"{pw_dir}/electronLaunch.ts")
    diff_schema = _git_diff("docs/session-state-schema.md")
    diff_closeout = _git_diff("ai_router/docs/close-out.md")
    diff_workflow = _git_diff("docs/ai-led-session-workflow.md")
    diff_notice = _git_diff("docs/cross-repo-checkout-notice.md")

    if args.round == "A":
        label = "Round A: full post-implementation bundle"
        bundle = (
            f"=== NEW {pw_dir}/chatsessionid-takeover.spec.ts ===\n"
            f"{spec_takeover}\n\n"
            f"=== NEW {pw_dir}/chatsessionid-missing-tolerance.spec.ts ===\n"
            f"{spec_tolerance}\n\n"
            f"=== NEW {pw_dir}/new-chat-id-cli-flow.spec.ts ===\n"
            f"{spec_cli}\n\n"
            f"=== git diff {pw_dir}/electronLaunch.ts ===\n"
            f"{diff_electron}\n\n"
            f"=== git diff docs/session-state-schema.md ===\n"
            f"{diff_schema}\n\n"
            f"=== git diff ai_router/docs/close-out.md ===\n"
            f"{diff_closeout}\n\n"
            f"=== git diff docs/ai-led-session-workflow.md ===\n"
            f"{diff_workflow}\n\n"
            f"=== git diff docs/cross-repo-checkout-notice.md ===\n"
            f"{diff_notice}\n"
        )
        asks = VERIFICATION_ASKS
    elif args.round == "A1":
        label = "Round A1: Layer-3 specs + electronLaunch.ts helper extensions"
        bundle = (
            f"=== NEW {pw_dir}/chatsessionid-takeover.spec.ts ===\n"
            f"{spec_takeover}\n\n"
            f"=== NEW {pw_dir}/chatsessionid-missing-tolerance.spec.ts ===\n"
            f"{spec_tolerance}\n\n"
            f"=== NEW {pw_dir}/new-chat-id-cli-flow.spec.ts ===\n"
            f"{spec_cli}\n\n"
            f"=== git diff {pw_dir}/electronLaunch.ts ===\n"
            f"{diff_electron}\n"
        )
        asks = (
            "Focus on checks #1–#4 from the criteria list (Layer-3\n"
            "spec correctness for the three new specs + electronLaunch.ts\n"
            "helper extensions). The doc-update checks (#5–#9) and the\n"
            "out-of-scope check (#10) will be verified separately in\n"
            "Round A2; do NOT spend tokens on them here.\n\n"
        ) + VERIFICATION_ASKS
    elif args.round == "A2":
        label = "Round A2: cross-tier doc updates + cross-repo notice"
        bundle = (
            f"=== git diff docs/session-state-schema.md ===\n"
            f"{diff_schema}\n\n"
            f"=== git diff ai_router/docs/close-out.md ===\n"
            f"{diff_closeout}\n\n"
            f"=== git diff docs/ai-led-session-workflow.md ===\n"
            f"{diff_workflow}\n\n"
            f"=== git diff docs/cross-repo-checkout-notice.md ===\n"
            f"{diff_notice}\n"
        )
        asks = (
            "Focus on checks #5–#10 from the criteria list (cross-tier\n"
            "doc updates + cross-repo notice update + cross-tier\n"
            "doc/code drift check + out-of-scope confirmation). The\n"
            "Layer-3 spec checks (#1–#4) were verified separately in\n"
            "Round A1; do NOT re-litigate them here.\n\n"
        ) + VERIFICATION_ASKS
    else:
        # Round B template — populated only if Round A surfaces
        # must-fix items requiring a re-verify.
        label = "Round B: re-verify after Round A must-fix changes"
        bundle = (
            f"=== NEW {pw_dir}/chatsessionid-takeover.spec.ts (post-Round-A) ===\n"
            f"{spec_takeover}\n\n"
            f"=== NEW {pw_dir}/chatsessionid-missing-tolerance.spec.ts (post-Round-A) ===\n"
            f"{spec_tolerance}\n\n"
            f"=== NEW {pw_dir}/new-chat-id-cli-flow.spec.ts (post-Round-A) ===\n"
            f"{spec_cli}\n\n"
            f"=== git diff {pw_dir}/electronLaunch.ts (post-Round-A) ===\n"
            f"{diff_electron}\n\n"
            f"=== git diff docs/session-state-schema.md (post-Round-A) ===\n"
            f"{diff_schema}\n\n"
            f"=== git diff ai_router/docs/close-out.md (post-Round-A) ===\n"
            f"{diff_closeout}\n\n"
            f"=== git diff docs/ai-led-session-workflow.md (post-Round-A) ===\n"
            f"{diff_workflow}\n\n"
            f"=== git diff docs/cross-repo-checkout-notice.md (post-Round-A) ===\n"
            f"{diff_notice}\n"
        )
        asks = (
            "Round B: confirm the Round A findings are addressed.\n"
            "List any net-new issues only — do NOT re-litigate Round\n"
            "A findings themselves."
        )

    print(f"Running {label} ...")
    _run_round(args.round, bundle, asks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
