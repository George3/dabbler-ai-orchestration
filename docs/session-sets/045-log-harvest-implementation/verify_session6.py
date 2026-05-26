"""Session 6 verification driver — Round A.

S6 is the release-and-documentation close-out of Set 045:
  - new top-level CONTRIBUTING.md (rebuild-trap note + test-layer guide)
  - new 045 UAT checklist (27 ad-hoc scenarios across 6 functional areas)
  - new change-log.md (Set 045 summary)
  - new docs/cross-repo-harvest-notice.md
  - version bumps: extension 0.20.0 -> 0.21.0; ai_router 0.7.0 -> 0.8.0
  - CHANGELOG.md [0.21.0] entry under [Unreleased]
  - CLAUDE.md extension-versioning block promotion

This Round A bundle covers exactly those artifacts (no joiner /
parser / extension TS changes in S6 -- those landed in S2-S5 and
were verified there). Verifier asked to focus on: are the
release docs operator-accurate; does the UAT checklist cover
the surface; do the change-log + CHANGELOG + CLAUDE.md
version-walk descriptions match the actual S1-S5 shipped
surface; is the cross-repo notice paste-ready.

Per memory feedback_split_large_verification_bundles: keep
the bundle scoped.
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


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 045 / Session 6 -- Round A verification (release session).

S6 is the close-out of Set 045 (log-harvest implementation).
The architectural commitments from Set 044 proposal v1 were locked
before S1 and were NOT relitigated within Set 045. Sessions 1-5
shipped the spike + joiner + wrapper + Claude parser + narration
template + Explorer surface; each was verified at the time
(5 VERIFIED + 1 REJECTED-then-fixed across S1-S5; cumulative
routed verification spend $0.3177 of $5 NTE).

S6 ships only release-and-documentation artifacts:

  1. CONTRIBUTING.md (NEW at repo root) -- per-test-layer scope
     guidance + rebuild-trap note (invoke through
     `npm run test:playwright`, not bare `npx playwright test`).
     Flagged by S5 verifier as a deferred nice-to-have.

  2. 045 UAT checklist -- 27 ad-hoc scenarios across 6 functional
     areas (dabbler-launch wrapper, Joiner CLI, Narration templates,
     Explorer signal badges, Explorer conflict pills,
     Missing-dependency degradation, Documentation). Each item has
     dual schema fields: `Passes`+`Feedback` (UAT Checklist Editor
     canonical) AND `Result: "pending"` (Dabbler extension parser's
     pending counter).

  3. change-log.md (NEW) -- per-session summaries +
     verification-round detail + actuals vs forecast. Contains
     two placeholder tokens ({{S6_VERIFICATION_COST}},
     {{S6_VERIFICATION_VERDICT}}, {{TOTAL_COST}}) the orchestrator
     fills in after this Round A returns.

  4. cross-repo-harvest-notice.md (NEW) -- paste-in CLAUDE.md
     snippet for the three consumer repos (parallel structure to
     the existing cross-repo-checkout-notice.md).

  5. Version bumps:
     - tools/dabbler-ai-orchestration/package.json: 0.20.0 -> 0.21.0
     - pyproject.toml: dabbler-ai-router 0.7.0 -> 0.8.0
     - tools/dabbler-ai-orchestration/CHANGELOG.md: new [0.21.0]
       section under [Unreleased]
     - CLAUDE.md: version-walk block promotion (0.20.0 -> Previous;
       new 0.21.0 Current entry summarizing Set 045)

THREE S5-deferred Round-A recommendations were considered at S6
start. The operator picked option 1 ONLY:
  - FOLD IN: CONTRIBUTING.md rebuild-trap note (doc-only, ~5 min)
  - DEFER: singleton HarvestService refactor (no current pain point)
  - DEFER: missing-events-ledger ConflictKind (audit-touching;
    would change Set 044-locked spec section 3 without an audit pass)

Release posture: publish PyPI + Marketplace after VERIFIED Round
A/B, operator-gated.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This is a release-session verification. The S6
surface is doc + version-bump only -- no joiner / parser /
extension TypeScript changes. The shipped surface S1-S5 was
verified at the time it landed. Focus on whether the release
docs accurately describe that surface and whether the UAT
checklist covers it.

ROUND A focus questions:

  Q1: change-log.md fidelity. Does the per-session summary
  match the actual file changes shipped? Are there material
  ship-list gaps (artifacts shipped but not mentioned, or
  artifacts described but not actually present)? Pay particular
  attention to:
    - S3 ('Round B fixes' deferral of normalize_engine breadth
      to joiner-spec.md section 9 row 5).
    - S5 ('Round A must-fix #1 + #2 resolutions: CSS custom
      properties + missing-dep toast).
    - S6 'What did not ship' deferred-items list.

  Q2: CHANGELOG.md [0.21.0] entry. Does it accurately describe
  the user-facing surface? Are the API descriptions
  (HarvestService, regenerateNarrationTemplates, etc.)
  recognizable to an operator who installs 0.21.0 and opens the
  Session Sets view?

  Q3: CLAUDE.md version-walk. Is the 0.21.0 Current block honest
  about what shipped? Is the 0.20.0 promotion to Previous
  preserving enough detail (Set 036 chatSessionId surface) for a
  future reader to walk the version history?

  Q4: UAT checklist coverage. Does the 27-scenario checklist
  cover the user-visible surface comprehensively? Are there
  obvious user paths NOT covered? Are any scenarios infeasible
  (require state that's hard to construct)? Schema sanity --
  do the dual `Passes` + `Result` fields make sense?

  Q5: cross-repo-harvest-notice.md paste-readiness. If a paster
  drops the snippet into a fresh consumer CLAUDE.md without any
  surrounding context, does it stand alone? Are the external
  GitHub links well-formed? Is the Option 1 / Option 2 framing
  clear enough that a new consumer can pick one?

  Q6: CONTRIBUTING.md. Is the test-layer guidance accurate (Layer
  1 pytest scope, Layer 2 npm run test:unit scope, Layer 3
  Playwright scope + rebuild trap)? Are any command snippets
  wrong (e.g., wrong directory, wrong flags)?

  Q7: Anything missing? Any release-touching artifact you'd
  expect for a dual-registry session-set close-out that's NOT
  in the bundle?

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have
    notes worth applying in-flight.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(REPO_ROOT / "CONTRIBUTING.md"),
        read_file(
            SET_DIR / "045-log-harvest-implementation-uat-checklist.json"
        ),
        read_file(SET_DIR / "change-log.md"),
        read_file(REPO_ROOT / "docs" / "cross-repo-harvest-notice.md"),
        read_file(
            REPO_ROOT / "tools/dabbler-ai-orchestration/CHANGELOG.md"
        ),
        read_file(REPO_ROOT / "CLAUDE.md"),
        read_file(REPO_ROOT / "pyproject.toml"),
        read_file(
            REPO_ROOT / "tools/dabbler-ai-orchestration/package.json"
        ),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-006-route-result.json"

    print(f"\n{'='*60}\n[Round A] sending to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=FOCUS_PROMPT,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE START ---\n{bundle}\n--- BUNDLE END ---",
        session_set="045-log-harvest-implementation",
        session_number=6,
    )
    result_dict = dump_route_result_to_json(result)
    out_path.write_text(
        json.dumps(result_dict, default=str, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"Provider: {result_dict.get('provider')}")
    print(f"Model: {result_dict.get('model') or result_dict.get('model_name')}")
    print(
        "Tokens: "
        f"in={result_dict.get('input_tokens', '?')}, "
        f"out={result_dict.get('output_tokens', '?')}"
    )
    print(f"Cost: ${result_dict.get('cost_usd', result_dict.get('cost', '?'))}")
    print(f"Latency: {result_dict.get('latency_ms', '?')} ms")
    text = (
        result_dict.get("response")
        or result_dict.get("text")
        or result_dict.get("content")
    )
    if isinstance(text, str):
        print(f"\n--- VERIFIER OUTPUT ---\n{text}\n--- end ---")
        verdict_path = out_dir / "session-006.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
