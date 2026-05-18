# Synthesis — custom-tree pivot consensus call

**Date:** 2026-05-18
**Inputs:** `consensus-gpt-5-4-manual.md` (GPT-5.4, manual paste in GitHub Copilot), `consensus-gemini-pro.json` (Gemini Pro via `dabbler-ai-router`, $0.0225)
**Status:** Awaiting operator decision on three divergences before S3 spec delta is drafted.

---

## Both reviewers agree

| Item | Verdict |
|---|---|
| **Core insight: per-session-set identity is the right model** | Both: approve |
| **Q1 — Storage shape:** in-tree under `<set>/.dabbler/orchestrator.json`, gitignored | Both: Shape A |
| **Q1 must-fix:** auto-patch `.gitignore` on init (non-interactive) | Both raise this |
| **Q2 — Reject `most-recently-modified` heuristic** | Both must-fix |
| **Q4 — Auto-expand defaults** | Both concur with proposal (GPT adds: key suppression to current session occurrence, not the set indefinitely) |
| **Q5 — Multi-window: both windows show same truth** | Both concur (GPT adds: include a freshness cue) |
| **Q6 — Add `sessionSetSlug`, bump to schema v3, validate on render** | Both must-fix |
| **Q7 — Don't defer ARIA, kbd nav, context menus** | Both must-fix (GPT adds: loading-state and `viewsWelcome` parity also v1) |
| **Q8 — Layer 2 model extraction in same change** | Both must-fix |
| **Q9 — Version bump to 0.15.0** | Both concur |
| **Q10 — Non-Claude provider work OUT of S3** | Both concur |

Twelve of the proposal's structural choices are ratified by both reviewers. Three diverge.

---

## Divergences — operator decisions needed

### D1. Packaging: bundled S3 vs. split into two

This is the **largest divergence** and shapes everything downstream.

**Gemini Pro:** Bundle. Approves the full pivot (identity + custom tree) as one S3, with the must-fix items above absorbed into scope. Argues "land the new foundation correctly first."

**GPT-5.4:** Split. *Approves the identity pivot but rejects the bundled custom-tree rewrite in the same S3.* Argues the reimplementation surface is larger than the proposal scopes:

> the row menu currently exposes 14 item-context actions… parity is not just up/down/enter/right-click; it also includes the loading-to-empty transition and command visibility rules.

GPT-5.4's proposed split:
- **S3:** per-session-set identity, marker-schema v3, hook-to-set resolution, `SessionSetsModel` data-layer extraction. **Native `TreeView` stays.** The current `WebviewView` indicator continues to render, but reads from a per-set marker resolved by the workspace-folder context (one indicator shows the most-recently-touched in-progress set, or "no set" if none).
- **Follow-on session:** custom webview tree, with parity requirements and tests spec-locked first.

**My read:** GPT-5.4's split-the-deliverables case is strong. The 14-row-context-menu surface plus the loading sentinel + scan-state gating + `viewsWelcome` are real and the proposal under-scopes them. Splitting de-risks. The cost is one extra session in Set 029 (which goes from 4 → 5 → 6) and a longer total runway, but each session ships a coherent improvement.

The case for Gemini's bundle: a single landing avoids a short-lived intermediate state where per-set markers exist but the renderer hasn't caught up to anchor them in-row.

### D2. Q2 mechanism (assuming ambiguity remains a v1 concern)

Both reject the heuristic. Both diverge on what replaces it.

**Gemini Pro:** Quick Pick on first ambiguous SessionStart per workspace. Persist the choice in `workspaceState`. Provide a `Dabbler: Reset ambiguous orchestrator association` command.

**GPT-5.4:** Fail closed. Don't attach the marker to a set row when ambiguous; log and render only as unassigned recent activity. Thread an explicit set identifier through the hook setup as the clean fix.

**My read:** GPT-5.4's "fail closed" is more conservative and matches `feedback_default_not_started_evidence_to_escalate` — when in doubt, require positive evidence to escalate. Gemini's Quick Pick is more user-friendly but adds new UI surface. If we adopt GPT-5.4's split (D1), the Quick Pick becomes harder to justify since the custom-tree work where it would live is deferred anyway.

### D3. Q3 orphan handling (Claude session outside any session set)

**Gemini Pro:** (c) workspace-level orphan marker rendered as special row labeled "Orchestrator (no active set)".

**GPT-5.4:** (a) top-level recent-activity pseudo-section. **Rejects (c)** — "a workspace-level orphan path reintroduces the very scope the proposal says is wrong."

**My read:** GPT-5.4 is right on the architecture point — if identity is per-set, falling back to a workspace-level marker quietly readmits workspace identity into the model. (a) is more honest about what the data represents. Cost: introduces a new UI concept ("recent activity" section). If D1 = split, this question moves to the follow-on session anyway.

---

## What changes regardless of D1/D2/D3

Even with no further input, ten must-fix items from the consensus call will land in whichever spec we draft:

1. Storage = Shape A; auto-patch `.gitignore` on init.
2. Reject `most-recently-modified` heuristic.
3. Bump marker schema to v3; add `sessionSetSlug` as an integrity field; reader validates slug matches host row before render.
4. ARIA, kbd nav, context menus, loading state, and `viewsWelcome` parity are v1 (if/when custom tree ships).
5. `SessionSetsModel` data-layer extraction is mandatory whenever the custom tree ships.
6. Non-Claude provider work deferred out of the custom-tree session.
7. Version bump to 0.15.0.
8. Auto-expand suppression keyed to the current session occurrence (GPT-5.4's refinement on Q4).
9. Freshness cue ("updated Xs ago") visible on shared multi-window state (GPT-5.4's refinement on Q5).
10. Layer 2 tests rewritten against `SessionSetsModel` rather than retired without replacement.

---

## Cost

- Gemini Pro: $0.0225
- GPT-5.4: $0.00 (manual paste workaround)
- **Total consensus call: $0.0225**
- **Set 029 cumulative: $1.464 of $5.00 NTE; remaining $3.54**

---

## Next step

Operator answers D1 (most consequential), and optionally D2 + D3. I then draft the S3 spec delta consistent with those choices and the ten must-fix items above.
