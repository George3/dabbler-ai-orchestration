VERIFIER: openai gpt-5-4
VERDICT: ISSUES_FOUND | verified: False
ISSUES: 3
COST_USD: 0.18226749999999997
======================================================================
**ISSUES FOUND**

- **Issue 1:** Pull-surface materiality coverage is asserted on the whole markdown file instead of the extracted prompt body actually used at runtime (`ai_router/tests/test_verification_framing.py:test_pull_template_carries_materiality_layer`).
  - **Category:** Correctness
  - **Severity:** Major
  - **Details:** **Violation:** Deliverable 3 required proving the materiality/anti-nitpick layer is present on **both reviewer surfaces**, and the diff itself states the pull surface is evaluated from the prompt body the dual-surface runner uses. **Impact:** Required phrases can be moved outside that extracted body and this test still passes, so the real pull reviewer can lose the new layer without pytest catching it; that undermines the only in-scope Layer-1 protection for this session. **Evidence:** The presence test does `phrase.lower() in _pull_text().lower()`, but the adjacent additivity test explicitly switches to `pull_body = dual_surface_verify.prompt_body_of(_pull_text())` with the comment “the same prompt body the dual-surface runner uses.” **Correct answer:** Check the required materiality phrases against `prompt_body_of(_pull_text())` (or the exact runtime-extracted pull prompt), not the whole file.

- **Issue 2:** The new materiality pins are too weak to be load-bearing; they do not actually enforce several required parts of the added layer (`ai_router/tests/test_verification_framing.py:MATERIALITY_PHRASES`, `test_push_template_carries_materiality_layer`, `test_pull_template_carries_materiality_layer`).
  - **Category:** Completeness
  - **Severity:** Major
  - **Details:** **Violation:** Session 1 was explicitly limited to pytest coverage, and the task asked for materiality/anti-nitpick language pins that would catch real weakening of the new layer. **Impact:** A future edit can remove core required semantics while leaving the six checked substrings somewhere in the template, and all 14 new tests still pass; that means the regressions this session was meant to prevent are not actually pinned. **Evidence:** `MATERIALITY_PHRASES` only checks `["so what?", "semantic equivalence", "python -m pytest -v", "merge decision", "plausible path", "nits"]`, and both tests are plain substring checks. They do **not** pin the explicit `Violation / Impact / Evidence` triad, the “correct and complete response should come back VERIFIED” rule, or the “manufacturing a Minor ... is itself a false-positive failure” clause. **Correct answer:** Add explicit assertions for the required semantics, at minimum the `Violation`/`Impact`/`Evidence` trio and the anti-manufacturing/`VERIFIED` language, so a degenerate template cannot satisfy the suite by sprinkling a few generic phrases.
