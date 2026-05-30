"""Set 052 S3 cross-provider verification of the S2 implementation.

Verifier: gemini-2.5-pro (google) — a different provider from the
Claude/Opus orchestrator that wrote S2. Feeds the ACTUAL code files
plus neutral framing of the two deviations S2 flagged, and asks for a
structured verdict. Mirrors the Set 051 S4 call mechanics.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import yaml
from ai_router import providers

EXT = REPO / "tools" / "dabbler-ai-orchestration"

CODE_FILES = [
    "src/utils/routerConfig.ts",
    "src/dashboard/dashboardHtml.ts",
    "src/utils/metrics.ts",
    "src/test/suite/costDashboardGate.test.ts",
]


def read(rel):
    return (EXT / rel).read_text(encoding="utf-8")


def main():
    cfg = yaml.safe_load((REPO / "ai_router" / "router-config.yaml").read_text(encoding="utf-8"))
    gcfg = cfg["providers"]["google"]
    model = next(m for m in cfg["models"].values() if m.get("model_id") == "gemini-2.5-pro")

    code_blocks = "\n\n".join(
        f"=== FILE: {rel} ===\n{read(rel)}" for rel in CODE_FILES
    )

    # Relevant manifest + wiring excerpts (actual lines, not paraphrase).
    pkg = json.loads(read("package.json"))
    menus = pkg.get("contributes", {}).get("menus", {})
    wiring = {
        "package.json:menus.commandPalette[showCostDashboard]": [
            m for m in menus.get("commandPalette", []) if m.get("command") == "dabbler.showCostDashboard"
        ],
        "package.json:menus.view/title[showCostDashboard]": [
            m for m in menus.get("view/title", []) if m.get("command") == "dabbler.showCostDashboard"
        ],
    }
    ext_gate = "\n".join(read("src/extension.ts").splitlines()[35:48])

    system_prompt = (
        "You are a senior TypeScript/VS Code-extension reviewer performing an "
        "independent cross-provider verification. You did NOT write this code. "
        "Be skeptical and concrete. Judge correctness, honesty of user-facing "
        "copy, and whether the implementation matches its stated intent. "
        "Return ONLY a JSON object with keys: verdict (one of "
        "'VERIFIED' | 'VERIFIED_WITH_NOTES' | 'ISSUES_FOUND'), "
        "critical (array of {title, detail}), important (array), "
        "nice_to_have (array), deviation_rulings (array of "
        "{deviation, ruling, rationale}), summary (string)."
    )

    user_message = f"""## Context

This is Set 052 of the dabbler-ai-orchestration extension: a fix for a
"dead" cost-dashboard icon. The ROOT CAUSE (diagnosed in the audit) was a
read/write path mismatch: the Python AI router WRITES metrics to
`ai_router/router-metrics.jsonl` (configurable via `metrics.log_filename`),
but the dashboard READ a hardcoded `ai_router/metrics.jsonl` it never
wrote to — so the panel was always empty and rendered a placeholder
telling the user to set `METRICS_ENABLED = True`. That flag is FICTIONAL:
there is no `config.py METRICS_ENABLED`; the real knob is
`metrics.enabled` in `router-config.yaml`, and it already defaults ON.

The locked design (S1 verdict) had the implementation (S2):
- D1: point the reader at the file the router actually writes, via ONE
  shared resolver (no second hardcoded name).
- D3: contribute the cost icon/command ONLY when the workspace actually
  routes (a resolvable `ai_router/router-config.yaml`) — absent on
  Lightweight. Gate via a `dabblerSessionSets.routesCost` context key.
- D4: on open, compute rate-estimate staleness in-extension from
  `metadata.pricing_reviewed` vs `review_frequency_days` (default 30;
  missing/invalid = stale); non-blocking banner with an update action.
- D5: three honest states — disabled (name the REAL `metrics.enabled`
  knob, never the fictional flag) / on-but-empty / on-with-data.

## The actual code under review

{code_blocks}

=== extension.ts (gate wiring, lines ~36-48) ===
{ext_gate}

=== package.json gate wiring (extracted) ===
{json.dumps(wiring, indent=2)}

## Two deviations the implementer flagged for you to rule on

DEVIATION 1 — "D7 Layer-3 Playwright icon smoke pivoted to a
deterministic manifest gate-wiring guard". The locked verdict asked for a
Layer-3 Playwright smoke asserting the cost icon is present (Full) /
absent (Lightweight) plus banner/empty/disabled states. The implementer
reports that VS Code `view/title` actions duplicate-render in the DOM and
collapse every action past the first into a lazily-created overflow, so a
gated action is genuinely absent from the DOM in a default-width sidebar
regardless of the gate — making a Playwright assertion non-deterministic
and uninformative. They removed the flaky Playwright spec and replaced it
with `costDashboardGate.test.ts` (above), which pins the manifest gate
wiring deterministically, and unit-test the panel copy against the same
pure builders the panel renders. Net Layer-3 coverage of the new panel:
none added. They cite an in-repo precedent (`migration-cta-v4.spec.ts`)
that unit-tests a modal rather than driving it from Playwright.
QUESTION: Is dropping the Playwright icon-visibility smoke in favor of the
manifest guard + pure-builder unit tests an acceptable engineering call,
or does it leave a real coverage gap that should block the close?

DEVIATION 2 — "schema reconciliation beyond the literal D1 text". D1 said
"fix the read path." To actually render real data the implementer also
renamed `MetricsEntry.session_num` -> `session_number` (the router never
emits `session_num`, so the CSV column was silently blank) and filtered
out `adjudication` bookkeeping rows (no model, zero cost). QUESTION: is
this in-scope and correct, or scope creep / a risk?

Review the code, rule on both deviations, and return the JSON verdict."""

    result = providers.call_model(
        provider_name="google",
        model_id="gemini-2.5-pro",
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=16000,
        config=gcfg,
        generation_params={"thinking_budget": 6000},
    )

    in_cost = model["input_cost_per_1m"] / 1_000_000 * result.input_tokens
    out_cost = model["output_cost_per_1m"] / 1_000_000 * result.output_tokens
    print("=== VERIFIER RAW OUTPUT ===")
    print(result.content)
    print("=== USAGE ===")
    print(json.dumps({
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "input_cost_per_1m": model["input_cost_per_1m"],
        "output_cost_per_1m": model["output_cost_per_1m"],
        "cost_usd": round(in_cost + out_cost, 6),
        "stop_reason": result.stop_reason,
    }, indent=2))


if __name__ == "__main__":
    main()
