"""Round-B explicit cross-provider verification for Set 049 S5.

Per spec §5 S5: "Verification: Round A + Round B (final session)."

Round A was gates-only (close_session route() short-circuited under
runtime_mode default). Round B is an explicit cross-provider call
to validate the S5 close-out artifacts.

The session set is ALREADY CLOSED. This call is the after-the-fact
sanity check the spec requires; the verdict is recorded as a
session-review artifact for audit history.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_router import route
from ai_router.session_log import SessionLog


SESSION_SET = "docs/session-sets/049-orchestrator-coordination-removal"
SESSION_NUMBER = 5
REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    spec = read(f"{SESSION_SET}/spec.md")
    close_reason = read(f"{SESSION_SET}/s5-close-reason.md")
    disposition = read(f"{SESSION_SET}/disposition.json")
    change_log = read(f"{SESSION_SET}/change-log.md")
    uat_checklist = read(
        f"{SESSION_SET}/049-orchestrator-coordination-removal-uat-checklist.json"
    )
    claude_md = read("CLAUDE.md")
    workflow_md = read("docs/ai-led-session-workflow.md")
    ai_router_changelog = read("ai_router/CHANGELOG.md")
    ext_changelog = read("tools/dabbler-ai-orchestration/CHANGELOG.md")

    prompt = f"""# Set 049 Session 5 — Round-B Verification

You are reviewing the close-out artifacts of Set 049 Session 5 (the
final session of an audit-then-spec rip-out set). The set has
already passed close_session gate checks; this is an explicit
Round-B cross-provider review per spec §5 S5.

## Spec (Set 049 S5 scope is at §5)

{spec}

## Session 5 close-reason (what S5 produced)

{close_reason}

## Session 5 disposition

{disposition}

## Set 049 change-log.md (per-session narrative)

{change_log}

## Rip-out UAT checklist

{uat_checklist}

## CLAUDE.md (full file)

{claude_md[:12000]}

[... CLAUDE.md continues; truncated at 12 KB for context budget ...]

## ai-led-session-workflow.md — the rewritten Orchestrator-identity section

The "Orchestrator check-out / check-in (Set 033)" section was
replaced. Snippet of the rewrite at section "Orchestrator identity
and concurrency (post-Set-049)" (search the workflow file):

{_extract_section(workflow_md, "Orchestrator identity and concurrency (post-Set-049)")}

## ai_router CHANGELOG (recent entries)

{ai_router_changelog[:8000]}

## Extension CHANGELOG (recent entries)

{ext_changelog[:8000]}

## Your job

Evaluate Session 5's close-out artifacts against the spec §5 S5
directives:

1. **CLAUDE.md** rewrite — was the "Hard-coordination enforcement
   (Sets 033 / 036) is OFF by default" section retired entirely?
   Was the version walk updated correctly (v0.24.0 added, prior
   versions demoted)?
2. **docs/ai-led-session-workflow.md** Step 6 / Step 8 references —
   were coordination-layer references cleanly retired?
3. **UAT checklist** — does it cover the spec §5 S5 scope items
   (clean session start/close on Full and Lightweight, new
   orchestrator-block shape, migrator dry-run + apply on a fixture
   v3 file, accept-with-warning behavior on `--chat-session-id`,
   Explorer surface free of harvest badges / conflict pills,
   writer-bypass detector still fires on a synthetic bypass,
   close_session and start_session both clean on cancel/restore)?
4. **PyPI version bump** — pyproject.toml + __init__.py +
   CHANGELOG entry consistent? Backfill of [0.8.0]/[0.9.0]/[0.10.0]
   accurate against extension CHANGELOG mirrors?
5. **Marketplace version bump** — package.json + CHANGELOG entry
   consistent?
6. **change-log.md** — accurate per-session narrative with commit
   references?

Flag any:
- Factual errors (wrong commit hash, wrong version number, wrong
  test count, wrong file path).
- Inconsistencies (e.g., CLAUDE.md says one thing, change-log.md
  says another).
- Spec deviations not documented in s5-close-reason.md.
- Important omissions (a directive in spec §5 S5 that the close-out
  artifacts don't address).

Be terse. Use the VERIFIED / ISSUES FOUND format from
ai_router/prompt-templates/verification.md.
"""

    result = route(
        content=prompt,
        task_type="session-verification",
        complexity_hint=70,
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )

    # RouteResult is a dataclass in ai_router/__init__.py with fields:
    # content, model_name, model_id, tier, input_tokens, output_tokens,
    # cost_usd, total_cost_usd, complexity_score, escalated,
    # escalation_history, elapsed_seconds, truncated, verification.
    # Write content to disk IMMEDIATELY before doing anything else.
    review_path = (
        REPO_ROOT / SESSION_SET / "session-reviews" / "session-005-round-2.md"
    )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(result.content, encoding="utf-8")

    snapshot = {
        "model_name": result.model_name,
        "model_id": result.model_id,
        "tier": result.tier,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost_usd": result.cost_usd,
        "total_cost_usd": result.total_cost_usd,
        "complexity_score": result.complexity_score,
        "escalated": result.escalated,
        "escalation_history": [list(t) for t in result.escalation_history],
        "elapsed_seconds": result.elapsed_seconds,
        "truncated": result.truncated,
        "verification_present": result.verification is not None,
    }
    snapshot_path = REPO_ROOT / SESSION_SET / "round-b-route-result.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    # SessionLog.save_session_review is the canonical writer — also call
    # it so the audit history shows the standard path.
    log = SessionLog(SESSION_SET)
    try:
        log.save_session_review(
            session_number=SESSION_NUMBER,
            review_text=result.content,
            round_number=2,
        )
    except Exception as exc:
        print(f"SessionLog.save_session_review failed: {exc!r}")

    # Print summary using ASCII only (Windows cp1252 console can't handle
    # arrows in user content).
    print(f"Wrote Round-B review to {review_path}")
    print(f"Wrote RouteResult snapshot to {snapshot_path}")
    print(f"Round-B cost: ${snapshot['cost_usd']} | model: {snapshot['model_name']}")
    print(f"Tokens in/out: {snapshot['input_tokens']}/{snapshot['output_tokens']}")
    if snapshot["truncated"]:
        print("WARNING: verifier response truncated.")


def _extract_section(text: str, heading: str) -> str:
    """Extract the markdown section starting at `heading` until the next ###."""
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if heading in line and line.lstrip().startswith("###"):
            inside = True
            out.append(line)
            continue
        if inside:
            if line.lstrip().startswith("### ") and heading not in line:
                break
            out.append(line)
    return "\n".join(out)[:8000]


if __name__ == "__main__":
    main()
