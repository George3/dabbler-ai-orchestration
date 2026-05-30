Set 053 Session 1 (1 of 2) close-out — audit & design-lock.

S1 inventoried every session-state.json writer (Python + TS) and found
the load-bearing fact: all of them already stamp schemaVersion from the
constant, so a file written through the framework's CLI is never stale —
the only real failure vector is hand-authoring that bypasses the writers.

A CI-centric proposal (CI required-check + git hooks + baseline-allowlist
+ Azure/GitHub wrappers) went to a 2-provider adversarial consensus
(gemini-pro + gpt-5-4, $0.0362). Both confirmed CI-as-centerpiece and
both rejected the baseline-allowlist. The operator then rejected the
entire CI frame: "stop adding sophistication; just add the check to the
script that writes session-state.json; CI OFTEN FAILS." Correct — the
session-lifecycle CLI (start_session/close_session) is the universal,
editor/host/CI-agnostic trigger, and the inventory had pointed there all
along.

LOCKED minimal design (verdict.md): embed the existing detect_drift scan
into start_session as a non-blocking warning (+ optional soft
close_session note); check_migrations stays an optional manual tool;
CI / git-hooks / baseline-allowlist all dropped; "old schema acceptable"
honored by the warning being non-fatal. Scope collapsed 3 → 2 sessions.

Verification: manual (this is an audit/design session — no code shipped;
the cross-provider consensus served as the design review, and the
operator made the final design call). The process lesson (LLMs favor
good-sounding architecture; cross-provider agreement on a shared frame is
correlated error; prefer baking logic into the existing lifecycle) is
banked to memory.

Routed cost $0.0362 of $10 NTE (0.36%). S2 implements the start_session
scan + tests + doc + version bump + close-out; publish held for operator.
