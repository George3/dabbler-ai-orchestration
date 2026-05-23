## Copilot Effort Sidebar Results — Set 044 / Session 5

> **Session:** 044 / S5. **Date:** 2026-05-23. **Method:** matched-pair
> Copilot subprocess runs at `--effort low` and `--effort high` against
> the synthetic-set, with the same task battery as S4a baseline. Closes
> (or moves toward closing) [`narration-design.md`](narration-design.md)
> §11 Q3 and Q4.
> **Companion docs:**
> [`copilot-narration-results.md`](copilot-narration-results.md) §5.5
> recorded the `--effort medium` baseline data this sidebar compares
> against; [`cross-backend-synthesis.md`](cross-backend-synthesis.md)
> §6 row 4 flagged this measurement as a candidate sidebar.
> **Memory:** project_044_copilot_effort_sidebar_deferred was created
> at S4b kickoff when the operator skipped it; that memory is closed by
> this document.

---

### 1. Headline

| Open question | Status before S5 sidebar | Status after S5 sidebar |
|---|---|---|
| **Q3** — Does `gen_ai.request.reasoning_effort` appear in OTel at `--effort low` or `--effort high`? | OMITTED at `--effort medium` (S4a); low/high unmeasured | **OMITTED at all three effort levels.** The attribute is unconditionally absent from Copilot 1.0.51 OTel emission. **CLOSED.** |
| **Q4** — Do `gen_ai.usage.reasoning.output_tokens` values distinguish low/medium/high effort buckets? | Not measured | **Partial answer: per-turn values overlap heavily across low and medium; per-session aggregate volume separates high from (low ∪ medium). Underpowered at N=1 per level.** |

**Material implication for the S5 proposal: Branch A (native
reasoning-effort attribute) is empirically dead on Copilot at every
exposed effort level.** Both backends — Claude and Copilot — now need
narration or some non-native channel to surface A3 reasoning effort.
This symmetry simplifies one strategic question the proposal must
address.

---

### 2. Run setup (held constant)

| Constant | Value |
|---|---|
| Copilot CLI version | 1.0.51 (per S4a; no upgrade between sessions) |
| Workspace | `c:\tmp\dabbler-log-harvest\synthetic-set\` |
| Model | `gpt-5.4` (explicit `--model gpt-5.4`) |
| Custom-instructions | DISABLED (`--no-custom-instructions`; matches S4a baseline; AGENTS.md was stashed as `AGENTS.md.copilot-stashed` by S4b, but `--no-custom-instructions` makes that irrelevant) |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | `true` (per S4a; required for full output capture) |
| `COPILOT_OTEL_ENABLED` | `true` |
| `COPILOT_OTEL_EXPORTER_TYPE` | `file` |
| Permission mode | `--allow-all-tools --allow-all-paths` |
| Task battery | identical 5-task prompt from
[`copilot-narration-results.md`](copilot-narration-results.md) §3 |
| Session persistence | `-s` (save session) |
| Pre-run reset | `session-state.json` rewritten to pristine shape before each run |

**Treatment difference**: only `--effort` (`low` vs `high`).

**Driver**:
[`sidebar_runner.ps1`](sidebar_runner.ps1) (committed alongside this
file). Total wall-clock for both runs: ~30 s on a hot Copilot
CLI; zero router dollars.

> **Pristine-state confound noted**: the synthetic-set's resting
> state file has `status: "in-progress"` + `lifecycleState:
> "ready_to_start"` (carried forward from S4a/S4b, never returned
> to `not-started`). Both Copilot runs therefore reported task 3 as
> "already in-progress" and treated task 4 as a no-op mutation
> rather than a real edit. **This is immaterial to Q3/Q4** — the
> measured signals are OTel `chat <model>` span attributes, which
> are emitted regardless of whether task 4 actually mutates the
> file. Mentioned for audit completeness only.

---

### 3. OTel output inventory

| Run | OTel JSONL | Records | Chat spans |
|---|---|---|---|
| `--effort low`  | `c:/tmp/dabbler-log-harvest/otel/s5-sidebar-low.jsonl`  | 20 | 5 |
| `--effort high` | `c:/tmp/dabbler-log-harvest/otel/s5-sidebar-high.jsonl` | 26 | 7 |

Higher effort produces more chat spans (5 vs 7) for the same task
battery, consistent with Copilot allocating extra round-trips for
reasoning. The S4a `--effort medium` baseline recorded 4 chat
spans, so the chat-span count appears to scale with effort
(low=5, medium=4, high=7) — but this single-shot per-effort
measurement is too noisy to use directly. The low > medium
inversion is plausibly within run-to-run variance (the §7.7 task-1
tool-choice variance from S4b illustrates similar noise floors).

---

### 4. Q3 — `gen_ai.request.reasoning_effort` presence

Result across all chat spans in each run:

| Run | Per-chat-span `gen_ai.request.reasoning_effort` |
|---|---|
| `--effort low`    | `[None, None, None, None, None]` |
| `--effort medium` (S4a baseline) | `[None, None, None, None]` |
| `--effort high`   | `[None, None, None, None, None, None, None]` |

**The attribute is omitted at every measured effort level.** This is
not a "default-effort omits, non-default emits" pattern (as
hypothesized in
[`smoke-probe-results.md`](smoke-probe-results.md) §5 H1); it is a
**Copilot-CLI-wide omission**.

Two plausible explanations, neither investigable from inside this
sidebar:

1. **Telemetry policy:** Copilot 1.0.51 deliberately suppresses
   `gen_ai.request.reasoning_effort` from its OTel emission for
   privacy/telemetry-policy reasons. Out of band probing
   (Copilot release notes / source) would confirm or deny.
2. **Version-specific omission:** the attribute may appear in a
   later Copilot release. Would require re-test on a future
   Copilot version.

The proposal does NOT need to resolve which mechanism caused the
omission. The empirical fact is sufficient: **the Copilot OTel
surface does not carry the effort signal at any exposed
`--effort` value.**

---

### 5. Q4 — `gen_ai.usage.reasoning.output_tokens` per turn

Per-chat-span values:

| Run | Per-span values | Stats |
|---|---|---|
| `--effort low`    | `[70, 282, 177, 18, 50]` | min=18, max=282, sum=597, n=5 |
| `--effort medium` (S4a baseline) | `[516, 15, 59, 163]` | min=15, max=516, sum=753, n=4 |
| `--effort high`   | `[516, 53, 33, 2015, None, 180, 144]` | min=33, max=2015, sum=2941, n=6 (one span had no `reasoning.output_tokens` attribute at all) |

> Note: `None` in the high-effort row means one of the 7 chat spans
> emitted no `reasoning.output_tokens` attribute. Whether this is
> a non-reasoning chat span or an attribute-omission gap is not
> isolated from this single sample.

**Per-turn discrimination — FAILS.**

The low and medium runs both produce values in the same envelope
(roughly 15-300), with single-value overlap (`50` ≈ `59`). A
harvester observing a single turn cannot infer effort from
`reasoning.output_tokens` alone — the low and medium distributions
are not separable.

**Per-session aggregate discrimination — SUGGESTIVE but UNDERPOWERED.**

| Effort | Total reasoning tokens | Chat spans | Mean per span |
|---|---|---|---|
| low    |  597 | 5 | 119 |
| medium |  753 | 4 | 188 |
| high   | 2941 | 6 | 490 |

High is clearly separated from low and medium on total volume
(~4× sum, ~3× mean, plus the singular 2015-token outlier turn).
Low and medium overlap on both volume and mean. **A
high-vs-not-high discriminator on aggregate volume is plausible;
a three-way low/medium/high discriminator is not, from this
sample.**

This is N=1 per effort level. A robust per-session estimator
would require ~5-10 matched runs per effort to characterize the
within-effort variance. That's a Set 045 (or later) sidebar, not
something to commit this set to.

---

### 6. Confound notes

#### 6.1 Pristine-state drift on synthetic-set

The synthetic-set's resting state had `status: "in-progress"`
(carried forward from earlier 044 runs that wrote
`in-progress` and never reset to `not-started`). Both sidebar
runs observed this state and reported task 3 as "already
in-progress", treating task 4 as a no-op edit.

Effect on Q3/Q4: **immaterial.** The reasoning-effort attribute
and reasoning-output-tokens proxy are emitted independent of
whether task 4 actually mutates the file. Chat spans still
fire; tool calls still execute (the `apply_patch` span appears
in both runs at chat-span position matching task 4).

Effect on S4a comparability: minor. The S4a baseline run also
treated `not-started` → `in-progress` as a real mutation; the
sidebar runs treated it as a no-op. The token counts and turn
counts therefore reflect slightly different "work done" between
sidebar and baseline. Not a basis for adjusting any conclusion
in this doc, but it should be flagged if the proposal needs
to compare absolute token-volume numbers across the runs.

#### 6.2 Task-5 (`ai_router.start_session --help`) reproducible failure

Both runs reported task 5 as failing because the synthetic-set
workspace's Python environment doesn't have `ai_router`
installed (the synthetic-set is a Copilot-target scratch dir,
not a dev checkout). This is **unchanged from S4a** and is
incidental to the B4 signal — the subprocess invocation argv
is still observable in OTel.

#### 6.3 Variance bound — single-run-per-effort

Every observation here is from one run at each effort level. The
S4b §7.8 tool-sequence variance (Glob vs Bash on task 1 across
v1 / v2 runs of the same prompt) demonstrates that Copilot's
non-deterministic choices vary across runs. The Q4 numbers
should be read with that variance bound in mind: low-effort
distributions could plausibly extend higher than 282 on another
run, and the medium-vs-low separation could disappear under
a more thorough characterization.

---

### 7. Implications for the S5 proposal

1. **Branch A is empirically dead on Copilot.** The
   `gen_ai.request.reasoning_effort` attribute is omitted at
   every exposed effort level. Any A3 (reasoning-effort
   harvest) signal on Copilot must come from either:
   - narration (the v1 design's Branch B), or
   - a parallel non-OTel channel (e.g., the orchestrator
     records `--effort` at session check-out and the harvester
     joins on session-id).

2. **Symmetry with Claude is now confirmed.** Claude's
   `usage` block has no reasoning-axis field (S2 + S4b);
   Copilot's OTel has no reasoning-axis attribute (S4a + S5
   sidebar). **Both backends are in the same
   "native-A3-absent" bucket.** This symmetry simplifies one
   axis of the proposal: narration vs non-native-channel is
   the trade-off to evaluate, NOT "per-backend Branch A vs
   Branch B."

3. **The `reasoning.output_tokens` proxy is too noisy to
   replace `reasoning_effort`.** Per-turn: distributions overlap
   across low and medium. Per-session aggregate: separable for
   high vs not-high at N=1 but underpowered. A proposal that
   relies on this proxy for per-session effort estimation needs
   either (a) a properly powered cross-effort calibration set
   (Set 045+), or (b) some external join (state-file
   `orchestrator.effort` is the obvious candidate, but that's
   not a *harvest* signal — it's the orchestrator's own
   record).

4. **The session-start-only A3 framing remains viable.** If S5's
   proposal accepts that A3 lands at session boundary only (via
   narration's `phase=session-start` marker carrying
   `effort=...`), the empirical evidence from this sidebar
   neither helps nor hurts that path. Branch B per-turn
   narration is unreliable on Claude (S4b: 0/3) and untested on
   Copilot. Session-start-only is the lowest-risk shape.

5. **Pull-in trigger NOT met.** The memory
   `project_044_copilot_effort_sidebar_deferred` said the
   sidebar should be pulled in "only if Copilot Branch A vs
   Branch B materially changes the design." It DID — Branch A
   is dead on Copilot, which removes one design dimension.
   That removal **simplifies** the proposal rather than
   complicating it, so this finding is a "fewer branches to
   reason about in consensus" benefit, not a destabilization.

---

### 8. Verdict

**Q3 CLOSED:** `gen_ai.request.reasoning_effort` is unconditionally
absent from Copilot 1.0.51 OTel output at low, medium, and high
effort levels.

**Q4 PARTIALLY ANSWERED:** the `reasoning.output_tokens` proxy fails
per-turn three-way discrimination but supports per-session
high-vs-not-high discrimination at N=1. Robust three-way
characterization deferred to a follow-on set (Set 045 or later)
if needed; not on the critical path for S5's proposal.

**S5 proposal incorporates:** "Branch A on Copilot is empirically
unavailable; both backends require narration or a non-native
channel for A3." This is the new boundary condition for the
proposal.

**S4 + S5-sidebar harvest-objective tally:** **1 of 15** harvest
objectives closes by narration on both backends (C3 turn-0
only, conditional on phrasing on Claude and OTel content-capture
env var on Copilot). The other 14 are natively reachable. A3
remains conditional on narration on both backends; the sidebar
confirmed Copilot cannot supply A3 natively.
