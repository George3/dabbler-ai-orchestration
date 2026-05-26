"""Routed cross-provider verification for Set 047 Session 6.

Bundles the three new/edited doc files (canonical schema doc,
authoring-guide edits, set change-log) along with the audit-locked
spec, all five prior close-reason files, and key writer/reader
source files into a single session-verification call. Persists the
verifier's verdict + write-up to disk for the close-out attestation.

Mirrors the S5 driver structure.

Per memory ``feedback_session_verification_gpt54_429_pivot_to_gemini``:
this uses ``task_type='session-verification'`` so the router's tier-
routing config picks the configured verifier.

Per memory ``feedback_ai_router_route_result_handling``: dump the
RouteResult attributes via getattr() into a plain dict BEFORE any
attribute access on a returned namedtuple/dataclass field.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ai_router import route  # type: ignore  # noqa: E402


SESSION_DIR = Path(__file__).resolve().parent

PROMPT_FILE = SESSION_DIR / "s6-verification-prompt.md"

BUNDLE_FILES = [
    # Primary targets — the three docs this session ships
    "docs/session-state-schema.md",
    "docs/planning/session-set-authoring-guide.md",
    "docs/session-sets/047-state-file-schema-v4-audit/change-log.md",
    # Audit-locked spec — the source of truth for what shipped
    "docs/session-sets/047-state-file-schema-v4-audit/spec.md",
    # Prior close-reason files — the source of truth for per-session
    # change-log accuracy
    "docs/session-sets/047-state-file-schema-v4-audit/s1-close-reason.md",
    "docs/session-sets/047-state-file-schema-v4-audit/s2-close-reason.md",
    "docs/session-sets/047-state-file-schema-v4-audit/s3-close-reason.md",
    "docs/session-sets/047-state-file-schema-v4-audit/s4-close-reason.md",
    "docs/session-sets/047-state-file-schema-v4-audit/s5-close-reason.md",
    # Current state — referenced by the schema doc's worked examples
    "docs/session-sets/047-state-file-schema-v4-audit/session-state.json",
    # Writer source — to verify schema-doc claims about emitted fields
    "ai_router/session_state.py",
    "ai_router/session_lifecycle.py",
    # Reader shim — to verify schema-doc claims about reader contract
    "ai_router/progress.py",
    # TS writer mirror + cancel lifecycle
    "tools/dabbler-ai-orchestration/src/utils/sessionState.ts",
    "tools/dabbler-ai-orchestration/src/utils/cancelLifecycle.ts",
    # Prerequisites cross-reference
    "tools/dabbler-ai-orchestration/src/utils/fileSystem.ts",
    # Rollback procedure (cross-referenced by the schema doc)
    "docs/v3-to-v4-rollback-procedure.md",
]


def build_payload() -> str:
    prompt = PROMPT_FILE.read_text(encoding="utf-8")
    chunks = [prompt, "\n\n---\n\n# Files bundled for review\n"]
    for rel in BUNDLE_FILES:
        path = REPO_ROOT / rel
        if not path.is_file():
            chunks.append(f"\n## {rel}\n\n_NOT FOUND_\n")
            continue
        chunks.append(f"\n## `{rel}`\n\n```\n")
        chunks.append(path.read_text(encoding="utf-8"))
        chunks.append("\n```\n")
    return "".join(chunks)


def main() -> int:
    payload = build_payload()
    payload_chars = len(payload)
    print(f"[verify] payload: {payload_chars} chars", flush=True)

    t0 = time.time()
    result = route(
        content=payload,
        task_type="session-verification",
        session_set="047-state-file-schema-v4-audit",
        session_number=6,
    )
    dt = time.time() - t0

    result_dict: dict = {}
    for attr in (
        "content",
        "model_name",
        "model_id",
        "tier",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "total_cost_usd",
        "complexity_score",
        "escalated",
        "elapsed_seconds",
        "truncated",
    ):
        try:
            result_dict[attr] = getattr(result, attr, None)
        except Exception as exc:
            result_dict[attr] = f"<accessor error: {exc}>"

    out_path = SESSION_DIR / "s6-verification-result.json"
    out_path.write_text(
        json.dumps(
            {
                "elapsed_sec": dt,
                "payload_chars": payload_chars,
                "result": {
                    k: v for k, v in result_dict.items() if k != "content"
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    transcript_path = SESSION_DIR / "s6-verification-transcript.md"
    transcript_path.write_text(
        result_dict.get("content") or "<no content returned>",
        encoding="utf-8",
    )

    print(
        f"[verify] done in {dt:.1f}s — "
        f"cost ${result_dict.get('cost_usd')} on "
        f"{result_dict.get('model_name')} (tier {result_dict.get('tier')})",
        flush=True,
    )
    print(f"[verify] transcript: {transcript_path}", flush=True)
    print(f"[verify] result meta: {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
