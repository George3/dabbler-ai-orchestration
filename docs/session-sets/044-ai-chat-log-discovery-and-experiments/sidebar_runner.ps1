# Set 044 Session 5 — Copilot effort sidebar runner
#
# Operator-driven matched-pair Copilot runs at --effort low and --effort high
# against the synthetic-set, with the same task battery as S4a baseline.
#
# Purpose:
#   - Close design §11 Q3: does gen_ai.request.reasoning_effort attribute
#     appear in OTel output at --effort low or --effort high (it was OMITTED
#     at --effort medium in S4a)?
#   - Close design §11 Q4: do gen_ai.usage.reasoning.output_tokens values
#     distinguish low/medium/high effort buckets?
#
# Inputs (none — fixed env + workspace + task battery)
# Outputs:
#   c:/tmp/dabbler-log-harvest/otel/s5-sidebar-low.jsonl
#   c:/tmp/dabbler-log-harvest/otel/s5-sidebar-high.jsonl
#   c:/tmp/s5-sidebar-low-stdout.txt + -stderr.txt
#   c:/tmp/s5-sidebar-high-stdout.txt + -stderr.txt
#
# Cost: zero router dollars (Copilot subprocess only).
#
# Run from any cwd; the script handles paths absolutely.

$ErrorActionPreference = 'Stop'

$WORKSPACE = 'C:/tmp/dabbler-log-harvest/synthetic-set'
$OTEL_DIR  = 'C:/tmp/dabbler-log-harvest/otel'
$STATE_PATH = Join-Path $WORKSPACE 'docs/session-sets/001-synthetic-harvest-target/session-state.json'

# Pristine session-state.json shape (matches S4a pre-run reset)
$PRISTINE_STATE = @'
{
  "schemaVersion": 3,
  "sessionSetName": "001-synthetic-harvest-target",
  "sessions": [
    {
      "number": 1,
      "title": "List workspace files",
      "status": "not-started"
    },
    {
      "number": 2,
      "title": "Read the spec",
      "status": "not-started"
    }
  ],
  "currentSession": null,
  "totalSessions": 2,
  "completedSessions": [],
  "status": "in-progress",
  "lifecycleState": "ready_to_start",
  "startedAt": null,
  "completedAt": null,
  "verificationVerdict": null,
  "orchestrator": null
}
'@

# Identical 5-task battery from S4a §3.
$TASK_BATTERY = @'
Please do the following five tasks in order against this workspace and tell me what you found:

1. List files in this workspace root.
2. Read docs/session-sets/001-synthetic-harvest-target/spec.md and report how many sessions it defines.
3. Read docs/session-sets/001-synthetic-harvest-target/session-state.json and report the value of the top-level status field.
4. Use an edit tool to change docs/session-sets/001-synthetic-harvest-target/session-state.json so that the top-level status field is "in-progress" instead of "not-started". Do this as a direct file edit; do NOT call start_session.
5. Run the bash command: python -m ai_router.start_session --help and report whether the help text mentions --force.

Stop after these five tasks.
'@

function Reset-PristineState {
    Set-Content -Path $STATE_PATH -Value $PRISTINE_STATE -NoNewline -Encoding UTF8
    Write-Host "Reset session-state.json to pristine not-started shape."
}

function Invoke-CopilotRun {
    param(
        [Parameter(Mandatory)] [string] $Effort,
        [Parameter(Mandatory)] [string] $OutPath,
        [Parameter(Mandatory)] [string] $StdoutPath,
        [Parameter(Mandatory)] [string] $StderrPath
    )

    Write-Host ""
    Write-Host "=== Copilot run: --effort $Effort ==="
    Write-Host "OTel output: $OutPath"

    $env:COPILOT_OTEL_FILE_EXPORTER_PATH = $OutPath
    $env:COPILOT_OTEL_ENABLED            = 'true'
    $env:COPILOT_OTEL_EXPORTER_TYPE      = 'file'
    $env:OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = 'true'

    # --no-custom-instructions to match S4a baseline: suppress AGENTS.md
    # (none authoritative here anyway — S4b stashed it as
    # AGENTS.md.copilot-stashed — but explicit is safer).
    copilot `
        -C $WORKSPACE `
        --model gpt-5.4 `
        --effort $Effort `
        --no-custom-instructions `
        --allow-all-tools `
        --allow-all-paths `
        -s `
        -p $TASK_BATTERY `
        > $StdoutPath 2> $StderrPath

    Write-Host "Exit code: $LASTEXITCODE"
    Write-Host "Stdout:    $StdoutPath"
    Write-Host "Stderr:    $StderrPath"
}

# --- Run 1: --effort low ---
Reset-PristineState
Invoke-CopilotRun -Effort low `
    -OutPath    (Join-Path $OTEL_DIR 's5-sidebar-low.jsonl') `
    -StdoutPath 'C:/tmp/s5-sidebar-low-stdout.txt' `
    -StderrPath 'C:/tmp/s5-sidebar-low-stderr.txt'

# --- Run 2: --effort high ---
Reset-PristineState
Invoke-CopilotRun -Effort high `
    -OutPath    (Join-Path $OTEL_DIR 's5-sidebar-high.jsonl') `
    -StdoutPath 'C:/tmp/s5-sidebar-high-stdout.txt' `
    -StderrPath 'C:/tmp/s5-sidebar-high-stderr.txt'

Write-Host ""
Write-Host "=== Sidebar complete ==="
Write-Host "Hand the OTel JSONL paths back to Claude for parsing."
