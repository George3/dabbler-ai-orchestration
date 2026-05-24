"""Session 4 verification driver — Set 045 / log-harvest implementation.

Bundles the S4 deliverables and asks a cross-provider verifier
(Gemini Pro) to confirm the Claude per-event parser + narration
v1.1 template + extension command match the S1/S2 contracts and
the four defensive phrasing rules locked in Q3.

Per memory `feedback_ai_router_route_result_handling`: dump
RouteResult to JSON before any attribute access.
Per memory `feedback_session_verification_gpt54_429_pivot_to_gemini`:
go straight to gemini-pro to avoid the GPT-5.4 429 cascade.
Per memory `feedback_split_large_verification_bundles`: bundle
estimated <100KB; well within gemini-pro's context window.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import ai_router  # noqa: E402  type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SET_DIR = Path(__file__).resolve().parent


def read_file(path: Path) -> str:
    rel = path.relative_to(REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    return f"=== FILE: {rel} ===\n{text}"


def dump_route_result_to_json(result) -> dict:
    if dataclasses.is_dataclass(result):
        return dataclasses.asdict(result)
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items()}
    return {"_repr": repr(result)}


SYSTEM_SUMMARY = """
Set 045 (log-harvest implementation) ships the dual-primary
observability architecture locked by Set 044's consensus-audited
proposal: a Python launch wrapper + per-backend native-log parsers
+ a joiner that detects coordination conflicts and writer-bypass
writes.

Session 1 (CLOSED, VERIFIED, $0.024) resolved the four Set 044
open questions and locked joiner location to Python.
Session 2 (CLOSED, VERIFIED, $0.053) shipped joiner-spec.md +
canonical Harvest Record schema + Python joiner skeleton with 59
Layer-1 tests.
Session 3 (CLOSED, VERIFIED, $0.107) shipped the dabbler-launch
wrapper + Copilot OTel per-event parser + harvest() join wire-up,
with three verification rounds catching 5 must-fix bugs in the
join algorithm (vendor-variant engine handling + single-bind
invariant + filter-before-binding + bound-native event stream).

Cumulative routed Set 045 coming into S4: $0.184 of $5 NTE budget.

Session 4 (THIS verification) ships the Claude-side counterpart
to S3's Copilot work plus the narration v1.1 template authoring:

  - ai_router/joiner/parsers.py adds read_claude_session_events()
    — per-event HarvestRecord emission for ~/.claude/projects/
    <slug>/<conv>.jsonl. Maps Claude JSONL record types to the
    canonical event_type enum (joiner-spec.md §5.1):
    * first user/assistant record → session_start (once)
    * each assistant record → turn
    * each tool_use block → tool_call (redacted via
      _summarize_claude_tool_args, §7 posture)
    * assistant.message.usage → usage (tokens_in summed across
      input_tokens + cache_creation + cache_read; tokens_out
      from output_tokens)
    * text blocks matching MARKER_REGEX → marker event with
      source="narration"
    Noise types (queue-operation, ai-title, last-prompt,
    file-history-snapshot, attachment) are skipped. Sticky
    context (cwd, conv_id, model) is established from the first
    record carrying each field and provider defaults to
    "anthropic" once a model is seen.

  - ai_router/joiner/schema.py _native_events_for() now dispatches
    to read_claude_session_events for claude engines (was: single
    session_start fallback). The Copilot branch is unchanged.

  - ai_router/narration.py (NEW) — canonical narration v1.1
    templates + marker regex + parser + render() + CLI. Two
    template kinds (claude → CLAUDE.md, agents → AGENTS.md), both
    asking the assistant to emit
    [DABBLER-NARRATION v1 phase=session-start set=... session=N
    total=M effort=...] as the first text of its first response.
    The four Q3 defensive rules (no harvest lexical family, no
    pretense self-disclosure, framed as project convention, minimal
    caps) are honored in the template prose. project_state_for_
    template() reads session-state.json via the canonical D13 path
    ai_router.progress.read_progress.

  - tools/dabbler-ai-orchestration/src/commands/
    regenerateNarrationTemplates.ts (NEW) — VS Code command
    "Dabbler: Regenerate Narration Templates" that picks an
    in-progress session set (auto-selects when exactly one),
    shells out to python -m ai_router.narration twice (claude +
    agents kinds), writes outputs to
    <set-dir>/narration-templates/CLAUDE.md and AGENTS.md, and
    opens the CLAUDE template for inspection. Wired into
    extension.ts; declared in package.json.

  - docs/narration-templates.md (NEW) — operator-facing
    reference explaining when to use the templates, how to
    regenerate them, the marker anatomy, the defensive phrasing
    rules, and the diagnostic-flag semantics for malformed
    markers.

  - 18 new Layer-1 tests: 5 read_claude_session_events scenarios
    (canonical stream, missing file, malformed lines, noise-only
    file, session_start-once invariant, Bash argv redaction) +
    13 narration tests (marker regex + detect_marker semantic
    checks + render_template + defensive-rule audit + round-trip
    + project_state_for_template + CLI integration). Pytest 808
    passed (+33 vs S3's 775) + 1 skipped, no regressions. TS
    typecheck clean. Extension test:unit harness 531 passing.

S5 wires Explorer to the joiner CLI. S6 ships UAT + cross-tier
docs + dual-registry release.
""".strip()


FOCUS_PROMPT = """
Bias cautions: This prompt was authored by an AI agent that may
have an opinion on the answer. Its framing may inadvertently
constrain you to in-scope refinements when the right answer is to
question the scope. The work being reviewed may be presented as
further along than it should be. Before answering as posed,
briefly check whether this is the right question. If a different
question would be more useful, answer that one too.

ROUND A — Session 4 deliverable verification for Set 045
(log-harvest implementation).

You are Gemini Pro, asked to verify that Session 4 of Set 045
ships a Claude per-event parser + narration v1.1 template + an
extension command that match the S1 phrasing-trigger ablation
output, the S2 canonical Harvest Record §5 schema, and the S3
join-pattern precedent verbatim.

Verification targets:

A. **Claude per-event parser
   (read_claude_session_events in parsers.py).**

   1. Per joiner-spec.md §5.1, producers MUST emit the canonical
      enum: event_type ∈ {launch, session_start, turn, tool_call,
      marker, usage, session_end}. The parser emits
      session_start / turn / tool_call / usage / marker.
      session_end is NOT emitted (Claude JSONL has no explicit
      termination event; the file just stops). Is non-emission
      the right call, or should the parser synthesize a
      session_end at last_event_ts so staleness detection in S5
      has a clean signal? Note the symmetric trade-off: a
      synthesized session_end at last_event_ts would be wrong
      for sessions still mid-conversation when the joiner reads.

   2. Sticky-context updates: cwd is set on first cwd field
      seen and is sticky; conv_id is overwritten on every record
      carrying sessionId. Is that the right asymmetry, or should
      conv_id also stick to first-seen (a within-file sessionId
      change is rare but theoretically possible)?

   3. The first user OR assistant record yields session_start.
      Tests confirm noise-only files emit nothing. Is using the
      first user-or-assistant boundary correct, or should the
      parser require a user record specifically (Claude conversations
      always start with a user turn; an assistant-first JSONL
      would be a forensic artifact)?

   4. Token accounting:
      tokens_in = input_tokens + cache_creation_input_tokens +
      cache_read_input_tokens. tokens_out = output_tokens.
      Is the "total input tokens processed" interpretation
      correct, or should the joiner expose them as separate
      counters (Copilot's flat inputTokens has no cache split,
      so a flat sum aids cross-engine comparison; but a billing
      consumer downstream cares about the cache split)?

   5. Tool-call redaction (_summarize_claude_tool_args):
      preserves file_path / path / file / filename and
      line_count / lines / count / limit. Adds command_head
      (first whitespace-split token of a Bash command's
      `command` field). Strips old_string / new_string / argv
      body. Is the Bash command_head heuristic safe (it
      preserves "curl" but not the URL+key), or does it leak in
      the rare case where the verb itself is sensitive?

   6. Marker detection runs ONLY on assistant text blocks (not
      user content; not thinking blocks). Per Set 044 §3.1 the
      marker is emitted by the assistant; the user side carrying
      a marker would be the operator's own paste, not a
      narrated marker. Is the assistant-only scoping correct?

   7. Tolerance: bad JSONL lines skip; OSError on the file
      returns nothing. Empty cwd_canonical is tolerated (record
      carries ""). Is this the right "tolerant streaming
      generator" posture (matches the Copilot parser's
      behavior), or should missing cwd abort the parser?

B. **_native_events_for dispatch (schema.py).**

   1. Claude branch added alongside copilot. The branch list-
      materializes the parser output (per the docstring: caller
      sorts the final stream by ts, so a list buys nothing over
      a generator EXCEPT that the assemble loop in harvest()
      iterates the list to apply _merge_launch_context). Is the
      eager-list materialization the right precedent (mirrors
      the Copilot branch), or should the Claude branch return
      the streaming generator?

   2. The "future engines" fallback still emits a single
      session_start. Is the right behavior for an unknown engine
      (forward-compat for Codex / Gemini parsers), or should an
      unknown engine raise (loud-fail per the operator's
      `feedback_default_not_started_evidence_to_escalate`
      cousin "default to lowest-engagement bucket")?

C. **Narration v1.1 template (ai_router/narration.py).**

   1. MARKER_REGEX matches the narration-design.md §2.3 regex
      verbatim — anchored single-line, with the optional-quote
      character class covering ASCII + 4 Unicode curly variants.
      Is the character class right (the visual encoding of
      U+201C/D and U+2018/19 makes diffs confusing)?

   2. detect_marker emits ParsedMarker with diagnostic flags:
      skipped (unknown version), incomplete (missing required
      fields), parse_error (malformed version number),
      semantic_error (placeholder-leakage / unknown-phase /
      unknown-effort-enum / session-exceeds-total /
      non-integer-{session,total}). Are these exhaustive vs.
      narration-design.md §5.5, or is a check missing? Should
      "placeholder-leakage" also flag SET-SLUG appearing in the
      session field (current implementation only checks the
      five string values against a placeholder set)?

   3. Templates obey the four Q3 defensive rules — no
      harvest|harvester|harvesting|harvested lexical family, no
      synthetic|smoke probe|NOT a real|test fixture pretense
      markers, framed as project convention not data-emission
      ask, minimal caps. A unit test scans the rendered output
      for the forbidden patterns. Is the test sufficient
      coverage for "the templates obey rule 3 (framing) and
      rule 4 (caps)", or does it only cover rules 1+2?

   4. project_state_for_template reads state via
      ai_router.progress.read_progress (D13-compliant). The
      progress reader requires a v3 sessions[] OR synthesizes
      one from v2 currentSession + totalSessions + status. If
      the orchestrator starts a session via start_session.py
      but the state file's status is somehow not "in-progress"
      (a writer bug), read_progress.current_session is None
      and the function refuses to render. Is the refusal
      correct (fail-loud), or should the function fall back to
      raw currentSession?

   5. The CLI exposes --state-file vs --set-slug+--session+
      --total as mutually exclusive sources. effort is
      separately optional. Is the CLI surface ergonomic enough
      for Lightweight-tier operators (who may not have a
      session-state file to read), or should there be a
      stdin-mode for piped consumption?

D. **Extension command
   (regenerateNarrationTemplates.ts).**

   1. The command picks the in-progress session set
      (auto-select when exactly 1; quickpick otherwise). It
      writes rendered files to <set-dir>/narration-templates/
      (under the session-set folder, NOT the workspace root).
      The operator must then COPY the rendered file to the
      *consumer project's* workspace root. Is the indirection
      correct (avoids clobbering an operator-authored
      CLAUDE.md at the workspace root), or is it confusing
      enough that the command should offer to write directly
      to the consumer project with a confirm prompt?

   2. The command shells out to `python -m ai_router.narration`
      twice (once per kind). Both invocations share the same
      pythonPath resolver pattern as installAiRouter +
      checkOutOrchestrator. Is the spawnSync usage correct, or
      does the absence of a withProgress wrapper mean a slow
      Python startup makes the UI feel frozen?

   3. The "Copy CLAUDE.md / AGENTS.md to the consumer project's
      workspace root" hint is in the success toast text. Is
      that discoverability enough, or should the command add a
      dedicated "Copy to consumer workspace" action button?

E. **Test coverage.**

   1. 18 new Layer-1 tests: 5 Claude parser scenarios +
      13 narration tests. The Claude tests use synthetic JSONL
      fixtures (no real ~/.claude reads). Are the scenarios
      complete vs. the spec, or is a case missing (e.g.,
      attachments with file references that should NOT trip
      tool-call emission, or thinking-block content that
      should NOT be scanned for markers)?

   2. The defensive-rule audit test renders the templates with
      a neutral set_slug ("example-project") so any
      "harvest" substring is in the template prose, not a
      substitution. Is the audit assertion strong enough
      ("no harvest|harvester|... in re.IGNORECASE"), or
      should it also check sentence framing (rule 3) — and
      what would that check even look like?

   3. The S3 e2e test fixture (_write_claude_jsonl in
      test_dabbler_launch_join_e2e.py) was updated to write a
      proper type=user record so the new per-event parser
      emits a session_start (it previously wrote a minimal
      no-type record that survived the old fallback). Is this
      a reasonable fixture update, or does it mask a parser
      regression (the old fallback was lenient about the JSONL
      shape; the new parser is strict — is the strictness
      defensible)?

F. **Cross-cutting / re-question.**

   Per the bias-cautions preamble: if a different question
   would be more useful, answer that one too. Specifically:

     - The marker parser is shared between Claude and Copilot
       in principle, but S4 only wires it into the Claude
       per-event parser. The Copilot OTel parser doesn't scan
       gen_ai.output.messages for markers (the field requires
       OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
       per narration-design.md §5.0). Should S4 also add
       Copilot-side marker scanning, or is that legitimately a
       follow-on (e.g., S5 Explorer integration could surface
       which backends have marker support active)?

     - The Q3 optional ablation protocol (A1–A8) was not run
       in this session. The templates ship with "defensive by
       best-evidence" posture. Is that the right call, or
       should S4 have spent ~$1–3 on the ablation to upgrade
       to "defensive by isolated trigger boundary" before
       Marketplace release in S6?

     - The narration template tells the assistant to emit ONE
       marker at session start and no per-turn markers. If a
       Claude session sends the assistant TWO marker emissions
       (operator paste + assistant generation, or two
       consecutive turns both opening with the marker), the
       parser emits two marker records. Is the joiner robust
       to that (e.g., downstream dedups, or accepts the
       duplicate)? Should the parser dedup-by-(set,session)
       within a single conversation?

     - read_progress requires a fairly complete v3 state file
       (sessions[] OR a v2 ledger with status+currentSession).
       The narration template render path is intentionally
       D13-compliant. But the Lightweight-tier convention is
       hand-maintained completedSessions[]; a Lightweight
       state with currentSession=4 but status="not-started"
       (a writer mistake) would refuse to render. Is the
       refusal a feature (catches a hand-edit bug early) or a
       footgun (a Lightweight operator can't render the
       template until the status is corrected)?

Format the verdict as either:
  - VERIFIED: no must-fix issues. (Followed by any nice-to-have notes.)
  - REJECTED: <bulleted list of must-fix issues>.
""".strip()


def main() -> int:
    bundle_parts = [
        read_file(SET_DIR / "joiner-spec.md"),
        read_file(SET_DIR / "open-question-resolution.md"),
        read_file(REPO_ROOT / "ai_router/narration.py"),
        read_file(REPO_ROOT / "ai_router/joiner/schema.py"),
        read_file(REPO_ROOT / "ai_router/joiner/parsers.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_narration.py"),
        read_file(REPO_ROOT / "ai_router/tests/test_joiner_parsers.py"),
        read_file(
            REPO_ROOT
            / "tools/dabbler-ai-orchestration/src/commands/regenerateNarrationTemplates.ts"
        ),
        read_file(REPO_ROOT / "docs/narration-templates.md"),
    ]
    bundle = "\n\n".join(bundle_parts)
    print(f"Bundle: {len(bundle)} chars across {len(bundle_parts)} parts")

    out_dir = SET_DIR / "session-reviews"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "session-004-route-result.json"

    print(f"\n{'='*60}\n[Round A] sending to gemini-pro...\n{'='*60}")
    result = ai_router.query(
        model="gemini-pro",
        content=FOCUS_PROMPT,
        task_type="session-verification",
        context=f"{SYSTEM_SUMMARY}\n\n--- BUNDLE START ---\n{bundle}\n--- BUNDLE END ---",
        session_set="045-log-harvest-implementation",
        session_number=4,
    )
    result_dict = dump_route_result_to_json(result)
    out_path.write_text(
        json.dumps(result_dict, default=str, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"Provider: {result_dict.get('provider')}")
    print(f"Model: {result_dict.get('model') or result_dict.get('model_name')}")
    print(
        "Tokens: "
        f"in={result_dict.get('input_tokens', '?')}, "
        f"out={result_dict.get('output_tokens', '?')}"
    )
    print(f"Cost: ${result_dict.get('cost_usd', result_dict.get('cost', '?'))}")
    print(f"Latency: {result_dict.get('latency_ms', '?')} ms")
    text = (
        result_dict.get("response")
        or result_dict.get("text")
        or result_dict.get("content")
    )
    if isinstance(text, str):
        print(f"\n--- VERIFIER OUTPUT ---\n{text}\n--- end ---")
        verdict_path = out_dir / "session-004.md"
        verdict_path.write_text(text, encoding="utf-8")
        print(f"Wrote {verdict_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
