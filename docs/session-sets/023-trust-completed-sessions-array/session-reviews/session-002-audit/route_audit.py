"""Route Set 023 Session 2 audit prompt to a specified model.

Usage: python route_audit.py <model-name>
Saves <model-name>.json (full RouteResult dump) alongside this script.
"""
import json
import sys
import dataclasses
from pathlib import Path

from ai_router import query

HERE = Path(__file__).parent
PROMPT_PATH = HERE / "prompt.md"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: route_audit.py <model-name>", file=sys.stderr)
        return 2
    model = sys.argv[1]
    content = PROMPT_PATH.read_text(encoding="utf-8")

    result = query(
        model=model,
        content=content,
        task_type="analysis",
        session_set="docs/session-sets/023-trust-completed-sessions-array",
        session_number=2,
    )

    # Dump full RouteResult to JSON before any attribute access
    # (memory rule: lost $0.34 to wrapper-crash bugs).
    if dataclasses.is_dataclass(result):
        dump = dataclasses.asdict(result)
    else:
        dump = {k: getattr(result, k, None) for k in dir(result) if not k.startswith("_")}

    out = HERE / f"{model}.json"
    out.write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out}")
    print(f"model={dump.get('model_name')!r} cost=${dump.get('cost_usd', 0):.4f} "
          f"in={dump.get('input_tokens')} out={dump.get('output_tokens')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
