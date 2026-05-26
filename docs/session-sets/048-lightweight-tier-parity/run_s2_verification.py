"""Set 048 Session 2 end-of-session cross-provider verification.

Bundles the production code shipped in S2 (Commits A-D) for review by a
cross-provider verifier. Per feedback_split_large_verification_bundles
the bundle is held to ~700 LOC of source code (excluding tests, which
are reviewed via passing-status only).

Output files alongside this script: s2-verification-prompt.md (the
full prompt sent), s2-verification-transcript.md (route + verify
responses), s2-verification-result.json (verdict + cost summary).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402

SESSION_SET = "048-lightweight-tier-parity"
SESSION_NUMBER = 2


def _read(p: str) -> str:
    return (REPO_ROOT / p).read_text(encoding="utf-8")


def _diff(old_lines: str, new_lines: str) -> str:
    """Crude inline-diff context for diff blocks (not a real diff)."""
    return f"NEW:\n```\n{new_lines}\n```"


def _build_prompt() -> str:
    spec_config_py = _read("ai_router/spec_config.py")
    runtime_mode_py = _read("ai_router/runtime_mode.py")
    suggestion_disposition_py = _read("ai_router/suggestion_disposition.py")
    types_ts_excerpt = _read("tools/dabbler-ai-orchestration/src/types.ts")

    # Extract just the Set 048 sections of close_session.py + __init__.py
    # for context. Full files are too large.
    close_session_py = _read("ai_router/close_session.py")
    init_py = _read("ai_router/__init__.py")

    # Pull just the close_session run() changes and __init__ stub helpers.
    cs_changes = (
        "Three changes to ai_router/close_session.py:\n\n"
        "1. New --no-router and --accept-suggestions flags in _build_parser():\n\n"
        "    p.add_argument('--no-router', action='store_true', dest='no_router', ...)\n"
        "    p.add_argument('--accept-suggestions', action='store_true', dest='accept_suggestions', ...)\n\n"
        "2. main() resolves runtime_mode at entry-point start (before run(args)):\n\n"
        "    from runtime_mode import resolve_no_router_mode\n"
        "    resolve_no_router_mode(\n"
        "        cli_flag=bool(getattr(args, 'no_router', False)),\n"
        "        session_set_dir=Path(args.session_set_dir) if args.session_set_dir else None,\n"
        "    )\n\n"
        "3. run() integration: \n"
        "   (a) manual_attestation block: if args.no_router and not args.manual_verify,\n"
        "       auto-supply a stock attestation when no --reason-file (so the audit\n"
        "       trail records Lightweight-tier intent).\n"
        "   (b) method resolution: args.no_router branch sets method='manual'.\n"
        "   (c) NEW soft-gate check after gate_checks pass + before state flip:\n"
        "       fires only under --no-router; reads external-verification.md;\n"
        "       branches on --accept-suggestions / TTY / non-TTY; aborts with\n"
        "       result='aborted_at_soft_gate' + emits closeout_failed event\n"
        "       on TTY non-affirmative answer.\n\n"
        "Full close_session.py is ~1700 lines; only the changes above are new\n"
        "in S2. The pre-existing flow (gate_checks, lock, event emission,\n"
        "state flip) is unchanged.\n"
    )

    init_changes = (
        "Two changes to ai_router/__init__.py:\n\n"
        "1. New module-level stub builders + constants:\n\n"
        "    _NO_ROUTER_MODEL = 'no-router-mode'\n"
        "    _NO_ROUTER_VERDICT = 'no_router_skipped'\n\n"
        "    def _build_no_router_route_stub() -> RouteResult: ...\n"
        "    def _build_no_router_verification_stub(generator_model: str) -> VerificationResult: ...\n\n"
        "2. route() and verify() prologues short-circuit when no-router-mode is active:\n\n"
        "    def route(content, ...):\n"
        "        try:\n"
        "            from runtime_mode import is_no_router_mode\n"
        "            if is_no_router_mode():\n"
        "                return _build_no_router_route_stub()\n"
        "        except Exception:\n"
        "            pass\n"
        "        _init()  # original code resumes\n"
        "        ...\n\n"
        "    def verify(route_result, ...):\n"
        "        try:\n"
        "            from runtime_mode import is_no_router_mode\n"
        "            if is_no_router_mode():\n"
        "                return _build_no_router_verification_stub(\n"
        "                    generator_model=route_result.model_name)\n"
        "        except Exception:\n"
        "            pass\n"
        "        _init()  # original code resumes\n"
        "        ...\n"
    )

    return (
        "# Set 048 Session 2 cross-provider verification request\n\n"
        "## Context\n\n"
        "Set 048 Session 2 ships the Lightweight-tier `--no-router` mode "
        "infrastructure. The audit-locked spec is at "
        "`docs/session-sets/048-lightweight-tier-parity/spec.md` §3.1 "
        "(activation), §3.4 (tri-state UAT/E2E + upfront positive-"
        "confirmation prompt), §3.5 (external-verification.md soft "
        "gate), and §3.6 (spec.md schema additions).\n\n"
        "Four commits make up S2:\n"
        "- A: spec.md schema additions (tier field + tri-state UAT/E2E) — Python + TS parsers + tests.\n"
        "- B: --no-router activation infrastructure (runtime_mode.py with three-knob precedence).\n"
        "- C: route()/verify() short-circuit + external-verification.md soft gate.\n"
        "- D: suggestion_disposition reader/writer helpers + CLI backcompat tests + deferral note for the runtime gate.\n\n"
        "Test counts:\n"
        "- Python: 980 passed + 1 skipped (98 new for S2)\n"
        "- TypeScript: 633 passed + 2 pre-existing failures unrelated to S2\n\n"
        "## What I'm asking you to verify\n\n"
        "1. **Correctness** — Does the code do what the spec says?\n"
        "2. **Safety** — Could anything here accidentally call an LLM or hit credentials under --no-router?\n"
        "3. **Backwards compatibility** — Will pre-Set-048 invocations break?\n"
        "4. **Edge cases** — Are there race conditions, missing-file paths, or precedence-order bugs?\n"
        "5. **Scope tightening** — Commit D's deferral of the runtime gate (consumes suggestion_disposition) is documented in the commit message. Is the deferral defensible?\n\n"
        "## Code under review\n\n"
        "### ai_router/spec_config.py (new, Commit A)\n\n"
        "```python\n"
        f"{spec_config_py}\n"
        "```\n\n"
        "### ai_router/runtime_mode.py (new, Commit B)\n\n"
        "```python\n"
        f"{runtime_mode_py}\n"
        "```\n\n"
        "### ai_router/suggestion_disposition.py (new, Commit D)\n\n"
        "```python\n"
        f"{suggestion_disposition_py}\n"
        "```\n\n"
        "### ai_router/close_session.py — Set 048 changes summary (Commits B + C)\n\n"
        f"{cs_changes}\n\n"
        "### ai_router/__init__.py — Set 048 changes summary (Commit C)\n\n"
        f"{init_changes}\n\n"
        "### tools/dabbler-ai-orchestration/src/types.ts (Commit A schema)\n\n"
        "```typescript\n"
        f"{types_ts_excerpt}\n"
        "```\n\n"
        "## Verdict format\n\n"
        "Return a verdict (VERIFIED / ISSUES_FOUND) at the top of your response, "
        "then itemize concerns by Category (Correctness / Safety / Completeness / "
        "Backcompat / Edge-case / Other), Severity (Critical / Important / "
        "Nice-to-have), Location (file:line or section reference), Details, "
        "and Fix suggestion.\n"
    )


def _write_response(out_path: Path, label: str, result, verifier=False) -> None:
    text = (
        getattr(result, "raw_response", None)
        or getattr(result, "content", None)
        or ""
    )
    header = [
        f"# {label}",
        "",
        f"- **Provider:** {getattr(result, 'verifier_provider', getattr(result, 'model_id', 'unknown'))}",
        f"- **Model:** {getattr(result, 'verifier_model', getattr(result, 'model_name', 'unknown'))}",
        f"- **Cost:** {getattr(result, 'verifier_cost_usd', getattr(result, 'total_cost_usd', None))}",
    ]
    if verifier:
        header.append(f"- **Verdict:** {getattr(result, 'verdict', 'unknown')}")
    header.extend(["", "---", "", str(text)])
    out_path.write_text("\n".join(header), encoding="utf-8")
    print(f"  -> wrote {out_path.name} ({len(str(text))} chars)")


def main() -> int:
    prompt = _build_prompt()
    (HERE / "s2-verification-prompt.md").write_text(prompt, encoding="utf-8")
    print(f"Prompt: {len(prompt)} chars, {len(prompt.splitlines())} lines")

    print("\n========== ROUTE ==========")
    route_result = ai_router.route(
        content=prompt,
        task_type="code-review",
        context=(
            "Cross-provider verification of Set 048 Session 2's --no-router "
            "mode implementation. The code introduces a runtime-mode resolver, "
            "verification short-circuit, and external-verification.md soft "
            "gate. Pre-existing code paths must remain unchanged for Full-tier "
            "invocations."
        ),
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _write_response(HERE / "s2-verification-route.md", "Route response", route_result)

    print("\n========== VERIFY ==========")
    verify_result = ai_router.verify(
        route_result=route_result,
        original_task=prompt,
        task_type="code-review",
        session_set=SESSION_SET,
        session_number=SESSION_NUMBER,
    )
    _write_response(
        HERE / "s2-verification-verify.md",
        "Cross-provider verifier response",
        verify_result,
        verifier=True,
    )

    summary = {
        "session_set": SESSION_SET,
        "session_number": SESSION_NUMBER,
        "route_model": getattr(route_result, "model_name", "unknown"),
        "route_cost": getattr(route_result, "total_cost_usd", None),
        "verify_model": getattr(verify_result, "verifier_model", "unknown"),
        "verify_cost": getattr(verify_result, "verifier_cost_usd", None),
        "verify_verdict": getattr(verify_result, "verdict", None),
    }
    (HERE / "s2-verification-result.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print("\n========== SUMMARY ==========")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
