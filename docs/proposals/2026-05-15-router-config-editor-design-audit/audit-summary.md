# Router-config editor — design alignment audit (synthesis)

**Date:** 2026-05-15
**Reviewers:** GPT-5.4 (OpenAI), Gemini Pro (Google), Claude Opus 4.7 (this orchestrator)
**Audit cost:** $0.1197 across both reviewers (GPT-5.4 $0.0919 + Gemini Pro $0.0278)
**Raw verdicts preserved at:** `gpt-5-4-result.json` and `gemini-pro-result.json` in this folder.

---

## Headline

**All three reviewers concur the design is ready to spec — with conditions.**

Both AI reviewers return "yes-with-conditions"; this orchestrator
shares that verdict. The disagreements are bounded and focused on
two architectural details (provider schema, significance heuristic)
and one judgement call (CLI deletion scope). Everything else is
either consensus or low-stakes refinement.

---

## Where all three agree (consensus — lock these in)

| Topic | Consensus position |
|---|---|
| **Q2 — Truth source** | YAML files (`router-config.yaml` + `budget.yaml`) stay canonical. Extension grows a custom-webview editor. `package.json` settings stay only for extension-UI-behavior (notifications toggle, view filters, `pythonPath`). |
| **Q3a — Budget scope** | Three-way dropdown is fine, but **default to per session-set**. Per-project is the advanced option. Per-session is friction-heavy and contradicts the operator's "no per-write prompts" preference — keep it available but framed as exception, not equal choice. |
| **Q3b — Optimally intrusive UX** | Combination: hard cap + warn-at-percent (operator-configurable, e.g., 80%). **Three-state UI:** silent if projected cumulative is below warn threshold; heads-up notification if it crosses warn; explicit confirm if it crosses block. Hysteresis: one warning per band, not on every call. |
| **Q5 — Configurable env-var names** | Real win, not YAGNI. Resolution lives in **Python `ai_router`** (canonical — every execution path honors it) AND the extension reads the same field for setup validation + diagnostics ("env var `MY_ORG_GEMINI_KEY` is not set"). |
| **Q7 — Sharp edges (the must-haves)** | (a) **Schema validation** on round-trip read + write — non-negotiable. (b) **Webview scope includes `budget.yaml`** too, not just `router-config.yaml`. (c) **Forward-migration** on schema version mismatch. |
| **Q8 — Sequencing** | **Split into two session-sets.** Audit-and-spec set first (this one); implementation set later. Both reviewers prefer this over the single-set option; this orchestrator's initial preference (single set) is overridden by the consensus. |

---

## Where the reviewers diverge (operator must pick)

### D1. `outsourceMode` cleanup scope (Q1)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | Deprecate the **spec-level flag** now. **Keep** `ai_router.queue_status`, `heartbeat_status`, and `two-cli-workflow.md` until there's explicit evidence no external repo uses them. |
| **Gemini Pro** | Deprecate **everything**: spec flag, both CLIs, and the workflow doc. Architectural dead end; clean-sweep. |
| **Claude (this orch.)** | The Set 024 commit message and CHANGELOG explicitly said the CLIs stay "for operators running outsource-last in other repos." Reversing that within a week of v0.13.14 would be a credibility hit. **Side with GPT** — flag deprecation in this work, CLI deletion as a future "if we're sure" cleanup. |

**Recommendation:** Pick GPT's cautious path. Concrete next step: spec
deprecates `outsourceMode` from `spec.md` but leaves Python CLIs +
two-cli-workflow.md untouched. A future "Set N+M: remove
outsource-last entirely" decision can be made on evidence (or its
absence).

### D2. Provider schema — `providers:` vs alias-for-`models:` (Q6)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | **Dissent** with table-as-`models:`-alias. Credentials, endpoints, and API protocol are provider-level; `models:` is a routing inventory. Multi-model providers (OpenAI has many models behind one API key) would duplicate auth config under the alias approach. Recommends a new top-level `providers:` block; `models:` entries reference `provider_id`. |
| **Gemini Pro** | **Concur** with table-as-`models:`-alias. Simpler implementation; one canonical structure; direct UI-to-data mapping. |
| **Claude (this orch.)** | GPT's reasoning is technically more correct (provider ≠ model is right OO modeling, and the existing `router-config.yaml` already has a separate `providers:` block at lines 25–48 — `anthropic:`, `google:`, `openai:` — that the proposed alias would conflict with). Gemini missed that existing structure. **Side with GPT.** |

**Recommendation:** Adopt GPT's `providers:` shape. The current
`router-config.yaml` already has a `providers:` block; the new schema
**extends** that block to include `api_key_env_var`, `api_base_url`,
`display_label`, `enabled`. `models:` entries gain a `provider_id`
reference field (today the provider is inferred from the model_id
prefix — that ad-hoc coupling becomes explicit).

### D3. "Significance" heuristic (Q4)

| Reviewer | Position |
|---|---|
| **GPT-5.4** | **Mixed.** Feasible only as soft suggestion in planning/checklist flow, never silent gating. Score from high-signal events (schema changes, dependency choices, multi-repo blast radius). One dismiss per session. |
| **Gemini Pro** | **Dissent.** Scrap the heuristic entirely. Replace with explicit operator-invoked mechanism: a `Dabbler: Flag Decision for Cross-Provider Review` command, or a code annotation (`# @dabbler:outsource-review("...")`) the orchestrator recognizes. |
| **Claude (this orch.)** | Both AIs converge on "automatic detection is unreliable." Gemini's explicit-command path is the more defensible UX and matches the operator's "default not started; positive evidence to escalate" memory pattern. **Side with Gemini.** |

**Recommendation:** Replace the "Suggest outsourcing on significant
decisions" checkbox with: (a) a manual VS Code command
(`Dabbler: Flag Decision for Cross-Provider Review`) that the
operator invokes when they want a routed second opinion, and (b) a
recognized code-annotation pattern the orchestrator picks up during
session work. The toggle goes away; the capability becomes a tool
the operator reaches for deliberately.

---

## New sharp edges surfaced (lock these before spec)

### S1. "Never" routing-mode conflicts with mandatory verification (GPT, Q7)

The proposed `AI Outsourcing` dropdown has a "Never" option. The
workflow's Rule 2 is "Never skip verification" — the only legal
bypass today is `budget.yaml`'s `verification_method: skipped` or
`manual-via-other-engine`. **The dropdown must reconcile with the
existing budget.yaml verification policy**. Concrete options:

- (a) "Never" disables **all non-verification routing only**;
  end-of-session verification still fires unless `budget.yaml`
  separately declares `verification_method: skipped`.
- (b) "Never" sets `verification_method: skipped` in `budget.yaml`
  too — single-knob convenience, at the cost of hiding the
  audit-trail implication.
- (c) Rename "Never" to "Verification only" to make the semantics
  explicit (Verification only == "all routing except mandatory
  end-of-session verification is disabled").

**Recommendation:** Pick (c). The current dropdown already has
"Only for Cross-Provider Verification" as a distinct option; "Never"
adds confusion. Either drop "Never" entirely (the
"verification only" option already covers the "minimal routing"
intent) **or** rename "Never" to "Disabled including verification"
to force the operator to acknowledge they're opting out of Rule 2.

### S2. Shared-vs-local config separation (GPT, Q7)

`router-config.yaml` is checked into the repo (shared with
collaborators). But some fields are **operator-machine-local**:
notification env-var names, Pushover keys, possibly `pythonPath`,
maybe even API-key env-var name overrides. Today there's no
local-only YAML; this design needs one.

**Recommendation:** Introduce a `.gitignore`-d
`ai_router/local-overrides.yaml` (or similar) for operator-local
fields. Webview shows which fields are shared-canonical vs.
local-overridden. Round 2 of the spec should decide which fields
default to which file.

### S3. secretStorage as a future-proofing concern (both)

Both reviewers raise VS Code's `secretStorage` API as an alternative
to env-var-only key storage. **Gemini calls it a must-have**; GPT
says "defer with an abstraction." The current env-var-only model
is fine for most operators but creates friction in security-strict
orgs.

**Recommendation:** GPT's middle path — design the resolver
abstraction now (every key lookup goes through
`resolve_secret(name, source)`), implement env-var as the only
backend in v1, add `secretStorage` and `keyring`/etc. backends in
future sets when there's demand. Gemini's "ship it now" is overkill
without a concrete operator request.

---

## Updated gating-decision checklist (operator picks before spec)

| # | Decision | Recommended |
|---|---|---|
| G1 | `outsourceMode` cleanup scope | GPT's path — deprecate spec flag, keep CLIs |
| G2 | Provider schema shape | GPT's path — extend `providers:` block, add `provider_id` to `models:` |
| G3 | "Significance" heuristic | Gemini's path — replace toggle with explicit command + annotation |
| G4 | "Never" dropdown semantics | Rename or drop; reconcile with `verification_method` |
| G5 | Shared-vs-local config | Add `.gitignore`-d local-overrides file |
| G6 | secretStorage | Resolver abstraction now, backends as needed |
| G7 | Budget scope default | Per session-set (per consensus) |
| G8 | Sequencing | Two session-sets (this one finishes as audit + spec doc; next set implements) |

---

## What this audit-and-spec set produces, if the operator concurs

If the operator agrees with the recommendations above, the
remaining deliverables for this set are:

1. **`spec.md`** for the eventual implementation set — locking the
   schema, the UX shapes, the migration path, and the "Never"
   semantics resolution.
2. **A schema example file** showing the proposed shape of
   `router-config.yaml` + `budget.yaml` + `local-overrides.yaml`
   post-change, side by side with the current shape, for diff
   review.
3. **Wireframes** (ASCII or markdown-table mockups) of the
   webview — table layout for providers, dropdown for outsourcing
   mode, three-state budget prompt UX.
4. **No implementation code.** That's the next session-set.

---

## Open questions the audit could **not** answer (these need operator input)

- **Q-A. The `outsourceMode` removal sequencing.** Does the operator
  agree with GPT's "remove flag now, keep CLIs until evidence"
  staging, or prefer Gemini's clean-sweep?

- **Q-B. The "Never" naming.** The operator originally wrote "Never"
  in the sketch. Is that an explicit "disable verification too"
  intent, or an oversight that should be renamed?

- **Q-C. Per-session budget scope.** Both reviewers want it
  de-prioritized. Is the operator OK demoting it to advanced /
  hidden, or do they have a use case in mind where per-session
  approval is the right granularity?

- **Q-D. The local-overrides file.** Does the operator want
  `ai_router/local-overrides.yaml`, `.dabbler-local.yaml`, or a
  different name? Does it live in the repo root or in `ai_router/`?

- **Q-E. The annotation pattern for significance flagging.** Is
  `# @dabbler:outsource-review("...")` the right syntax, or does the
  operator have a preference (`# DABBLER-REVIEW:`, structured
  comment, dedicated file, etc.)?
