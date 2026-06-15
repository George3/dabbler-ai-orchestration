"""Set 067 S4 - log activity steps + write the initial disposition.

Run with the repo venv from the repo root. Logs the S4 work steps to
activity-log.json (the close gate requires a current-session entry) and writes
disposition.json's summary + files_changed so the path-aware-critique producer
builds a faithful critique instruction. Verdict / next_orchestrator are
finalized after cross-provider verification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ai_router"))

from session_log import SessionLog  # noqa: E402

SET_DIR = REPO / "docs/session-sets/067-pull-verifier-adapter-experiment-a"

log = SessionLog(str(SET_DIR), total_sessions=4)

STEPS = [
    ("session-004/register", "Registered S4; read spec, guidance, S1-S3 deliverables, experiment-a-results.md (capability CONFIRMED)."),
    ("session-004/producer", "Implemented ai_router/pull_critique.py: opt-in producer driving pull_route per provider, assembling + writing the Set 066 path-aware-critique.json artifact; multi-provider invariant + identity stamping + envelope validation."),
    ("session-004/export", "Exported produce_path_aware_critique / build_instruction / ProducerResult / PullCritiqueError / DEFAULT_PROVIDERS from ai_router/__init__.py."),
    ("session-004/tests", "Added ai_router/tests/test_pull_critique.py (11 tests, fake run_pull, no metered calls); full suite 1503 passed / 1 skipped."),
    ("session-004/docs", "Added ai_router/docs/pull-verifier.md; added opt-in automated-alternative notes to docs/path-aware-critique-schema.md and the path-aware-critique.md template."),
    ("session-004/version", "Bumped ai_router 0.20.0 -> 0.21.0 (pyproject.toml) + CHANGELOG 0.21.0 entry."),
]

start = log.get_entries_for_session(4)
next_step = max((e["stepNumber"] for e in start), default=0) + 1
for i, (key, desc) in enumerate(STEPS):
    log.log_step(4, next_step + i, key, desc, "complete")

print(f"Logged {len(STEPS)} S4 steps; activity-log now has "
      f"{len(log.get_entries_for_session(4))} session-4 entries.")

# --- Initial disposition (summary + files_changed for the producer) ---
files_changed = [
    "ai_router/pull_critique.py",
    "ai_router/__init__.py",
    "ai_router/tests/test_pull_critique.py",
    "ai_router/docs/pull-verifier.md",
    "docs/path-aware-critique-schema.md",
    "ai_router/prompt-templates/path-aware-critique.md",
    "pyproject.toml",
    "ai_router/CHANGELOG.md",
]
summary = (
    "Set 067 Session 4 of 4 (FINAL): conditional producer wiring + synthesis + "
    "release. Experiment A (S3) CONFIRMED path-aware capability, so the "
    "pre-registered S4 gate fired: wired the first-party pull verifier "
    "(pull_verifier.py, S1-S2) as an OPT-IN automated producer of the Set 066 "
    "path-aware-critique.json artifact. New ai_router/pull_critique.py: "
    "produce_path_aware_critique() drives pull_route once per provider (default "
    "GPT-5.4 + Gemini-Pro) over a read-only repo sandbox, reuses the manual "
    "path-aware-critique.md template as the critique instruction, assembles the "
    "Set 066 envelope, and writes it beside spec.md. It REFUSES to write a "
    "gate-failing artifact (>=2 distinct providers with usable verdicts; a "
    "failing provider is skipped not fatal), stamps sessionSetName + the "
    "recorded pathAwareCritique level for the gate identity check, and validates "
    "with the same validator the gate uses before writing. CLI: python -m "
    "ai_router.pull_critique <set-dir> [--provider p:m] [--sandbox] [--level] "
    "[--dry-run]. Manual flow stays the default; producer is strictly opt-in. "
    "Exported the public surface from __init__. 11 new tests (fake run_pull, no "
    "metered calls); full Python suite 1503 passed / 1 skipped. Docs: new "
    "ai_router/docs/pull-verifier.md + automated-alternative notes in the schema "
    "doc and template. Version ai_router 0.20.0 -> 0.21.0 + CHANGELOG. Routed "
    "per-session verification UNCHANGED; run_test sandbox / contract-gate / "
    "Experiment B / routed keep-demote-retire all deferred to Set 068. "
    "Dogfooded the set's own pathAwareCritique:required gate by producing this "
    "set's path-aware-critique.json via the new producer."
)

disp_path = SET_DIR / "disposition.json"
disp = json.loads(disp_path.read_text(encoding="utf-8"))
disp["summary"] = summary
disp["files_changed"] = files_changed + [
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/path-aware-critique.json",
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/change-log.md",
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/disposition.json",
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/activity-log.json",
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/session-state.json",
    "docs/session-sets/067-pull-verifier-adapter-experiment-a/session-events.jsonl",
]
# Reset close-out fields to be finalized after verification.
disp["status"] = "in-progress"
disp_path.write_text(json.dumps(disp, indent=2) + "\n", encoding="utf-8")
print(f"Wrote initial disposition summary ({len(summary)} chars).")
