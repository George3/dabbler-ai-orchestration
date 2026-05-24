"""End-of-session verification for Set 045 Session 1.

Sends the session's spike-pass artifacts to a non-Anthropic verifier
(default per router-config.yaml: gpt-5-4) for independent review.

Writes the raw verifier output to
``docs/session-sets/045-log-harvest-implementation/session-reviews/session-001.md``
per the workflow Step 6 convention. Per the standing lesson
``feedback_ai_router_route_result_handling``, dumps the RouteResult
to disk before any attribute access.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Run from repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402
from ai_router import route  # noqa: E402

# Force gemini-pro for this verification call. The default session-verification
# override is gpt-5-4 but the OpenAI endpoint is returning sustained 429s on
# this workload — pivot to Gemini Pro (still cross-provider from Anthropic).
# This monkey-patches the in-process config only; no committed file is changed.
ai_router._init()
ai_router._config["routing"]["task_type_overrides"]["session-verification"] = "gemini-pro"

SET_DIR = REPO_ROOT / "docs" / "session-sets" / "045-log-harvest-implementation"
REVIEWS_DIR = SET_DIR / "session-reviews"
REVIEWS_DIR.mkdir(exist_ok=True)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


bundle_parts = [
    ("open-question-resolution.md",
     "docs/session-sets/045-log-harvest-implementation/open-question-resolution.md"),
    ("joiner-location-decision.md",
     "docs/session-sets/045-log-harvest-implementation/joiner-location-decision.md"),
    ("spike-prototypes/claude_phrasing_ablation_analysis.md",
     "docs/session-sets/045-log-harvest-implementation/spike-prototypes/claude_phrasing_ablation_analysis.md"),
    ("spike-prototypes/correlation_prototype_report.json (Q2 actual run output, evidence for the resolution doc's claims)",
     "docs/session-sets/045-log-harvest-implementation/spike-prototypes/correlation_prototype_report.json"),
    ("spike-prototypes/joiner_python_report.json (Q4 Python perf evidence)",
     "docs/session-sets/045-log-harvest-implementation/spike-prototypes/joiner_python_report.json"),
    ("spike-prototypes/joiner_typescript_report.json (Q4 TypeScript perf evidence)",
     "docs/session-sets/045-log-harvest-implementation/spike-prototypes/joiner_typescript_report.json"),
]

content_blocks = []
for label, rel_path in bundle_parts:
    text = read_text(REPO_ROOT / rel_path)
    content_blocks.append(f"### {label}\n\n```\n{text}\n```\n")

content = (
    "## Set 045 / Session 1 spike — work submitted for verification\n\n"
    "**Session goal:** resolve four open empirical questions from Set 044's\n"
    "log-harvest proposal v1 (Q1 bypass rate, Q2 deterministic wrapper-to-\n"
    "native-log correlation, Q3 Claude phrasing-trigger ablation, Q4 joiner\n"
    "location decision). The session was scoped as spike-only per a start-\n"
    "of-set descope: no production-grade `dabbler-launch` CLI shipped in S1;\n"
    "the canonical wrapper ships in S3. Throwaway prototype code is preserved\n"
    "under `spike-prototypes/` for S2/S3 reference.\n\n"
    "**Artifacts under review** (in order):\n"
    + "".join(f"- `{label}`\n" for label, _ in bundle_parts)
    + "\n"
    + "\n".join(content_blocks)
)

context = (
    "You are an independent verifier reviewing a session set's spike-pass\n"
    "deliverables in this AI-led-workflow repo (dabbler-ai-orchestration).\n"
    "The orchestrator was Claude Opus 4.7; verification routes to a different\n"
    "provider for cross-provider review. Focus on:\n\n"
    "1. **Q2 correlation prototype** — is the join logic sound? Are window\n"
    "   sizing, cwd canonicalization, and ambiguity handling correctly\n"
    "   reasoned? Any missed edge cases that would invalidate the\n"
    "   'deterministic correlation works' verdict?\n"
    "2. **Q4 joiner location decision** — does the rubric in `joiner-\n"
    "   location-decision.md` hold up under scrutiny? Are there\n"
    "   counter-arguments for TypeScript that the orchestrator missed?\n"
    "   Is the IPC-cost argument honest? The Pass A (Set 044) consensus\n"
    "   was 2-1 Python; this session's benchmark adds new evidence —\n"
    "   evaluate whether the additional evidence strengthens, weakens, or\n"
    "   is irrelevant to that prior consensus.\n"
    "3. **Q3 Claude phrasing ablation analysis** — is the hypothesis matrix\n"
    "   well-reasoned? Are the defensive template rules in §4 likely to be\n"
    "   sufficient for Set 045 S4 to ship a working CLAUDE.md narration\n"
    "   template without running the optional follow-on ablation?\n"
    "4. **Q1 bypass-rate log** — is the schema sensible? Is the\n"
    "   end-of-day-reflective capture protocol realistic given operator\n"
    "   workflow constraints?\n"
    "5. **Cross-cutting** — anything in the resolution doc that\n"
    "   misrepresents the prototypes or overstates what was actually\n"
    "   proven? Anything that should have been done that wasn't (within\n"
    "   the spike-only scope)?\n\n"
    "Use the standard VERIFIED / ISSUES FOUND verdict format.\n"
)

result = route(
    content=content,
    task_type="session-verification",
    context=context,
    session_set=str(SET_DIR),
    session_number=1,
)

# Per feedback_ai_router_route_result_handling — dump first, access later.
result_dump = {
    "model": getattr(result, "model", None),
    "provider": getattr(result, "provider", None),
    "tier": getattr(result, "tier", None),
    "complexity_score": getattr(result, "complexity_score", None),
    "task_type": getattr(result, "task_type", None),
    "input_tokens": getattr(result, "input_tokens", None),
    "output_tokens": getattr(result, "output_tokens", None),
    "cost_usd": getattr(result, "cost_usd", None),
    "stop_reason": getattr(result, "stop_reason", None),
    "verification": getattr(result, "verification", None),
    "auto_verified": getattr(result, "auto_verified", None),
    "content_length": len(getattr(result, "content", "") or ""),
}
debug_path = REVIEWS_DIR / "session-001-route-result.json"
with open(debug_path, "w", encoding="utf-8") as f:
    json.dump(result_dump, f, indent=2, default=str)

# Persist raw verifier output FIRST per the Windows cp1252 lesson.
review_text = getattr(result, "content", "") or ""
review_path = REVIEWS_DIR / "session-001.md"
with open(review_path, "w", encoding="utf-8") as f:
    f.write(review_text)

# Print summary only (NOT result.content) to avoid cp1252 crash.
summary = {
    "review_path": str(review_path),
    "debug_path": str(debug_path),
    "model": result_dump["model"],
    "provider": result_dump["provider"],
    "tier": result_dump["tier"],
    "cost_usd": result_dump["cost_usd"],
    "content_length": result_dump["content_length"],
}
print(json.dumps(summary, indent=2, default=str))
