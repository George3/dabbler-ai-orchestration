---
title: Lightweight dedicated verification sessions
status: PROPOSAL OF RECORD
date: 2026-06-05
authors: human + GitHub Copilot (GPT-5.4)
applies-to: lightweight-tier session-set workflow
note: >
  De-duplicated 2026-06-05 in Set 057 Session 1. The file previously held
  two concatenated drafts; the cleaner second draft below is kept as the
  proposal of record. Gemini feedback and Claude's 2026-06-05 review fed the
  pre-locked dispositions (L1-L4) in the Set 057 spec. The S1 cross-provider
  audit verdict lives in `verdict.md` alongside this file.
---

# Lightweight dedicated verification sessions

## Purpose

This proposal replaces the Lightweight tier's semi-manual copy/paste
verification step with an optional dedicated verification-session flow.
The design goal is not Full-tier parity. The design goal is a small,
bounded workflow that agents are likely to follow correctly.

Two constraints drive the design:

1. The verification session, not the human, should create the follow-on
   remediation session when issues are found. That reduces the risk that
   the work simply stops after verification.
2. Lightweight operators must still be able to opt out of dedicated
   verification entirely.

When this proposal says an issue is "closed," that means it has reached a
terminal disposition. It does not always mean "fixed in code."

## Operator choice

When the operator chooses the Lightweight tier, prompt for one of two
verification modes:

```text
How would you like to incorporate verification by other AI engines?
(a) dedicated verification sessions (recommended)
(b) out-of-band or no verification
```

Suggested stored values:

```text
verificationMode: dedicated-sessions | out-of-band-or-none
```

If `verificationMode = out-of-band-or-none`, the session set follows the
existing Lightweight path and closes without dedicated verification
machinery.

If `verificationMode = dedicated-sessions`, the workflow below applies.

## Design principles

1. Keep the state machine small.
2. Keep work, verification, and remediation as separate sessions.
3. Require a different AI engine for verification than for the work being
   reviewed.
4. Let the verification session create the remediation session, but do not
   let it dictate the remediation outcome.
5. Re-run verification only when remediation changed code or
   documentation.
6. Escalate to the human instead of adding more automatic branches.

## Session roles

### Work session

The normal implementation or documentation session.

### Verification session

Reviews the most recent work or remediation session using a different AI
engine.

The verification session must do exactly one of these:

1. Pass the work with no open issues.
2. Emit findings and create exactly one remediation session.
3. Escalate to the human because the question is underdetermined,
   high-impact, or over the automatic-round limit.

### Remediation session

Responds to findings from the prior verification session.

The remediation session may:

1. Fix issues.
2. Close issues with an allowed non-fix disposition.
3. Escalate to the human.

The remediation session must not create another remediation session. Only
verification sessions may create remediation sessions.

## Minimal finding contract

Each finding must include:

1. `issueId` - stable across rounds.
2. `severity` - `Critical`, `Major`, `Minor`, or `Advisory`.
3. `type` - one of:
   - `deterministic-defect`
   - `contingent-risk`
   - `standards-departure`
   - `missing-context`
4. `description` - concise statement of the problem.
5. `verificationMethod` - a concrete way to test whether the issue is
   resolved.
6. `suggestedTestOrCheck` - preferably an automated test, otherwise a
   deterministic repro command, static check, or doc check.

This is intentionally small. If a finding cannot meet this contract, it
should not drive repeated verification loops.

## Allowed dispositions

The remediation session may close an issue only with one of these
dispositions:

1. `fixed`
2. `not-reproducible`
3. `accepted-risk`
4. `accepted-consequence`
5. `advisory-disagreement`
6. `needs-more-context`
7. `escalate-human`

## Session-set states

This proposal keeps the set-level states intentionally small:

1. `work-in-progress`
2. `awaiting-verification`
3. `awaiting-remediation`
4. `awaiting-human`
5. `closed-verified`
6. `closed-dispositioned`
7. `closed-no-verification`

State meaning:

- `work-in-progress`: a normal work session is the active next step.
- `awaiting-verification`: the next session must be a verification
  session.
- `awaiting-remediation`: the next session must be the remediation
  session created by the verifier.
- `awaiting-human`: automation is paused pending a human decision.
- `closed-verified`: verification passed with no open issues.
- `closed-dispositioned`: remaining issues were closed by accepted,
  terminal dispositions under policy.
- `closed-no-verification`: the operator chose the Lightweight path with
  no dedicated verification flow.

## Allowed transitions

Only these transitions are allowed.

### 1. Work completion

`work-in-progress -> awaiting-verification`

Condition: the work session completes and
`verificationMode = dedicated-sessions`.

`work-in-progress -> closed-no-verification`

Condition: the session set completes and
`verificationMode = out-of-band-or-none`.

### 2. Verification outcome

`awaiting-verification -> closed-verified`

Condition: the verification session reports no open issues.

`awaiting-verification -> awaiting-remediation`

Condition: the verification session reports one or more open issues.

Required action: the verification session must create exactly one
remediation session and seed its `spec.md` with:

1. The finding list.
2. The required verification methods.
3. Any proposed tests or repro commands.
4. Any required human-approval notes.

`awaiting-verification -> awaiting-human`

Condition: the verifier lacks enough context, the issue is too
high-impact for automatic handling, or the next verification round needs
human approval.

### 3. Remediation outcome

`awaiting-remediation -> awaiting-verification`

Condition: the remediation session changed code or documentation.

`awaiting-remediation -> closed-dispositioned`

Condition: the remediation session made no code or documentation changes
and every open issue reached a terminal disposition allowed by policy.

`awaiting-remediation -> awaiting-human`

Condition: the remediator wants to accept, defer, or dispute a
`Critical` or `Major` finding, or the remediator cannot proceed safely.

### 4. Human decision

`awaiting-human -> awaiting-remediation`

Condition: the human requests more remediation.

`awaiting-human -> awaiting-verification`

Condition: the human supplies more context and wants a new verification
pass without remediation changes.

`awaiting-human -> closed-dispositioned`

Condition: the human explicitly accepts the remaining issues or chooses
to close them by policy.

`awaiting-human -> closed-verified`

Condition: the human determines that no open issues remain.

No other transitions are allowed.

## Verification rules

### Rule 1: Later rounds must stay narrow

Round 1 may discover any issues.

Round 2 and later may raise only:

1. Existing unresolved `issueId` values.
2. Regressions caused by remediation.
3. Newly discovered `Critical` or `Major` issues.

This prevents verification from turning later rounds into fresh general
audits.

### Rule 2: Contingent risks may be closed deliberately

If a finding represents a risk rather than a deterministic failure, the
remediation session may close it as `accepted-risk` if it records the
risk clearly.

If the finding is `Critical` or `Major`, human approval is required.

### Rule 3: Deterministic problems may be accepted only explicitly

If a finding describes a problem that always occurs and the remediator
intends to leave it in place, the issue may be closed as
`accepted-consequence` only if the consequence is described clearly.

If the finding is `Critical` or `Major`, human approval is required.

### Rule 4: Subjective departures should not ping-pong

If a finding is a subjective departure from best practice, architecture,
standards, or conventions, the remediation session may close it as
`advisory-disagreement` when it either:

1. Accepts the departure as intentional, or
2. Gives a reasoned disagreement.

Once closed this way, the issue must not reappear in later rounds unless
the human changes policy or the departure causes a new objective defect.

### Rule 5: Every finding needs a falsifiable check

Every finding must identify a concrete verification method.

Preferred order:

1. Automated test.
2. Deterministic repro command.
3. Static or schema validation.
4. Documentation consistency check.

The first task of the remediation session is to evaluate that proposed
check.

If the proposed check is defective, the remediation session must say why.
If possible, it should replace it with a better one.

### Rule 6: Critical and Major non-fix closures require human approval

If the remediator wants to close a `Critical` or `Major` finding as
`accepted-risk`, `accepted-consequence`, or `advisory-disagreement`, or
wants to dispute the finding, the workflow must move to
`awaiting-human`.

### Rule 7: Re-verification happens only after actual changes

The only time a new verification round is scheduled automatically is when
the remediation session changed code or documentation.

If no code or documentation changed, the issue set must terminate by
disposition or human decision instead of scheduling another
verification round.

### Rule 8: Automatic rounds are bounded

To prevent ping-pong:

1. Verification rounds 1 and 2 may run automatically.
2. Verification round 3 requires explicit human approval.
3. Every verification round after 3 also requires explicit human
   approval.

This proposal deliberately does not add a separate tie-break state. If a
third engine is needed, that should be a human-directed action while the
set is in `awaiting-human`.

## Stop conditions

The workflow must stop automatic progression when any of these is true:

1. Verification passes with no open issues.
2. All remaining issues have terminal, policy-allowed dispositions and no
   new code or documentation changes were made.
3. A `Critical` or `Major` issue needs a non-fix closure or is in
   dispute.
4. The next verification round requires human approval.
5. The verifier cannot provide a concrete verification method.
6. The operator chose `out-of-band-or-none` at session-set start.

## Summary

This proposal keeps the Lightweight workflow intentionally small:

1. Optional dedicated verification.
2. Separate work, verification, and remediation sessions.
3. Verification creates remediation when needed.
4. Only a few set-level states.
5. Bounded re-verification loops.
6. Human review for high-severity non-fix closures and later rounds.

That keeps the process more reliable than today's manual copy/paste flow
without pushing the Lightweight tier all the way into Full-tier
complexity.
