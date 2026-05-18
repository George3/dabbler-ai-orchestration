"""Route Set 029 Session 1 Bucket-2 consensus questions to GPT-5.4 + Gemini Pro.

Applies the in-session delegation pattern operator authorized
2026-05-18 (memory: feedback_prefer_ai_consensus_over_human_prompt).
The Round-A verifier (gpt-5-4) returned REJECTED with 7 Bucket-2
design refinements that need judgment calls. Rather than surface
each one to the operator, this script presents Claude's proposed
defaults to both reviewers and asks for accept / modify / reject
verdicts per item. Convergence -> apply. Divergence -> escalate.

Per memory feedback_ai_router_route_result_handling, the RouteResult
is dumped to JSON before any field access.

Per memory feedback_audit_then_spec_for_substantial_features, the
operator wants three-way agreement before non-trivial work begins;
this is the third leg.

Per memory feedback_ai_router_usage, this is an in-session router
call. The new memory feedback_prefer_ai_consensus_over_human_prompt
explicitly carves an exception for design/process consensus.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT))

import ai_router  # noqa: E402


CONSENSUS_PROMPT = """\
# Set 029 Session 1 — Bucket 2 design refinements consensus call

## Context

Set 029 ships a small VS Code webview view above the Dabbler Session
Set Explorer that shows the current orchestrator's model + effort
level as two semi-circle CSS gauges. Operator's failure mode: a
session silently starts on a lower-tier model after dialing down for
a cheap task and forgetting to dial back up.

Session 1 is the cross-provider design audit. The audit synthesis
(`audit-summary.md`) locked Q1-Q6 and resolved 5 showstoppers. A
session-verification call against the synthesis came back REJECTED
with 7 design refinements (the "Bucket 2" must-fix items below).

The verifier was gpt-5-4. Gemini Pro was silent on most Q1-Q6
specifics in the original audit. For each of the 7 items below, I
(Claude Opus 4.7, the synthesis author) have a proposed default
fix. **I'm asking each of you to independently verdict each item
as ACCEPT_AS_PROPOSED, MODIFY (with specifics), or REJECT (with
alternative).**

If both engines independently ACCEPT_AS_PROPOSED, that's consensus
and I apply the fix. If you MODIFY or REJECT, name the specific
change. If the two engines diverge, the operator decides.

Be specific and concrete. Skip stylistic nits. Focus on whether the
proposed fix (a) actually addresses the verifier's concern, (b)
remains internally consistent with the rest of the audit, and (c)
is implementable within Session 2/3 scope.

---

## Item B2-1: Multi-writer precedence policy (Q7 #1 — only true architectural gap)

**Verifier concern:** marker file `~/.dabbler/current-orchestrator.json`
is global and single-canonical; four providers may write it
concurrently. Current "last write wins" lets a Codex `configured-default`
background write stomp a fresh Claude `current` signal. Verifier:
"Define precedence before Session 3."

**Proposed fix:** Adopt the following precedence + arbitration policy
in `audit-summary.md` § "Marker file schema (REVISED — locked)":

> **Multi-writer precedence (NEW).** Marker writers MUST read the
> current file, compare `signalKind` precedence, and skip the write
> if the proposed signal is weaker than the existing fresh signal.
>
> Precedence (high → low): `current` > `manual` > `last-observed` >
> `configured-default`.
>
> Decision tree (run by every writer, including the Codex
> config.toml watcher and the manual-override quickpick):
>
> 1. Read existing marker. If missing → write unconditionally.
> 2. If existing `updatedAt` is older than `stalenessMaxSec` (8h
>    default) → write unconditionally; stale signals never block a
>    fresh write.
> 3. If proposed `signalKind` precedence ≥ existing `signalKind`
>    precedence → write.
> 4. Otherwise → skip write; log a "skipped: stronger signal exists"
>    line to `~/.dabbler/orchestrator-writer.log` for operator
>    diagnostics.
>
> The manual-override quickpick has an "override stronger signal"
> escape hatch: when invoked, it offers a "Force override existing
> Claude live signal?" confirmation if it detects a fresher
> `current` signal from another writer.

**Implementation surface:** `write-orchestrator-marker.js` (shared
helper from Session 2) and the manual-override command (Session 3).
~30 LOC added to the shared helper.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-2: configured-default vs stale visual collision (Q3 verifier finding)

**Verifier concern:** the visual-treatment matrix uses diagonal
stripes for `configured-default` AND stripes (with desaturation)
for stale state. At ≤100px gauge size these are too similar to
distinguish reliably.

**Proposed fix:** reassign visual treatments. Diagonal stripes
become STALE-ONLY. `configured-default` gets dashed rim + a small
"DEFAULT" pill badge below the model name. Updated matrix in
`audit-summary.md`:

| signalKind | Gauge fill | Rim | Sublabel suffix | Badge | Tooltip |
|---|---|---|---|---|---|
| `current` | Solid color | Solid | (none) | (none) | "live signal" |
| `configured-default` | Solid color (~85% opacity) | Dashed | "(default)" | "DEFAULT" pill | "configured default from ~/.codex/config.toml — does not track runtime changes" |
| `last-observed` | Hollow rim + filled needle | Solid | "(last /think Xm ago)" | small clock icon | "last observed Xm ago via /think" |
| `manual` | Solid + operator-icon overlay | Solid | "(manual)" | (overlay only) | "set manually at HH:MM" |

Stale state (signal-agnostic): diagonal hatch overlay at 50%
opacity over whatever the underlying signalKind treatment is, plus
"last updated Xh ago" annotation. No install-hook CTA.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-3: last-observed visual still too close to live (Q2 verifier finding)

**Verifier concern:** at small gauge sizes the `last-observed`
hollow-rim treatment plus "(last)" suffix may still read as a live
signal at a glance, recreating the failure mode the feature exists
to prevent.

**Proposed fix:** strengthen with three additive cues (folded into
the matrix in B2-2):
1. Hollow rim + filled needle (existing).
2. Small clock-icon overlay top-right of the gauge (NEW).
3. Sublabel suffix now includes the time elapsed: "(last /think
   12m ago)" instead of just "(last)". The time-elapsed is the
   strongest "this is not live" cue because it visibly ages.

The clock icon is rendered as inline SVG, ~12×12px, with `aria-label`
"last observed signal" for screen readers.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-4: Windows retry ceiling too short (Q2/S5 verifier finding)

**Verifier concern:** the locked 3-attempt retry loop at 50/150/400ms
totals 600ms, which is likely below typical Windows file-lock /
antivirus contention window during file-watcher activity. Verifier
suggested ~1-2s ceiling.

**Proposed fix:** bump to 4 attempts (initial + 3 retries) at
50/200/600/1200ms backoff = 2050ms total ceiling. Apply uniformly
across all writers (Claude SessionStart hook script, Codex
config.toml watcher, manual-override quickpick). Document the
ceiling in `audit-summary.md` § S5 and `spec.md` lines 304-305 and
513-514.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-5: initial-size guarantee unrealistic (Q2/S3 verifier finding)

**Verifier concern:** dropping `initialSize` from the contributes.views
block means VS Code may restore a user-resized height that doesn't
fit the ≤100px content. The audit-summary doesn't plainly state
this limitation.

**Proposed fix:** add explicit limitation to `audit-summary.md` § S3
mitigation and to the CHANGELOG entry for 0.13.18:

> **Container height cannot be guaranteed.** The orchestrator
> indicator content is sized to fit within 100px of vertical space,
> but VS Code persists user-resized view heights across sessions and
> across extension updates. If the operator has previously dragged
> the view divider to a different height, that height is restored.
> To reset: right-click the view header → "Reset Location" (or drag
> the divider back). The CSS uses `overflow: auto` to keep the
> content scrollable if compressed below 100px; gauges remain
> visible but may scroll horizontally.

Add a Playwright assertion that the content area fits within 100px
in a clean profile (the existing screenshot assertion). No
guarantee for resized profiles.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-6: confidence field justification or drop (Q3 verifier finding)

**Verifier concern:** the `confidence` field in marker schema v2
appears only in schema text and a vague tooltip mention. Either
make it pull weight or drop it.

**Proposed fix:** KEEP and operationalize. Tooltip copy in
`audit-summary.md` § "Visual treatment by signalKind" now embeds
confidence explicitly:

- `current` + `confidence: "high"` → "live signal (high confidence)"
- `configured-default` + `confidence: "medium"` → "configured
  default (medium confidence — does not track runtime changes)"
- `last-observed` + `confidence: "high"` → "last observed via
  /think (high confidence in detection, but may not reflect
  current message)"
- `manual` + `confidence: "high"` → "set manually (high confidence)"

Future-use: a per-provider downgrade path. E.g., if Claude
SessionStart hook fires but model field is empty/null, marker
writes `signalKind: "current"` + `confidence: "low"` + `model:
"unknown"`, and the gauge tooltip says "live signal (low confidence —
hook payload missing model)". Lets the schema flex without changing
visual-treatment categories.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Item B2-7: SessionStart-on-/clear behavior unknown (Q7 #3 verifier finding)

**Verifier concern:** if Claude's `/clear` command fires SessionStart,
the Medium-effort reset will clobber a recent `last-observed`
`/think*` signal. Audit didn't consider this.

**Proposed fix:** add to `spec.md` Session 2 step 5 (the
SessionStart hook installer):

> **Pre-implementation verification:** verify whether `/clear`
> fires the SessionStart hook. If yes, the Medium reset is desired
> (operator chose to start a new context). If `/clear` runs a
> different lifecycle event without SessionStart, the marker's
> `last-observed` effort persists across the clear — document this
> as a known asymmetry in CHANGELOG.

Add new risk R7 to `spec.md` § Risks:

> **R7 — /clear-vs-SessionStart asymmetry.** If `/clear` does not
> fire SessionStart, the gauge may display stale `last-observed`
> effort from before the clear. Mitigation: document in CHANGELOG;
> operator has manual-override quickpick as universal reset.

**Verdict requested:** ACCEPT_AS_PROPOSED / MODIFY / REJECT?

---

## Format for your response

Respond with exactly seven verdict blocks, in order:

```
B2-1: ACCEPT_AS_PROPOSED | MODIFY (...) | REJECT (...)
B2-2: ...
B2-3: ...
B2-4: ...
B2-5: ...
B2-6: ...
B2-7: ...
```

For MODIFY, name the specific change. For REJECT, name the
alternative. Keep each verdict block under 5 lines.

If you find a Bucket-1 doc-fix item that's also worth flagging
(beyond the 7 above), add a final "Additional observations" section
under 10 lines. Otherwise skip.
"""


def _dump(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    return {
        "content": getattr(result, "content", None),
        "model_name": getattr(result, "model_name", None),
        "model_id": getattr(result, "model_id", None),
        "tier": getattr(result, "tier", None),
        "input_tokens": getattr(result, "input_tokens", None),
        "output_tokens": getattr(result, "output_tokens", None),
        "cost_usd": getattr(result, "cost_usd", None),
        "total_cost_usd": getattr(result, "total_cost_usd", None),
        "elapsed_seconds": getattr(result, "elapsed_seconds", None),
    }


def _run_one(model: str, content: str, out_path: Path) -> dict:
    print(f"\n{'='*60}\n[{model}] sending consensus call...\n{'='*60}")
    result = ai_router.query(
        model=model,
        content=content,
        task_type="session-verification",
        session_set=str(
            REPO_ROOT
            / "docs"
            / "session-sets"
            / "029-orchestrator-model-effort-gauges"
        ),
        session_number=1,
    )
    dumped = _dump(result)
    out_path.write_text(
        json.dumps(dumped, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    cost = dumped.get("total_cost_usd") or dumped.get("cost_usd") or "?"
    print(
        f"[{model}] cost=${cost} "
        f"in={dumped.get('input_tokens')} out={dumped.get('output_tokens')}"
    )
    print(f"[{model}] saved to: {out_path}")
    text = dumped.get("content") or dumped.get("response") or dumped.get("text")
    if isinstance(text, str):
        print(f"\n--- [{model}] OUTPUT ---\n{text}\n--- end [{model}] ---")
    return dumped


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("--only-gpt", "--only-gemini"):
        which = sys.argv[1]
    else:
        which = "--both"

    if which in ("--both", "--only-gpt"):
        _run_one("gpt-5-4", CONSENSUS_PROMPT, HERE / "consensus-gpt-5-4.json")
    if which in ("--both", "--only-gemini"):
        _run_one("gemini-pro", CONSENSUS_PROMPT, HERE / "consensus-gemini-pro.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
