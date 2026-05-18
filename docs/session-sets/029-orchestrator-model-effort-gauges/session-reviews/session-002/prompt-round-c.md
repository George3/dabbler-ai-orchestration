# Session 2 verification — Round C (confirmation pass on Round A + Round B must-fix items)

## Context

Round A (marker writer + CSS visual matrix) returned with 3 must-fix
items; Round B (provider + installer) returned with 2 must-fix items.
Total 5 must-fix items, all addressed. This Round C is a focused
confirmation pass: did the fixes actually fix the issues, and did the
fixes introduce any new bugs?

## Round A must-fix items + fixes applied

1. **TOCTOU race in `attemptWriteWithPrecedence`** (Q2). The original
   read existing → decide → write pattern had a race window. The fix
   adds a re-read immediately before `fs.renameSync` and re-evaluates
   precedence against that latest snapshot; skips with `reason:
   "weaker-than-existing-on-reread"` if a concurrent writer raced
   ahead with a stronger marker. Code is now in
   `write-orchestrator-marker.js` `attemptWriteWithPrecedence`.

2. **UserPromptSubmit merge/bootstrap clobber risk** (Q6). Both the
   merge-existing and bootstrap-when-missing paths can clobber a
   fresher SessionStart marker that lands between the initial read
   and the rename. Fix: added a re-read inside the
   `mode === "user-prompt-submit"` branch, after the tmp file is
   written but before the rename. If a marker exists at the re-read
   point, the merge uses THAT latest marker as the top-level
   snapshot (preferring fresh top-level signal over the
   bootstrap/initial-snapshot we'd otherwise write).

3. **Stale stripes painted BEHIND the SVG, not as an overlay** (Q8).
   Original: `.stale .gauge-svg { background-image: ... }` paints
   stripes on the SVG's background layer (i.e., behind the SVG
   content). Verifier was right — strokes don't get striped this
   way. Fix: replaced with `.stale .gauge-cell::before` absolute-
   positioned at z-index 2, occupying the gauge's 54px height,
   `pointer-events: none`. Stripe alpha bumped from 0.18 to 0.45
   (closer to the audit's "50% opacity" target).

## Round B must-fix items + fixes applied

4. **Effort suffix keyed off wrong signal** (Q1). Original code in
   `renderLoaded` had the `(default)` / `(manual)` branches checking
   `marker.signalKind` (top-level model signal) instead of
   `marker.effort.signalKind`. This means a Codex `configured-default`
   session with a `/think*` observation would render "(default)" on
   the effort gauge instead of the elapsed-time suffix. Fix: all
   three effort suffix branches now check `marker.effort.signalKind`.

5. **Gauge angle math wrong basis** (Q4). Original code used a
   `(180 + needleAngleDeg)` offset in the `Math.cos`/`Math.sin`
   calls, which inverted the y-axis behavior. At `needleAngleDeg =
   -90`, the offset gave 90°, and `Math.sin(90°) = 1`, so
   `fillEndY = cy + radius * 1 = cy + radius` — BELOW the gauge
   instead of at the top. All needle/fill endpoints were below
   the visible viewBox. Fix: removed the `180 +` offset; the angle
   is now used directly. With SVG's y-axis going down, `sin(-90°) =
   -1` correctly places the endpoint at `cy - radius` (top center).
   Also simplified `largeArc` to always be 0 since all upper-
   semicircle arcs are ≤180°.

## What you're being asked to verify in Round C

Re-bundle: the FULL post-fix versions of the marker writer + provider
+ CSS are inlined below. Round C focuses ONLY on:

**Q1.** For each of the 5 must-fix items above, does the fix
actually address the issue? Trace through the code with the fix in
place against the original concern.

**Q2.** Did any of the fixes introduce a new bug? Specifically:
- The re-read-before-rename in `attemptWriteWithPrecedence` uses
  `Date.now()` for the stale check, while the initial read used
  `nowMs`. Could a stale signal that JUST aged past
  `stalenessMaxSec` during our retry-loop window cause an
  inconsistent decision (initial read says fresh → re-read says
  stale)? If so, what's the worst-case behavior?
- The `user-prompt-submit` merge path now ALWAYS re-reads, even on
  the bootstrap path. If the initial read returned `null` (no
  marker) but the re-read returns a freshly-written
  SessionStart marker, we discard the bootstrap and merge onto the
  latest. Correct? Or is there a corner case where the initial read
  saw a CORRUPT/parse-fail marker and the re-read sees a fresh
  one, and the corrupt-but-parseable-in-one-direction would be
  trickier?
- The new gauge math always uses `largeArc = 0`. For
  `needleAngleDeg = 0` exactly (rightmost), is the arc from
  leftmost (7,35) to rightmost (63,35) at radius 28 with largeArc=0
  actually the correct upper-semicircle path? SVG spec says when
  the chord = 2*radius exactly (true for a diameter), there are
  exactly two arc options (large or small), and `largeArc=0` picks
  the smaller — which for a 180° chord is still 180° (no smaller
  option). Verify SVG-spec-wise this renders the upper arc, not
  the lower.

**Q3.** Spot-check the two doc updates (audit-summary.md D3
superseding note + spec.md D3 update). Are they sufficient to
prevent future maintainers from being confused by the "≤100px"
phrasing in adjacent context that wasn't updated?

**Q4.** Overall: are all 5 must-fix items resolved and no new
must-fix items introduced? Is Session 2 ready to close out?

Short, structured response per question. Skip stylistic nits — this
is the close-out gate.
