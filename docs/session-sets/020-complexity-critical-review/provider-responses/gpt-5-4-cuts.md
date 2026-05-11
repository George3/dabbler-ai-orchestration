# GPT-5.4 complexity audit

**Model:** gpt-5-4 (gpt-5.4)
**Task type:** session-verification / analysis
**Cost:** $0.1954 (total: $0.1954)
**Tokens in/out:** 8757 / 11568
**Elapsed:** 177.6s
**Complexity score:** 70

## Response

{
  "overall_complexity_score": 7,
  "overall_verdict": "The repo is functional and mostly principled, but the steady-state surface is broader than it needs to be because platform-only, recovery-only, and onboarding-only concerns leak into the default docs and config.",
  "buckets": {
    "A": {
      "load_bearing": 9,
      "lightweight_consumer_cost": "high",
      "no_uat_e2e_consumer_cost": "high",
      "cuts": [
        {
          "what": "Split the mandatory session lifecycle from gated appendices for UAT/E2E, outsource-last, and verifier-disagreement detail.",
          "file": "docs/ai-led-session-workflow.md",
          "rationale": "A 1,752-line single read path forces every consumer through branches that many will never execute.",
          "risk": "medium"
        },
        {
          "what": "Move reference-only material such as parallel trigger phrase variants and orchestrator-switching instructions out of the core workflow.",
          "file": "docs/ai-led-session-workflow.md",
          "rationale": "Invocation phrasing and operator reference material do not need to live in the per-session operating manual.",
          "risk": "low"
        },
        {
          "what": "Replace repeated prose about requiresUAT/requiresE2E/uatStyle/uatScope/outsourceMode with one compact gating matrix.",
          "file": "docs/ai-led-session-workflow.md",
          "rationale": "The same branching logic currently appears in multiple sections, which increases reading cost and drift risk.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep one canonical ordered session procedure.",
          "rationale": "A single source of truth for Steps 0–10 is load-bearing for consistent orchestration behavior."
        },
        {
          "what": "Keep the explicit adjudication ladder and record_adjudication() requirement.",
          "rationale": "Cross-provider verification only stays auditable if verifier disagreements have a standard, logged resolution path."
        }
      ]
    },
    "B": {
      "load_bearing": 7,
      "lightweight_consumer_cost": "medium",
      "no_uat_e2e_consumer_cost": "medium",
      "cuts": [
        {
          "what": "Extract 'When UAT is required', 'When E2E is required', and 'Choosing uatStyle' into a gated appendix or repo addendum.",
          "file": "docs/planning/session-set-authoring-guide.md",
          "rationale": "The default spec-authoring path is non-UAT, so the universal guide should bias hard toward requiresUAT:false.",
          "risk": "low"
        },
        {
          "what": "Collapse config-block field semantics into a single table and link out for behavior details.",
          "file": "docs/planning/session-set-authoring-guide.md",
          "rationale": "The authoring guide and workflow doc currently duplicate flag explanations in slightly different prose.",
          "risk": "medium"
        },
        {
          "what": "Move the dabbler-platform migration note out of the universal authoring guide.",
          "file": "docs/planning/session-set-authoring-guide.md",
          "rationale": "Consumer-specific migration history is not steady-state authoring guidance.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep explicit invalid-combination rules in the authoring guide.",
          "rationale": "Rejecting bad specs at authoring time is cheaper than teaching the orchestrator more runtime branching."
        },
        {
          "what": "Keep the named anti-patterns section.",
          "rationale": "Those rules compress a lot of failure experience into fast authoring guidance."
        }
      ]
    },
    "C": {
      "load_bearing": 5,
      "lightweight_consumer_cost": "low",
      "no_uat_e2e_consumer_cost": "low",
      "cuts": [
        {
          "what": "Create separate Lightweight and Full adoption prompts instead of one heavily branched bootstrap flow.",
          "file": "docs/adoption-bootstrap.md",
          "rationale": "The current document mixes two materially different adoption experiences into one decision tree.",
          "risk": "medium"
        },
        {
          "what": "Move the seven-pattern organization catalog to an appendix or optional examples section.",
          "file": "docs/adoption-bootstrap.md",
          "rationale": "Pattern cataloging is helpful but not essential to the core bootstrap transaction.",
          "risk": "low"
        },
        {
          "what": "Turn the State B sub-path branching into a compact decision table.",
          "file": "docs/adoption-bootstrap.md",
          "rationale": "This is structured choice logic, and prose branching is more verbose than necessary.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep the explicit early adoption-tier choice.",
          "rationale": "Lightweight versus Full is a first-order fork that should be decided before any later setup work."
        },
        {
          "what": "Keep the operator review/edit/batch-approve checklist step.",
          "rationale": "That pause prevents bootstrap automation from overcommitting a new project into the wrong shape."
        }
      ]
    },
    "D": {
      "load_bearing": 8,
      "lightweight_consumer_cost": "none",
      "no_uat_e2e_consumer_cost": "high",
      "cuts": [
        {
          "what": "Split --repair and --repair --apply into a separate repair CLI so close_session.py only handles the normal close-out state machine.",
          "file": "ai_router/close_session.py",
          "rationale": "Operational remediation paths materially expand the branching and failure surface of the main command.",
          "risk": "medium"
        },
        {
          "what": "Retire --manual-verify once all active Full-tier consumers have stable verification paths.",
          "file": "ai_router/close_session.py",
          "rationale": "Bootstrapping escape hatches tend to become permanent complexity taxes if they are never sunset.",
          "risk": "medium"
        },
        {
          "what": "Extract outsource-last queue polling and timeout handling into a dedicated helper/module.",
          "file": "ai_router/close_session.py",
          "rationale": "Platform-only queue behavior should not dominate the universal close-out implementation.",
          "risk": "low"
        },
        {
          "what": "Consolidate missing disposition.json handling to one validation point.",
          "file": "ai_router/close_session.py, ai_router/gate_checks.py",
          "rationale": "The current dual-path failure reporting adds branching without clear functional gain.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep --force double-gated by env var and reason file.",
          "rationale": "Incident recovery is rare but real, and the current safeguards are appropriate for a destructive bypass."
        },
        {
          "what": "Keep the file lock and deterministic gate checks.",
          "rationale": "Close-out is the synchronization barrier, so correctness matters more than elegance here."
        },
        {
          "what": "Keep structured disposition.json as a required close-out artifact.",
          "rationale": "The handoff and audit trail are materially better with a machine-validatable disposition than with freeform notes."
        }
      ]
    },
    "E": {
      "load_bearing": 8,
      "lightweight_consumer_cost": "none",
      "no_uat_e2e_consumer_cost": "high",
      "cuts": [
        {
          "what": "Delete schema-v1 compatibility and the backfill utility after confirming all active consumers are on v2.",
          "file": "ai_router/session_state.py, ai_router/backfill_session_state.py",
          "rationale": "Completed migrations should not leave permanent compatibility branches in the runtime path.",
          "risk": "low"
        },
        {
          "what": "Move dump_session_state_schema.py out of the shipped runtime package into scripts or docs tooling.",
          "file": "ai_router/dump_session_state_schema.py",
          "rationale": "Schema-dump tooling is a maintenance utility, not core session-state behavior.",
          "risk": "low"
        },
        {
          "what": "Consider deriving session-state.json from session-events.jsonl instead of persisting both artifacts.",
          "file": "ai_router/session_state.py, ai_router/session_events.py",
          "rationale": "Maintaining both a ledger and a mutable snapshot is the main source of drift and repair complexity.",
          "risk": "high"
        }
      ],
      "defenses": [
        {
          "what": "Keep the append-only session-events ledger.",
          "rationale": "For auditability and repair, the immutable event history is the more valuable artifact."
        },
        {
          "what": "Keep a consumer-readable snapshot cache unless on-demand derivation is proven fast enough.",
          "rationale": "The extension benefits from a simple readable state file even if it duplicates derived data."
        },
        {
          "what": "Keep next_orchestrator validation for non-final completed sessions.",
          "rationale": "That requirement directly supports orderly handoff across multi-session sets."
        }
      ]
    },
    "F": {
      "load_bearing": 7,
      "lightweight_consumer_cost": "none",
      "no_uat_e2e_consumer_cost": "medium",
      "cuts": [
        {
          "what": "Collapse the public task taxonomy from 13 types to a smaller set of coarse classes by merging low-use categories like formatting, summarization, documentation, analysis, planning, and refactoring.",
          "file": "ai_router/router-config.yaml",
          "rationale": "The routing taxonomy is broader than observed steady-state use and creates ongoing config and model-selection overhead.",
          "risk": "medium"
        },
        {
          "what": "Replace the four-weight complexity heuristic with per-task default tiering plus explicit hints and the existing one-step escalation.",
          "file": "ai_router/router-config.yaml, ai_router/__init__.py",
          "rationale": "The repo already states that heuristic refinement is a non-goal, so the heuristic itself is a prime candidate for simplification.",
          "risk": "medium"
        },
        {
          "what": "Move UAT-specific task types into a gated platform-only routing extension.",
          "file": "ai_router/router-config.yaml",
          "rationale": "Non-UAT consumers currently pay config surface for platform-only routing behavior.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep the explicit session-verification cross-provider model pin.",
          "rationale": "Verification independence is central enough that it should stay explicit rather than heuristic."
        },
        {
          "what": "Keep adjudication logging in router metrics.",
          "rationale": "Those records are one of the few feedback loops that can justify or falsify routing policy choices."
        },
        {
          "what": "Keep one-step escalation.",
          "rationale": "A small, bounded fallback is a practical guardrail without turning routing into a retry maze."
        }
      ]
    },
    "G": {
      "load_bearing": 4,
      "lightweight_consumer_cost": "low",
      "no_uat_e2e_consumer_cost": "low",
      "cuts": [
        {
          "what": "Stop describing adoption and budget as a matrix; document Lightweight as a separate mode and budget tiers only inside the Full path.",
          "file": "docs/adoption-bootstrap.md",
          "rationale": "The current framing explains a matrix that largely collapses immediately, which adds terminology more than capability.",
          "risk": "low"
        },
        {
          "what": "Remove the adoption-vs-budget disambiguation paragraph from the mandatory workflow read path.",
          "file": "docs/ai-led-session-workflow.md",
          "rationale": "Bootstrap taxonomy does not need to be revisited every session by already-adopted repos.",
          "risk": "low"
        },
        {
          "what": "Merge middle and ample if they do not drive meaningfully different routing policy in practice.",
          "file": "docs/adoption-bootstrap.md",
          "rationale": "Four budget labels are only worth keeping if they map to materially distinct behavior, not just descriptive nuance.",
          "risk": "medium"
        }
      ],
      "defenses": [
        {
          "what": "Keep the explicit Lightweight versus Full adoption choice.",
          "rationale": "That distinction is one of the clearest and most useful simplifications already present in the system."
        },
        {
          "what": "Keep $0 as a distinct Full-tier budget option.",
          "rationale": "A no-paid-API Full mode is meaningfully different from Lightweight because it still preserves the rest of the orchestration machinery."
        }
      ]
    },
    "H": {
      "load_bearing": 6,
      "lightweight_consumer_cost": "medium",
      "no_uat_e2e_consumer_cost": "medium",
      "cuts": [
        {
          "what": "Derive uatScope:none from requiresUAT:false and remove none as an explicit spec value.",
          "file": "docs/ai-led-session-workflow.md, docs/planning/session-set-authoring-guide.md",
          "rationale": "This removes one state and one category of needless config verbosity without reducing expressiveness.",
          "risk": "low"
        },
        {
          "what": "If ad-hoc UAT remains unused, move Rule 11b and its ProgrammaticVerification/NoProgrammaticPathReason mechanics into a dormant addendum until first production adoption.",
          "file": "docs/ai-led-session-workflow.md, docs/planning/session-set-authoring-guide.md",
          "rationale": "A second UAT regime in the universal path is costly if no active consumer is exercising it.",
          "risk": "medium"
        },
        {
          "what": "Make uatStyle a repo/addendum default with per-set override only for exceptions.",
          "file": "docs/ai-led-session-workflow.md, docs/planning/session-set-authoring-guide.md",
          "rationale": "Per-spec style selection adds decision surface even though a repo will usually have one dominant mode.",
          "risk": "medium"
        }
      ],
      "defenses": [
        {
          "what": "Keep requiresUAT and requiresE2E as spec-level gates.",
          "rationale": "Those flags embody the repo philosophy of gated extensions instead of hidden repo-specific assumptions."
        },
        {
          "what": "Keep the explicit rejection of uatStyle:\"dsl\" with requiresE2E:false.",
          "rationale": "That invalid-combination rule prevents silent weakening of the DSL verification contract."
        },
        {
          "what": "Keep DSL Playwright parity requirements for platform.",
          "rationale": "For a real UI consumer, that is the substantive value of having a DSL path at all."
        }
      ]
    },
    "I": {
      "load_bearing": 6,
      "lightweight_consumer_cost": "medium",
      "no_uat_e2e_consumer_cost": "medium",
      "cuts": [
        {
          "what": "Split queue/heartbeat views and queue actions into an optional platform-only extension contribution.",
          "file": "tools/dabbler-ai-orchestration/src/queueActions.ts, tools/dabbler-ai-orchestration/src/ProviderQueuesProvider.ts, tools/dabbler-ai-orchestration/src/ProviderHeartbeatsProvider.ts",
          "rationale": "outsourceMode:last is a single-consumer specialization and should not shape the default extension surface.",
          "risk": "medium"
        },
        {
          "what": "Hide or remove the ai_router install command in Lightweight workspaces.",
          "file": "tools/dabbler-ai-orchestration/src/commands/installAiRouterCommands.ts",
          "rationale": "Lightweight users should not be nudged toward Python tooling they intentionally do not adopt.",
          "risk": "low"
        },
        {
          "what": "Consider separating the Cost Dashboard from the core Explorer extension if Lightweight adoption becomes real.",
          "file": "tools/dabbler-ai-orchestration/src/CostDashboard.ts",
          "rationale": "Cost telemetry is valuable for Full-tier users but not part of the minimum Explorer-only product.",
          "risk": "medium"
        }
      ],
      "defenses": [
        {
          "what": "Keep SessionSetsProvider as the shared core extension surface.",
          "rationale": "The Explorer is the one extension feature that clearly serves all adoption tiers."
        },
        {
          "what": "Keep the trigger-phrase copy command.",
          "rationale": "It packages canonical workflow entry points into a very low-complexity convenience."
        },
        {
          "what": "Keep the adoption bootstrap prompt command.",
          "rationale": "Onboarding usability matters, even if the bootstrap doc itself should be slimmer."
        }
      ]
    },
    "J": {
      "load_bearing": 2,
      "lightweight_consumer_cost": "none",
      "no_uat_e2e_consumer_cost": "none",
      "cuts": [
        {
          "what": "Trim MEMORY.md to a rolling index and archive older entries so the loaded context stays well below the truncation threshold.",
          "file": "~/.claude/projects/<repo>/memory/MEMORY.md",
          "rationale": "Once prompt loading truncates, extra memory entries become unmanaged noise rather than useful recall.",
          "risk": "low"
        },
        {
          "what": "Delete feedback memories that merely restate rules already enforced by the workflow docs.",
          "file": "~/.claude/projects/<repo>/memory/feedback/*",
          "rationale": "Duplicating canonical process rules in memory creates another source of truth that can drift.",
          "risk": "low"
        },
        {
          "what": "Move consumer-specific project state out of this repo's memory and into each consumer repo's own memory.",
          "file": "~/.claude/projects/<repo>/memory/project/*",
          "rationale": "The orchestration repo memory should hold orchestration facts, not a secondary cross-repo project tracker.",
          "risk": "low"
        }
      ],
      "defenses": [
        {
          "what": "Keep durable operator-preference and sharp failure-mode memories.",
          "rationale": "A small amount of stable memory reduces repeated operator correction without changing repo code or docs."
        },
        {
          "what": "Keep memory outside the repo.",
          "rationale": "This is an operator aid, and it should not be promoted into shared repository complexity."
        }
      ]
    }
  }
}
