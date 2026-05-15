# Session 1 verification prompt — Set 025 (router-config editor spec)

## Context

Set 025 is a **doc-only** session set. Its sole purpose is to capture
a cross-provider design audit's locked decisions into three
operationalizable documents that Set 026 (the implementation set)
will build to.

The audit ran earlier today: GPT-5.4 + Gemini Pro reviewed the same
design prompt, this orchestrator (Claude Opus 4.7) synthesized their
verdicts, and the operator picked between divergences. Eight gating
decisions (G1–G8) are locked. Set 025 Session 1 produces:

1. `spec.md` — implementation spec for Set 026, including the
   session-by-session plan and the decisions captured.
2. `schema-examples.md` — current-vs-proposed YAML side-by-side
   for `router-config.yaml`, `budget.yaml`, the new
   `local-overrides.yaml`, plus `package.json` and `.gitignore`.
3. `wireframes.md` — ASCII webview layout for six sections
   (routing/verification, budget, providers table, significance
   flagging, notifications, local overrides).

The full audit work + synthesis is preserved at
`docs/proposals/2026-05-15-router-config-editor-design-audit/`
(prompt.md, gpt-5-4-result.json, gemini-pro-result.json,
audit-summary.md).

## What you're being asked to verify

Set 025 produces only docs — no code. Your verification is a
**doc-only review** of the three deliverables. The implementation
itself happens in Set 026; your role here is to catch sharp edges
in the spec before any code is written.

Please review the three documents inlined below and answer:

**Q1. Gating-decision capture.** Does `spec.md` accurately capture
all eight gating decisions (G1–G8) from the audit summary? Any
decision misrepresented, lost in translation, or contradicted between
documents? (The audit summary itself is included as Appendix A
below for reference.)

**Q2. Internal consistency across the three docs.** Do `spec.md`,
`schema-examples.md`, and `wireframes.md` agree on the schema shape,
the dropdown semantics, the file boundaries (shared vs. local),
and the migration path? Any mutual contradictions?

**Q3. Schema sanity (`schema-examples.md`).** Is the proposed YAML
shape implementable as described? Specifically:
- Does the `providers:` block extension (`display_label`,
  `enabled`) collide with any existing field in the current schema?
- Is the `budget.yaml` `threshold_scope` → `scope` rename with
  legacy-name aliasing a safe migration, or does it create a
  permanent ambiguity?
- Is the `local-overrides.yaml` shape a strict subset of the
  shared YAMLs, or does it introduce keys that have no canonical
  shared analog (and is that OK)?

**Q4. Wireframe / dropdown semantics consistency.** The "Routing &
Verification" section (Section 1 of wireframes.md) shows two
decoupled dropdowns with a constraint ("Automatic via API" is
disabled when routing = Disabled). Does the spec's G4 decision text
match the wireframe behavior? Does the wireframe's UX preview match
the actual constraint (does "Manual" still work when routing =
Disabled)?

**Q5. Set 026 buildability.** Reading just `spec.md` + the two
companion docs (and not this prompt or the audit summary), could a
fresh orchestrator pick up Set 026 cold and execute Sessions 1–5
as described? What's the smallest concrete gap that would force
them to circle back to a design decision?

**Q6. Open architectural questions.** Specifically:
- Does the `local-overrides.yaml` merge semantics need a clearer
  precedence rule (e.g., what if a provider exists ONLY in
  `local-overrides.yaml`, never in the shared file — is that an
  add or an error)?
- The webview validation runs at save time; should it also run on
  *load* to catch hand-edited YAML drift?
- The "atomic save across multiple files" behavior in
  `wireframes.md` § Validation — is the proposed `tmp write +
  rename` sequence actually atomic across multiple files, or only
  per-file? If only per-file, the cross-file consistency claim
  needs softening.

**Q7. Anything missing from the Set 026 session breakdown.** The
spec proposes five Set 026 sessions
(`outsourceMode` clean-sweep → schema → webview → significance
flagging → release). Reading the deliverables, would you split,
merge, or reorder any? Any session that needs work the spec
doesn't mention?

**Q8. Overall.** Is the spec ready for Set 026 to start? If not, the
smallest concrete change to get it there.

A short, structured response (per-question verdict + reasoning + any
concrete suggestions) is fine.
