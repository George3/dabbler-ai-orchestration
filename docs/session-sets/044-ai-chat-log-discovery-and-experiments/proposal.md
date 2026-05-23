# Proposal — Log-Harvest Observability for the Session Set Explorer

> **Session:** 044 / S5. **Status:** v0 draft for cross-provider
> consensus. **Author:** Claude (`claude-opus-4-7`, high effort) acting
> as Set 044 orchestrator.
> **Companion docs (the evidence base):**
> [`spec.md`](spec.md),
> [`baseline-comparison.md`](baseline-comparison.md),
> [`narration-design.md`](narration-design.md),
> [`copilot-narration-results.md`](copilot-narration-results.md),
> [`claude-narration-results.md`](claude-narration-results.md),
> [`cross-backend-synthesis.md`](cross-backend-synthesis.md),
> [`copilot-effort-sidebar-results.md`](copilot-effort-sidebar-results.md).
> **Reader audience:** GPT-5.4, Gemini Pro, Opus 4.6 (cross-provider
> consensus call); the operator (go/no-go for S6 implementation vs
> deferral to Set 045).

---

## 0. Headline recommendation

**Build a log-harvest observability layer; do not build the
launch-adapter sets (037–041) as currently scoped.** The Session Set
Explorer can be given honest, cross-AI orchestrator-state signal at
a small fraction of the engineering cost of per-provider launch
adapters, because the assistants' existing log files already carry
14 of the 15 enumerated harvest objectives natively. The one missing
signal (the Dabbler set/session boundary, "C3") closes via a small,
session-start-only narration contract that has been demonstrated to
work on both Copilot and Claude under specific phrasing discipline.

**Phasing**:
- **S6 (this set):** ship a Copilot-only minimum viable harvester —
  parser + narration template + Explorer surface — to prove the
  end-to-end path. Estimated complexity: comparable to a single
  prior session.
- **Set 045 (new):** Claude-side parser + both backends running
  in production + cross-AI conflict-detection join. The real
  engineering work lives here.

**Roadmap reshape**:
- Sets 038 (Claude launch adapter), 039 (Copilot launch adapter),
  040 (Codex launch adapter), and 041 (Gemini launch adapter)
  **die outright** as currently scoped.
- Set 037 (launch-adapter foundations) **shrinks dramatically** —
  the `LaunchAdapter` / `LaunchPlan` contract is no longer needed;
  what remains, if anything, is a thin "post-launch identity
  notification" hook that doesn't gate launches.
- Sets 042–043 (chat interface) are unaffected — they answer a
  different question (does Dabbler own a chat surface) and don't
  depend on harvesting vs adapters.

---

## 1. Why this set existed (problem statement)

The Session Set Explorer is the operator-facing surface that displays
which AI is working on which session set with what model and effort.
The Set 033 check-out / check-in machinery makes this reliable for
**AIs that go through the dabbler writer** (`start_session` /
`close_session`): they hold a check-out in `session-state.json`,
they show up correctly in the per-row accordion, and the Set 034
right-click menu does the right thing.

But AIs **running outside the writer path** — a Copilot session
working in a workspace without invoking the lifecycle CLI, a Claude
Code session opened by the operator without `/start-session`-style
discipline, a Codex session reading files at someone's direction —
are **invisible to the Explorer**. The Explorer can lie about
session state in those cases. Worse, two AIs working on the same
session set without coordination is exactly the failure mode the
Set 033 architecture was designed to prevent, and the Explorer
can't surface that failure when the AIs are outside the writer.

Two solutions to that gap were on the table going into Set 044:

| Approach | What it does | What it costs |
|---|---|---|
| **Launch adapters (Sets 037–041)** | Wrap every assistant CLI launch in extension code that captures the launch identity at the IDE-launch boundary; provide a `LaunchAdapter` per provider | 4 substantial session sets of extension work (`LaunchPlan` contract, per-provider argv/env mapping, terminal-launch hosting, IDE command surface changes); was scoped *before* any empirical investigation of what logs already contain |
| **Log harvesting (this set)** | Parse the log files the assistants are already writing; surface their identity and behavior signals into the Explorer; add a narration contract for the one missing signal | TBD — the entire point of Set 044 is to determine this cost empirically |

Set 044's job is to decide which of those two we build. This
proposal is the answer.

---

## 2. The 15 harvest objectives and where they live

A reliable Explorer needs, at minimum, the following 15 signals from
each in-flight AI session. The empirical answer to "where do those
signals already live" was the work of S1 (Copilot harvest) and S2
(Claude harvest), refined by S3 (narration design) and tested live
in S4 (narration experiments) and the S5 effort sidebar.

| # | Objective | Copilot native | Claude native | Notes |
|---|---|---|---|---|
| A1 | Engine name | implicit in process | implicit in launch + JSONL path | trivial |
| A2 | Model id per turn | `gen_ai.request.model` on chat span | `model` on assistant event | reliable |
| A3 | **Reasoning effort** | **ABSENT** (S5 sidebar: omitted at low+medium+high) | **ABSENT** (S2 + S4b: no field at any effort) | **needs narration or non-native channel** |
| A4 | Provider | `gen_ai.provider.name` | implicit (anthropic) | reliable |
| A5 | Conv / session id | `gen_ai.conversation.id` | JSONL filename + `sessionId` | reliable |
| B1 | Tool calls (name + args) | OTel `execute_tool` spans + `gen_ai.output.messages` (with content-capture env var) | tool_use blocks in assistant events | reliable |
| B2 | Touches to `session-sets/**` | derivable from B1 via path filter | derivable from B1 | reliable |
| B3 | Touches to `session-state.json` | derivable from B1 | derivable from B1 | reliable |
| B4 | Subprocess invocations of writer | argv visible in `execute_tool powershell` span | tool_use args for Bash invocations | reliable (subject to content-capture flag) |
| B5 | Writer-bypass file writes | Edit/apply_patch tool calls on state files | tool_use Edit/Write on state files | reliable |
| C1 | Per-turn timestamps | OTel span start/end times | JSONL event timestamps | reliable |
| C2 | Workspace cwd | `gen_ai.client.workspace.path` (and process cwd) | JSONL `cwd` field | reliable |
| C3 | **Dabbler set/session boundary marker** | **ABSENT** (Copilot doesn't know about Dabbler) | **ABSENT** (same reason) | **needs narration; the only "must-narrate" signal** |
| C4 | Tool-call sequence | implicit in OTel span ordering | implicit in JSONL event order | reliable |
| C5 | Token usage / cost proxy | `gen_ai.usage.*` | `usage` block on assistant events | reliable |

**14 of 15 are natively reachable; only C3 strictly requires
narration.** A3 is also unreachable natively on both backends, but
A3's value at per-turn fidelity is dubious (S4b: Claude silently
drops per-turn markers 0/3; S5 sidebar: Copilot's
`reasoning.output_tokens` proxy is too noisy per-turn). A3 at
**session-start fidelity** comes "for free" once C3's narration
marker is in place — both can be carried in the same
`phase=session-start` payload.

So the practical narration scope is: **one marker per session, at
session start, carrying both C3 and A3**. Everything else is
parsed from native log surface.

---

## 3. Empirical findings (compressed)

The S1–S5 work resolved several previously-open questions. The
proposal builds on these resolved facts:

1. **Copilot OTel JSONL is the right native surface on Copilot.** The
   alternate surface (`session-store.db turns`) drops the narration
   marker in a two-round-trip artifact (smoke-probe §3.1); the OTel
   `gen_ai.output.messages` field carries the marker reliably.
   Precondition: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`.
2. **Claude Code JSONL** (`~/.claude/projects/<workspace>/<session-id>.jsonl`)
   carries assistant text content inline by default — no opt-in
   required. The marker lands in `message.content[].text`.
3. **The same parser regex works on both backends** because both
   surfaces inline marker text in an assistant-output slot. The
   parser is backend-agnostic at the field level; backend asymmetry
   is absorbed in the *delivery channel*, not in the parser.
4. **Narration works on Copilot** with the v1 `AGENTS.md` channel,
   cleanly, at the session-start position. Per-turn narration
   compliance is untested on Copilot (the deferred Branch B test
   case).
5. **Narration works on Claude only with carefully-phrased
   instructions.** The v1 phrasing (which used words like
   "synthetic harvest target," "NOT a real project") triggered
   Claude's prompt-injection classifier; Claude refused to comply.
   A v2 reframe that presented CLAUDE.md as a normal project
   convention (no harvest/synthetic/NOT-real language) flipped
   Claude to compliance for the session-start marker but **0/3 of
   the expected per-turn markers landed** even under acceptable
   phrasing.
6. **`gen_ai.request.reasoning_effort` is unconditionally absent
   from Copilot OTel** at every exposed effort level (S5 sidebar).
   Branch A (native A3) is dead on Copilot. Claude was already
   known to lack a native A3 field. Both backends are now
   symmetric in needing narration for A3.

---

## 4. Proposed architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Per-AI log writers (already exist, not modified by us)         │
│                                                                 │
│   Copilot 1.0.51                       Claude Code 2.1.63       │
│   ──────────────                       ─────────────────        │
│   OTel file exporter                   ~/.claude/projects/      │
│   $COPILOT_OTEL_FILE_EXPORTER_PATH     <workspace-slug>/        │
│   (requires OTEL_INSTRUMENT_...=true)  <session-id>.jsonl       │
│                                                                 │
│        │                                       │                │
│        ▼                                       ▼                │
│   ┌──────────────┐                       ┌──────────────┐       │
│   │ Copilot      │                       │ Claude       │       │
│   │ parser       │                       │ parser       │       │
│   │ (per-backend │                       │ (per-backend │       │
│   │  shim,       │                       │  shim,       │       │
│   │  emits       │                       │  emits       │       │
│   │  canonical   │                       │  canonical   │       │
│   │  records)    │                       │  records)    │       │
│   └──────┬───────┘                       └──────┬───────┘       │
│          │   (canonical Harvest Record stream)  │               │
│          └───────────────────┬───────────────────┘              │
│                              │                                  │
│                              ▼                                  │
│                  ┌────────────────────────┐                     │
│                  │  Harvester / joiner    │                     │
│                  │  - cross-source merge  │                     │
│                  │  - session-state join  │                     │
│                  │  - conflict detection  │                     │
│                  └──────────┬─────────────┘                     │
│                             │                                   │
│                             ▼                                   │
│              ┌─────────────────────────────┐                    │
│              │  Session Set Explorer       │                    │
│              │  (existing webview tree)    │                    │
│              │  - per-row badges           │                    │
│              │  - conflict warnings        │                    │
│              └─────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 Per-backend parser shims

Each backend has a small parser whose only job is to convert a
backend-specific log file into a **canonical Harvest Record stream**.
Canonical record shape (proposed):

```jsonc
{
  "ts":             "2026-05-23T08:30:14.123Z",    // C1
  "engine":         "copilot" | "claude",          // A1
  "model":          "gpt-5.4",                     // A2
  "provider":       "github" | "anthropic",        // A4
  "conv_id":        "<provider conv/session id>",  // A5
  "workspace_cwd":  "C:/.../some/repo",            // C2
  "event_type":     "turn" | "tool_call" | "marker" | "usage",
  "tool":           "Edit" | "Bash" | "apply_patch" | ...,  // B1
  "tool_args":      { ... },                       // B1 detail
  "set_slug":       "044-ai-chat-log-discovery..." | null,  // C3 (from marker only)
  "session_number": 5 | null,                      // C3 (from marker only)
  "effort":         "high" | "medium" | "low" | null,  // A3 (from marker only)
  "tokens_in":      14049,                         // C5
  "tokens_out":     613,                           // C5
  "raw_ref":        { "file": "...", "line": 12 }
}
```

The parsers are small (a few hundred lines each, including the
backend-specific demangling and the `phase=session-start` marker
extractor). They do not maintain state; they read forward over the
log file and emit records.

### 4.2 Narration contract v1.1

Revised from v1 LOCKED in light of S4 evidence:

| v1 LOCKED scope | v1.1 proposed scope |
|---|---|
| `phase=session-start` AND `phase=turn` markers | **`phase=session-start` only**. Per-turn markers dropped from the contract. |
| Branch A (native effort) for Copilot, Branch B (narrated effort) for Claude | **Branch B at session-start only for both backends.** A3 carried inside the session-start marker payload. |
| AGENTS.md (Copilot) + CLAUDE.md (Claude) as delivery channels | **Same**, but with a *canonical template* that the operator (or extension) MUST use verbatim. No paraphrasing. Phrasing-sensitivity risk on Claude is mitigated by template stability rather than by "phrase carefully." |
| Parameterization mechanism unspecified | **Mechanism (2)**: operator-side build step (or extension command) reads `session-state.json` and writes a pre-substituted instruction file. Mechanism (1) — manual substitution — is documented as a known failure shape and not recommended. |

The v1 parser-skip discipline (§5.4 / §5.5 of narration-design.md)
carries forward unchanged; it correctly handles the phantoms
observed in S4a (gen_ai.system_instructions echoes) and S4b
(refusal-narrative substrings).

### 4.3 Harvester / joiner

A small process that:
1. Watches each per-backend log directory for new records.
2. Joins them on `workspace_cwd` to identify the relevant Dabbler
   repo + session set.
3. Cross-references against `session-state.json` (the writer's truth)
   to detect:
   - **Coordination conflicts** — an AI is touching a session set
     no one has checked out, OR a different AI is checked out and
     yet a second AI is also touching the same set.
   - **Out-of-band session-state writes** — the writer-bypass signal
     (B5) appearing in the canonical record stream when the writer
     itself didn't run.
4. Pushes signals to the Explorer.

The joiner is the engineering center of gravity. The parsers are
shallow; the joiner is where conflict semantics live.

### 4.4 Operator-facing setup

| Backend | Required setup |
|---|---|
| Copilot | One environment variable: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`. Optionally route OTel output to a Dabbler-known path via `COPILOT_OTEL_FILE_EXPORTER_PATH`. The extension can set both via its terminal-launch helper. |
| Claude | A `CLAUDE.md` file at the workspace root containing the canonical narration template. The extension can write/regenerate this file at session check-out. |

Both are lightweight. Neither requires "wrapping the launch" in
the launch-adapter sense.

---

## 5. What ships when

### 5.1 In S6 (this set, smallest viable proof)

**Concrete scope:**
1. Copilot OTel parser shim (single file, ~200 LOC).
2. Narration template generator: writes `AGENTS.md` for the
   active session set into the workspace root at check-out time.
3. Minimal harvester: walks the configured OTel directory, emits
   canonical records to a JSONL log Dabbler owns.
4. Explorer change: per-row indicator showing
   "Copilot detected: <model> on session <n>" when harvest records
   match the row's set slug. No conflict detection yet.
5. Layer-3 Playwright coverage of the new Explorer indicator.
6. Ad-hoc UAT checklist for the operator-visible Explorer change.

**Explicit non-goals in S6**:
- Claude-side parser (Set 045).
- Conflict detection / joiner logic beyond a simple "set slug
  match" badge (Set 045).
- Codex / Gemini parsers (later sets, if needed).
- Reshaping the launch-adapter sets in their own metadata (a
  separate housekeeping commit, post-044).

**Effort estimate**: 1 session's worth of work given that the
parser is small, the narration template is already designed (v1.1
is a focused revision of v1), and the Explorer is webview HTML
that has had recent iteration cycles (Set 034). Comparable to S5
of Set 029 or S3 of Set 033 in scope.

### 5.2 In Set 045 (the real engineering)

1. Claude JSONL parser.
2. The full joiner: conflict detection, multi-source merge,
   out-of-band write detection.
3. Explorer conflict surfacing: visible badges when a writer-bypass
   is detected or when two AIs are observed on the same set.
4. Operator-facing setup polish: the extension command that
   regenerates `AGENTS.md` / `CLAUDE.md` from current state.
5. Long-running harvest persistence (a JSONL ledger Dabbler keeps).
6. Layer-1 / Layer-2 / Layer-3 coverage of the joiner semantics.

**Effort estimate**: 4–6 sessions. Smaller than Sets 037–041
combined (which were ~12 sessions in aggregate), and concentrates
the engineering on the *useful* parts (conflict semantics)
instead of on per-provider launch boilerplate.

---

## 6. Roadmap reshape — explicit calls

### 6.1 Set 037 — Launch-Adapter Foundations
**Status: SHRINK DRAMATICALLY or RETIRE.**

The `LaunchAdapter` / `LaunchPlan` / `BeginSessionRequest` contract is
the load-bearing artifact of Set 037. It is **no longer needed** —
the harvester reads logs the assistants already write; we don't
need to gate or wrap launches.

What might survive: a thin "post-launch identity notification" hook
that the extension can call after a manual terminal launch to record
"the operator just opened Copilot in this workspace at this time."
That's a one-file change, not a session-set.

**Recommendation**: retire Set 037 outright; if the post-launch hook
proves useful, fold it into Set 045 as one of its sessions.

### 6.2 Set 038 — Claude Launch Adapter
**Status: DIE.**

Claude already writes a complete JSONL log of every session to
`~/.claude/projects/`. The harvester reads it. Wrapping Claude's
launch buys nothing the JSONL doesn't already deliver.

### 6.3 Set 039 — Copilot Launch Adapter
**Status: DIE.**

Same story. Copilot already emits OTel. The harvester reads it.
Wrapping Copilot's launch buys nothing the OTel doesn't already
deliver, except setting the one required env var — which is a
one-line addition to the extension's terminal-launch helper,
not a session-set.

### 6.4 Set 040 — Codex Launch Adapter
**Status: DIE (but Codex parser deferred to a follow-on).**

Codex was out of scope for Set 044 by spec (line 51 of
[`spec.md`](spec.md)). If the harvester needs Codex coverage
later, it gets a parser shim — comparable in size to the Copilot
parser. That work belongs in a follow-on, not in a launch-adapter
session-set.

### 6.5 Set 041 — Gemini Launch Adapter
**Status: DIE.**

Same as Codex: out of scope for 044, add a parser shim later if
needed.

### 6.6 Sets 042–043 — Chat Interface
**Status: UNAFFECTED.**

These answer a different question: does Dabbler own a chat surface
for assistant interaction? Independent of the harvest-vs-adapter
choice. Keep as-scoped.

### 6.7 Set 036 — chatSessionId and Watcher Scope
**Status: UNAFFECTED, RUNS NEXT.**

Set 036 implements the audit-locked verdicts from the
`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`
proposal. It's writer-side discipline (the `start_session` and
`close_session` boundary), orthogonal to log harvesting. Per the
2026-05-22 sequencing decision, 044 runs first because its findings
could reshape what 036 needs to display; this proposal does not
reshape any 036 commitment. **036 should run next as planned.**

---

## 7. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Claude's injection classifier refuses the v1.1 template phrasing | medium | medium (operator-facing setup fails on Claude) | (a) freeze a v1.1 canonical template; (b) provide an ablation test that catches refusal early; (c) hook-channel fallback (write the marker via Claude's `SessionStart` hook instead of `CLAUDE.md`) as a documented escape hatch. |
| Operator forgets to set the OTel content-capture env var on Copilot | high | high (parser sees Copilot work but can't extract marker / tool args) | extension's terminal-launch helper sets the env var by default; the harvester emits a one-shot warning if it observes OTel records lacking `gen_ai.output.messages`. |
| Per-session A3 fidelity isn't enough (operator wants per-turn effort) | low | low | A3 is a "nice to have" — effort changes mid-session are not currently exposed by either CLI; the proposal accepts session-start fidelity as the maximum any narration path can reliably deliver. |
| Parameterization mechanism (1) failure — operator manually edits the template and forgets to substitute values | low (mechanism (2) is the default) | low | the v1.1 narration contract drops mechanism (1) as recommended; the §5.5 parser-skip discipline catches the most-egregious placeholder-leak shape anyway. |
| Conflict-detection edge cases under multi-AI workflows | medium | medium | conflict semantics are Set 045's center of gravity, not S6's; S6 ships only "set-slug match" indicator; the heavy semantics ship with their own coverage. |
| OTel file growth across long sessions | low | low | parser reads forward and truncates after a configurable size threshold; this is an ops detail, not a design risk. |

---

## 8. Open questions for consensus

These are the questions the cross-provider consensus call should
specifically engage with. They are NOT pre-decided by this draft.

1. **Is the harvest-vs-adapter framing correct, or is there a third
   option this proposal missed?** (E.g., a hybrid where the
   extension records launch identity *without* wrapping the
   process, then the harvester joins on the launch record. The
   proposal's "post-launch identity notification" hook is a
   minimal version of this.)
2. **Is dropping per-turn narration from the contract the right
   call, or should a hook-channel fallback for per-turn
   reasoning-effort be in v1.1's scope?** S4b §10 raised this.
   Cross-backend-synthesis §8 item 6 raised this.
3. **Is "Copilot-only minimum viable proof in S6" the right
   scoping**, or is Claude the right first target instead (because
   the JSONL is always-on and no env var setup is needed)?
4. **Should the conflict-detection joiner live inside the VS Code
   extension (TypeScript) or as a Python process the extension
   launches?** The router lives in Python; the extension is
   TypeScript. The harvester crosses both worlds.
5. **Should this proposal commit to retiring Sets 038–041
   immediately**, or should they be parked-not-deleted in case
   Set 045 finds a regression that motivates them? Cost of parking
   is low (one line in each set's `CANCELLED.md`); cost of
   premature deletion is zero (git history holds them).
6. **Does the S6 "minimal viable proof" carry enough operator-
   visible value** to be worth shipping in 044 vs deferring all
   implementation to Set 045 and keeping 044 as a pure spike?
   The spec leaves this branch open (line 305–315 of `spec.md`).

7. **Should a Python launch-wrapper become the primary C3 / A3
   channel, with narration relegated to a fallback for
   free-running sessions?**

   **The idea** (operator-floated, 2026-05-23 during S5 proposal
   review): instead of (or in addition to) instructing the AI to
   emit a `phase=session-start` narration marker, a small Python
   CLI wraps the AI CLI launch. Invocation shape:

   ```
   dabbler-launch claude --set 044 --session 5 --effort high -p "..."
   dabbler-launch copilot --set 044 --session 5 --effort medium -p "..."
   ```

   The wrapper records the Dabbler launch context (set slug,
   session number, effort, timestamp, launcher identity) to a
   Dabbler-owned log *before* spawning the AI subprocess. The AI
   then runs normally and writes its own native log (Claude JSONL
   / Copilot OTel). The harvester joins on
   `conversation_id` / `session_id` across the wrapper log and
   the AI's native log. The wrapper is small (an order of
   magnitude smaller than per-provider launch adapters — no
   `LaunchAdapter` class, no `LaunchPlan` contract; the AI's own
   CLI handles argv/env, the wrapper only adds Dabbler context).

   **What it changes for the proposal:**
   - C3 is captured directly by the wrapper, with **no AI
     cooperation required**. Claude's phrasing-sensitivity
     (S4b §7.1) becomes irrelevant for Dabbler-launched
     sessions; the OTel content-capture env var on Copilot can
     be set by the wrapper rather than relying on operator
     setup discipline.
   - A3 is captured from the wrapper's CLI arg, not from a
     narration marker. The per-turn-marker unreliability on
     Claude (S4b §5.4) becomes irrelevant for the same reason.
   - Narration v1.1 becomes the **fallback** for sessions
     opened *outside* the wrapper (free-running terminal
     sessions), not the **primary** mechanism. The phrasing-
     sensitivity risk drops from primary to edge-case.
   - The wrapper is a natural home for other cross-cutting
     concerns: per-session cost tracking, budget enforcement,
     conflict prevention (refuse to launch if another AI is
     checked out per `session-state.json`). Implementing those
     once in shared Python is architecturally cleaner than
     scattering them across per-provider launch adapters.

   **What it does NOT replace:**
   - The per-backend log parsers (§4.1) still own behavior-signal
     extraction: tool calls, per-turn tokens, mutations to
     session-state, writer-bypass detection. The wrapper sees
     only the launch context and stdin/stdout — not the AI's
     internal tool calls or thinking. Parser work is unchanged.
   - The harvester / joiner (§4.3) still owns conflict semantics.
   - Free-running sessions opened outside the wrapper still need
     log parsing to be observable. The wrapper is the primary
     channel only for Dabbler-launched sessions.

   **What it partially resurrects from Sets 037-041:** the
   wrapper IS a launch adapter — but a single, cross-provider
   Python CLI, NOT the per-provider TypeScript `LaunchAdapter`
   architecture. The bulk of Sets 037-041 (per-provider adapter
   classes, `LaunchPlan` contract, `BeginSessionRequest`,
   terminal-launch hosting) still dies. What survives is a
   single shared concept that's ~1 file's worth of code,
   not 4 session-sets' worth.

   **Specific decision points for consensus:**

   1. **Is the wrapper-plus-narration-fallback architecture
      stronger than narration-only?** The proposal's draft
      framing accepts narration's risks (phrasing-sensitivity,
      per-turn unreliability) as the cost of universal coverage.
      The wrapper trades universality for reliability — it works
      cleanly when invoked but doesn't help when bypassed.
      Trade-off worth making?

   2. **If yes, should the wrapper ship in S6 instead of (or in
      addition to) the Copilot parser shim?** The wrapper is
      smaller and provider-agnostic; it might be a better
      "smallest viable proof" than a Copilot-specific parser.
      Alternatively: ship wrapper + Copilot parser together in
      S6 if the combined scope still fits one session.

   3. **What's the wrapper's interactive-mode story?** Both
      Claude Code and Copilot CLI have headless `-p` mode (used
      throughout S4 / S5 sidebar) and interactive REPL mode
      (the dominant operator pattern). Headless mode is trivial
      to wrap; interactive mode requires TTY passthrough that
      can be fragile on Windows. Does the proposal commit to
      both, or only headless in S6 with interactive deferred?

   4. **Where does the wrapper live in the repo?** Candidate
      homes: (a) `ai_router/` as a new sibling to
      `start_session.py` / `close_session.py`; (b)
      `tools/dabbler-launch/` as a separate Python package;
      (c) inside the extension's terminal-launch helper as a
      TypeScript implementation. (a) reuses the router's
      installation surface; (c) is closer to where the launch
      actually originates.

   5. **Does the wrapper interact with the chat-interface
      question (Sets 042-043)?** If Dabbler eventually owns a
      chat surface, the chat backend would presumably invoke
      AI CLIs the same way the wrapper does — making the
      wrapper effectively a building block for any future
      chat-surface decision. Worth confirming the architectural
      compatibility now, before locking either direction.

   6. **Should the wrapper be ungated default, or opt-in?**
      Ungated-default means every Dabbler-launched session
      records identity automatically — strongest observability.
      Opt-in means the operator decides per-session — lowest
      friction. The proposal currently has no opinion here.

   Memory `project_pluggable_pipeline` (2026-05-02) flagged a
   similar "pluggable router extension points" idea that was
   parked; this is a more concrete version of the same
   instinct, scoped to launch identity rather than to router
   internals.

---

## 9. Recommendation for S6 (go/no-go)

**Recommendation: GO for S6 in-set implementation**, scoped to the
"Copilot-only minimum viable proof" of §5.1.

**Why GO over DEFER**:
- The S6 scope is genuinely small (one parser shim + one Explorer
  indicator + a narration template) given the design work S1-S5 has
  already done.
- The "minimum viable proof" lets us validate the proposal end-to-end
  before committing Set 045 to the heavier conflict-semantics work.
  An end-to-end run on Copilot reveals any architectural surprise
  cheaply.
- Sets 037-041 retirement should be reflected in the repo state
  promptly. Closing 044 with a working proof + retired adapter sets
  is a stronger signal than closing 044 with only a paper proposal
  and a 12-session adapter roadmap still nominally live.

**What would flip this to DEFER**:
- Consensus uncovers a serious flaw in the harvest-vs-adapter
  framing.
- Consensus mandates a v1.1 narration redesign that doesn't fit a
  single session's work.
- The estimated S6 scope grows past ~2× of a typical single session
  during proposal review.

If any of those happen, S5 closes with the proposal locked but no
S6 implementation; Set 045 owns end-to-end implementation.

---

## 10. Acceptance criteria for this proposal

This draft is acceptable for the consensus call when:

- §1 (problem statement) makes the harvest-vs-adapter choice clear
  to a reader who hasn't seen S1–S4 deliverables.
- §2 (objectives table) accurately reports the S1+S2+S5-sidebar
  empirical findings without overclaiming.
- §4 (architecture) is concrete enough that an engineer could
  estimate parser-shim complexity from it.
- §6 (roadmap reshape) makes explicit, defensible calls for each
  of Sets 037–041 + 036 + 042–043.
- §8 (open questions) lists the actual decision points the
  consensus should engage, not generic risk language.
- §9 (go/no-go) carries a defended position with explicit flip
  conditions.

If consensus flags additional sections needed, this draft expands;
the underlying recommendation is stable enough to defend.
