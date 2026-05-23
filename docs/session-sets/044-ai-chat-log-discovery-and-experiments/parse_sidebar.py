"""Parse the S5 effort sidebar OTel JSONLs to extract A3 reasoning-effort
signals at --effort low and --effort high.

Closes (or moves toward closing):
  - Q3: Does `gen_ai.request.reasoning_effort` appear at non-default
    effort levels? (S4a measured medium = OMITTED.)
  - Q4: Do `gen_ai.usage.reasoning.output_tokens` value ranges
    distinguish low/medium/high effort buckets?

For comparison, S4a baseline at --effort medium recorded:
  reasoning.output_tokens per turn: [516, 15, 59, 163]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


OTEL_DIR = Path("C:/tmp/dabbler-log-harvest/otel")
LOW  = OTEL_DIR / "s5-sidebar-low.jsonl"
HIGH = OTEL_DIR / "s5-sidebar-high.jsonl"


def load_lines(path: Path) -> list[dict]:
    lines: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError as e:
                print(f"  WARNING: bad JSON in {path.name}: {e}")
    return lines


def attr_value(rec: dict, key: str):
    """OTel JSONL attribute lookup. Records typically carry attributes
    in record['attributes'][key] but the spec wraps them as either
    flat dicts or {"value": {"...Value": v}} shapes depending on
    exporter version. Handle both."""
    attrs = rec.get("attributes") or {}
    val = attrs.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        for k, v in val.items():
            if k.endswith("Value"):
                return v
        return val
    return val


def summarize(path: Path, label: str) -> dict:
    records = load_lines(path)
    print(f"\n=== {label} ({path.name}) ===")
    print(f"  Total records: {len(records)}")

    # Group records by type/name
    by_name: dict[str, int] = {}
    for r in records:
        name = r.get("name") or r.get("span_name") or r.get("type") or "<unknown>"
        by_name[name] = by_name.get(name, 0) + 1
    print(f"  Records by name (top 10):")
    for n, c in sorted(by_name.items(), key=lambda x: -x[1])[:10]:
        print(f"    {c:4d}  {n}")

    # Find chat spans
    chat_spans = [r for r in records if (r.get("name") or "").startswith("chat ")]
    print(f"  Chat spans: {len(chat_spans)}")

    # Per-chat-span: reasoning_effort attribute + reasoning.output_tokens
    effort_values: list = []
    rot_values: list = []
    for i, span in enumerate(chat_spans):
        effort_values.append(attr_value(span, "gen_ai.request.reasoning_effort"))
        rot_values.append(attr_value(span, "gen_ai.usage.reasoning.output_tokens"))

    print(f"  Per-chat-span gen_ai.request.reasoning_effort: {effort_values}")
    print(f"  Per-chat-span gen_ai.usage.reasoning.output_tokens: {rot_values}")

    # Filtered Nones for stats
    rot_nums = [v for v in rot_values if isinstance(v, (int, float))]
    if rot_nums:
        print(f"  reasoning.output_tokens stats: "
              f"min={min(rot_nums)}, max={max(rot_nums)}, "
              f"sum={sum(rot_nums)}, count={len(rot_nums)}")

    # Look for ALL attributes on the first chat span for completeness
    if chat_spans:
        first = chat_spans[0]
        attrs = first.get("attributes") or {}
        all_keys = sorted(attrs.keys())
        # Print only the reasoning/effort-relevant keys
        relevant = [k for k in all_keys if "reasoning" in k or "effort" in k or "model" in k or "usage" in k]
        print(f"  First chat span relevant attr keys:")
        for k in relevant:
            print(f"    {k} = {attrs[k]}")

    return {
        "label": label,
        "chat_span_count": len(chat_spans),
        "reasoning_effort_attr": effort_values,
        "reasoning_output_tokens": rot_values,
    }


def main() -> int:
    print("S5 Copilot effort sidebar — OTel parse")
    print(f"Repo root: {Path.cwd()}")

    if not LOW.exists() or not HIGH.exists():
        print(f"ERROR: missing OTel JSONLs at {LOW} or {HIGH}")
        return 2

    low_summary  = summarize(LOW,  "EFFORT=LOW")
    high_summary = summarize(HIGH, "EFFORT=HIGH")

    print("\n=== Comparison vs S4a medium baseline ===")
    print("  S4a --effort medium baseline reasoning.output_tokens: [516, 15, 59, 163]")
    print(f"  S5  --effort low    reasoning.output_tokens: {low_summary['reasoning_output_tokens']}")
    print(f"  S5  --effort high   reasoning.output_tokens: {high_summary['reasoning_output_tokens']}")
    print()
    print(f"  reasoning_effort attribute present at low?  : "
          f"{any(v is not None for v in low_summary['reasoning_effort_attr'])}")
    print(f"  reasoning_effort attribute present at high? : "
          f"{any(v is not None for v in high_summary['reasoning_effort_attr'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
