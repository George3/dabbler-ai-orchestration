# Set 020 Session 1 — AI Assignment

**Status:** Authored 2026-05-11; awaiting operator approval before any work executes.

**Scope** — single-session complexity audit. Inventory the 10
audit buckets named in `spec.md`, route the inventory + targeted
excerpts to two independent verifiers (GPT-5.4 and Gemini 2.5
Pro), synthesize their independent passes into a written
`simplification-proposal.md`. **No implementation lands in this
set.** Approved cuts go into a follow-on Set 021.

---

## 1. Findings (from prerequisite reads + spec confirmation)

### 1a. Router task-type routing forces

Confirmed via [ai_router/router-config.yaml:217-256](../../../ai_router/router-config.yaml#L217-L256):

| Task type | Forced model | Notes |
|---|---|---|
| `session-verification` | `gpt-5-4` | Cross-provider verifier for Claude orchestrators. **This is the GPT-5.4 route.** |
| `architecture` | `opus` | Same provider as orchestrator — wouldn't satisfy cross-provider. Skip. |
| `code-review` | `sonnet` | Same provider — skip. |
| `analysis`, `planning`, `refactoring` | tier-based default | Tier-2 maps to `gemini-pro` (via models config); tier-3 to `opus`. With `max_tier=2` clamp + high `complexity_hint`, lands on Gemini Pro reliably. **This is the Gemini route.** |

**Decision:**
- **GPT-5.4 route:** `route(task_type="session-verification", complexity_hint=85)` — config force, no clamp needed.
- **Gemini 2.5 Pro route:** `route(task_type="analysis", max_tier=2, complexity_hint=80)` — `max_tier=2` clamps escalation, ensuring Gemini Pro lands rather than Opus.

`route()` has no explicit model override parameter (confirmed via signature at `ai_router/__init__.py:411`); task-type + max_tier is the right lever.

### 1b. Audit surface confirmed

Per-bucket line counts (re-confirmed at this read):

- A. Workflow doc — 1752 lines (`docs/ai-led-session-workflow.md`)
- B. Authoring guide — 489 lines
- C. Adoption bootstrap — 465 lines
- D. close-out machinery — `close_session.py` 1677 + `gate_checks.py` 630 + `disposition.py` 391 + `close_lock.py` ≈ 2700 lines
- E. session-state machinery — `session_state.py` 1293 + supporting modules ≈ 1500+ lines
- F. router + task-type — `router-config.yaml` 587 + `ai_router/__init__.py` + supporting modules
- G. Adoption × budget tier matrix — split across bootstrap + workflow doc
- H. UAT/E2E gate stack — just split by Set 019; new
- I. Extension surfaces — `tools/dabbler-ai-orchestration/src/` (commands, dashboard, providers, wizard, utils)
- J. Memory system — operator-side `~/.claude/projects/<repo>/memory/` (out of repo)

Total audit subject: ~10k Python + ~3k canonical docs + extension TS.

### 1c. Verifier prompt size budget

The two routes each take a prompt. Set 019's verification route was
26.6k chars for ~$0.10 at GPT-5.4. For Set 020, each verifier sees:

- The full `audit-inventory.md` (target ~6-8k chars)
- Targeted excerpts of the most-debated surfaces (~10-15k chars)
- Philosophy frame from CLAUDE.md (~500 chars)
- Structured response schema (~800 chars)
- Question framing (~1k chars)

**Per-route prompt target: 25-30k chars.** Comfortably within
per-route cost projection of $0.20-$0.35 for GPT-5.4 and
$0.15-$0.30 for Gemini Pro.

What goes in the targeted excerpts:
- Workflow doc §UAT Checklist Rule (the just-split subsections) + §E2E + Step 8 + Rules list
- `close_session.py` mode flags + gate check list + the `--repair`/`--force`/`--manual-verify` semantics
- `router-config.yaml` task-type table + tier weights + verifier_fallback config
- Adoption-bootstrap.md Step 4.5 (Lightweight tier) + Step 5 (budget tier) + Step 6 (pattern catalog)

What does NOT go in the prompt: full file contents of any single
module. The inventory's structural summaries are the primary input.

### 1d. The "what would you cut?" question framing

The prompt asks each verifier to **score every bucket (A-J)** on:

1. **Load-bearing score (1-10):** How essential is this to the
   stated repo philosophy? 10 = cannot remove; 1 = pure ornament.
2. **Cost to Lightweight-tier consumer:** how much of this surface
   is dead weight for a Lightweight consumer? Bucket-by-bucket
   yes/no/partial.
3. **Cost to no-UAT/no-E2E consumer:** same question, for
   `requiresUAT: false` + `requiresE2E: false` consumers.
4. **Concrete cut suggestions:** per bucket, what specific
   lines/flags/branches would you cut? (With concrete file paths /
   line ranges where possible.)
5. **Concrete defenses:** per bucket, what specifically should
   stay? (With one-line rationale.)
6. **Overall complexity score (1-10):** an aggregate verdict on
   the whole surface — is the orchestration framework over-,
   under-, or right-engineered for its stated purpose?

The prompt explicitly asks for defenses, not just cuts — Set 020
spec §Risks names "verifier 'what would you cut?' bias toward
more cuts" as a risk; the prompt structure mitigates it.

---

## 2. Edit plan (concrete)

### 2a. Author `audit-inventory.md`

Target ~6-8k chars. Sections in order:

- **Purpose** (one paragraph) — what the inventory is and how
  it'll be used (input to two verifier prompts).
- **Bucket A through J** — per bucket:
  - 1-paragraph structural summary
  - Key flags / modes / branches / line counts
  - Dependency relationships (who consumes this surface)
  - Current consumer fit notes (does dabbler-platform need this?
    dabbler-access-harvester? dabbler-homehealthcare-accessdb?)
- **Cross-bucket dependencies** — items where complexity in one
  bucket exists *because of* another (e.g., disposition.json
  schema exists because close-out gate needs it; UAT rule split
  exists because there are two consumer shapes).
- **Philosophy frame** — one-paragraph quote of the universal-
  core / gated-extensions principle from CLAUDE.md.

### 2b. Operator approval gate on `audit-inventory.md`

If the inventory mischaracterizes any bucket, fix it before
routing. The inventory is the *input* to both verifier prompts;
bias in the input cascades. **This is a real gate, not a
formality** — the operator should look hard at whether the
buckets accurately represent the surface as they understand it.

### 2c. Author `verifier-prompt-template.md`

One reusable prompt template parameterized by `<verifier_name>`.
Contents:

- Repo + Set 020 context (one paragraph)
- Philosophy frame quote
- Inventory (inlined from `audit-inventory.md`)
- Targeted excerpts (~10-15k chars from workflow doc, close_session.py,
  router-config.yaml, bootstrap doc — names of sources marked
  inline so the verifier can map their feedback back to files)
- Six scoring questions (1a-1f from finding 1d above)
- Structured JSON response schema for the per-bucket scoring + overall
- Cross-provider intent note ("the orchestrator is Anthropic Opus
  4.7; you are reviewing from a different provider; differences
  in opinion are the point").
- Note that the verifier can request specific excerpts if needed
  for a Round 2 (signals the prompt is not a one-shot expectation).

### 2d. Route to GPT-5.4

`route(task_type="session-verification", complexity_hint=85, ...)`.
The script:
- Read `verifier-prompt-template.md` and `audit-inventory.md`
- Concat + substitute `<verifier_name>` = "GPT-5.4"
- Call route(), save RouteResult to JSON first per memory rule
- Save markdown response to `provider-responses/gpt-5-4-cuts.md`
  with metadata header (model, cost, tokens, elapsed)
- Log cost cumulatively

Expected cost: $0.20-$0.35. Expected wall time: ~90-120s.

### 2e. Route to Gemini 2.5 Pro

`route(task_type="analysis", max_tier=2, complexity_hint=80, ...)`.
Same script shape:
- Same template, substitute `<verifier_name>` = "Gemini 2.5 Pro"
- Same RouteResult-to-JSON-first discipline
- Save to `provider-responses/gemini-2-5-pro-cuts.md`

Expected cost: $0.15-$0.30. Wall time similar.

If the route lands on a model other than `gemini-pro` (e.g., the
tier-2 default is overridden somewhere I missed), I'll catch that
in the RouteResult dump and ask the operator before continuing —
landing on Sonnet instead of Gemini Pro would defeat the
cross-provider intent.

### 2f. Compare independent passes

In-session synthesis. For each bucket A-J, classify:

- **Unanimous cuts** — both verifiers proposed the same cut.
- **Unanimous defenses** — both verifiers said leave alone.
- **Split-opinion** — one cut, one defended; capture both verbatim.

Capture each verifier's **overall complexity score** for the
aggregate verdict. If both score 8+ ("over-engineered"), that's a
strong signal. If they split (one says 4 "under-engineered" and
one says 9 "over-engineered"), that's a philosophical disagreement
warranting the optional tiebreaker.

### 2g. Optional tiebreaker (Phase F)

**Gated on operator approval at this step.** I'll present the
comparison and ask whether the disagreement merits a third route.
Default: skip unless materially split.

If approved, the tiebreaker route:
- Provider: ideally Claude (Opus) — turns out Anthropic *can* be
  the third opinion when the orchestrator is asking "which of
  these two non-Anthropic opinions better serves the stated
  philosophy?" because the philosophy is the Anthropic-authored
  CLAUDE.md.
- `route(task_type="planning", complexity_hint=80, ...)` —
  planning is a high-complexity Anthropic-friendly task type.
  Default tier-3 lands on Opus.
- Save to `provider-responses/tiebreaker-opus.md`.

Budget: $0.10-$0.20 additional.

### 2h. Author `simplification-proposal.md`

The primary deliverable. Five sections per the spec:

1. **High-confidence cuts** — items both verifiers (and the
   optional tiebreaker if invoked) flagged. Per item: file path,
   nature of edit, one-paragraph rationale, estimated effort for
   the follow-on implementation set.
2. **Split-opinion items** — items one verifier cut, the other
   defended. Both arguments quoted verbatim. Orchestrator notes
   one-sentence read on which way to lean (this is *opinion*,
   operator-overridable).
3. **Defended-as-load-bearing** — items the audit considered
   cutting and decided should stay. With one-paragraph rationale.
   Future audits inherit these defenses unless evidence changes.
4. **Deferred items** — items worth simplifying but where the
   cost of the cut exceeds the value today. With notes on what
   would unlock them later (a consumer-side change, a stable
   pattern, etc.).
5. **Implementation roadmap** — operator-approved cuts ordered by
   independence (cuts that don't depend on other cuts go first)
   and risk (lower-risk cuts go first within an independence
   tier). Each item gets a suggested session-set slug for the
   follow-on Set 021.

### 2i. Close-out artifacts + commit + push + close-out

Same shape as Set 019:
- `change-log.md` (narrative of inventory + dual route + synthesis)
- `disposition.json` (status: completed, verification_method:
  api, next_orchestrator: null since final session of set,
  blockers: [])
- `activity-log.json` (entries[] shape — learned from Set 019's
  gate-caught defect)
- `session-state.json` (flipped via `close_session`)
- `session-events.jsonl` (written by `close_session`)
- Commit. Push. Run `close_session`.

---

## 3. Risk callouts

- **Bucket scoping bias in `audit-inventory.md`.** If I frame a
  bucket as "this is load-bearing" implicitly, the verifiers may
  echo that. Mitigation: the inventory uses neutral structural
  summaries ("close_session.py is N lines and handles modes X, Y,
  Z"); the verifiers do their own scoring without my prior.
- **Verifier disagreement about CLAUDE.md philosophy.** The
  universal-core / gated-extensions principle is contested
  ground. A verifier may consider the principle itself wrong or
  unclear. Mitigation: the prompt asks them to score *against*
  the stated philosophy — disagreement with the philosophy is a
  separate signal worth surfacing in the proposal's
  defended-as-load-bearing section.
- **Cost overrun on tiebreaker.** If both verifier passes score
  the surface very differently, the tiebreaker is tempting.
  Mitigation: I check with the operator before routing the
  tiebreaker; default-skip.
- **Set 019 freshness bias.** The `uatStyle` split just shipped
  in Set 019. Verifiers may flag it as "new and untested" without
  evaluating its actual complexity contribution. Mitigation: the
  prompt explicitly notes Set 019 just shipped and asks the
  verifier to evaluate the *steady-state* surface, not the diff.
- **Synthesis fabrication.** It's tempting in the synthesis to
  imply both verifiers agreed when they had similar-but-distinct
  framing. Mitigation: the proposal's high-confidence-cuts
  section requires *both* verifiers to have explicitly flagged
  the item; split-opinion is the catch-all when framing differs.
- **Operator overriding load-bearing defenses.** The defended-as-
  load-bearing section may include items the operator personally
  wants to cut anyway. Mitigation: those go to the implementation
  set as "operator-override cuts" — the audit logged its judgment,
  the operator overrides explicitly.

---

## 4. Out of scope (Session 1)

- **Any code or canonical-doc edits.** Audit-only.
- **Pruning the memory system.** Bucket J is audited; pruning
  happens later if/when the operator approves the proposal items.
- **Rewriting CLAUDE.md / AGENTS.md / GEMINI.md.** Read as
  context, never edited.
- **Implementation of any proposed cut.** Set 021 territory.
- **Cost-report routing or budget changes.** The audit may
  *recommend* changes; doesn't *make* them.

---

## 5. Acceptance criteria for Session 1

- [ ] `audit-inventory.md` exists; 10 buckets covered; structural summaries + flags + dependencies per bucket.
- [ ] `verifier-prompt-template.md` exists; complete prompt with philosophy frame + inventory + excerpts + 6 scoring questions + JSON schema.
- [ ] `provider-responses/gpt-5-4-cuts.md` exists; per-bucket scoring + cuts + defenses; metadata header.
- [ ] `provider-responses/gemini-2-5-pro-cuts.md` exists; same structure. Confirmed via RouteResult dump that the model landed was actually `gemini-pro` (not a fallback).
- [ ] `simplification-proposal.md` exists with all five sections; each high-confidence cut names a concrete next-step.
- [ ] All five close-out gates pass.
- [ ] Cumulative metered cost recorded in `change-log.md` and confirmed within projection ($0.35-$1.00).
- [ ] No code or canonical-doc edits committed.

---

## 6. Decisions still open (Session 1)

1. **Should I include `audit-inventory.md`'s philosophy frame as a
   separate document or inline it in the prompt?** Recommendation:
   **inline in the prompt**. The inventory is the structural
   document; the philosophy frame is the lens. Separating them
   risks the inventory standing alone without context.
2. **For the Gemini Pro route, if the RouteResult shows a model
   other than `gemini-pro` (e.g., flash, or a fallback), pause
   and ask?** Recommendation: **yes, pause.** A misrouted second
   pass defeats the dual-verifier intent. Operator gets to decide
   whether to re-route, accept the alternative, or abandon
   Gemini-side input.
3. **Should the proposal's implementation roadmap include
   estimated costs for each Set 021 candidate?** Recommendation:
   **yes, ballpark.** Rough $X-$Y range per item helps the
   operator gate which cuts are worth pursuing.

---

**Awaiting operator approval. After approval, work proceeds in
order 2a → 2b (operator inventory review) → 2c → 2d → 2e → 2f →
[2g if approved] → 2h → 2i.**
