VERIFIER: openai gpt-5-4
VERDICT: ISSUES_FOUND | verified: False
ISSUES: 3
COST_USD: 0.27129000000000003
======================================================================
**ISSUES FOUND**

- **Issue 1:** The new materiality pins are not actually load-bearing and can pass a degenerate or contradictory template (`ai_router/tests/test_verification_framing.py`: `MATERIALITY_PHRASES`, `test_push_template_carries_materiality_layer`, `test_pull_template_carries_materiality_layer`)
  - **Category:** Completeness
  - **Severity:** Major
  - **Details:** **Violation:** The task explicitly asks whether the pins are “load-bearing (would they catch a real weakening), or could they pass on a degenerate template?”, and the added comments claim these are “Distinctive, multi-word, INVERSION-RESISTANT phrases”. **Impact:** These tests are the new regression net for the anti-nitpick layer; if they can be satisfied by stray or quoted text, a future weakening can slip through with green tests, defeating the session’s stated purpose. **Evidence:** `MATERIALITY_PHRASES` includes generic single-word probes (`'violation'`, `'impact'`, `'evidence'`, `'nits'`) despite the “not generic single words” comment, and both tests only do `phrase.lower() in _norm(...)`, which cannot distinguish the required rule from contradictory context. **Correct answer:** Replace the weak substring probes with clause-level pins or structured regexes that assert the actual rule blocks: ordered triad language, semantic-equivalence rule, merge-decision anchor, anti-laundering clause, and non-blocking NITS semantics.

- **Issue 2:** The diff adds a new `NITS` output grammar without any added proof that the unchanged parser/consumer accepts it (`ai_router/prompt-templates/verification.md`, `ai_router/prompt-templates/path-aware-critique.md`, `ai_router/tests/test_verification_framing.py`)
  - **Category:** Completeness
  - **Severity:** Major
  - **Details:** **Violation:** S1 requires adding a `NITS` subsection while also holding “No verification.py code change in S1”; that makes compatibility with existing parsing/consumption logic a required invariant. **Impact:** If the current pipeline does not ignore or tolerate `NITS`, the prompts now instruct models to emit outputs that the existing code may misparse or reject, which is a fix-before-merge risk. **Evidence:** Both templates now instruct a `NITS` section, but the added tests only cover phrase presence and `classify_framing_strength`; the only parser-compat check visible in the diff is the pre-existing `test_upgraded_template_still_parses_issues()`, and no new test exercises `VERIFIED`/`ISSUES FOUND`/`ISSUES_FOUND` output with a trailing `NITS` block. **Correct answer:** Add parser/consumer regression tests proving both surfaces still parse when `NITS` is present, or do not instruct models to emit `NITS` until that compatibility is established.
