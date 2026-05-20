# H4 follow-up: holder identity key for check-out conflict comparison

> **Date:** 2026-05-19 (Set 032 Session 1 — follow-on to the
> audit-resolution packet)
> **Context:** GPT-5.4 confirmed all five original items
> (H1, H2, H3, OQ1, OQ2) but raised a NEW must-resolve as **H4**.
> You confirmed all five originals; you have not yet seen H4.
> The other reviewer is **GPT-5.4**. This packet asks you to
> confirm / refine / refute the pre-audit verdict on H4 only.

---

## The H4 problem (verbatim from GPT-5.4)

> The packet still does not define what counts as the same
> orchestrator for conflict checks. The existing `orchestrator`
> block contains mutable fields such as `model` and `effort`, and
> the recommended OQ1 verdict explicitly allows in-place updates
> like effort changes and `lastActivityAt` refreshes. Set 033
> therefore needs an explicit holder-equality rule: either a
> stable subset of fields or a dedicated immutable owner key
> nested inside `orchestrator`. Without that, H3's hard-refusal
> path risks false conflicts or accidental lock stealing.

## Why this matters

H3 locks "hard coordination at write time": `start_session` refuses
to write when a different orchestrator holds the check-out. OQ1
merges check-out state into the existing `orchestrator: { engine,
provider, model, effort }` block plus new `checkedOutAt` /
`lastActivityAt` timestamps. With `effort` mutable (via `/think*`)
and `model` potentially mutable (e.g., Claude Opus → Claude Sonnet
mid-session switch is a real case), the conflict-comparison rule
must specify WHICH FIELDS DEFINE IDENTITY.

If we compare the whole block: an `effort` change from medium to
high looks like a different holder → false conflict. If we compare
nothing: two genuinely different orchestrators (Claude vs. Codex)
never trigger a conflict → architecture defeats its own purpose.

## H4 pre-audit recommended verdict

**Holder identity = `engine`.** Specifically: the conflict-equality
predicate compares the `engine` field only. Other fields under
`orchestrator` (`provider`, `model`, `effort`) are MUTABLE display
state that may be updated in place by the holder during the
session without triggering a conflict.

**Rationale:**

- `engine` is the stable identifier for "which orchestrator is
  driving" (claude / gpt-5-4 / gemini-pro / codex / copilot).
- `provider` is derivable from `engine` in nearly all cases
  (claude → anthropic, gpt-5-4 → openai, gemini-pro → google) and
  adds no real distinguishing power.
- `model` is mutable in legitimate cases (operator switches Claude
  Opus → Sonnet mid-session for cost; this is the SAME
  orchestrator and should not trigger conflict). Adding `model`
  to identity would force a force-override on every model swap.
- `effort` is explicitly mutable per the existing `/think*` flow
  and the OQ1 verdict's "in-place updates" framing.

**Schema implication:** No new fields. The `engine` field already
exists in `session-state.json`'s `orchestrator` block. Set 033
documents (in `docs/session-state-schema.md` + the close-out doc)
that `engine` is the identity key for conflict comparison and the
other three fields are mutable holder-state.

**Alternative considered and rejected:** add a new immutable
`orchestratorOwnerKey` field at check-out time. Rejected because
(a) it duplicates `engine` for no information gain; (b) it adds
a hand-maintenance burden for Lightweight tier; (c) the
"dedicated immutable owner key" framing was offered as one of
two options by GPT — `engine`-as-key is the equivalent of "stable
subset" in their phrasing, just narrowed to one field.

**Edge case worth flagging in Set 033 spec:** if a future
`engine` value collides (e.g., two distinct claude-via-X providers
end up with `engine: "claude"`), the rule needs to extend to
`engine + provider`. For the current registered set of engines
(claude, gpt-5-4, gemini-pro, codex, copilot), `engine` alone is
sufficient.

---

## Response format

Same as the original packet:

```
Item: H4
Verdict: confirm | refine | refute
Reasoning: 2-5 sentences.
If refine/refute: proposed alternative + why it beats `engine`-only.
```

Plus one final sentence: any *other* must-resolve items you see
on second pass that the original audit-resolution packet missed?
(If none, just say "no additional items.")
