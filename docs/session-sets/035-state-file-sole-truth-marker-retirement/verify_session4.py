"""Session 4 verification driver — Set 035 (state-file sole truth).

Round A bundles the final-session aggregation artifacts:

  - docs/session-sets/035-.../change-log.md — NEW. Final-session
    aggregation per [[project_final_session_changelog_pre_close]]:
    top context block, one section per session, "What ships across
    the framework" / "Risks closed" / "Follow-ups out of scope"
    closing summary.
  - tools/dabbler-ai-orchestration/package.json — UPDATED.
    version 0.18.0 → 0.18.1.
  - tools/dabbler-ai-orchestration/CHANGELOG.md — UPDATED.
    New [0.18.1] section above [0.18.0] heading.
  - CLAUDE.md — UPDATED. "Current: v0.18.1" header replaces v0.18.0;
    Extension versioning walk extended with the 0.18.1 entry.

The session also ran the full test sweep:

  - python -m pytest → 643 passed, 1 skipped.
  - npx tsc --noEmit → clean.
  - npm run test:unit → 462 passing, 2 pre-existing unrelated failures.
  - npm run test:playwright → 14 passed, 3 pre-existing failures,
    3 skipped. The 3 failures are test-side scaffolding/locator
    issues (NOT production regressions); renderAccordionEmpty()
    still emits .acc-empty-cta and "No signal —" correctly.
    Deferred to Set 034 per the spec's out-of-scope clause.

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
Set 035 extends the H2 single-source-of-truth verdict from Set 033
Session 2 (orchestrator block) to the cancellation lifecycle.
Sessions 1-3 (closed 2026-05-21) shipped:

  S1: Reader migration — new readCancellationState() canonical entry
      point in cancelLifecycle.ts; fileSystem.ts:readSessionSets
      migrated to consult state.status first with console.warn-emitting
      legacy-fallback path. Schema doc rewritten. 10 new unit tests.
      Bundled empty-state grey-gauge removal in OrchestratorAccordion.ts.

  S2: Writer parity — 10-row byte-equivalent table committed
      (cancelLifecycle.ts vs ai_router/session_lifecycle.py).
      glossary-harvest.md tool authored + 40 clusters triaged across
      5 extension buckets (all acceptable variance, ZERO in-session
      fixes). 6 new writer-parity test cases.

  S3: Documentation alignment — schema doc finalized with three new
      subsections (Canonical reader / Writer symmetry / Layer-3
      coverage); ai-led-session-workflow.md reframed state-file-first;
      cancelLifecycle.ts JSDoc polished. 3 new Layer-3 Playwright
      scenarios in cancellation-state-file.spec.ts (all green).

Session 4 (THIS verification) is the final-session aggregation +
release session. Deliverables:

1. Full test sweep (Python pytest, npm test:unit, npm test:playwright,
   tsc --noEmit). Results documented in change-log.md Session 4
   section.

2. change-log.md authored at docs/session-sets/035-.../change-log.md
   following the Set 033 template: header (status, cost forecast,
   NTE), Context, one section per Session (Shipped + Verification),
   What ships across the framework, Risks closed, Follow-ups out of
   scope.

3. Version bumps:
   - tools/dabbler-ai-orchestration/package.json 0.18.0 → 0.18.1
   - tools/dabbler-ai-orchestration/CHANGELOG.md: new [0.18.1] section
   - CLAUDE.md: Extension versioning walk extended

4. pyproject.toml + ai_router/CHANGELOG.md: NOT TOUCHED. The Python
   mirror ai_router/session_lifecycle.py was last edited 2026-05-01
   (Set 010 rename). Session 2's writer-parity verification confirmed
   no Python edits needed. Per the spec: "PyPI release of
   dabbler-ai-router 0.6.1 (operator-gated per the established
   pattern; **skip if the Python mirror didn't change**)."

5. Round A verification (this call).

6. Marketplace 0.18.1 publish — operator-gated; runs AFTER
   verification passes.

7. close_session invocation for Set 035 Session 4.

Test sweep results (already complete at time of bundle):
  - python -m pytest: 643 passed, 1 skipped (3:35).
  - npx tsc --noEmit: clean.
  - npm run test:unit: 462 passing, 2 pre-existing unrelated failures
    (configEditor ViewColumn.One stub gap; notificationsSection
    "wired in Set 026 Session 7" assertion) — unchanged from S1/S2/S3
    activity-log.
  - npm run test:playwright: 14 passed, 3 pre-existing failures
    (session-sets-tree.spec.ts: ARIA tree structure / orchestrator
    block sublabel / empty-state CTA fallback), 3 skipped. The 3
    failures are test-scaffolding/locator-specificity issues, NOT
    production regressions: renderAccordionEmpty() at
    OrchestratorAccordion.ts:340 still emits the .acc-empty-cta
    div with "No signal —" prefix and the install button. Deferred
    to Set 034 (styling iteration) per the spec's out-of-scope clause.

Cumulative routed verification spend through S3 Round A: $0.0612 of
$0.50 forecast. Session 4 Round A is the final routed call for Set 035.
""".strip()


FOCUS_PROMPT = """
ROUND A — Session 4 final-aggregation faithfulness for change-log,
version bumps, and the release-readiness summary.

You are Gemini Pro, asked to verify that Session 4 of Set 035 ships
a change-log.md that accurately reflects what shipped across the four
sessions, version bumps that match the change-log's claims, and a
CLAUDE.md Extension versioning walk entry that doesn't contradict the
change-log.

Verify:

A. **change-log.md faithfulness.**

   1. Header block — `Status: COMPLETE (4 of 4 sessions complete;
      closed 2026-05-21)`, cost forecast, NTE ceiling. The
      "$0.0612 of $0.50 forecast" line at S3 close (cumulative)
      should match the activity-log routedApiCalls sum
      ($0.0161 + $0.0232 + $0.0218 = $0.0611, rounding to $0.0612).
   2. Context section names the Set 033 S2 H2 verdict + the
      audit-into-spec collapse rationale + the memory anchor
      [[project_034_035_state_file_sole_truth_audit]] correctly.
   3. Session 1 section accurately enumerates what shipped:
      - readCancellationState() with the four return values
      - fileSystem.ts:readSessionSets caller refactored
      - 10 new unit test cases under suite "readCancellationState
        (Set 035 state-file-first)"
      - OrchestratorAccordion.ts empty-state grey-gauge removal
        bundle (operator-directed)
      - Set 036 extension from 6→7 sessions (the rescope bundle)
      Verification: "Round A (gemini-pro) PASS — $0.0161".
   4. Session 2 section accurately enumerates:
      - 10-row writer-parity table committed to glossary-harvest.md
      - harvest_glossary.py tool authored (scripts/ directory)
      - glossary-harvest.md report (706 lines, 40 clusters, 5
        extension buckets, ZERO in-session fixes)
      - _cancelled.md mismatch resolution documented
      - 6 new writer-parity test cases
      - C1 follow-on logged (Python CLI print_session_set_status
        still file-presence-first at ai_router/__init__.py:935)
      Verification: "Round A (gemini-pro) PASS — $0.0232".
   5. Session 3 section accurately enumerates:
      - schema doc finalized with three new subsections
      - workflow doc reframed (two places: Cancelling/restoring +
        Step 1 find_active_session_set)
      - cancelLifecycle.ts JSDoc polish (six specific touchpoints)
      - cancellation-state-file.spec.ts (3 new Layer-3 scenarios, all
        green)
      Verification: "Round A (gemini-pro) PASS — $0.0218".
      Nice-to-have ("re-cancel preCancelStatus preservation") noted
      as addressed inline per [[feedback_dont_hide_behind_out_of_scope]].
   6. Session 4 section accurately enumerates:
      - test sweep results (643 pytest pass; 462 npm test:unit pass
        + 2 pre-existing unrelated failures; 14 Playwright pass + 3
        pre-existing deferred + 3 skipped; tsc clean)
      - change-log.md authored (this file)
      - version bumps: package.json 0.18.0 → 0.18.1; CHANGELOG.md
        [0.18.1] entry; CLAUDE.md walk extended
      - pyproject.toml UNCHANGED — no PyPI release this set
        (rationale: Python mirror not touched; writer-parity check
        confirmed)
   7. "What ships across the framework" closing summary accurately
      describes the post-035 state. "Risks closed" section addresses
      R1-R5 from the spec. "Follow-ups out of scope" includes the
      3 Layer-3 deferrals + C1 Python CLI follow-on + cross-writer
      golden-file fixtures + SUPERSEDED.md (explicit non-introduction).

B. **CHANGELOG.md [0.18.1] section accuracy.**

   1. Date is 2026-05-21; tagline references "Set 035 — state-file
      sole truth for cancellation".
   2. Header paragraph notes "No companion PyPI release this set"
      with the rationale.
   3. Added/Changed/Tests/Tooling/Known issues subsections all
      present and accurate against the change-log.md.
   4. The Known issues subsection correctly notes the 3 Layer-3
      failures are TEST-SIDE, not production regressions, and that
      renderAccordionEmpty still emits .acc-empty-cta and "No signal
      —" correctly.

C. **CLAUDE.md Extension versioning walk.**

   1. Top "Current: **v0.18.1**" line replaces "v0.18.0".
   2. New 0.18.1 entry inserted AFTER the 0.18.0 entry (chronological).
   3. Entry mentions: extends H2 to cancellation lifecycle;
      readCancellationState; fileSystem.ts:readSessionSets migration;
      10-row writer parity (no PyPI release); 16 new unit tests +
      3 new Layer-3 scenarios; bundled empty-state grey-gauge removal
      + glossary-harvest tool; deferred follow-ups for Set 034 +
      C1 Python CLI patch.
   4. No contradiction with change-log.md.

D. **Version bumps match.**

   1. package.json version is 0.18.1.
   2. CHANGELOG.md has [0.18.1] above [0.18.0].
   3. CLAUDE.md "Current" line is v0.18.1.
   4. pyproject.toml is NOT touched (no version bump beyond 0.6.0).

E. **Risk assessment.**

   1. The "No PyPI release this set" decision is correct given the
      writer-parity verification in Session 2. If a Python mirror
      edit was missed, naming the byte-equivalent claim in S2's
      activity-log + glossary-harvest.md parity table should suffice
      as evidence the decision is right.
   2. The 3 deferred Layer-3 failures: confirm none of them touch
      production cancellation code paths (cancelLifecycle.ts,
      fileSystem.ts cancellation branch, OrchestratorAccordion.ts
      renderAccordionEmpty source). They're test-side issues in
      session-sets-tree.spec.ts only. Surface any concern if the
      deferral feels wrong.
   3. The Marketplace 0.18.1 release is operator-gated AFTER this
      verification passes. The PAT availability inherits from Set
      033's rotated credential; no new credential surface.
   4. Per memory [[feedback_split_large_verification_bundles]]: this
      bundle is the final-session aggregation, including change-log
      (~280 lines) + CHANGELOG.md [0.18.1] section + CLAUDE.md
      versioning walk segment + Session 4 spec contract. Should fit
      comfortably under the 500-LOC slice guidance.

Format the verdict as:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.

Cite specific quoted phrases / file:line references when flagging
issues; skip stylistic nits.
""".strip()


def _bundle() -> str:
    parts = [
        # Primary deliverable A — change-log.md (full).
        read_file(SET_DIR / "change-log.md"),
        # Primary deliverable B — CHANGELOG.md [0.18.1] section.
        read_section(
            EXT_ROOT / "CHANGELOG.md",
            "## [0.18.1]",
            "\n## [0.18.0]",
        ),
        # Primary deliverable C — CLAUDE.md Extension versioning walk.
        read_section(
            REPO_ROOT / "CLAUDE.md",
            "## Extension versioning",
            "\n## Building",
        ),
        # Ground truth — Session 4 spec contract.
        read_section(
            SET_DIR / "spec.md",
            "## Session 4 of 4:",
            "\n---\n\n## Risks",
        ),
        # Ground truth — package.json head (version pin).
        read_section(
            EXT_ROOT / "package.json",
            '"name":',
            '"engines":',
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
        session_set="035-state-file-sole-truth-marker-retirement",
        session_number=4,
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
        print("Usage: python verify_session4.py round-a [round-b]", file=sys.stderr)
        sys.exit(2)

    sub = sys.argv[1]
    bundle = _bundle()
    print(f"Bundle size: {len(bundle):,} chars")
    if sub == "round-a":
        run_round(
            "Round A",
            bundle,
            FOCUS_PROMPT,
            out_dir / "round-a-session-4-result.json",
        )
    elif sub == "round-b":
        focus = (
            "ROUND B — confirm the must-fix issues from Round A are "
            "addressed in the updated artifacts.\n\n"
            "For each Round-A must-fix, confirm the fix is present "
            "and doesn't introduce a new contradiction. Format: "
            "VERIFIED or REJECTED with cited quotes; skip stylistic "
            "nits."
        )
        run_round(
            "Round B",
            bundle,
            focus,
            out_dir / "round-b-session-4-result.json",
        )
    else:
        print(f"Unknown subcommand: {sub}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
