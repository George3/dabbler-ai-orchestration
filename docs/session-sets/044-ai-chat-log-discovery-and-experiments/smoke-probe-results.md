## Pre-Lock Smoke Probe Results — Copilot CLI 1.0.51

> **Session:** 044 / S3. **Protocol:** narration-design.md §10.
> **Date:** 2026-05-22. **Run by:** Claude via Bash subprocess
> against operator's local Copilot 1.0.51 CLI (per operator
> answer to driver decision 2026-05-22).
> **Channel under test:** `AGENTS.md` at synthetic-set workspace
> root (`c:\tmp\dabbler-log-harvest\synthetic-set\AGENTS.md`).
> **Branch under test:** Branch A simulated (no `effort` key in
> the substituted instruction).

---

### 1. Headline verdict

**PASS for marker emission. ARCHITECTURAL REVISION REQUIRED
for harvester surface.**

- ✅ The LLM emits the marker verbatim with concrete substituted
  values, on its own line, as the first text output, no code
  fence, no paraphrase.
- ✅ The marker survives in `gen_ai.output.messages` attribute
  of the `chat <model>` OTel JSONL span — but only when
  `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`.
- ❌ The marker does **NOT** survive in
  `session-store.db turns.assistant_response`. The DB row
  captures only the LLM's final formatted output text (post-
  marker, post-commentary).
- 🟡 Bonus discovery: `gen_ai.usage.reasoning.output_tokens` is
  a per-turn native signal that was not documented in S1's
  Copilot inventory. Reshapes the A3 Copilot branch decision.

The smoke probe found exactly the class of bug GPT's pre-lock
gate was designed to catch: the contract as written assumed the
wrong persistent surface.

---

### 2. Probe protocol (executed)

#### 2.1 Setup

| Step | Outcome |
|---|---|
| 1. Identify Copilot custom-instructions channel | `AGENTS.md` files (per `copilot help environment` + `--no-custom-instructions` flag docs) |
| 2. Populate synthetic-set with minimal scaffold | `c:\tmp\dabbler-log-harvest\synthetic-set\docs\session-sets\001-synthetic-harvest-target\` with `spec.md` (2 sessions, low-effort) and `session-state.json` (schema v3, status not-started) |
| 3. Write substituted AGENTS.md | 1114 bytes at workspace root; full §7.1 instruction text with `set=001-synthetic-harvest-target`, `session=1`, `total=2`, no `effort` key (Branch A simulated) |

#### 2.2 Driver

```bash
# Run 1 — default OTel routing (inherited env had OTel
# exporter pointing to NUL device — discovered during probe)
copilot -C "C:/tmp/dabbler-log-harvest/synthetic-set" \
  -p "Begin Session 1... Follow AGENTS.md, then list files." \
  --allow-all-tools --allow-all-paths -s

# Run 2 — explicit OTel path + content capture ON
COPILOT_OTEL_FILE_EXPORTER_PATH="C:/tmp/dabbler-log-harvest/otel/smoke-probe.jsonl" \
COPILOT_OTEL_ENABLED=true \
COPILOT_OTEL_EXPORTER_TYPE=file \
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true \
copilot -C "C:/tmp/dabbler-log-harvest/synthetic-set" \
  -p "Begin Session 1... Follow AGENTS.md, then list files." \
  --allow-all-tools --allow-all-paths -s
```

#### 2.3 Stdout-side observation (both runs)

The visible terminal output included the marker as the first
line, followed by commentary and the file listing. Run 1
example:

```
[DABBLER-NARRATION v1 phase=session-start set=001-synthetic-harvest-target session=1 total=2]

Listing the workspace root.

**Workspace root files:**
- `AGENTS.md`
- `docs`
```

The marker was verbatim, concrete values substituted, no code
fence, on its own line, first text output. **Marker-emission
contract satisfied at the assistant's output level.**

---

### 3. Persistent-surface findings

#### 3.1 session-store.db — marker MISSING

For both runs, `turns.assistant_response` for the run's session
contained ONLY the post-marker text — the marker was dropped.
Specifically (Run 1):

| Field | Value |
|---|---|
| session_id | `5ef62da5-dc6e-41c5-89fa-45594cd0bb09` |
| cwd | `C:\tmp\dabbler-log-harvest\synthetic-set` |
| turn_index | 0 |
| length(assistant_response) | **48 bytes** |
| assistant_response | `**Workspace root files:**\n- `AGENTS.md`\n- `docs`` |
| Marker present? | **NO** |

This contradicts the design's §5.1 input-shape claim that the
Copilot harvester reads from `session-store.db turns`. The DB
captures something — but not the marker text the LLM emitted to
stdout.

Hypothesized cause (confirmed circumstantially by the process
log showing **two** "Sending request to the AI model" round-
trips in one turn): Copilot 1.0.51 makes two model calls per
turn — one for the marker-emission step, one for the final
output — and persists only the final round-trip's text as
`assistant_response`. Worth confirming with deeper OTel probing
in S5 if the harvester architecture needs the precise
mechanism, but the empirical fact stands: **the marker does not
survive to `assistant_response`**.

#### 3.2 OTel JSONL — marker PRESENT (with content capture ON)

Run 2's `c:\tmp\dabbler-log-harvest\otel\smoke-probe.jsonl`:

- 10 lines total; 223 KB.
- 9 distinct span/metric `name` values: `chat gpt-5.4`,
  `execute_tool report_intent`, `execute_tool view`,
  `invoke_agent`, plus 5 metrics.
- The marker text was found at **2 locations** within line 2
  (the first `chat gpt-5.4` span):
  - `$.attributes.gen_ai.output.messages` — the assistant's
    own output stream as a JSON-encoded array of message
    parts; marker starts at byte offset 57.
  - `$.attributes.gen_ai.system_instructions` — the AGENTS.md
    template echoed back as the system prompt; 38130 chars;
    marker starts at byte offset 29182.

The parser MUST scan `gen_ai.output.messages` and explicitly
NOT `gen_ai.system_instructions` — the latter contains the
instruction template literally (because Copilot's
custom-instructions surface inlines AGENTS.md into the system
prompt), and a parser that scans both would emit a duplicate
phantom marker on every turn.

#### 3.3 Process log — marker absent

`~/.copilot/logs/process-1779468325545-67428.log` contains only
operational events (session start, OTel init, model selection,
MCP connections, compaction stats). No assistant content, no
marker.

#### 3.4 OTel JSONL — bonus discoveries

Line 2's `chat gpt-5.4` span has 20 attributes, including:

| Attribute | Value | S1 inventory status |
|---|---|---|
| `gen_ai.request.model` | `gpt-5.4` | Documented |
| `gen_ai.provider.name` | `github` | Documented |
| `gen_ai.conversation.id` | `4ddea252-...` | Documented |
| `gen_ai.response.finish_reasons` | `['stop']` | New |
| `gen_ai.usage.input_tokens` | 14207 | Documented |
| `gen_ai.usage.output_tokens` | 378 | Documented |
| `gen_ai.usage.cache_read.input_tokens` | 12800 | New |
| **`gen_ai.usage.reasoning.output_tokens`** | **270** | **New — per-turn reasoning signal** |
| `github.copilot.cost` | 1 | New (cost-tracking) |
| `github.copilot.server_duration` | 8992 | New (latency-ms) |
| `github.copilot.turn_id` | `0` | New |
| `github.copilot.interaction_id` | `56480ef0-...` | New |

**No `gen_ai.request.reasoning_effort` attribute observed in
this span** even though the probe ran at default effort
(implicit "medium" per `--effort` defaulting). Two possible
interpretations:
1. The attribute appears only when `--effort` is set
   non-implicitly. Re-test with `--effort high` to confirm.
2. The attribute is absent entirely in Copilot 1.0.51's
   instrumentation; `reasoning.output_tokens` is the proxy
   signal.

`reasoning.output_tokens=270` (i.e., out of 378 total output
tokens, 270 were reasoning chain) IS a native per-turn signal
that distinguishes effort levels at coarse granularity (high
effort → more reasoning tokens). Not as clean as a literal
`high|medium|low` enum, but **it is the closest native
proximate** for the reasoning-axis A3 signal that the design
assumed was absent.

---

### 4. Design implications (to be folded before lock)

#### 4.1 §5.1 — Copilot input shape MUST change

**Before:** "Copilot: `(turn_text, {session_id, turn_index,
timestamp, cwd, host_type})` from `session-store.db turns` +
`sessions` join."

**After:** "Copilot: `(turn_text, {gen_ai.conversation.id,
github.copilot.turn_id, span.startTime, gen_ai.request.model,
gen_ai.provider.name})` from `chat <model>` spans in OTel
JSONL output, where `turn_text` is parsed from
`attributes.gen_ai.output.messages` JSON-array (filter for
`role=assistant, type=text`). REQUIRES
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` on
the Copilot side."

#### 4.2 §5.4 — Parser surface clarification

The parser scans `gen_ai.output.messages` ONLY. It explicitly
SKIPS `gen_ai.system_instructions`, where the template echo
would otherwise produce phantom markers.

#### 4.3 §6 — A3 Copilot branch may flip from B to A

Current draft: Copilot Branch B (narrated). Empirical finding:
`gen_ai.usage.reasoning.output_tokens` IS a native per-turn
signal. Whether it qualifies as "reliable high/medium/low
distinguishing" needs an additional probe with explicit
`--effort high|medium|low` runs to confirm the field's
value range covers the three buckets distinguishably.

S3's deferred live runs include this probe naturally. The
design lock can either:
- (a) Keep Copilot on Branch B (narrated A3) and treat the
  reasoning-tokens count as a *supplementary* native signal
  that the harvester optionally consults, OR
- (b) Defer the Copilot branch selection to S3 live runs
  (`a3_reasoning_source: native|narrated`) — config flag, not
  a contract change.

Recommend (b): the contract supports both branches; the
configuration flag selects.

#### 4.4 §8 — Comparability checklist updates

`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` MUST
be ON for both Copilot baseline AND Copilot narrated runs to
have the marker-bearing surface available for harvest. The
v1 draft had it as "default off both runs unless explicitly
flipped for both" — that has to become "explicitly ON for both
runs" to match the empirical harvester surface.

This is a redaction-cost increase that
baseline-comparison.md §3.2.1 already flagged but treated as
optional: "Copilot defaults to envelope-only; Claude defaults
to inline content... a harvester implementation that targets
'the smallest viable proof on Copilot'... can deliberately
leave Copilot's content-capture flag OFF". The empirical
finding flips this: leaving content-capture OFF makes the
marker invisible to the harvester. The Copilot-first POC's
redaction-cost advantage is partly given back.

#### 4.5 §10.1 — Probe protocol clarification

Step 4 of the probe (verify emission) MUST query OTel JSONL,
not `session-store.db`. The §10.1 text says "Open
`~/.copilot/session-store.db`. Read `turns.assistant_response`
for the new turn" — that's now known to be wrong. The probe
must read `attributes.gen_ai.output.messages` from the `chat
<model>` span in the OTel exporter file.

---

### 5. Decision points for operator

1. **Lock the design WITH harvester-surface revision to OTel?**
   This is the cleanest fit with the empirical reality. Cost:
   `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`
   becomes a required Copilot harvester precondition, with the
   redaction-cost increase that implies.

2. **Or attempt a workaround — relocate the marker to END of
   response so it lands in `assistant_response`?**
   This would re-test whether Copilot's last-LLM-call-only
   persistence captures an end-of-response marker. Risk:
   end-of-response text may be trimmed; the experiment failure
   pattern is the same. Also conflicts with the §3 "first text
   output" placement discipline.

3. **Or hybrid — emit the marker BOTH at start (for OTel) AND
   at end (for session-store.db) so either surface works?**
   Two markers per session; more LLM-discipline risk; minor
   token cost.

4. **A3 branch — pin to narrated (B) now, or defer to a
   per-backend config flag (b)?** Per §4.3 above.

---

### 6. Artifact paths

- Synthetic set: `c:\tmp\dabbler-log-harvest\synthetic-set\`
  - `AGENTS.md` (1114 bytes, full §7.1 instruction, Branch A
    simulated)
  - `docs\session-sets\001-synthetic-harvest-target\spec.md`
  - `docs\session-sets\001-synthetic-harvest-target\session-state.json`
- Run 1 stdout: not preserved (terminal-only).
- Run 2 stdout: not preserved (terminal-only).
- Run 1 DB row: `~/.copilot/session-store.db`, session
  `5ef62da5-dc6e-41c5-89fa-45594cd0bb09`, turn 0.
- Run 2 OTel JSONL: `c:\tmp\dabbler-log-harvest\otel\smoke-probe.jsonl`
  (10 lines, 223 KB; not committed — contains the
  AGENTS.md template echoed in `gen_ai.system_instructions` and
  ~1KB of operator-shaped prompt text in
  `gen_ai.input.messages`; structural metadata only is quoted
  in this results file).

---

### 7. Lock-pending status

The smoke probe demonstrates that:

- ✅ The narration contract (marker emission, format,
  placement, content discipline) is producible by the chosen
  LLM through the chosen channel.
- ✅ The marker survives to a queryable persistent artifact
  (OTel JSONL with content capture ON).
- ⚠️ The persistent artifact identified is NOT the one the
  current draft §5.1 says is the harvester input. Lock
  requires either updating §5.1 to match empirical reality
  (recommended) or revising the placement contract to land
  the marker in `session-store.db assistant_response`
  (riskier; probably same failure mode).

**Recommendation:** apply §4 design implications to
narration-design.md, then lock.
