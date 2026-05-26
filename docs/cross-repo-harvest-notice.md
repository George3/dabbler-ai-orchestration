# Cross-repo CLAUDE.md notice — log-harvest observability

**Authored:** 2026-05-25 (Set 045 Session 6)
**Audience:** consumer-repo CLAUDE.md authors (dabbler-platform,
dabbler-access-harvester, dabbler-homehealthcare-accessdb).

## Purpose

This is a one-time copy source. Paste the body below into each
consumer repo's top-level `CLAUDE.md` so its in-repo orchestrators
discover the dual-primary log-harvest surface the next time they
read their instruction file. The dabbler-ai-orchestration
extension and `dabbler-ai-router` PyPI package are already wired;
this notice is purely an instructions-side update.

No PRs are filed from this repo — the operator pulls the snippet
into each consumer manually per the established pattern, the same
way the existing
[`cross-repo-checkout-notice.md`](cross-repo-checkout-notice.md)
is propagated.

## What changed (one-paragraph summary)

The Session Set Explorer now surfaces **harvested-signal coverage**
(wrapper-launched / native-log / narration-marker / writer-bypass)
and **coordination conflicts** (engine-mismatch / bare-touch /
stale-checkout-touch / writer-bypass) for every session set,
combining a Dabbler-owned **launch wrapper**
(`python -m ai_router.dabbler_launch`) with native log scraping
of provider-side AI chat archives (Claude
`~/.claude/projects/<slug>/*.jsonl` + Copilot OTel JSONL). A new
**narration v1.1 template** (`Dabbler: Regenerate Narration
Templates` Command Palette action) ships canonical CLAUDE.md /
AGENTS.md files an operator can drop into a consumer workspace to
make a free-running AI session emit a single attribution marker
the joiner can correlate back to a Dabbler set. The architecture
treats wrapper + native-log channels as **co-equal** — neither is
a fallback for the other; both produce the canonical Harvest
Record schema documented at
[`docs/session-sets/045-log-harvest-implementation/joiner-spec.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/session-sets/045-log-harvest-implementation/joiner-spec.md).

Ships in `dabbler-ai-router` `0.8.0` (PyPI) and the
`DarndestDabbler.dabbler-ai-orchestration` VS Code Marketplace
extension `0.21.0` (Set 045).

---

## Snippet to paste into each consumer's CLAUDE.md

> Copy from the next horizontal-rule line through the trailing
> horizontal-rule line. The snippet is self-contained: it uses
> external links rather than referencing the consumer repo's own
> file layout, so it works unchanged in all three target repos.

---

### Log-harvest observability (dabbler-ai-router 0.8.0 + dabbler-ai-orchestration 0.21.0)

The Session Set Explorer now surfaces two new per-row signals for
every session set in the workspace:

- **Harvest-signal badges** — four single-letter badges per row
  showing what evidence the joiner found for that set:
  **W** (wrapper launch record present), **N** (native-log
  events from Claude or Copilot found), **M** (narration marker
  emitted), **B** (writer-bypass file activity detected).
  Each lights independently; off-state is grey/dim.
- **Conflict pills** — separate row below the signal strip with
  one pill per detected coordination conflict.
  Kinds: `engine-mismatch`, `bare-touch`, `stale-checkout-touch`,
  `writer-bypass`. Severity color follows IBM colorblind-safe
  palette. Hover for the joiner's note.

The surface is **observation-only** — it never writes to
`session-state.json` and never modifies the orchestrator block.
Set 036's check-out / check-in model remains the sole writer.

#### Two ways to feed the surface

Pick one or both. Wrapper and native-log channels are **co-equal**;
neither is a fallback for the other.

##### Option 1: Launch via `dabbler-launch` (the wrapper)

```bash
python -m ai_router.dabbler_launch --backend claude --workspace-cwd $PWD
python -m ai_router.dabbler_launch --backend copilot --workspace-cwd $PWD
```

The wrapper writes a launch record to
`~/.dabbler/launches.jsonl` immediately, then spawns the
underlying assistant. The joiner correlates the launch record to
the assistant's native log via
`(workspace_cwd, time_window=30s, conv_id post-bind)` keys.
Headless-mode only in this release; interactive TTY-passthrough
on Windows is a deferred follow-on.

##### Option 2: Drop a narration template into the workspace

If you'd rather launch your assistant the usual way (no wrapper),
have the assistant emit a single attribution marker at session
start. Run from the active session set's directory:

```
Dabbler: Regenerate Narration Templates    # Command Palette
```

The command writes
`<session-set>/narration-templates/CLAUDE.md` and `AGENTS.md`,
each containing a single `[DABBLER-NARRATION v1
phase=session-start set=<slug> session=<N> total=<T>
effort=<E>]` marker as the first text the assistant should emit.
A `Copy to consumer workspace…` action on the success toast
copies the rendered files to a target workspace root with
overwrite confirm.

The CLI equivalent:

```bash
python -m ai_router.narration --kind claude --state-file <set>/session-state.json --output <consumer>/CLAUDE.md
python -m ai_router.narration --kind agents --state-file <set>/session-state.json --output <consumer>/AGENTS.md
```

#### Required setup for the harvest surface

The extension shells out to `python -m ai_router.joiner` for both
coverage badges and conflict pills. If `dabbler-ai-router` is not
installed in the venv the extension finds at
`dabblerSessionSets.pythonPath`, a one-time setup warning toast
fires with an **Open settings** action; the Explorer keeps
rendering all rows but the badge / pill columns stay empty.
Install with:

```bash
pip install dabbler-ai-router>=0.8.0
```

Reload VS Code window; refresh the Session Sets view; the badges
and pills populate on the next snapshot.

#### Privacy / redaction

The joiner enforces `joiner-spec.md` §7 redaction on every
canonical Harvest Record it emits: tool arguments are summarised
(file path + line counts + Bash `command_head` only); raw
`old_string`, `new_string`, full argv bodies, file contents, and
free-form chat text are **never** included. The launch wrapper's
record contains workspace cwd + engine + provider + model +
effort + a uuid4 launch_id; no chat content. The narration marker
contains only the set slug + session number + total + effort.

#### Canonical references in dabbler-ai-orchestration

- [`docs/session-sets/045-log-harvest-implementation/joiner-spec.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/session-sets/045-log-harvest-implementation/joiner-spec.md)
  — full joiner contract: conflict modes, Harvest Record schema,
  CoverageSummary fields, ConflictReport fields, redaction
  posture, deferred follow-ups.
- [`docs/narration-templates.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/narration-templates.md)
  — operator reference for the narration v1.1 surface: when to
  use templates, marker anatomy, the four defensive phrasing
  rules, malformed-marker diagnostic flags.
- [`docs/session-sets/044-ai-chat-log-discovery-and-experiments/proposal.md`](https://github.com/darndestdabbler/dabbler-ai-orchestration/blob/master/docs/session-sets/044-ai-chat-log-discovery-and-experiments/proposal.md)
  — Set 044 consensus-audited proposal v1: the locked
  architectural commitments + the dual-primary rationale.

---

## Notes for the paster

- The snippet has its own H3 heading so it can drop into any
  existing CLAUDE.md without colliding with surrounding
  structure. Pick an insertion point near the existing
  `Orchestrator check-out / check-in` snippet from
  [`cross-repo-checkout-notice.md`](cross-repo-checkout-notice.md);
  the two notices are complementary (check-out is the writer
  surface; harvest is the observation surface).
- The links above are absolute GitHub URLs against `master` so
  they resolve regardless of which consumer repo the snippet
  lives in.
- Lightweight-tier consumers (`dabbler-homehealthcare-accessdb`)
  do **not** need to install `dabbler-ai-router` for the
  harvest surface to work in the canonical repo's view of their
  workspace — the joiner reads the consumer's
  `~/.claude/projects/<workspace-slug>/` archive directly. They
  may install the wrapper if they want to feed Option 1's launch
  channel, but it's optional.
- If you only ever launch AI sessions inside the
  `dabbler-launch` wrapper, the narration template is redundant
  — the wrapper's launch record already supplies the
  correlation key. If you only ever launch outside the wrapper,
  the template is the only way to attribute native-log events
  to a specific session set. Most operators use both.
