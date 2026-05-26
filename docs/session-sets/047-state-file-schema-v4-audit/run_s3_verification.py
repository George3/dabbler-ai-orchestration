"""Routed cross-provider verification for Set 047 Session 3.

Bundles the v3 → v4 migrator phase (Python module, TS mirror, TS
command, fileSystem detector + ActionRegistry split, types,
rollback doc, tests) into a single session-verification call and
persists the verifier's verdict + write-up to disk for the close-out
attestation.

Mirrors the Session-2 driver structure (`run_s2_verification.py`).

Per memory ``feedback_session_verification_gpt54_429_pivot_to_gemini``:
this uses ``task_type='session-verification'`` so the router's
tier-routing config picks the configured verifier.

Per memory ``feedback_ai_router_route_result_handling``: dump the
RouteResult attributes via getattr() into a plain dict BEFORE any
attribute access on a returned namedtuple/dataclass field — wrappers
have crashed in the past during attribute access.
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

PROMPT_FILE = SESSION_DIR / "s3-verification-prompt.md"

BUNDLE_FILES = [
    "ai_router/migrate_v3_to_v4.py",
    "tools/dabbler-ai-orchestration/src/utils/migrateSessionStateV4.ts",
    "tools/dabbler-ai-orchestration/src/commands/migrateSetV4.ts",
    "tools/dabbler-ai-orchestration/src/utils/fileSystem.ts",
    "tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts",
    "tools/dabbler-ai-orchestration/src/types.ts",
    "docs/v3-to-v4-rollback-procedure.md",
    "ai_router/tests/test_migrate_v3_to_v4.py",
    "tools/dabbler-ai-orchestration/src/test/suite/migrateSessionStateV4.test.ts",
    "tools/dabbler-ai-orchestration/src/test/suite/actionRegistry.test.ts",
    "tools/dabbler-ai-orchestration/src/test/playwright/migration-cta-v4.spec.ts",
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
        session_number=3,
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

    out_path = SESSION_DIR / "s3-verification-result.json"
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

    transcript_path = SESSION_DIR / "s3-verification-transcript.md"
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
