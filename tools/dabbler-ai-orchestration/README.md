# Dabbler AI Orchestration

An AI-led coding-session workflow for VS Code. Manage structured AI
sessions, automatic cross-provider verification, cost tracking, and
git-worktree-aware session-set state — all from the activity bar.

![Session Set Explorer in action](https://raw.githubusercontent.com/darndestdabbler/dabbler-ai-orchestration/master/tools/dabbler-ai-orchestration/media/session-set-explorer-in-action.png)

---

## What you get

- **Sessions, not infinite chats.** Bounded slices of work — one
  session, one orchestrator conversation, one verification, one
  commit. Sessions live inside ordered **session sets** that you and
  the AI co-design before any code is written. The activity-bar tree
  shows what's in flight, what's queued, and what's done.

- **Cost-minded routing.** Every reasoning task (code review,
  analysis, documentation, end-of-session verification) goes through
  the AI router, which picks the cheapest capable model per task and
  escalates only when needed. Real projects we tested measured
  **73% savings vs Opus-only** on a CLI/library project (990 routed
  calls) and **32% savings** on a UI app with UAT/E2E gates (370
  calls). Two sample reports ship in the
  [GitHub repo](https://github.com/darndestdabbler/dabbler-ai-orchestration/tree/master/docs/sample-reports).

- **Cross-provider verification, every session.** Each session ends
  with an independent verification by a model from a *different*
  provider than the one that did the work. The verifier returns
  structured JSON; disagreements surface for human adjudication
  rather than being silently merged or dismissed.

---

## Get started

After install, the Session Set Explorer shows a **Get Started**
welcome the first time you open a workspace with no
`docs/session-sets/` folder. Click **Copy adoption bootstrap prompt**
and paste it into a fresh AI chat (Claude Code, Gemini Code Assist,
or any GPT-based tool). The AI fetches the canonical setup
instructions and walks you through:

1. **A budget dialog** — set a not-to-exceed (NTE) dollar cap for
   verification spend. Verification calls typically cost $0.05–$0.80
   each; entering $0 switches to manual cross-provider review at
   no API cost.
2. **A plan alignment** — the AI proposes a session-set
   decomposition based on what you describe.
3. **A numbered action checklist** — *every* intended write, config,
   and scaffolding step is listed. You batch-approve before anything
   touches disk. No per-write confirmation prompts. You can
   interrupt at any time.

Once your first session set exists, the welcome content disappears
and the standard activity-bar tree takes over.

If you'd rather drive the setup from VS Code's UI directly, run
**`Dabbler: Get Started`** from the command palette
(`Ctrl+Shift+P` / `Cmd+Shift+P`). The wizard includes a
**Configure AI Router** button that opens the visual config editor
once your project is set up.

---

## What it'll cost

API spend is real and varies by project size and verification
appetite. Honest framing:

- **$0 budget** — verification routes through a *different* AI
  assistant you open manually (e.g. open a second AI chat as the
  verifier), or you skip verification with the decision logged. No
  API spend.
- **Non-zero budget** — the router makes synchronous API calls for
  cross-provider verification, capped at your not-to-exceed (NTE)
  threshold. Verification calls typically run **$0.05–$0.80 each**;
  a 3-session set usually totals **$0.15–$2.50**; a 6-session set
  **$0.30–$5.00**. These are empirical medians — outliers exist.

The router writes one JSON line per call to
`ai_router/router-metrics.jsonl` so you can audit spend at any
time. The **Cost Dashboard** command surfaces cumulative spend
visually; `python -m ai_router.report` produces a full markdown
manager-report with the Opus-baseline savings headline,
per-task-type unreliability rates, and auto-generated action
items. The framework is open-source (MIT) — your costs are entirely
your provider's API spend; nothing in this extension is paywalled.

---

## Requirements

- **VS Code** 1.85+
- **Python 3.10+** with a workspace `.venv/` (the
  **`Dabbler: Install ai-router`** command auto-detects or creates
  it for you)
- **API keys** as environment variables:
  - `ANTHROPIC_API_KEY` (Claude Sonnet, Opus)
  - `GEMINI_API_KEY` (Gemini Flash, Pro)
  - `OPENAI_API_KEY` (GPT-5.4, GPT-5.4 Mini)
  - All three are required so cross-provider verification has
    somewhere to route to.
- **One orchestrator AI agent** installed as a VS Code extension
  (Claude Code, Codex/GitHub Copilot, or Gemini Code Assist — the
  framework is agent-agnostic and supports switching mid-set).

Optional: `PUSHOVER_API_KEY` + `PUSHOVER_USER_KEY` for
end-of-session phone notifications.

Sign-up links and a full prerequisites checklist live in the
[GitHub repo's README](https://github.com/darndestdabbler/dabbler-ai-orchestration#prerequisites-tools-and-accounts).

---

## Other features

- **Orchestrator indicator on in-progress rows.** Every in-progress
  session set's row expands to an accordion-body with two side-by-side
  gauges — the model tier (low / mid / flagship, IBM colorblind-safe
  palette) and the current effort (low / medium / high / extra-high /
  max). The gauges read a per-set marker (`<workspace>/docs/session-
  sets/<slug>/.dabbler/orchestrator.json`) populated automatically by
  the Claude Code `SessionStart` hook (run **`Dabbler: Install
  Orchestrator Hook (Claude Code)`** once per workspace) and the Codex
  `~/.codex/config.toml` watcher. Right-click any in-progress row to
  open **Set Orchestrator Model & Effort…** (universal manual override
  for Gemini Code Assist + GitHub Copilot, or any time you want to
  declare what's running) or **Open Orchestrator Writer Log**
  (diagnostic — appended when multi-writer precedence skips a write).
  Both are also reachable via the Command Palette under the **Dabbler**
  category.
- **Visual config editor** (`Dabbler: Open Dabbler Config Editor`) —
  edit `router-config.yaml`, `budget.yaml`, and the gitignored
  `local-overrides.yaml` through a six-section panel without touching
  YAML directly. Sections cover routing mode, budget threshold,
  provider API-key env vars, significance flagging, Pushover
  notifications, and a local-overrides summary. Includes a
  live-validation drift banner and a "Send a test notification" button.
- **Significance flagging** — `Dabbler: Flag Decision for Cross-Provider
  Review` appends a one-line reason to the active set's review queue.
  `Dabbler: Scan Workspace for @dabbler:outsource-review Annotations`
  walks source files for `# @dabbler:outsource-review("...")` and
  `// @dabbler:outsource-review("...")` annotations and queues new
  findings automatically.
- **Cancel/Restore lifecycle** — cancel a session set mid-stream
  with a recorded reason; restore later if priorities shift. The
  audit trail accumulates across cycles.
- **UAT checklist editor integration** — for sets that opt in with
  `requiresUAT: true`, the orchestrator authors a checklist that
  pairs with the freely-available
  [UAT checklist editor](https://darndestdabbler.github.io/uat-checklist-editor/).
  Pending review blocks downstream sessions unless explicitly
  overridden.
- **Worktree auto-discovery** — parallel session sets running in
  sibling git worktrees show up in the activity-bar tree even when
  the worktree isn't open as a separate workspace folder.

---

## Learn more

- **GitHub:** [darndestdabbler/dabbler-ai-orchestration](https://github.com/darndestdabbler/dabbler-ai-orchestration)
- **Workflow mechanics:** [docs/ai-led-session-workflow.md](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/ai-led-session-workflow.md)
  (trigger phrases, the 10-step procedure, the rule list every
  orchestrator obeys).
- **Repository reference:** [docs/repository-reference.md](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/repository-reference.md)
  (deep feature descriptions, UAT/E2E flag matrix, worked
  end-of-session output, file map).
- **Sample reports:** [docs/sample-reports/](https://github.com/darndestdabbler/dabbler-ai-orchestration/tree/master/docs/sample-reports)
  (real `python -m ai_router.report` outputs from contrasting
  projects).

---

## License

MIT. Copyright © 2026 darndestdabbler.
