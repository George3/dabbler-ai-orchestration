"""Set 070 (S1) — framing-pin test for the push verification template.

The push (routed, snippet-fed) verification surface ships its reviewer prompt
in ``ai_router/prompt-templates/verification.md``. Before Set 070 that template
framed the reviewer weakly ("evaluate it objectively"), weaker than both the
Experiment A instrument that demoted push ("find every defect", moderate) and
its pull counterpart ``path-aware-critique.md`` ("devil's advocate, assume
flawed, prove it", strong). L-069-2: a surface must be measured at its
**strongest** adversarial framing before any demote/retire, and in any A/B the
framing must be a controlled, EQUAL variable across arms.

These tests pin two things so a future silent weakening is caught:

1. The push template carries the **strong adversarial (devil's-advocate)**
   framing — the same strength as the pull template.
2. The template still honours the machine contract
   :func:`ai_router.verification.build_verification_prompt` /
   :func:`ai_router.verification.parse_verification_response` depend on: the
   ``{original_task}`` / ``{task_type}`` / ``{original_response}`` placeholders
   and the ``VERIFIED`` / ``ISSUES FOUND`` verdict tokens.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import verification

PROMPT_TEMPLATES_DIR = Path(verification.__file__).resolve().parent / "prompt-templates"
PUSH_TEMPLATE = PROMPT_TEMPLATES_DIR / "verification.md"
PULL_TEMPLATE = PROMPT_TEMPLATES_DIR / "path-aware-critique.md"


def _push_text() -> str:
    return PUSH_TEMPLATE.read_text(encoding="utf-8")


# The load-bearing strong-framing phrases. Each is checked case-insensitively
# so cosmetic capitalisation edits don't break the pin, but a genuine
# weakening (dropping the devil's-advocate stance) trips it.
STRONG_FRAMING_PHRASES = [
    "devil's advocate",
    "assume the work is flawed",
    "rubber-stamp",
]


@pytest.mark.parametrize("phrase", STRONG_FRAMING_PHRASES)
def test_push_template_carries_strong_adversarial_framing(phrase: str):
    """verification.md must use the strong devil's-advocate framing (L-069-2)."""
    assert phrase.lower() in _push_text().lower(), (
        f"push verification template lost the strong-framing phrase {phrase!r}; "
        "a silent weakening below pull's framing would make any push-vs-pull "
        "comparison invalid as RETIRE evidence (L-069-2)."
    )


def test_push_template_no_longer_uses_weak_objective_framing():
    """The pre-Set-070 weak framing ('evaluate it objectively') is gone."""
    assert "evaluate it objectively" not in _push_text().lower()


def test_push_framing_strength_matches_pull():
    """Both surfaces carry the same devil's-advocate stance — framing is held
    EQUAL across arms, the precondition for a valid dual-surface comparison."""
    pull_text = PULL_TEMPLATE.read_text(encoding="utf-8").lower()
    push_text = _push_text().lower()
    for phrase in ("devil's advocate", "assume the work is flawed"):
        assert phrase in pull_text, f"pull template unexpectedly lacks {phrase!r}"
        assert phrase in push_text, f"push template unexpectedly lacks {phrase!r}"


def test_push_template_preserves_machine_placeholders():
    """The placeholders build_verification_prompt substitutes must survive."""
    text = _push_text()
    for placeholder in ("{original_task}", "{task_type}", "{original_response}"):
        assert placeholder in text, f"verification.md lost placeholder {placeholder}"


def test_push_template_preserves_verdict_tokens():
    """parse_verification_response keys off VERIFIED / ISSUES FOUND."""
    text = _push_text()
    assert "VERIFIED" in text
    assert "ISSUES FOUND" in text


def test_upgraded_template_still_parses_verified():
    """A VERIFIED verdict produced under the upgraded template parses clean."""
    prompt = verification.build_verification_prompt(
        original_task="do X",
        original_response="I did X correctly.",
        task_type="session-verification",
        template=_push_text(),
    )
    # The placeholders were substituted (no stray braces left behind).
    assert "{original_task}" not in prompt
    assert "do X" in prompt
    verdict, issues = verification.parse_verification_response(
        "VERIFIED — I tried to break it and could not; checked the X path."
    )
    assert verdict == "VERIFIED"
    assert issues == []


def test_upgraded_template_still_parses_issues():
    """An ISSUES FOUND verdict with the documented shape parses into findings."""
    verdict, issues = verification.parse_verification_response(
        "ISSUES FOUND\n\n"
        "- **Issue 1:** The X path is off by one.\n"
        "  - **Category:** Correctness\n"
        "  - **Severity:** Major\n"
    )
    assert verdict == "ISSUES_FOUND"
    assert len(issues) >= 1
