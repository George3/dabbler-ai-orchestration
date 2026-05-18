# Session 1 verification prompt — Set 029 (orchestrator model & effort indicator gauges)

## Context

Set 029 ships a small VS Code webview view that pins above the
Dabbler Session Set Explorer and shows the current orchestrator's
**model** and **effort level** as two side-by-side semi-circle CSS
gauges. The operator-facing failure mode being eliminated: a session
silently starts on a lower-tier model after the operator dialed down
for a cheap task and forgot to dial back up.

Set 029 is structured as **audit-then-implement**, four sessions:

- **Session 1** (this one): cross-provider design audit. Lock six
  open design questions (Q1–Q6) and any showstoppers reviewers
  raise. Produce `audit-summary.md`. Update `spec.md`.
- **Session 2**: core webview + Claude detection + hook installer.
- **Session 3**: non-Claude detection (Codex auto, Gemini/Copilot
  manual-only) + manual-override quickpick.
- **Session 4**: polish + Marketplace publish.

Session 1's audit was conducted by manual paste-and-collect against
GPT-5.4 and Gemini Pro — not via `ai_router.route()` — per memory
`feedback_ai_router_usage` (router reserved for end-of-session
verification only). The two reviewer responses live at
`docs/proposals/2026-05-17-model-effort-gauges-design-audit/`
(`gpt-5-4-result.json`, `gemini-pro-result.json`). The orchestrator
(Claude Opus 4.7) synthesized them into `audit-summary.md`, then
updated `spec.md` to mark Q1–Q6 RESOLVED and to incorporate the
five resolved showstoppers (S1–S5).

## What you're being asked to verify

Set 029 Session 1 produces **only docs** — no executable code (one
helper script was scoped but waived). Your verification is therefore
a **doc-only synthesis review**.

The artifacts inlined below are:

1. **`audit-summary.md`** — the synthesis under review. Locks
   Q1–Q6, resolves S1–S5, defines the marker schema v2 with
   `signalKind` + `confidence`, defines the visual-treatment matrix
   per `signalKind`, and prescribes the manual-override quickpick UX.
2. **`gpt-5-4-result.json`** — GPT-5.4's raw audit response (the
   input to the synthesis).
3. **`gemini-pro-result.json`** — Gemini Pro's raw audit response
   (also input).
4. **Spec excerpts** — the `spec.md` sections that changed as a
   result of the audit (D6 effort table, D7 marker path, D8 hook
   installer matrix, Q1–Q6 RESOLVED stubs, Sessions 2 & 3 rewritten
   steps, R5/R6 risks).

Please answer the following. A structured response (per-question
verdict + reasoning + any concrete must-fix items) is fine.

**Q1. Faithful synthesis of reviewer verdicts.** For each of
Q1–Q6, does `audit-summary.md`'s locked verdict accurately reflect
what GPT-5.4 and Gemini Pro actually said in their raw responses?
Flag any cases where the summary claims a reviewer "agreed" with
something the reviewer didn't actually opine on, or where a
reviewer's stated concern was lost in synthesis. Note: the summary
acknowledges Gemini was silent on Q2/Q3/Q4/Q6 — verify that
GPT-5.4's verdict alone on those questions is defensible from the
GPT raw response.

**Q2. Showstopper mitigations.** Five showstoppers (S1–S5) are
listed with mitigations. For each, is the mitigation an actual fix
(addresses the root cause) or does it merely defer the problem?
Specifically:
- **S1 / S4** (Claude Stop hook lacks `model` field / Stop timing
  is lagging) → switch to `SessionStart`. Is `SessionStart` actually
  documented to carry a `model` field (per GPT-5.4's primary-doc
  citation in its raw response)? Does it fire at the right time?
- **S2** (`/think*`-as-effort recreates the failure mode) → Medium
  default + `signalKind: "last-observed"` for observed `/think*`.
  Does the `"last-observed"` visual treatment (hollow rim + filled
  needle, sublabel suffix "(last)") *really* prevent the operator
  from misreading it as a live signal, or does it still look
  similar enough at a glance to recreate the failure?
- **S3** (`initialSize` is not a real VS Code contributes.views
  property) → drop it; rely on Playwright screenshot assertions.
  Is screenshot assertion an adequate substitute for guaranteed
  initial sizing, given the operator's hard ≤100px constraint?
  What happens if the user has previously dragged the view to a
  different height?
- **S5** (Windows atomic-write contention with file watcher) →
  retry loop with 3 attempts at 50/150/400ms backoff. Is this
  bounded-retry shape likely to succeed against Windows
  PermissionError behavior, or does the upper bound need to be
  longer? Is there a risk the retry loop itself triggers the
  watcher repeatedly and amplifies the contention?

**Q3. Marker schema v2 sanity.** The v2 schema (lines 167–190 of
`audit-summary.md`) introduces `signalKind`, `confidence`, and
nested `effort.signalKind` / `effort.confidence`. Verify:
- The four `signalKind` values (`current`, `configured-default`,
  `last-observed`, `manual`) cover all four provider × signal
  combinations Sessions 2 and 3 will produce. Any gap?
- The visual-treatment matrix (lines 207–213) maps each
  `signalKind` to a distinct visual treatment. Are all four
  visually distinguishable at gauge sizes that fit in a ≤100px
  webview, given typical VS Code rendering at 1×/1.5×/2× DPI?
  (Specifically: solid vs. striped fill at small sizes.)
- Is `confidence` actually used anywhere in the design? If it
  only appears in a tooltip, is the field worth its weight in the
  schema?

**Q4. Spec-vs-summary consistency.** Read the spec excerpts
inlined below against `audit-summary.md`. Any drift between the
two — e.g., a decision worded one way in the summary and a different
way in the spec, or a step in Session 2/3 that contradicts a locked
audit verdict? Pay particular attention to:
- D8 (hook installer matrix) — does it match the locked
  Claude=SessionStart / Codex=config-toml-watcher / Gemini-Copilot=
  manual-only pattern from the audit?
- Effort table D6 — does the Claude column match the Medium-default
  + last-observed-`/think*` resolution from Q1?
- Sessions 2 step 6 (effort tracking via `UserPromptSubmit` hook)
  — the audit notes uncertainty about whether `UserPromptSubmit`
  exposes message text; does the spec adequately gate the
  implementation on that uncertainty (i.e., verify field
  availability first; fall back to Medium-only if not)?
- R5 + R6 in the spec's Risks section — present and consistent
  with their audit-summary sources?

**Q5. Step-2 waiver implications.** Session 1 spec step 2
prescribed authoring `route_audit.py` and invoking
`ai_router.route(task_type='cross-provider-audit')` for both
reviewers. The audit was instead conducted by manual paste-and-
collect at $0.00 cost, per memory `feedback_ai_router_usage`. Does
this waiver introduce any traceability or reproducibility gap that
would bite Session 2 or a future maintainer reading the audit trail?
Specifically:
- Are the raw reviewer responses (`gpt-5-4-result.json`,
  `gemini-pro-result.json`) sufficient on their own to re-derive
  the synthesis if the audit-summary were lost?
- Is the prompt that was actually sent to each reviewer recoverable
  from the current artifacts (the proposal.md is preserved, but is
  it clear that's what was pasted)?
- Should the step-2 waiver be documented somewhere durable beyond
  the activity log so that Session 2/3/4 don't expect a
  `route_audit.py` to exist?

**Q6. Session 2 buildability.** Reading only `audit-summary.md`
and the `spec.md` excerpts (not this prompt), could a fresh
orchestrator pick up Session 2 cold and ship the Claude path?
Identify the smallest concrete gap that would force them to circle
back to a design decision.

**Q7. Open architectural questions.** Specifically:
- The marker file is at `~/.dabbler/current-orchestrator.json`
  (global, single canonical file). Multiple orchestrator surfaces
  write the same file. The audit prescribes write-and-rename with
  retry loop — but does the design address what happens when two
  surfaces are *simultaneously* active (e.g., the operator has
  Claude Code AND Cursor's Codex pane open)? Whose write wins, and
  is that the right behavior?
- The stale threshold (`stalenessMaxSec`, default 8h) — is 8h the
  right default for the operator's stated workflow (multi-day
  session sets with breaks)? Should it be a per-set or per-
  workspace override rather than a global setting?
- The `signalKind: "last-observed"` for Claude effort resets to
  Medium on `SessionStart`. Does "SessionStart" in Claude Code
  fire on every `/clear` or only on truly new sessions? If `/clear`
  fires SessionStart, the gauge could clobber a recently-set
  `/megathink` indicator unexpectedly. Audit consider this?

**Q8. Overall.** Is Set 029 Session 1 ready to close out? If not,
the smallest concrete change to get it there.

Short, structured response. Per-question verdict + reasoning + any
must-fix items. Skip stylistic nits.
