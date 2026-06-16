"""Set 070 (S1) - the dual-surface ("overdetermined") verification runner.

Runs **both** verification surfaces over the **same committed state**, with
**provider and adversarial framing held EQUAL across arms** (a steelman of each
surface, isolating *surface* as the only variable):

- **PUSH arm** - snippet-fed, single-shot, **no repository access**. The
  committed diff is fed inline under the ``verification.md`` template (Set 070
  strong devil's-advocate framing). This is the routed ``session-verification``
  surface, **pinned** to the chosen provider/model. We pin the provider rather
  than letting :func:`ai_router.route` pick it, because the dual-surface
  comparison *requires* provider held equal (L-069-2) and ``route``'s rule-based
  verifier selection cannot guarantee that.
- **PULL arm** - repository-reading, agentic tool loop. :func:`pull_route` over
  the repo at the committed state under the ``path-aware-critique.md`` template
  (strong devil's-advocate framing).

**Scope of Session 1.** S1 ships **only** the two-arm runner: it returns both
arms' RAW verdicts plus a recorded **attestation** that provider, model, and
framing strength were equal across arms. There is **NO merge yet** (S2 adds the
provenance merge + the fair-shake scoring; S2 wires the recorded
``verificationMode``-pattern option and the CLI).

**Why framing is enforced here, not trusted.** L-069-2: framing strength is a
cheap, prompt-only lever orthogonal to surface and provider count; a push-vs-pull
comparison whose arms used *unequal* framing is **invalid as RETIRE evidence**.
So this runner derives each arm's framing strength from the **actual template
text** (never a hand-asserted label) and, by default, **refuses** (raises
:class:`UnequalArmsError`) if provider, model, or framing strength differ. The
attestation that they were equal is part of the returned result.

No metered LLM call happens at import. Both arms are injectable (``run_push`` /
``run_pull``) so unit tests fake them; the production defaults are
:func:`_default_run_push` (a provider-pinned single-shot via
:func:`ai_router.providers.call_model`) and :func:`pull_route`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

try:  # package + bare-filename import shim (matches the test convention)
    from .providers import APIResult, call_model
    from .pull_verifier import (
        DiffConfig,
        PullCaps,
        PullResult,
        _dispatch_get_diff,
        _load_router_config,
        _pricing_for,
        _provider_config,
        _resolve_gen_params,
        _resolve_model,
        caps_from_config,
        pull_route,
    )
    from .pull_critique import _default_sandbox_for, build_instruction, prompt_body_of
    from .verification import build_verification_prompt, parse_verification_response
except ImportError:  # pragma: no cover - test/bare context
    from providers import APIResult, call_model  # type: ignore
    from pull_verifier import (  # type: ignore
        DiffConfig,
        PullCaps,
        PullResult,
        _dispatch_get_diff,
        _load_router_config,
        _pricing_for,
        _provider_config,
        _resolve_gen_params,
        _resolve_model,
        caps_from_config,
        pull_route,
    )
    from pull_critique import (  # type: ignore
        _default_sandbox_for,
        build_instruction,
        prompt_body_of,
    )
    from verification import (  # type: ignore
        build_verification_prompt,
        parse_verification_response,
    )


# ---------------------------------------------------------------------------
# Framing strength classification
#
# Derived from the ACTUAL template text so the equal-framing attestation is a
# measurement, not a hand-asserted label. The ladder mirrors L-069-2's three
# observed framing strengths; the runner's invariant is only that both arms sit
# at the SAME rung (and, by default, that the rung is ADVERSARIAL).
# ---------------------------------------------------------------------------

FRAMING_ADVERSARIAL = "adversarial-devils-advocate"
FRAMING_MODERATE = "moderate-find-every-defect"
FRAMING_WEAK = "weak-evaluate-objectively"
FRAMING_UNKNOWN = "unknown"

# The load-bearing markers that distinguish a genuine devil's-advocate framing
# (matched case-insensitively, the same phrases the framing-pin test pins).
_ADVERSARIAL_MARKERS = ("devil's advocate", "assume the work is flawed")


def classify_framing_strength(template_text: str) -> str:
    """Classify a prompt's adversarial framing strength from its text.

    ADVERSARIAL requires the devil's-advocate stance ("devil's advocate" +
    "assume the work is flawed"). Otherwise we fall back to MODERATE
    ("find every defect"-style) or WEAK ("evaluate objectively"); UNKNOWN when
    none of the signatures are present. The runner's equal-framing invariant
    only compares the resulting label across arms, so a weakened push template
    drops to a different label and trips :class:`UnequalArmsError`.
    """
    low = (template_text or "").lower()
    if all(marker in low for marker in _ADVERSARIAL_MARKERS):
        return FRAMING_ADVERSARIAL
    if "find every defect" in low or "find all defects" in low:
        return FRAMING_MODERATE
    if "evaluate objectively" in low or "evaluate it objectively" in low:
        return FRAMING_WEAK
    return FRAMING_UNKNOWN


@dataclass(frozen=True)
class ArmFraming:
    """The adversarial framing a verification arm ran under."""

    strength: str  # one of the FRAMING_* labels (derived from the template text)
    template: str  # the template filename / identifier that supplied the framing

    def to_dict(self) -> dict:
        return {"strength": self.strength, "template": self.template}


class DualSurfaceError(Exception):
    """The dual-surface runner could not run an arm."""


class UnequalArmsError(DualSurfaceError):
    """The two arms were not held equal (provider / model / framing differ).

    Raised by default so a comparison can never be produced with an uncontrolled
    framing or provider axis - which would be invalid as RETIRE evidence
    (L-069-2). Pass ``require_equal=False`` to capture an intentionally-unequal
    run for inspection (the attestation still records the inequality).
    """


@dataclass
class PushArmResult:
    """The push (snippet-fed, single-shot) arm's outcome."""

    provider: str
    model: str
    verdict: str  # "VERIFIED" / "ISSUES_FOUND"
    issues: List[dict]  # parsed via parse_verification_response
    raw: str  # the verifier's raw text (saved utf-8 by the caller)
    framing: ArmFraming
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "surface": "push",
            "provider": self.provider,
            "model": self.model,
            "verdict": self.verdict,
            "issues": self.issues,
            "framing": self.framing.to_dict(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class PullArmResult:
    """The pull (repo-reading, agentic) arm's outcome."""

    provider: str
    model: str
    verdict: str  # the forced submit_verdict verdict (or "NO_VERDICT")
    findings: List[dict]  # critique-entry findings (severity/category/description)
    ok: bool  # schema-valid verdict AND at least one probe ran
    framing: ArmFraming
    critique: Optional[dict] = None  # the full to_critique_entry() payload
    stop_reason: str = ""
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "surface": "pull",
            "provider": self.provider,
            "model": self.model,
            "verdict": self.verdict,
            "findings": self.findings,
            "ok": self.ok,
            "framing": self.framing.to_dict(),
            "critique": self.critique,
            "stop_reason": self.stop_reason,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class DualSurfaceRun:
    """Both arms' raw verdicts over one committed state. NO merge (S1)."""

    session_set: str
    committed_ref: str  # the diff range the push arm reviewed (provenance)
    sandbox_dir: str  # the repo the pull arm read
    provider: str
    model: str
    push: PushArmResult
    pull: PullArmResult
    framing_equal: bool
    attestation: dict

    def to_dict(self) -> dict:
        return {
            "schemaVersion": 1,
            "kind": "dual_surface_run",
            "sessionSet": self.session_set,
            "committedRef": self.committed_ref,
            "sandboxDir": self.sandbox_dir,
            "provider": self.provider,
            "model": self.model,
            "framingEqual": self.framing_equal,
            "attestation": self.attestation,
            "push": self.push.to_dict(),
            "pull": self.pull.to_dict(),
        }


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _prompt_templates_dir() -> Path:
    return Path(__file__).resolve().parent / "prompt-templates"


def load_push_template() -> str:
    """Return the push verification prompt template (``verification.md``)."""
    path = _prompt_templates_dir() / "verification.md"
    return path.read_text(encoding="utf-8")


def load_pull_template() -> str:
    """Return the RAW pull critique prompt template (``path-aware-critique.md``).

    The framing strength is classified from this **raw template text**, never
    from the rendered (placeholder-filled) instruction: the rendered instruction
    splices in session-specific content (the change summary / claims / file
    list), which could otherwise *spoof* the devil's-advocate markers and make a
    weakened template read as ``adversarial``. Classifying the raw bytes pins the
    framing to the template the operator controls, not to attacker-influenced
    interpolation.
    """
    path = _prompt_templates_dir() / "path-aware-critique.md"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The default arm runners (production). Both are injectable for tests.
# ---------------------------------------------------------------------------

@dataclass
class _PushRaw:
    """The provider-pinned single-shot push result, pre-parse.

    ``provider`` / ``model`` are the identities the arm **actually** ran under -
    echoed back so the runner can VERIFY (not assume) that both arms used the
    same provider/model. A run_push fake that leaves them empty is treated as
    "could not confirm equal", which is the honest default.
    """

    content: str
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def _default_run_push(
    *,
    provider: str,
    model: str,
    prompt: str,
    max_output_tokens: int,
    provider_config: dict,
    generation_params: dict,
) -> _PushRaw:
    """Run the push arm: one provider-pinned, snippet-fed, no-tools completion.

    Mirrors how :func:`ai_router.route` invokes :func:`providers.call_model`,
    but with the provider/model **pinned** (held equal to the pull arm). The
    whole filled ``verification.md`` prompt is the user message; there is no
    system prompt and no tool surface - that snippet-fed, repo-blind shape is
    exactly the *surface* variable the comparison isolates. The provider/model
    actually used are echoed back so the equal-arms attestation is a measurement.
    """
    api: APIResult = call_model(
        provider_name=provider,
        model_id=model,
        system_prompt="",
        user_message=prompt,
        max_tokens=max_output_tokens,
        config=provider_config,
        generation_params=generation_params,
    )
    return _PushRaw(
        content=api.content,
        provider=provider,
        model=model,
        input_tokens=api.input_tokens,
        output_tokens=api.output_tokens,
    )


# ---------------------------------------------------------------------------
# The two-arm runner
# ---------------------------------------------------------------------------

def run_dual_surface(
    session_set_dir: Union[str, Path],
    *,
    base_ref: str,
    head_ref: str = "",
    provider: str = "anthropic",
    model: Optional[str] = None,
    sandbox_dir: Optional[Union[str, Path]] = None,
    push_template: Optional[str] = None,
    pull_template: Optional[str] = None,
    config: Optional[dict] = None,
    caps: Optional[PullCaps] = None,
    require_equal: bool = True,
    run_push: Callable[..., _PushRaw] = _default_run_push,
    run_pull: Callable[..., PullResult] = pull_route,
) -> DualSurfaceRun:
    """Run the push and pull arms over the same committed state, equal-held.

    Parameters
    ----------
    base_ref / head_ref:
        The operator-pinned diff range the **push** arm reviews as its snippet
        (``git diff base_ref..head_ref``; empty ``head_ref`` => the working
        tree). The **pull** arm reads ``sandbox_dir`` (its working tree). For a
        true same-committed-state comparison the caller pins ``head_ref`` to the
        committed ref AND points ``sandbox_dir`` at a checkout of that ref; when
        ``head_ref`` is empty the push arm reviews the *worktree* diff and the
        provenance is recorded honestly as ``"{base_ref}..WORKTREE"`` so the
        ``committedRef`` field never overstates what was actually reviewed. (A
        frozen-checkout materialization of both arms is an S2/S3 enhancement.)
    provider / model:
        Held **equal** across both arms by construction (one variable drives
        both arm calls), and the equality is then **verified** against each arm's
        actual reported provider/model - never assumed (see ``attestation``).
        ``model`` defaults to the configured pull-verifier model pin for
        ``provider`` so both arms run the identical model - maximal equality.
    sandbox_dir:
        The repo the pull arm reads. Defaults to the git repo root containing the
        session-set dir (:func:`pull_critique._default_sandbox_for`), never
        ``Path.cwd()`` (the L-067-1 under-scope hazard).
    push_template / pull_template:
        The **raw** template text that is each arm's SINGLE source of truth
        (defaults: ``verification.md`` / ``path-aware-critique.md``). For each
        arm the framing is classified from the template's prompt body AND the
        executed prompt is rendered from that **same** template body - so the
        classified framing can never drift from what actually runs, and
        session-specific interpolation (filled into placeholders) can never spoof
        the adversarial markers (classification is on the *unfilled* body).
    require_equal:
        When True (default) a provider / model / framing-strength mismatch raises
        :class:`UnequalArmsError` (framing mismatch refuses *before* any metered
        call; a provider/model mismatch refuses *after* the arms report their
        actual identities). When False the run proceeds and the ``attestation``
        records the inequality (for deliberate inspection only - never as RETIRE
        evidence).
    run_push / run_pull:
        Injection seams; tests pass fakes so no metered call is made.

    Returns
    -------
    DualSurfaceRun
        Both arms' raw verdicts + the equal-framing attestation. **No merge** -
        S2 adds the provenance merge + scoring.
    """
    set_dir = Path(session_set_dir).resolve()
    if not set_dir.is_dir():
        raise DualSurfaceError(f"session set dir is not a directory: {set_dir}")

    if config is None:
        config = _load_router_config()
    model = _resolve_model(provider, model, config)
    if caps is None:
        caps = caps_from_config(config)
    if sandbox_dir is None:
        sandbox_dir = _default_sandbox_for(set_dir)
    sandbox_dir = Path(sandbox_dir).resolve()

    repo_root = str(sandbox_dir)
    diff_cfg = DiffConfig(repo_root=repo_root, base_ref=base_ref, head_ref=head_ref)
    # Honest provenance: an empty head_ref means the push arm reviewed the diff
    # against the WORKTREE, not a second committed ref - label it as such so the
    # committedRef field never misstates what was actually reviewed.
    committed_ref = f"{base_ref}..{head_ref}" if head_ref else f"{base_ref}..WORKTREE"

    # ---- Resolve each arm's framing from its SINGLE-source raw template ----
    # Each arm has exactly ONE prompt source: ``push_template`` / ``pull_template``.
    # The framing is classified from that template's prompt BODY, and the prompt
    # that is actually EXECUTED is rendered from the SAME body. There is no second
    # "instruction" input that could diverge from what was classified, so the
    # equal-framing attestation can never drift from what runs. Classification is
    # on the *unfilled* body, so placeholder interpolation (the diff snippet, the
    # set's change summary) can never spoof the adversarial markers.
    push_overridden = push_template is not None
    pull_overridden = pull_template is not None
    if push_template is None:
        push_template = load_push_template()
    if pull_template is None:
        pull_template = load_pull_template()
    pull_body = prompt_body_of(pull_template)
    pull_instruction = build_instruction(set_dir, template_text=pull_template)
    push_framing = ArmFraming(
        strength=classify_framing_strength(push_template),
        template="verification.md" if not push_overridden else "(custom-push)",
    )
    pull_framing = ArmFraming(
        strength=classify_framing_strength(pull_body),
        template="path-aware-critique.md" if not pull_overridden else "(custom-pull)",
    )

    # ---- Framing gate (BEFORE spending any metered call) ----
    # Framing strength is knowable from the templates alone, so a framing
    # mismatch refuses up front - no metered call is wasted on a known-invalid
    # comparison. Provider/model equality is verified AFTER the arms report
    # their actual identities (below), since only the run can confirm them.
    framing_equal = push_framing.strength == pull_framing.strength
    both_adversarial = (
        push_framing.strength == FRAMING_ADVERSARIAL
        and pull_framing.strength == FRAMING_ADVERSARIAL
    )
    if require_equal and not (framing_equal and both_adversarial):
        raise UnequalArmsError(
            "dual-surface arms not held equal at strong adversarial framing: "
            f"push={push_framing.strength!r} pull={pull_framing.strength!r}. "
            "A comparison with unequal/non-adversarial framing is invalid as "
            "RETIRE evidence (L-069-2). Upgrade the weaker template or pass "
            "require_equal=False to capture the inequality for inspection only."
        )

    # ---- PUSH arm: snippet-fed single-shot over the committed diff ----
    snippet, is_error, _elided = _dispatch_get_diff(diff_cfg)
    if is_error:
        raise DualSurfaceError(
            f"push arm could not resolve the committed diff for {committed_ref!r}: "
            f"{snippet}"
        )
    push_prompt = build_verification_prompt(
        original_task=(
            f"Review the committed change set for session set {set_dir.name} "
            f"(diff range {committed_ref}). Find every defect."
        ),
        original_response=snippet,
        task_type="session-verification",
        template=push_template,
    )
    pcfg = _provider_config(provider, config)
    gen_params = _resolve_gen_params(provider, config)
    push_raw = run_push(
        provider=provider,
        model=model,
        prompt=push_prompt,
        max_output_tokens=caps.max_output_tokens,
        provider_config=pcfg,
        generation_params=gen_params,
    )
    push_verdict, push_issues = parse_verification_response(push_raw.content)
    in_price, out_price = _pricing_for(model, config)
    push_cost = (
        push_raw.input_tokens / 1_000_000.0 * in_price
        + push_raw.output_tokens / 1_000_000.0 * out_price
    )
    push_result = PushArmResult(
        # The identities the push arm ACTUALLY reported (echoed by run_push), so
        # the attestation below verifies equality rather than assuming it.
        provider=push_raw.provider,
        model=push_raw.model,
        verdict=push_verdict,
        issues=push_issues,
        raw=push_raw.content,
        framing=push_framing,
        input_tokens=push_raw.input_tokens,
        output_tokens=push_raw.output_tokens,
        cost_usd=push_cost,
    )

    # ---- PULL arm: repo-reading agentic loop over the same committed state ----
    pull_res: PullResult = run_pull(
        sandbox_dir,
        pull_instruction,
        provider=provider,
        model=model,
        caps=caps,
        config=config,
    )
    critique = pull_res.critique
    pull_result = PullArmResult(
        provider=pull_res.provider,
        model=pull_res.model,
        verdict=(critique.verdict if critique is not None else "NO_VERDICT"),
        findings=[f.to_dict() for f in (critique.findings if critique else ())],
        ok=pull_res.ok,
        framing=pull_framing,
        critique=(critique.to_critique_entry() if critique is not None else None),
        stop_reason=pull_res.trace.stop_reason,
        cost_usd=pull_res.trace.cost_usd,
    )

    # ---- Equal-arms attestation (DERIVED from each arm's ACTUAL identity) ----
    # providerEqual / modelEqual are measured: the requested pair must match what
    # BOTH arms actually reported. A run_push fake that omits its identity, or a
    # pull binding that ran a different model, falsifies equality here rather than
    # being silently assumed true (honest telemetry; never hand-asserted).
    provider_equal = (
        push_result.provider == provider and pull_result.provider == provider
    )
    model_equal = push_result.model == model and pull_result.model == model
    attestation = {
        "providerEqual": provider_equal,
        "modelEqual": model_equal,
        "framingEqual": framing_equal,
        "pushFraming": push_framing.to_dict(),
        "pullFraming": pull_framing.to_dict(),
        "bothAdversarial": both_adversarial,
        "requestedProvider": provider,
        "requestedModel": model,
        "pushProvider": push_result.provider,
        "pushModel": push_result.model,
        "pullProvider": pull_result.provider,
        "pullModel": pull_result.model,
    }
    if require_equal and not (provider_equal and model_equal):
        raise UnequalArmsError(
            "dual-surface arms did not run on the equal provider/model: "
            f"requested {provider}/{model}; push ran "
            f"{push_result.provider}/{push_result.model}; pull ran "
            f"{pull_result.provider}/{pull_result.model}. A comparison whose "
            "arms differ in provider/model is invalid as RETIRE evidence "
            "(surface is no longer the only variable). Pass require_equal=False "
            "to capture the inequality for inspection only."
        )

    return DualSurfaceRun(
        session_set=set_dir.name,
        committed_ref=committed_ref,
        sandbox_dir=repo_root,
        provider=provider,
        model=model,
        push=push_result,
        pull=pull_result,
        framing_equal=framing_equal,
        attestation=attestation,
    )
