"""Set 030 Session 1 — guard that ``spec-title-extraction`` is wired in.

Session 5 of Set 030 ships the in-extension migration UX, including an
AI-fallback path that routes via ``task_type='spec-title-extraction'``
when regex extraction of session titles from spec.md fails. Per the
spec's GPT-5.4 revision (D14), this task type is registered in Session
1 — not Session 5 — to remove a late-set dependency risk.

This test pins the registration so a future router-config edit that
silently drops it fails CI before Session 5 reaches for the task type
and crashes on a missing override.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import models  # type: ignore[import-not-found]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTER_CONFIG_PATH = REPO_ROOT / "ai_router" / "router-config.yaml"


def _load_router_config() -> dict:
    """Read router-config.yaml directly (no API-key validation).

    ``ai_router.config.load_config`` validates provider API keys at load
    time, which would force the test environment to mint env vars for
    every provider. The structural assertions below only need the YAML
    shape, so we bypass the validator.
    """
    return yaml.safe_load(ROUTER_CONFIG_PATH.read_text(encoding="utf-8"))


def test_spec_title_extraction_registered_in_task_type_scores():
    config = _load_router_config()
    scores = config["complexity"]["task_type_scores"]
    assert "spec-title-extraction" in scores, (
        "spec-title-extraction missing from complexity.task_type_scores — "
        "Session 5's AI-fallback path will fall back to the 'general' "
        "score and route inconsistently. Re-register per Set 030 Session 1."
    )
    # Score should be in the low/mechanical band (~10-40). The exact
    # value is the spec-author's call; pin a range, not a number, so a
    # later tune-up doesn't break this test.
    assert 10 <= scores["spec-title-extraction"] <= 40, (
        f"spec-title-extraction score {scores['spec-title-extraction']} is "
        "outside the low/mechanical band; reconsider routing implications."
    )


def test_spec_title_extraction_pins_a_cheap_model_via_override():
    config = _load_router_config()
    overrides = config["routing"]["task_type_overrides"]
    assert "spec-title-extraction" in overrides, (
        "spec-title-extraction must have an explicit routing override so "
        "the cost is predictable to the operator (the AI-fallback path "
        "in Session 5 confirms cost before running)."
    )
    model_name = overrides["spec-title-extraction"]
    # The pinned model must exist in the registry.
    assert model_name in config["models"], (
        f"task_type_override pins {model_name!r} for spec-title-extraction "
        "but no such model is registered in models:."
    )
    # And it should be a tier-1 model — the task is mechanical.
    tier = config["models"][model_name]["tier"]
    assert tier == 1, (
        f"spec-title-extraction is pinned to {model_name!r} (tier {tier}); "
        "expected a tier-1 model — the task is short, structured, and "
        "operator-paying-per-call, so cheaper is better."
    )


def test_spec_title_extraction_has_per_model_params():
    config = _load_router_config()
    params = config.get("task_type_params", {}).get("spec-title-extraction")
    assert params is not None, (
        "task_type_params.spec-title-extraction missing — a future tier "
        "bump or override could land on an un-tuned model and emit "
        "unexpected thinking tokens."
    )
    # Every model in the pool should have a default; we don't insist on
    # exact values (the spec-author tuned them), but the keys must be
    # present so a routing change is fully covered.
    expected_models = {"gemini-flash", "gemini-pro", "sonnet", "opus", "gpt-5-4-mini", "gpt-5-4"}
    actual_models = set(params.keys())
    missing = expected_models - actual_models
    assert not missing, (
        f"task_type_params.spec-title-extraction missing model entries: {missing}"
    )


def test_spec_title_extraction_resolves_via_pick_model():
    config = _load_router_config()
    # pick_model() requires the full config dict. It walks
    # routing.task_type_overrides first — if registration is correct,
    # we land on the pinned model regardless of complexity score.
    chosen = models.pick_model(
        complexity_score=10,
        max_tier=3,
        task_type="spec-title-extraction",
        config=config,
    )
    assert chosen == config["routing"]["task_type_overrides"]["spec-title-extraction"]


def test_spec_title_extraction_is_not_in_always_route():
    # Operator-driven only: the in-extension migration CTA decides when
    # to route, after explicit cost confirmation. Auto-routing would
    # bypass that confirmation — guard the carve-out.
    config = _load_router_config()
    always_routed = config["delegation"]["always_route_task_types"]
    assert "spec-title-extraction" not in always_routed, (
        "spec-title-extraction must NOT be auto-routed; Session 5 confirms "
        "cost before each call. Auto-routing would bypass the prompt."
    )


def test_spec_title_extraction_is_not_auto_verified():
    # Verifying a short structured extraction adds cost without buying
    # reliability (the output is its own verdict — the JSON parses or
    # it doesn't). Carve-out should hold.
    config = _load_router_config()
    auto_verify = config["verification"]["auto_verify_task_types"]
    assert "spec-title-extraction" not in auto_verify, (
        "spec-title-extraction must NOT be auto-verified; a second-opinion "
        "round on a structured-JSON extract burns budget without raising "
        "confidence (the schema is the verdict)."
    )
