"""Routed cross-provider verification for Set 047 Session 4.

Bundles the writer-flip phase part 1 (Python writers emit v4) into a
single session-verification call and persists the verifier's verdict
+ write-up to disk for the close-out attestation.

Mirrors the Session-2 / Session-3 driver structure.

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

PROMPT_FILE = SESSION_DIR / "s4-verification-prompt.md"

BUNDLE_FILES = [
    # Writer surfaces (the heart of S4)
    "ai_router/session_state.py",
    "ai_router/session_lifecycle.py",
    # Shim extensions (lifecycle derivation, plan-less totalSessions,
    # status-gated completedAt, dropped last-completed orchestrator
    # fallback)
    "ai_router/progress.py",
    # New v4 writer-shape test pinning
    "ai_router/tests/test_session_state_v4_writers.py",
    # Updated test fixtures (subset; the full diff is too large for one
    # bundle, but these are the key v4-emission assertions)
    "ai_router/tests/test_session_state_v3.py",
    "ai_router/tests/test_chatsessionid_writer.py",
    "ai_router/tests/test_checkout_writer.py",
    "ai_router/tests/test_start_session.py",
    "ai_router/tests/test_close_session_snapshot_flip.py",
    "ai_router/tests/test_read_status.py",
    "ai_router/tests/e2e/fixtures.py",
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
        session_number=4,
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

    out_path = SESSION_DIR / "s4-verification-result.json"
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

    transcript_path = SESSION_DIR / "s4-verification-transcript.md"
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
