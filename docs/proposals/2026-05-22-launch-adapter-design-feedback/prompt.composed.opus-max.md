# Prompt Instructions Sent to Gemini Pro

Review the attached Dabbler launch-adapter design packet as a critical,
repo-specific design reviewer.

The packet includes:

- the current adapter design document: `coding-assistant-adapter-spec.md`
- the existing related implementation set: Set 036
- the newly authored session-set roadmap: Sets 037 through 043

Please evaluate the design as proposed, not some hypothetical greenfield
alternative.

## What to review

1. Is the split between Set 036 and the new launch-adapter work correct?
2. Is Set 037 the right place to reconcile Set 036 with the new adapter
   roadmap, or should that reconciliation happen differently?
3. Is the session-set DAG sensible, or is it over-split / under-split?
4. Is one discovery session per CLI/provider adapter the right pattern?
5. Is the chat-interface work correctly separated into later sets, or is
   that an architectural mistake?
6. Are there contradictions, hidden prerequisites, or ordering problems
   across the design packet?
7. What concrete edits should be made to the specs before implementation
   begins?

## Output format

Use this exact section structure:

1. `Overall verdict`
2. `What is strong`
3. `Findings` — severity-ordered, concrete, repo-specific
4. `Set 036 reconciliation`
5. `Session-set DAG and sizing`
6. `Chat interface judgement`
7. `Recommended spec edits before implementation`

When you cite a concern, name the file and session number where
possible.

Prefer criticism that changes the plan over generic praise.

## Related Files

- Instructions-only source: `prompt.md`
- Full composed packet sent through ai-router: `prompt.composed.md`
- Gemini response: `gemini-pro-response.md`
- Full route result JSON: `gemini-pro-result.json`

## Design packet

### Original adapter design document
Source: coding-assistant-adapter-spec.md
```markdown
# Multi-Backend Coding-Assistant Adapter Specification

**Purpose:** Define a Dabbler-compatible adapter layer that standardizes session
launch across coding-assistant backends while keeping `python -m ai_router.start_session`
and `python -m ai_router.close_session` as the canonical ownership writers.

**Status:** Draft v2
**Last reviewed:** 2026-05-22
**Locally characterized CLI:** GitHub Copilot CLI 1.0.51 on Windows
**Why this revision exists:** Dabbler already has a lifecycle writer and check-out
model. The missing capability is a uniform way to *launch* sessions with explicit
model, effort, and mode. A full headless conversation runtime is an optional later
layer, not the first ship target.

**Official Copilot CLI docs consulted for this revision:**

- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference
- https://docs.github.com/en/copilot/concepts/agents/copilot-cli/autopilot

---

## 1. Problem Statement

Dabbler can already record orchestrator ownership on a session set. The current
gap is narrower and more concrete:

- The extension can record `provider + model + effort`, but for Gemini and Copilot
  that is mostly declarative bookkeeping rather than a real launch path.
- `Check Out As...` is a coordination command, not a backend session launcher.
- The UI intentionally retired misleading orchestrator controls until there is a
  real session-launch path behind them.

The immediate product need is therefore:

1. Pick a uniform session profile.
2. Acquire Dabbler ownership through the canonical writer.
3. Launch the backend with that profile.

That is a smaller, safer deliverable than immediately replacing every backend's
conversation loop with a Dabbler-owned chat runtime.

---

## 2. Design Principle: Separate Ownership, Launch, and Conversation

This specification uses three layers with deliberately different responsibilities.

### 2.1 Ownership Layer (already exists in Dabbler)

This layer is canonical today.

- `ai_router.new_chat_id` provides Dabbler's per-chat identity when the host does
  not expose one.
- `ai_router.start_session` owns the check-out write.
- `ai_router.close_session` owns the check-in write.
- `session-state.json` is the source of truth for current holder identity.
- The extension renders state; it does not infer ownership from backend config files.

### 2.2 Launch Layer (first ship target)

This is the missing abstraction.

- Resolve a user-visible `SessionProfile` into backend-specific argv, env, cwd,
  and isolated config-home decisions.
- Launch either an interactive backend session or a one-shot prompt-mode process.
- Return enough metadata for audit, attach, and close-out.

This layer is sufficient to solve "launch chat sessions uniformly with model and
effort".

### 2.3 Conversation Layer (optional later)

Only build this layer if Dabbler decides to own the entire conversation loop.

- One prompt becomes one backend invocation.
- Dabbler stores conversation history and replay state.
- Native backend resume becomes an optimization rather than the primary contract.

This layer should not block the launch work.

```
VS Code extension / launcher
    |
    v
beginSession()
    |
    +--> ai_router.new_chat_id         (if needed)
    +--> ai_router.start_session       (canonical ownership write)
    +--> LaunchAdapter.buildLaunchPlan (backend translation)
    |
    v
Interactive CLI window or prompt-mode invocation
    |
    v
Optional future ConversationAdapter
```

---

## 3. Canonical Terms

### 3.1 `dabblerChatSessionId`

The Dabbler-owned per-chat identity written through `start_session` and used for
ownership checks, takeover UX, and close-out audit.

This is **not** the same thing as a backend-native conversation ID.

### 3.2 `nativeResumeToken`

A backend-native session locator when the backend exposes one and Dabbler can
retrieve it in a documented or well-characterized way.

Examples:

- Copilot CLI session picker / resume token.
- Codex conversation ID.

This token is optional. Dabbler correctness must not depend on it.

### 3.3 `SessionProfile`

The user-visible session selection: backend, provider, model, effort, and
optionally a backend-specific thinking toggle.

### 3.4 Dabbler Effort Scale

Keep Dabbler's canonical effort vocabulary aligned with the current extension:

`low | medium | high | max`

Adapters map this to backend-native values. Do **not** make Copilot's or Codex's
latest flag spelling the canonical repo-wide source of truth.

---

## 4. Canonical Types

```ts
type BackendId = "claude-code" | "codex" | "gemini-cli" | "copilot-cli";
type DabblerEffort = "low" | "medium" | "high" | "max";
type SessionMode = "normal" | "plan" | "autonomous";
type LaunchKind = "interactive" | "prompt";

interface SessionProfile {
  backend: BackendId;
  engine: "claude" | "codex" | "gemini" | "copilot";
  provider: "anthropic" | "openai" | "google" | "github";
  model: string;
  effort: DabblerEffort;
  thinking?: boolean;
}

interface PermissionPolicy {
  allowAll?: boolean;
  availableTools?: string[];
  allowTools?: string[];
  denyTools?: string[];
  addDirs?: string[];
  allowUrls?: string[];
  denyUrls?: string[];
  noAskUser?: boolean;
}

interface IsolationPolicy {
  workingDirectory: string;
  backendHomeDir?: string;
  preserveUserState: boolean;
}

interface BeginSessionRequest {
  sessionSetDir: string;
  sessionNumber?: number | null;
  profile: SessionProfile;
  sessionMode: SessionMode;
  launchKind: LaunchKind;
  initialPrompt?: string;
  dabblerChatSessionId?: string | null;
  nativeResumeToken?: string | null;
  permissions?: PermissionPolicy;
  isolation: IsolationPolicy;
  forceTakeover?: boolean;
  name?: string;
}

interface LaunchPlan {
  argv: string[];
  env: Record<string, string>;
  cwd: string;
  mode: LaunchKind;
  notes: string[];
}

interface BeginSessionResult {
  dabblerChatSessionId: string;
  sessionNumber: number;
  stateFile: string;
  launchPlan: LaunchPlan;
  nativeResumeToken: string | null;
  nativeResumeSupported: boolean;
  actualModelProbe: "stdout" | "jsonl" | "otel" | "none";
}

interface LaunchAdapter {
  readonly id: BackendId;
  readonly supportsInteractiveLaunch: boolean;
  readonly supportsHeadlessTurns: boolean;
  readonly supportsNativeResume: boolean;

  buildLaunchPlan(req: BeginSessionRequest): Promise<LaunchPlan>;
  normalizeActualModel?(artifacts: LaunchArtifacts): string | null;
}

interface LaunchArtifacts {
  stdout: string;
  stderr: string;
  files?: string[];
}
```

---

## 5. `beginSession()` Contract (exact)

`beginSession()` is the center of the launch layer. It is the contract the
extension should call before opening a terminal, starting a prompt-mode backend,
or offering takeover/attach UX.

### 5.1 Required behavior

1. Resolve `dabblerChatSessionId`.
   - Use the caller-supplied value when present.
   - Otherwise generate one with `python -m ai_router.new_chat_id`.

2. Acquire canonical ownership *before* backend launch.
   - Invoke `python -m ai_router.start_session` with:
     - `--session-set-dir`
     - `--session-number` when provided
     - `--engine`
     - `--model`
     - `--effort`
     - `--provider`
     - `--chat-session-id`
     - `--force` when takeover is explicit
   - If `start_session` refuses, do not spawn the backend.

3. Resolve backend launch parameters.
   - Call `LaunchAdapter.buildLaunchPlan(req)`.

4. Spawn the backend process.
   - Interactive launch opens a terminal session.
   - Prompt launch executes a one-shot command and captures artifacts.

5. Return a `BeginSessionResult` that keeps Dabbler identity separate from any
   backend-native resume token.

### 5.2 Boundary rule

`beginSession()` is allowed to fail *before* the backend process starts.
It must not create a partially launched backend and only then discover that the
session set is held by another chat.

### 5.3 Close rule

`close_session` remains the authoritative close-out path. Backend teardown and
Dabbler ownership release are related, but not the same action.

---

## 6. Launch Layer vs. Conversation Layer

The launch layer is required. The conversation layer is optional.

### 6.1 Launch layer responsibilities

- Uniform profile picking.
- `new_chat_id` generation.
- `start_session` / takeover enforcement.
- Backend-specific argv/env/cwd/home resolution.
- Interactive session launch.
- One-shot prompt launch.

### 6.2 Conversation layer responsibilities

- Per-turn `send()`.
- History replay.
- Native resume fallback.
- Event normalization for a Dabbler-owned chat UI.

### 6.3 Optional future contract

If Dabbler later owns the full loop, use a separate interface instead of making
the launch contract do both jobs.

```ts
interface ConversationAdapter {
  readonly id: BackendId;
  readonly supportsNativeResume: boolean;

  send(req: TurnRequest): AsyncIterable<AssistantEvent>;
  resumeToken(result: TurnResult): string | null;
}

interface TurnRequest {
  dabblerChatSessionId: string;
  nativeResumeToken?: string | null;
  history: Message[];
  message: string;
  profile: SessionProfile;
  sessionMode: SessionMode;
  workdir: string;
}

interface AssistantEvent {
  type: "text" | "tool_call" | "tool_result" | "model_info" | "status" | "error" | "done";
  data: unknown;
}

interface TurnResult {
  activeModel: string | null;
  nativeResumeToken: string | null;
  tokensUsed?: number;
  exitCode: number;
}
```

This section is intentionally secondary. Do not block launch work on it.

---

## 7. Copilot CLI: Officially Documented Surface (May 2026)

This section is based on the official GitHub docs listed at the top of this file.
Anything not stated there should be treated as unverified until locally characterized.

| Concern | Officially documented | Dabbler v1 policy |
|---|---|---|
| Interactive launch | `copilot` launches the interactive UI. `-i/--interactive=PROMPT` starts an interactive session and immediately executes a prompt. | Use this for a real "open chat" launch path. |
| Programmatic one-shot mode | `-p/--prompt=PROMPT` runs non-interactively and exits when done. Installed 1.0.51 help also examples this with `--allow-all-tools`, and labels that flag as required for non-interactive mode. | Use this for prompt-mode turns, probes, and automation, but always include an explicit non-interactive permission stance rather than assuming interactive prompts exist. |
| Model selection | `--model`, `COPILOT_MODEL`, and `settings.json` `model` are documented. Precedence is agent -> `--model` -> `COPILOT_MODEL` -> settings -> default. | Pass `--model` explicitly from Dabbler. Do not rely on ambient settings. |
| Effort selection | Installed 1.0.51 help accepts `none`, `low`, `medium`, `high`, `xhigh`, and `max` for `--effort` / `--reasoning-effort`. The docs pass was less explicit about the upper tiers. | Keep Dabbler's `max` effort. On Copilot CLI 1.0.51+, pass `--effort max` directly. Dabbler still does not expose `none` as a canonical tier. |
| Session mode | `--mode=interactive|plan|autopilot`, `--plan`, and `--autopilot` are documented. | Map `normal -> interactive`, `plan -> --plan`, `autonomous -> --autopilot` with explicit permission policy. |
| Resume / continue | `--continue` resumes the most recent session. `--resume[=VALUE]` resumes a named or selected session. Docs say session history under `~/.copilot/session-state/` powers this. | Allow interactive attach/resume UX, but do not make prompt-mode correctness depend on native Copilot resume. |
| Machine-readable output | `--output-format=json` emits JSONL. `-s/--silent` suppresses stats and decoration. | Use JSONL as transport, but do not lock its schema into Dabbler until locally characterized. |
| Actual model reporting | Docs say non-silent non-interactive output shows the model used. OTel `chat` spans document `gen_ai.response.model`. | Prefer an optional OTel audit path for durable actual-model capture. Otherwise parse non-silent output as a stopgap. |
| Permissions | `--allow-all`, `--allow-all-tools`, `--allow-tool`, `--deny-tool`, `--available-tools`, `--add-dir`, `--allow-url`, `--deny-url`, `--no-ask-user` are documented. Installed 1.0.51 help states `--allow-all-tools` is required for non-interactive mode. | Translate Dabbler permission policy directly to Copilot flags. For v1 prompt-mode, default to `--allow-all-tools` unless a narrower locally verified non-interactive permission profile is available. |
| Isolation | `COPILOT_HOME` replaces the entire `~/.copilot` path. Docs say it contains `settings.json`, `permissions-config.json`, `session-state/`, `logs/`, and more. | Use per-session `COPILOT_HOME` when reproducibility or isolation matters. |
| Auth | `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` are documented in precedence order. | Use vendor-native auth only. |
| Backend chat identity | Installed 1.0.51 help documents `--session-id <id>` to resume an existing session or task, or set the UUID for a new session. No official per-chat env var is documented. | Keep Dabbler's chat ID as the canonical ownership id. When that id is UUID-shaped, pass it through as Copilot `--session-id` for new launches. |

### 7.1 Important Copilot-specific nuance

The docs support a useful distinction:

- Dabbler can own **session identity** through `chatSessionId`.
- Copilot can still own **its own interactive session history** behind `--resume`.

Those are related but separate concerns. The launch contract should keep them separate.

### 7.3 Local characterization update for 1.0.51

The installed CLI tightened three previously open questions:

- `--session-id <uuid>` is a supported way to seed a new Copilot session id.
- `--effort` accepts both `xhigh` and `max`.
- Non-interactive mode should be launched with an explicit permission choice,
  and the shipped help text points at `--allow-all-tools` as the default-safe
  scripting path.

### 7.2 Optional OTel audit path

The command reference documents OpenTelemetry file export and the `chat` span
attribute `gen_ai.response.model`.

That gives a more robust path for actual-model auditing than scraping terminal text:

- Set `COPILOT_OTEL_FILE_EXPORTER_PATH` to a temp JSONL file.
- Run the Copilot command.
- Read the emitted `chat` span for `gen_ai.response.model` and
  `gen_ai.conversation.id`.

This is optional in v1, but it is the best documented path if model fidelity is
important.

---

## 8. CopilotLaunchAdapter v1 (first implementation slice)

This is the first concrete implementation slice to build.

### 8.1 Scope

Ship a uniform Copilot launcher, not a full Copilot conversation runtime.

### 8.2 Responsibilities

1. Accept a Dabbler `BeginSessionRequest`.
2. Resolve or generate `dabblerChatSessionId`.
3. Call `ai_router.start_session` before spawning Copilot.
4. Map Dabbler profile and permissions to documented Copilot CLI flags.
5. Launch either:
   - an interactive Copilot terminal session, or
   - a prompt-mode Copilot process.
6. Return launch metadata and an optional `nativeResumeToken`.

### 8.3 Command mapping

#### Interactive normal session

```bash
copilot \
  --session-id <uuid> \
  --model <model> \
  --effort <mapped-effort>
```

#### Interactive plan session

```bash
copilot \
  --session-id <uuid> \
  --model <model> \
  --effort <mapped-effort> \
  --plan
```

#### Interactive session with an initial prompt

```bash
copilot \
  --session-id <uuid> \
  --model <model> \
  --effort <mapped-effort> \
  --interactive "<prompt>"
```

#### Prompt-mode one-shot turn

```bash
copilot \
  --session-id <uuid> \
  --model <model> \
  --effort <mapped-effort> \
  --allow-all-tools \
  --output-format json \
  --prompt "<prompt>"
```

#### Autonomous prompt-mode run

```bash
copilot \
  --session-id <uuid> \
  --autopilot \
  --yolo \
  --max-autopilot-continues 10 \
  --model <model> \
  --effort <mapped-effort> \
  --prompt "<prompt>"
```

### 8.4 Permission mapping

Translate `PermissionPolicy` directly:

- `allowAll -> --allow-all`
- `availableTools -> --available-tools`
- `allowTools -> --allow-tool`
- `denyTools -> --deny-tool`
- `addDirs -> --add-dir`
- `allowUrls -> --allow-url`
- `denyUrls -> --deny-url`
- `noAskUser -> --no-ask-user`

### 8.5 Isolation mapping

When `backendHomeDir` is supplied, set:

```text
COPILOT_HOME=<backendHomeDir>
```

Docs explicitly say this relocates the entire state directory, including:

- `settings.json`
- `permissions-config.json`
- `session-state/`
- `logs/`
- `session-store.db`

Recommended v1 location pattern:

```text
<workspace>/.dabbler/backend-homes/copilot/<dabblerChatSessionId>/
```

### 8.6 Resume policy

For v1:

- Interactive launch may offer an `Attach As...` path that uses `--continue` or
  `--resume` for a human-driven terminal session.
- When Dabbler launches Copilot with `--session-id <dabblerChatSessionId>`, the
  adapter may set `nativeResumeToken` to the same UUID value.
- Prompt-mode launches should assume `nativeResumeToken = null` unless Dabbler has
  locally characterized a stable scripted resume flow.
- Dabbler's own history replay remains the portability fallback.

### 8.7 Actual model policy

For v1:

- `actualModelProbe = "otel"` when OTel file export is enabled.
- Otherwise `actualModelProbe = "stdout"` when non-silent prompt mode is used.
- Otherwise `actualModelProbe = "none"`.

Do not claim that Copilot JSONL output contains a stable resolved-model field until
that schema is characterized against a pinned version.

### 8.8 Pseudocode

```ts
async function beginSession(req: BeginSessionRequest): Promise<BeginSessionResult> {
  const chatId = req.dabblerChatSessionId ?? await newChatId();

  const sessionNumber = await startSessionBoundaryWrite({
    sessionSetDir: req.sessionSetDir,
    sessionNumber: req.sessionNumber ?? null,
    engine: req.profile.engine,
    provider: req.profile.provider,
    model: req.profile.model,
    effort: req.profile.effort,
    chatSessionId: chatId,
    force: req.forceTakeover === true,
  });

  const plan = await copilotLaunchAdapter.buildLaunchPlan({
    ...req,
    dabblerChatSessionId: chatId,
  });

  return {
    dabblerChatSessionId: chatId,
    sessionNumber,
    stateFile: `${req.sessionSetDir}/session-state.json`,
    launchPlan: plan,
    nativeResumeToken: plan.argv.includes("--session-id") ? chatId : null,
    nativeResumeSupported: true,
    actualModelProbe: plan.env.COPILOT_OTEL_FILE_EXPORTER_PATH ? "otel" : "stdout",
  };
}
```

---

## 9. Build Order

1. Add `beginSession()` and `LaunchAdapter` to the extension-side orchestration layer.
2. Implement `CopilotLaunchAdapter` first.
3. Evolve `Check Out As...` into `Launch As...`, but keep `start_session` as the
   canonical writer.
4. Add a distinct `Attach As...` flow for interactive resume.
5. Add `CodexLaunchAdapter`.
6. Add `GeminiLaunchAdapter`.
7. Revisit whether a full `ConversationAdapter` is worth the complexity.

---

## 10. Non-Goals and Risks

### 10.1 Non-goals

- Replacing `start_session` / `close_session` with backend-owned state.
- Reintroducing config-file watchers as ownership inference.
- Locking undocumented backend env vars into the canonical contract.
- Requiring native backend resume for correctness.

### 10.2 Risks

1. **Copilot CLI update churn.** Pin versions when possible and keep the docs-verified
   and locally-characterized surfaces distinct.
2. **Effort mismatch.** Copilot docs currently expose a flag-level and settings-level
   discrepancy for the highest effort tier.
3. **Prompt-mode schema drift.** JSONL output format is documented, but the exact
   event schema is not locked in the docs quoted here.
4. **Auth coupling mistakes.** Each backend must authenticate through its own official path.
5. **Over-scoping too early.** Launch uniformity solves the current UX gap. A full
   headless conversation runtime should be justified separately.

---

## 11. Bottom Line

For Dabbler, the right first move is:

- keep ownership in the existing writer,
- add a real launch adapter layer,
- implement Copilot first against documented flags and `COPILOT_HOME`,
- treat full per-turn conversation control as a later, optional layer.

That gives a uniform, honest session-launch path without reopening the watcher-
drift problems that Set 036 is explicitly trying to eliminate.

```

### Existing related implementation plan (Set 036) (first 220 lines only)
Source: docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/spec.md
```markdown
# chatSessionId identity refinement + MVVM watcher-scope discipline — implementation

> **Purpose:** ship the chatSessionId identity refinement and the
> MVVM-watcher-scope discipline locked by the cross-provider audit
> at
> [`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/).
> Refines H4 from `engine + provider` to
> `engine + provider + chatSessionId`. Retires the codex config-
> toml watcher and `signalKind` inference variants. Adds the
> per-set lifecycle lock that Q5 made load-bearing.
> **Created:** 2026-05-21 (post-Set-033-close)
> **Session Set:** `docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/`
> **Prerequisites:**
> - Set 033 (`033-orchestrator-checkout-checkin-implementation`) CLOSED
>   — shipped H1+H2+H3+H4 base composite + OQ1+OQ2.
> - Audit-locked proposal at
>   `docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/`
>   with `proposal-addendum.md` capturing the locked verdicts.
> **Pattern:** audit-then-spec per
> [[feedback_audit_then_spec_for_substantial_features]] —
> the audit half ran informally (Gemini Pro routed + GPT-5.4
> manual paste); this set is the implementation half.

---

## Session Set Configuration

```yaml
totalSessions: 7
requiresUAT: false
requiresE2E: true
uatScope: none
uatStyle: ad-hoc
effort: high
```

> **`requiresE2E: true`** — the chatSessionId-mismatch takeover
> UX is a new operator-visible affordance (modal in IDE / CLI
> prompt in terminal). Layer-3 Playwright coverage is the right
> layer for "what the operator sees painted on screen."
>
> **`effort: high`** — the change touches:
> - The Python writer (`ai_router/start_session.py`,
>   `ai_router/close_session.py`, `ai_router/session_state.py`,
>   `ai_router/session_events.py`).
> - A new Python CLI (`ai_router/new_chat_id.py`).
> - The Claude Code hook invoker (Node).
> - The extension's reader (`OrchestratorAccordion.ts`,
>   `inProgressSetsService.ts`).
> - The Codex config-toml watcher (RETIRED entirely).
> - Layer-2 + Layer-3 test surfaces.
> - All three canonical docs + the cross-repo notice.
> - A new convention test (Q7 watcher-inventory).
> - Two registry releases (PyPI + Marketplace).
>
> Similar scope to Set 033; same effort grade.

---

## Project Overview

### What the audit locked (compact recap)

The proposal-addendum at
[`docs/proposals/2026-05-21-chatsessionid-and-watcher-scope/proposal-addendum.md`](../../proposals/2026-05-21-chatsessionid-and-watcher-scope/proposal-addendum.md)
locked the following pattern (operator-adjudicated, GPT-leaning):

| Item | Locked verdict |
|---|---|
| **D1** Watcher-scope discipline | REFINED — discipline applies to *orchestrator-state inference*; non-orchestrator UI refresh watchers stay permitted |
| **D2** MVC-shaped agent API | REFINED — token source is native per-chat metadata surface (env, hook, or fallback CLI), not env-var-only |
| **Q1** chatSessionId source per orchestrator | REFINED — no env var confirmed for any orchestrator; Claude Code uses hook-payload `session_id`; others use the fallback CLI |
| **Q2** Cadence of identity checks | REFINED — per-boundary; "destructive ops" narrowly defined (ownership transitions + --force + repo-wide git + repo-wide scripts) |
| **Q3** Takeover UX | REFINED — modal in IDE; CLI prompt in terminal; toast is secondary notification only |
| **Q4** chatSessionId on close | REFINED — clear from `session-state.json`; persist in `closeout_succeeded` event payload alongside engine + provider + (optional) model |
| **Q5** Hybrid migration tolerance | REFINED — hybrid only with explicit cross-process serialization (shared per-set lifecycle lock) |
| **Q6** `requireExplicitTakeover` setting | REJECTED — no persistent off-switch; if real friction surfaces later, ship a one-shot affordance |
| **Q7** Watcher-scope enforcement | REFINED — allowlisted watcher-inventory unit test |

### What ships across the seven sessions

- **S1** — Writer migration + per-set lifecycle lock. Q5's lock
  is the gating prerequisite for the hybrid-migration safety;
  everything else builds on it.
- **S2** — `new_chat_id` CLI + Claude Code hook-invoker passes
  through the per-chat `session_id`. Q1 native-source wiring.
- **S3** — `signalKind` retirement + Codex config-toml watcher
  retirement. D1 watcher-scope discipline applied.
- **S4** — Takeover UX (modal + CLI) + watcher-inventory
  convention test. Q3 + Q7 user-facing surface.
- **S5** — Layer-3 Playwright coverage + cross-tier docs +
  cross-repo notice update.
- **S6** — Orchestrator-agnostic UI audit + empty-state refactor.
  Sweeps the extension UI for Claude-specific framing now that
  the writer treats Claude Code, Codex CLI, Gemini Code Assist,
  and GitHub Copilot as equal first-class orchestrators. Added
  per operator directive 2026-05-21 on the back of the Set 035
  Session 1 empty-state polish — gauge geometry was already
  orchestrator-agnostic, but the empty-state CTA copy still
  pointed at the Claude Code hook by default.
- **S7** — Final tests + change-log + dual-registry release.

---

## Session 1 of 7: Writer migration + per-set lifecycle lock (Q5 prerequisite)

**Goal:** add `chatSessionId` to the orchestrator block + refine
H4 + add the per-set lifecycle lock that makes the hybrid
migration safe.

**Steps:**

1. **Schema delta** — `orchestrator` block gains
   `chatSessionId: string | null` field.
   `session-state.json` invariant: `orchestrator` is `null` when
   `status != in-progress` (unchanged); when non-null, the
   `chatSessionId` field is present (may be null for legacy
   sets, per Q5 tolerant-on-read).
2. **`start_session.py` refinement:**
   - New `--chat-session-id <value>` argument (optional;
     defaults to value of `$CHAT_SESSION_ID` env if set,
     otherwise None).
   - H4 identity predicate refined to:
     `existing.engine == new.engine
     AND existing.provider == new.provider
     AND existing.chatSessionId == new.chatSessionId`.
   - Tolerant-on-read: a missing `chatSessionId` in the existing
     orchestrator block is treated as "same holder" for engine +
     provider matches (Q5 tolerant-on-read).
   - Strict-on-write: the new write always populates
     `chatSessionId` (from arg, env, or null if neither
     supplied).
   - Refusal message extended to name the existing chatSessionId
     (or "no chat session ID recorded" for legacy state files).
3. **Per-set lifecycle lock (Q5 hard requirement):**
   - Rename `.close_session.lock` to `.lifecycle.lock` in
     `ai_router/close_lock.py` (or wherever the lock helper
     lives).
   - Both `start_session` AND `close_session` acquire this lock
     for the duration of their read/check/write window.
   - Stale-window reaping semantics preserved.
   - Lock contention: blocks for a bounded timeout (default
     30s), then exits with `EXIT_LOCK_CONTENTION = 5` (new exit
     code; document in `start_session.py` exit-code table).
4. **`close_session.py` extension** —
   `closeout_succeeded` event payload gains `chatSessionId`,
   `engine`, `provider`, and `model` fields (Q4 audit
   trail). Reader tolerance for older payloads without these
   fields.
5. **`session_state.py` writer** —
   `_flip_state_to_closed()` continues to set
   `orchestrator: None` on close (Set 033 Session 6 behavior);
   the chatSessionId is naturally cleared as part of nulling
   the block.
6. **`session_events.py`** — the `closeout_succeeded` event's
   payload contract documented; the existing `append_event()`
   helper signature unchanged (payload is already open-shape).
7. **Unit tests** in `ai_router/tests/`:
   - Fresh check-out writes `chatSessionId` correctly.
   - Same-(engine, provider, chatSessionId) re-attach is benign.
   - Different chatSessionId (with matching engine+provider) is
     refused; refusal message names the holder's chatSessionId.
   - `--force` overrides and rewrites chatSessionId.
   - Legacy state file (no chatSessionId) is tolerated on read;
     first new write populates the field.
   - Lock contention between simultaneous start_session calls
     serializes correctly.
   - `closeout_succeeded` event payload includes chatSessionId
     + engine + provider + model.
8. **End-of-session verification** (gemini-pro, Round A).

**Creates:**
- `ai_router/tests/test_chatsessionid_writer.py`

**Touches:**
- `ai_router/start_session.py`
- `ai_router/close_session.py`
- `ai_router/session_state.py`
- `ai_router/session_events.py`
- `ai_router/close_lock.py` (rename + extend)

**Ends with:** writer side ships chatSessionId; per-set
lifecycle lock prevents the migration race Q5 flagged; tests
cover all branches.

**Progress keys:** `session-001/schema-delta-applied`,
`session-001/start-session-refined`,
`session-001/lifecycle-lock-introduced`,
`session-001/close-session-event-payload-extended`,
`session-001/legacy-tolerance-wired`,
`session-001/unit-tests-green`,
`session-001/round-a-verification`

**Estimated cost:** $0.05–$0.15.

---

## Session 2 of 7: `new_chat_id` CLI + Claude Code hook-invoker pass-through

**Goal:** the agent-facing token-source plumbing. Claude Code
gets its native per-chat ID (from the hook payload's
`session_id`) wired through to `start_session`. All other
orchestrators use the new `new_chat_id` CLI.

**Steps:**

1. **`ai_router/new_chat_id.py`** — new module + CLI entrypoint:
   - `python -m ai_router.new_chat_id` prints a UUID v4.
   - `--export` prints a shell-eval-able line; `--shell
     bash|powershell|fish` selects the syntax (default: detect
     via `$SHELL` env / `os.name`).
   - Idempotent within a shell session: if `$CHAT_SESSION_ID`
     (or `$env:CHAT_SESSION_ID`) is already set, the CLI emits
     the existing value rather than a fresh one.
   - Exits 0 on success; 1 on shell-detect failure when
     `--shell` not provided.
2. **`tools/dabbler-ai-orchestration/scripts/claude-session-start-invoker.js`**
   — extend to parse `session_id` from the stdin JSON payload
   that Claude Code's SessionStart hook delivers, and forward
   it as `--chat-session-id <value>` to
```

### New shared launch foundation plan (Set 037)
Source: docs/session-sets/037-launch-adapter-foundations/spec.md
```markdown
# LaunchAdapter Foundations + Set 036 Reconciliation

> **Purpose:** reconcile the launch-adapter roadmap with Set 036's
> `chatSessionId` / watcher-scope plan, then land the shared
> extension-side `beginSession()` boundary, adapter registry, and
> launch-host plumbing that all provider-specific adapter sets depend
> on.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/037-launch-adapter-foundations/`
> **Prerequisites:** None. Set 036 remains an adjacent planning surface;
> Session 1 explicitly reconciles the two plans before shared code lands.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** this set changes the VS Code extension's operator-facing
> command surface and establishes the shared launch boundary that will
> open external CLIs. Layer-3 coverage is warranted for the visible IDE
> flow, and ad-hoc UAT is warranted because the behavior crosses the IDE
> plus external terminal/CLI boundary.

---

## Project Overview

- Set 036 remains authoritative for writer-side identity,
  `chatSessionId`, and watcher-scope discipline.
- This set becomes authoritative for extension-side launch orchestration:
  `BeginSessionRequest`, `BeginSessionResult`, `LaunchPlan`,
  `LaunchAdapter`, adapter registration, and terminal-launch hosting.
- Downstream provider sets plug backend-specific argv/env rules into the
  shared contract defined here.
- Non-goals:
  - backend-specific flag mapping beyond fake/stub adapters;
  - a Dabbler-owned chat transcript UI;
  - replacing `python -m ai_router.start_session` / `close_session` as
    the lifecycle boundary.

---

## Sessions

### Session 1 of 4: Reconcile Set 036 and lock the shared launch contract

**Steps:**
1. Compare Set 036, [coding-assistant-adapter-spec.md](../../../coding-assistant-adapter-spec.md), and the existing extension command surfaces.
2. Record every overlap or conflict, especially around `chatSessionId`,
   native resume tokens, provider launch identity, and whether any Set
   036 wording needs an addendum or direct edit.
3. Freeze the shared extension-side contract for `BeginSessionRequest`,
   `BeginSessionResult`, `LaunchPlan`, `LaunchAdapter`, and provider
   capability metadata.
4. Declare the dependency DAG for the downstream Claude, Copilot,
   Codex, Gemini, and chat-interface sets.
5. Verify the reconciliation with a routed analysis review before moving
   to implementation.

**Creates:**
- `docs/session-sets/037-launch-adapter-foundations/reconciliation-notes.md`

**Touches:**
- `docs/session-sets/036-chatsessionid-and-watcher-scope-implementation/spec.md`
- `coding-assistant-adapter-spec.md`

**Ends with:** a written reconciliation that makes Set 036 and the new
launch roadmap non-contradictory, plus a frozen shared contract for the
provider sets.

**Progress keys:**
- `session-001/036-reconciled`
- `session-001/shared-contract-frozen`
- `session-001/downstream-dag-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `beginSession()` boundary + adapter registry

**Steps:**
1. Add the TypeScript types and services for `BeginSessionRequest`,
   `BeginSessionResult`, `LaunchPlan`, `LaunchArtifacts`, and
   `LaunchAdapter`.
2. Implement the shared `beginSession()` flow: generate `new_chat_id`
   when needed, call `start_session`, stop on ownership refusal, and
   return a provider-agnostic launch plan.
3. Add an adapter registry and capability model so the extension can ask
   which providers support interactive launch, prompt mode, native
   resume, and actual-model probes.
4. Add unit tests with a fake adapter so the provider-specific sets only
   have to prove mapping logic, not the orchestration skeleton.

**Creates:**
- `tools/dabbler-ai-orchestration/src/launching/LaunchAdapter.ts`
- `tools/dabbler-ai-orchestration/src/launching/beginSession.ts`
- `tools/dabbler-ai-orchestration/src/launching/adapterRegistry.ts`
- shared test coverage for the boundary service

**Touches:**
- `tools/dabbler-ai-orchestration/src/extension.ts`
- existing command-registration surfaces that need the shared launcher

**Ends with:** a provider-agnostic launch boundary with unit tests and
no provider-specific CLI assumptions baked into the shared service.

**Progress keys:**
- `session-002/launch-types-added`
- `session-002/begin-session-boundary-wired`
- `session-002/adapter-registry-added`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Add `Launch As...` / `Attach As...` command surface + launch host

**Steps:**
1. Introduce honest operator commands for launch and attach, rather than
   overloading `Check Out As...`.
2. Add a terminal launch host that can open an interactive CLI session
   from a `LaunchPlan` and capture a prompt-mode invocation when the
   adapter requests one-shot execution.
3. Decide how the legacy checkout command degrades: retire it, bridge it,
   or keep it as a low-level recovery affordance.
4. Surface capability-aware UI copy so unsupported launch modes are
   disabled rather than implied.
5. Add Layer-2 coverage for the new commands and fake-adapter launch host.

**Creates:**
- launch-host service(s)
- capability-aware launch/attach commands

**Touches:**
- `tools/dabbler-ai-orchestration/package.json`
- `tools/dabbler-ai-orchestration/src/commands/`
- `tools/dabbler-ai-orchestration/src/providers/ActionRegistry.ts`

**Ends with:** the extension can invoke the shared launch boundary and
open a provider-specific session through a real launch/attach surface.

**Progress keys:**
- `session-003/launch-command-added`
- `session-003/attach-command-added`
- `session-003/launch-host-wired`
- `session-003/layer2-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and downstream handoff

**Steps:**
1. Run focused unit, Layer-2, and Layer-3 coverage for the shared launch
   surfaces.
2. Produce the ad-hoc UAT checklist for the operator-visible launch and
   attach flows.
3. Update roadmap/docs so the downstream provider sets inherit the final
   contract rather than stale proposal text.
4. Write `change-log.md` and explicitly hand off to the provider sets as
   the next DAG frontier.

**Creates:**
- `docs/session-sets/037-launch-adapter-foundations/change-log.md`
- `docs/session-sets/037-launch-adapter-foundations/037-launch-adapter-foundations-uat-checklist.json`

**Touches:**
- shared docs and extension docs touched by the new launch contract

**Ends with:** the shared launch foundation is documented, tested,
operator-validated, and ready for provider-specific adapters.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New Claude adapter plan (Set 038)
Source: docs/session-sets/038-claude-launch-adapter/spec.md
```markdown
# Claude Launch Adapter

> **Purpose:** bring Claude Code onto the same launch-adapter contract as
> the other providers, so Claude launch and attach behavior stops being a
> special-case installer path and becomes a normal `LaunchAdapter`
> implementation backed by the shared `beginSession()` boundary.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/038-claude-launch-adapter/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: medium
```

> **Rationale:** Claude already has hook plumbing, but this set changes
> operator-visible launch/attach behavior and needs IDE-visible regression
> coverage plus human validation of the external CLI flow.

---

## Project Overview

- Session 1 discovers the current Claude Code launch surface: model,
  effort, mode, permissions, hook payload, and any native attach/resume
  affordances.
- Sessions 2-3 implement `ClaudeLaunchAdapter` and reconcile it with the
  existing SessionStart hook installer from Set 036.
- Non-goals:
  - replacing Claude Code's own transcript UI;
  - building the Dabbler chat panel;
  - weakening the writer-side `chatSessionId` guarantees from Set 036.

---

## Sessions

### Session 1 of 4: Discover and characterize Claude Code launch surfaces

**Steps:**
1. Read the current Claude Code docs and locally characterize the CLI
   help surface for model, effort, plan/autonomous modes, permissions,
   hook payload, and any attach/resume behavior.
2. Verify how Claude's native `session_id` / hook metadata should map to
   Dabbler's `dabblerChatSessionId` and whether any reconciliation note
   is needed after Set 037.
3. Capture stable versus version-sensitive surfaces in a discovery note
   that the implementation sessions can treat as ground truth.

**Creates:**
- `docs/session-sets/038-claude-launch-adapter/discovery-notes.md`

**Touches:**
- local docs references as needed

**Ends with:** a pinned description of the Claude launch surface and its
mapping to the shared launch contract.

**Progress keys:**
- `session-001/claude-docs-read`
- `session-001/local-cli-characterized`
- `session-001/chat-id-mapping-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `ClaudeLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement `ClaudeLaunchAdapter` against the shared registry and launch
   boundary from Set 037.
2. Map Claude model, effort, and mode selections onto the shared
   `SessionProfile` and `SessionMode` contract.
3. Decide and implement Claude-specific isolation semantics (cwd,
   config-home, and any environment shaping) without reintroducing file
   watchers.
4. Add focused unit tests for argv/env generation.

**Creates:**
- Claude-specific adapter implementation and tests

**Touches:**
- shared launching registry and extension command surfaces as needed

**Ends with:** a working Claude launch-plan builder backed by tests.

**Progress keys:**
- `session-002/claude-adapter-added`
- `session-002/claude-argv-mapped`
- `session-002/isolation-policy-wired`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Unify hook installer, attach flow, and actual-model reporting

**Steps:**
1. Rework the Claude hook installer and any launch commands so they flow
   through the shared launch contract rather than parallel one-off code.
2. Add the attach story for existing Claude chats/sessions where the
   local CLI surface supports it; otherwise surface the limitation
   honestly in the UI.
3. Implement actual-model capture/reporting for Claude launch results if
   the CLI exposes a stable source.
4. Add Layer-2 coverage for the command and hook/launch integration.

**Creates:**
- integration tests for Claude launch/hook wiring

**Touches:**
- `tools/dabbler-ai-orchestration/src/commands/installOrchestratorHookClaudeCode.ts`
- Claude-facing launch/attach commands

**Ends with:** Claude launch, hook install, and attach behavior all flow
through the same adapter path.

**Progress keys:**
- `session-003/hook-installer-unified`
- `session-003/attach-path-added`
- `session-003/model-reporting-wired`
- `session-003/layer2-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for Claude command, hook, and launch
   flows.
2. Produce an ad-hoc UAT checklist covering launch, attach, and failure
   states.
3. Update docs and handoff notes so the chat-interface sets can treat
   Claude as a normal adapter.
4. Write `change-log.md`.

**Creates:**
- `docs/session-sets/038-claude-launch-adapter/change-log.md`
- `docs/session-sets/038-claude-launch-adapter/038-claude-launch-adapter-uat-checklist.json`

**Touches:**
- Claude-specific docs and shared launch docs as needed

**Ends with:** Claude is fully onboarded to the shared launch-adapter
surface and documented for downstream chat UI work.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New Copilot adapter plan (Set 039)
Source: docs/session-sets/039-copilot-launch-adapter/spec.md
```markdown
# Copilot Launch Adapter

> **Purpose:** implement the first fully documented provider adapter for
> the shared launch boundary, using the live Copilot CLI surface to ship
> `CopilotLaunchAdapter`, attach behavior, model/effort mapping, and
> honest operator-facing launch flows.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/039-copilot-launch-adapter/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** Copilot is the first concrete provider launch adapter,
> with real operator-visible launch/attach behavior and CLI integration
> that needs both automated coverage and manual validation.

---

## Project Overview

- Session 1 is the pinned Copilot discovery pass: docs, local CLI help,
  auth expectations, `--session-id`, `--effort`, permission rules,
  `COPILOT_HOME`, JSONL output, and OTel model probes.
- Sessions 2-3 implement `CopilotLaunchAdapter`, attach/resume behavior,
  and actual-model capture.
- This set is the prerequisite for the first rudimentary chat-interface
  set, which is intentionally Copilot-first.
- Non-goals:
  - multi-provider chat UI;
  - undocumented Copilot env vars as contract inputs;
  - loosening `start_session` refusal semantics.

---

## Sessions

### Session 1 of 4: Discovery and local characterization for Copilot CLI

**Steps:**
1. Re-run the official-docs and local-help audit for the pinned Copilot
   CLI version in the repo environment.
2. Lock the accepted model/effort/session-id/permission/output flags and
   identify which behaviors remain doc-backed versus locally
   characterized only.
3. Capture the exact `COPILOT_HOME`, prompt-mode, attach/resume, and
   actual-model-probe strategy for implementation.

**Creates:**
- `docs/session-sets/039-copilot-launch-adapter/discovery-notes.md`

**Touches:**
- Copilot-specific planning notes as needed

**Ends with:** a pinned Copilot adapter contract that future sessions can
implement without reopening discovery.

**Progress keys:**
- `session-001/copilot-docs-confirmed`
- `session-001/local-cli-characterized`
- `session-001/otel-strategy-recorded`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `CopilotLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement the interactive and prompt-mode launch mappings for model,
   effort, session mode, permission policy, and `COPILOT_HOME`.
2. Pass Dabbler's UUID-shaped chat id through `--session-id` for new
   launches when appropriate.
3. Add focused tests for argv/env generation, especially `--allow-all`
   versus `--allow-all-tools`, attach-mode flags, and `max` effort.
4. Wire the adapter into the shared registry.

**Creates:**
- Copilot adapter implementation and focused tests

**Touches:**
- shared launch registry and command surfaces as needed

**Ends with:** a working launch-plan generator for Copilot backed by
unit tests.

**Progress keys:**
- `session-002/copilot-adapter-added`
- `session-002/session-id-passthrough-wired`
- `session-002/permission-mapping-wired`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Attach/resume, actual-model reporting, and IDE wiring

**Steps:**
1. Implement the operator attach flow for `--continue` / `--resume` or
   an explicit limitation if native attach is not stable enough.
2. Add actual-model reporting using the best documented path available
   (OTel when enabled, otherwise non-silent stdout parsing).
3. Add Layer-2 and Layer-3 coverage for the launch and attach surfaces,
   using a safe fake/stub strategy where the real CLI cannot run in CI.
4. Validate refusal and recovery UX when `start_session` or Copilot
   launch fails.

**Creates:**
- Copilot launch/attach integration tests

**Touches:**
- Copilot-facing command surfaces and status UI

**Ends with:** Copilot launch and attach behavior is wired into the
extension with honest model reporting and failure handling.

**Progress keys:**
- `session-003/attach-path-added`
- `session-003/model-reporting-wired`
- `session-003/layer3-tests-green`
- `session-003/failure-ux-verified`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the Copilot adapter and command
   flows.
2. Produce the ad-hoc UAT checklist for launch, attach, prompt mode,
   and error recovery.
3. Update docs, including any operator-facing setup instructions that
   changed after the real adapter landed.
4. Write `change-log.md` and mark this set as the chat-foundations
   prerequisite.

**Creates:**
- `docs/session-sets/039-copilot-launch-adapter/change-log.md`
- `docs/session-sets/039-copilot-launch-adapter/039-copilot-launch-adapter-uat-checklist.json`

**Touches:**
- Copilot-specific docs and shared launch docs as needed

**Ends with:** Copilot is the first end-to-end launch adapter and is
ready to support the first in-extension chat-interface set.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New Codex adapter plan (Set 040)
Source: docs/session-sets/040-codex-launch-adapter/spec.md
```markdown
# Codex Launch Adapter

> **Purpose:** onboard Codex to the shared launch-adapter contract after
> the watcher-retirement work, replacing any lingering config-based
> inference expectations with an explicit `CodexLaunchAdapter` that owns
> launch, attach, and model/effort mapping.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/040-codex-launch-adapter/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** Codex launch behavior is operator-visible and must not
> regress into config-file watcher inference. The set needs IDE-level
> coverage and manual validation of the real CLI launch path.

---

## Project Overview

- Session 1 discovers the current Codex CLI launch surface: interactive
  versus prompt mode, model/effort flags, profiles, sandbox/approval,
  and native resume behavior.
- Sessions 2-3 implement `CodexLaunchAdapter`, attach handling, and
  actual-model reporting without reviving config watchers.
- Non-goals:
  - reintroducing `config.toml` watcher inference;
  - a Codex-owned substitute for Dabbler's lifecycle writer;
  - the in-extension chat transcript UI.

---

## Sessions

### Session 1 of 4: Discovery and local characterization for Codex CLI

**Steps:**
1. Read current Codex docs and locally characterize the CLI flags for
   model, effort, profile, mode, sandbox/approval, and resume.
2. Decide which Codex capabilities fit directly into the shared launch
   contract and which need adapter-specific notes.
3. Record any version-sensitive surfaces and confirm that Set 036's
   watcher-retirement rules remain intact.

**Creates:**
- `docs/session-sets/040-codex-launch-adapter/discovery-notes.md`

**Touches:**
- Codex planning notes as needed

**Ends with:** a pinned Codex capability map for launch/attach work.

**Progress keys:**
- `session-001/codex-docs-read`
- `session-001/local-cli-characterized`
- `session-001/watcher-retirement-reconfirmed`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `CodexLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement interactive and prompt-mode launch-plan generation for
   Codex, including model, effort, profile, and mode mapping.
2. Decide how isolation/home semantics should work for Codex in the
   shared launcher without relying on watcher-driven config reads.
3. Wire the adapter into the shared registry and add focused argv/env
   tests.
4. Preserve a clear separation between Dabbler `chatSessionId` and any
   Codex-native resume token.

**Creates:**
- Codex adapter implementation and focused tests

**Touches:**
- shared launch registry and command surfaces as needed

**Ends with:** Codex has a working launch-plan generator and adapter
registration backed by unit tests.

**Progress keys:**
- `session-002/codex-adapter-added`
- `session-002/profile-mapping-wired`
- `session-002/isolation-policy-wired`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Attach/resume, actual-model reporting, and IDE wiring

**Steps:**
1. Implement the attach path when Codex exposes a stable native resume
   surface; otherwise capture the limitation in capability metadata.
2. Add actual-model reporting from the best stable Codex output source.
3. Add Layer-2 and Layer-3 coverage for launch, attach, and refusal UX.
4. Confirm the operator flow no longer implies background watcher-based
   detection.

**Creates:**
- Codex launch/attach integration tests

**Touches:**
- Codex-facing command surfaces and any UI badges/tooltips

**Ends with:** Codex launch and attach behavior is fully explicit and
tested.

**Progress keys:**
- `session-003/attach-path-added`
- `session-003/model-reporting-wired`
- `session-003/layer3-tests-green`
- `session-003/no-watcher-regression`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the Codex adapter and command
   flows.
2. Produce the ad-hoc UAT checklist for Codex launch, attach, and error
   handling.
3. Update docs and operator guidance.
4. Write `change-log.md` and close the set.

**Creates:**
- `docs/session-sets/040-codex-launch-adapter/change-log.md`
- `docs/session-sets/040-codex-launch-adapter/040-codex-launch-adapter-uat-checklist.json`

**Touches:**
- Codex-specific docs and shared launch docs as needed

**Ends with:** Codex is onboarded to the shared launch-adapter path and
documented for downstream chat work.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New Gemini adapter plan (Set 041)
Source: docs/session-sets/041-gemini-launch-adapter/spec.md
```markdown
# Gemini Launch Adapter

> **Purpose:** onboard Gemini to the shared launch-adapter contract with
> an explicit discovery step that decides the target binary/surface,
> then implement a stable `GeminiLaunchAdapter` without speculative
> assumptions about soon-changing CLI behavior.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/041-gemini-launch-adapter/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** Gemini has the highest discovery risk because the CLI
> surface is in flux. The set still ends in operator-visible IDE launch
> behavior, so it needs both automated coverage and manual validation.

---

## Project Overview

- Session 1 is a go/no-go discovery pass: confirm whether the target is
  the current Gemini CLI, its replacement surface, or a temporarily
  gated adapter.
- Sessions 2-3 implement `GeminiLaunchAdapter` only against the locked
  discovery verdict, including model/thinking/effort mapping and prompt
  output handling.
- Non-goals:
  - shipping against undocumented or obviously sunset-only behavior;
  - treating Gemini config files as an ownership signal;
  - the in-extension chat transcript UI.

---

## Sessions

### Session 1 of 4: Discovery and target-binary decision for Gemini

**Steps:**
1. Read the current Gemini documentation and locally inspect the CLI (or
   successor) surface for model selection, prompt mode, JSON/stream
   output, thinking/effort controls, permissions, and resume behavior.
2. Decide whether the implementation target is the current Gemini CLI, a
   successor binary, or a capability-gated placeholder if the surface is
   too unstable.
3. Capture the decision and the exact adapter contract in a discovery
   note that future sessions treat as the locked source of truth.

**Creates:**
- `docs/session-sets/041-gemini-launch-adapter/discovery-notes.md`

**Touches:**
- Gemini planning notes as needed

**Ends with:** a documented target decision that prevents speculative
Gemini implementation.

**Progress keys:**
- `session-001/gemini-docs-read`
- `session-001/local-cli-characterized`
- `session-001/target-binary-locked`
- `session-001/round-a-verification`

---

### Session 2 of 4: Implement `GeminiLaunchAdapter.buildLaunchPlan()`

**Steps:**
1. Implement the launch-plan mapping for the chosen Gemini surface,
   including model, mode, permissions, and any thinking/effort mapping.
2. Add capability gating when the chosen surface cannot yet support a
   requested feature.
3. Add focused argv/env tests so unstable CLI details stay localized to
   the adapter.
4. Register the adapter with the shared launch registry.

**Creates:**
- Gemini adapter implementation and focused tests

**Touches:**
- shared launch registry and command surfaces as needed

**Ends with:** Gemini has a working launch-plan generator for the locked
target surface.

**Progress keys:**
- `session-002/gemini-adapter-added`
- `session-002/capability-gating-wired`
- `session-002/argv-mapping-tested`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Output handling, actual-model reporting, and IDE wiring

**Steps:**
1. Implement the best stable machine-readable or text-output handling
   path for prompt-mode Gemini runs.
2. Add actual-model reporting from the most reliable surfaced signal.
3. Add Layer-2 and Layer-3 coverage for launch, failure, and any attach
   or limitation UX.
4. Confirm the operator UX honestly reflects unsupported Gemini features
   instead of implying parity where none exists.

**Creates:**
- Gemini launch integration tests

**Touches:**
- Gemini-facing command surfaces and UI messaging

**Ends with:** Gemini launch behavior is integrated into the extension
with honest capability reporting.

**Progress keys:**
- `session-003/output-path-wired`
- `session-003/model-reporting-wired`
- `session-003/layer3-tests-green`
- `session-003/capabilities-honest`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the Gemini adapter and command
   flows.
2. Produce the ad-hoc UAT checklist for launch, limitations, and error
   handling.
3. Update docs and operator guidance based on the locked target-binary
   decision.
4. Write `change-log.md` and close the set.

**Creates:**
- `docs/session-sets/041-gemini-launch-adapter/change-log.md`
- `docs/session-sets/041-gemini-launch-adapter/041-gemini-launch-adapter-uat-checklist.json`

**Touches:**
- Gemini-specific docs and shared launch docs as needed

**Ends with:** Gemini is onboarded to the shared launch path with clear
documentation of any remaining limits.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New chat foundation plan (Set 042)
Source: docs/session-sets/042-rudimentary-chat-interface-foundations/spec.md
```markdown
# Rudimentary Chat Interface Foundations (Copilot-First)

> **Purpose:** build the first in-extension chat surface only if opening a
> vendor TUI is not sufficient, starting with a minimal Copilot-first
> panel that proves transcript persistence, prompt submission, and shared
> `beginSession()` integration before multi-provider expansion.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/042-rudimentary-chat-interface-foundations/`
> **Prerequisites:**
> - Set 037 (`037-launch-adapter-foundations`) CLOSED.
> - Set 039 (`039-copilot-launch-adapter`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** this set introduces a brand-new operator-visible UI
> surface inside the extension. It needs both IDE-level coverage and a
> human judgment pass on layout, transcript clarity, and error handling.

---

## Project Overview

- This set answers the product question directly: if Dabbler wants more
  than "open the vendor TUI in a terminal," then yes, a rudimentary chat
  interface is required.
- The scope is deliberately limited to a Copilot-first proof so the UI
  shape lands before multi-provider complexity arrives.
- Deliverables: a minimal chat panel/webview, transcript persistence,
  prompt composer, session picker, and prompt-mode Copilot integration.
- Non-goals:
  - multi-provider event normalization;
  - streaming/tool timeline parity with vendor TUIs;
  - replacing the vendor TUI for advanced workflows.

---

## Sessions

### Session 1 of 4: Discovery and minimal-UX boundary for the chat panel

**Steps:**
1. Inventory the extension's current webview/view surfaces and choose the
   minimal viable chat host (panel, view, or existing surface extension).
2. Lock the transcript persistence model, failure states, and what the
   first Copilot-first UX will and will not show.
3. Decide how the chat panel relates to `Launch As...` / `Attach As...`
   so the product story stays coherent.
4. Capture the UI contract in a discovery note before implementation.

**Creates:**
- `docs/session-sets/042-rudimentary-chat-interface-foundations/discovery-notes.md`

**Touches:**
- chat/UI planning notes as needed

**Ends with:** a frozen minimal UX contract for the first in-extension
chat surface.

**Progress keys:**
- `session-001/ui-host-chosen`
- `session-001/transcript-model-locked`
- `session-001/launch-chat-story-aligned`
- `session-001/round-a-verification`

---

### Session 2 of 4: Scaffold the panel/webview and transcript store

**Steps:**
1. Build the panel/webview host and minimal layout shell.
2. Add transcript persistence and session selection/state restoration.
3. Add the prompt composer and message rendering primitives.
4. Add focused tests for storage/state transitions.

**Creates:**
- chat panel/webview implementation
- transcript store/state plumbing

**Touches:**
- extension activation and webview assets as needed

**Ends with:** a local chat shell exists with persistent transcript
state, even before provider execution is wired.

**Progress keys:**
- `session-002/chat-shell-added`
- `session-002/transcript-store-added`
- `session-002/prompt-composer-added`
- `session-002/unit-tests-green`

---

### Session 3 of 4: Wire Copilot prompt-mode execution through `beginSession()`

**Steps:**
1. Submit prompts through the shared launch boundary and the Copilot
   adapter's prompt-mode path.
2. Render user/assistant turns, loading states, and failure/refusal
   states honestly.
3. Decide whether the first UI exposes model/effort selection inline or
   reuses the launch profile picker.
4. Add Layer-2 and Layer-3 coverage for the first end-to-end chat flow.

**Creates:**
- Copilot-first chat execution wiring and tests

**Touches:**
- chat UI assets and Copilot adapter surfaces as needed

**Ends with:** a rudimentary in-extension chat can send a prompt and
render the result through the shared launch boundary.

**Progress keys:**
- `session-003/copilot-chat-wired`
- `session-003/failure-states-rendered`
- `session-003/profile-selection-decided`
- `session-003/layer3-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run focused regression coverage for the first chat panel.
2. Produce the ad-hoc UAT checklist for transcript feel, prompt
   submission, restore behavior, and failure handling.
3. Update docs so the next set can expand from a stable Copilot-first
   UI rather than re-deciding the foundations.
4. Write `change-log.md`.

**Creates:**
- `docs/session-sets/042-rudimentary-chat-interface-foundations/change-log.md`
- `docs/session-sets/042-rudimentary-chat-interface-foundations/042-rudimentary-chat-interface-foundations-uat-checklist.json`

**Touches:**
- chat UI docs and extension docs as needed

**Ends with:** the first in-extension chat surface exists and is ready
for multi-provider expansion.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```

### New multi-provider chat follow-up plan (Set 043)
Source: docs/session-sets/043-multi-provider-chat-interface-followup/spec.md
```markdown
# Multi-Provider Chat Interface Follow-up

> **Purpose:** expand the first rudimentary chat panel from its
> Copilot-first proof into a multi-provider surface that can launch and
> render Claude, Codex, and Gemini through the shared adapter model,
> with normalized transcript semantics, attach/resume handling, and
> capability-aware UX.
> **Created:** 2026-05-22
> **Session Set:** `docs/session-sets/043-multi-provider-chat-interface-followup/`
> **Prerequisites:**
> - Set 038 (`038-claude-launch-adapter`) CLOSED.
> - Set 040 (`040-codex-launch-adapter`) CLOSED.
> - Set 041 (`041-gemini-launch-adapter`) CLOSED.
> - Set 042 (`042-rudimentary-chat-interface-foundations`) CLOSED.
> **Workflow:** Orchestrator -> AI Router -> Cross-provider verification

---

## Session Set Configuration

```yaml
totalSessions: 4
requiresUAT: true
requiresE2E: true
uatScope: per-set
uatStyle: ad-hoc
effort: high
```

> **Rationale:** this set broadens a UI surface across multiple CLIs with
> different capabilities and failure modes. It needs both automated IDE
> coverage and human validation of the capability-aware UX.

---

## Project Overview

- Session 1 standardizes the transcript/event/resume model across the
  now-available provider adapters.
- Sessions 2-3 add the remaining providers and capability-aware UX.
- The goal is a multi-provider rudimentary chat surface, not feature
  parity with each vendor's native TUI.
- Non-goals:
  - reproducing every vendor-specific slash command or tool inspector;
  - hiding provider limitations instead of surfacing them honestly;
  - collapsing Dabbler `chatSessionId` and native provider resume tokens
    into one field.

---

## Sessions

### Session 1 of 4: Discovery and normalization plan for multi-provider chat

**Steps:**
1. Inventory the output/event/resume differences across Claude, Codex,
   and Gemini now that their launch adapters exist.
2. Lock a normalized transcript/event model for the chat UI, including
   how unsupported features appear.
3. Decide which providers get full prompt-mode transcript rendering,
   which get attach-only first, and which require explicit capability
   banners.
4. Capture the plan in a discovery note before expanding the UI.

**Creates:**
- `docs/session-sets/043-multi-provider-chat-interface-followup/discovery-notes.md`

**Touches:**
- chat UI planning notes as needed

**Ends with:** a locked normalization plan for multi-provider chat
expansion.

**Progress keys:**
- `session-001/provider-gaps-inventoried`
- `session-001/transcript-model-frozen`
- `session-001/capability-banners-decided`
- `session-001/round-a-verification`

---

### Session 2 of 4: Add Claude and Codex integration to the chat UI

**Steps:**
1. Add Claude and Codex execution paths to the chat panel using the
   normalized transcript model.
2. Render capability-aware controls so unsupported modes or attach paths
   are shown honestly rather than silently missing.
3. Add focused unit and Layer-2 coverage for the new provider paths.
4. Keep Copilot behavior stable while the provider matrix expands.

**Creates:**
- Claude/Codex chat integration and tests

**Touches:**
- chat panel/provider integration code

**Ends with:** the chat panel can handle Claude and Codex in addition to
Copilot.

**Progress keys:**
- `session-002/claude-chat-added`
- `session-002/codex-chat-added`
- `session-002/capability-controls-rendered`
- `session-002/layer2-tests-green`

---

### Session 3 of 4: Add Gemini, attach/resume UX, and richer status rendering

**Steps:**
1. Add Gemini integration according to the locked capability model from
   Set 041.
2. Introduce attach/resume UX where supported and explicit limitation
   messaging where not.
3. Add richer but still minimal status rendering: provider, model,
   effort, and attach state.
4. Add Layer-3 coverage for a representative multi-provider flow.

**Creates:**
- Gemini chat integration and multi-provider UI tests

**Touches:**
- chat panel/provider integration code and status UI

**Ends with:** the rudimentary chat UI supports the full provider set the
launch adapters made available.

**Progress keys:**
- `session-003/gemini-chat-added`
- `session-003/attach-ux-added`
- `session-003/status-rendering-added`
- `session-003/layer3-tests-green`

---

### Session 4 of 4: Regression, UAT, docs, and change-log

**Steps:**
1. Run regression coverage for the multi-provider chat surface.
2. Produce the ad-hoc UAT checklist for provider switching, transcript
   clarity, attach/resume behavior, and failure states.
3. Update docs and roadmap notes for any follow-on polish set that the
   UI still needs.
4. Write `change-log.md` and close the set.

**Creates:**
- `docs/session-sets/043-multi-provider-chat-interface-followup/change-log.md`
- `docs/session-sets/043-multi-provider-chat-interface-followup/043-multi-provider-chat-interface-followup-uat-checklist.json`

**Touches:**
- chat UI docs and provider integration docs as needed

**Ends with:** a multi-provider rudimentary chat surface exists with
honest capability signaling and regression coverage.

**Progress keys:**
- `session-004/regression-green`
- `session-004/uat-checklist-written`
- `session-004/docs-updated`
- `session-004/change-log-written`
```
