# CLAUDE.md — dabbler-ai-orchestration

## Purpose

This repo is the canonical source of truth for shared AI orchestration
infrastructure used across all Dabbler AI-led-workflow repos:

- **`ai_router/`** — multi-provider routing, prompt templates, session
  state, metrics, and workflow utilities
- **`tools/dabbler-ai-orchestration/`** — the "Dabbler AI Orchestration" VS Code
  extension

Your role in this repo is **canonical source and release gatekeeper**:
- Changes to `ai_router` are released to PyPI
- Changes to the extension are released to the VS Code Marketplace
- Consumer repos consume both via their respective registries — no file copying

## Consumer repos

| Repo | ai_router | Extension |
|---|---|---|
| `dabbler-access-harvester` | `pip install dabbler-ai-router` | VS Code Marketplace |
| `dabbler-platform` | `pip install dabbler-ai-router` | VS Code Marketplace |
| `dabbler-homehealthcare-accessdb` | not used (Lightweight tier) | VS Code Marketplace |

## Portability rule

> **Universal core, gated extensions, addendum specifics.**
>
> Anything in the core must work unmodified when `requiresUAT: false` and
> `requiresE2E: false` are permanent defaults. UI/UAT/E2E-specific behavior
> must be gated on spec-level flags.

## License

`LICENSE` at the repo root is canonical. `tools/dabbler-ai-orchestration/LICENSE`
is a required duplicate — `vsce package` expects the file alongside
`package.json` and has no flag to point elsewhere. Keep both in sync.

## Extension versioning

- Current: **v0.13.15**
- Publisher: `DarndestDabbler` (VS Code Marketplace: `DarndestDabbler.dabbler-ai-orchestration`)
- Namespace: `dabblerSessionSets` (shared across all consumers)
- Build: `cd tools/dabbler-ai-orchestration && npx vsce package`
- Publish: `cd tools/dabbler-ai-orchestration && npx vsce publish`

## Building & testing

```bash
# Extension (requires Node/npm)
cd tools/dabbler-ai-orchestration
npm install
npx vsce package

# ai_router (Python, requires .venv with `pip install -e .[tests]` from repo root)
python -m pytest
```

### Router-config editor

The VS Code extension ships a visual config editor (`Dabbler: Open Dabbler Config Editor`)
that reads and writes `ai_router/router-config.yaml`, `ai_router/budget.yaml`, and
`ai_router/local-overrides.yaml` (gitignored). The editor is implemented in
`tools/dabbler-ai-orchestration/src/configEditor/`. Key files:

- `ConfigEditorPanel.ts` — webview panel, load/save/drift-detect, Python subprocess dispatch
- `yamlReadWrite.ts` — comment-preserving YAML round-trip (uses the `yaml` package)
- `schemaValidator.ts` — AJV-based validation of all three config files
- `sections/` — one file per section (routing, budget, providers, significance, notifications, local-overrides-summary)
- `patch.ts` — `applyPatch()` translates the webview `SavePayload` into YAML mutations

The wizard (`Dabbler: Get Started`) now also has a "Configure AI Router" button
that opens the config editor directly.

## Repo layout standard

The sibling-worktrees-folder layout is the dabbler standard for new
repos and the migration target for existing ones — main checkout at
`~/source/repos/<repo>/` (never moves), worktrees at
`~/source/repos/<repo>-worktrees/<slug>/`. See
`docs/planning/repo-worktree-layout.md` for the layout, fresh-repo
setup recipe, migration recipes (covering both the legacy sibling-
worktree pattern and the retired bare-repo + flat-worktree pattern),
drift recovery, deactivate-mode recipe, and gotchas. Consumer repos
point their own agent-instruction files at this doc.

## Quick start

New to this repo? Read [`docs/quick-start.md`](docs/quick-start.md) first —
it explains the framework in five minutes and points to the right reference
docs from there.

## Close-out and outsource-last

Step 8 of `docs/ai-led-session-workflow.md` is collapsed to a single
paragraph that points at the canonical close-out reference:

- **`ai_router/docs/close-out.md`** — when `python -m
  ai_router.close_session` runs, how to invoke it, what it does
  (gate checks, idempotent writes, lock contention), common
  failures and remediation, the manual-flag matrix
  (`--interactive`, `--force`, `--manual-verify`, `--repair`), and
  troubleshooting (stranded sessions, mixed-mode drift,
  reconciler behavior).
`close_session --help` echoes Section 2 of `close-out.md`; the doc
is the single source of truth.
