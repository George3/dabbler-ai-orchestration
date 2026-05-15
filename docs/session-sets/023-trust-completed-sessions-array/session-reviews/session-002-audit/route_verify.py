"""Route the Set 023 Session 2 audit-summary verification prompt
to gpt-5-4-mini (third-provider verifier — not a subject)."""
import dataclasses
import json
import sys
from pathlib import Path

from ai_router import query

HERE = Path(__file__).parent

prompt_tpl = (HERE / "verify-prompt.md").read_text(encoding="utf-8")
gpt_raw = json.loads((HERE / "gpt-5-4.json").read_text(encoding="utf-8"))["content"]
gemini_raw = json.loads((HERE / "gemini-pro.json").read_text(encoding="utf-8"))["content"]
audit = (HERE / "audit-summary.md").read_text(encoding="utf-8")

rendered = (prompt_tpl
    .replace("{{GPT_RAW}}", gpt_raw)
    .replace("{{GEMINI_RAW}}", gemini_raw)
    .replace("{{AUDIT_SUMMARY}}", audit)
)

(HERE / "verify-prompt.rendered.md").write_text(rendered, encoding="utf-8")

result = query(
    model="gpt-5-4-mini",
    content=rendered,
    task_type="analysis",
    session_set="docs/session-sets/023-trust-completed-sessions-array",
    session_number=2,
)

dump = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else {
    k: getattr(result, k, None) for k in dir(result) if not k.startswith("_")
}
(HERE / "verify-result.json").write_text(
    json.dumps(dump, indent=2, default=str), encoding="utf-8"
)
print(f"model={dump.get('model_name')!r} cost=${dump.get('cost_usd', 0):.4f} "
      f"in={dump.get('input_tokens')} out={dump.get('output_tokens')}")
print("---")
print(dump.get("content", "")[:2000])
