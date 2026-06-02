Set 055 Session 1 (1 of 2) close-out - audit and design-lock.

Session 1 completed the audit-only half of the set. It re-verified the
current tree, confirmed that structured verifier issues already exist in
memory but have no modern root-level durable artifact, and wrote the
design record under
`docs/proposals/2026-06-02-structured-verification-issue-artifacts/`:

- `proposal.md` - recommended dispositions for the Session 1 questions
- `consensus-review.md` - routed cross-provider review from `gemini-pro`
- `verdict.md` - the authoritative locked design

The session also updated
`docs/session-sets/055-structured-verification-issue-artifacts/spec.md`
with the `S1 Audit Lock` summary so Session 2 has a single in-set
summary of the decisions.

The locked contract is:

- root-level per-round issue files (`sN-issues.json`, then
  `sN-issues-round-<M>.json`)
- a small envelope (`schemaVersion`, `sessionNumber`,
  `verificationRound`, `verificationVerdict`, `issues`)
- preserved verifier fields with optional advisory `resolution_*`
  annotations
- no empty issue file for clean rounds
- manual / `--no-router` JSON allowed only when structured findings
  actually exist
- helper optional only if duplication justifies it
- no runtime readers or close-out gate dependency in Set 055

Verification: API. A formal `session-verification` pass via `gpt-5-4`
returned `VERIFIED` with no findings; the raw verifier response is
preserved in `s1-verification.md`. The earlier cross-provider design
consensus also returned `CONSENSUS-AGREE`, so Session 1 closes with both
the design review and the end-of-session verification recorded on disk.

Session 2 is the implementation/docs pass only. It should treat
`verdict.md` as canonical where it differs from `proposal.md`, keep the
helper convenience-only, avoid runtime readers, and ship a release only
if Python code lands.