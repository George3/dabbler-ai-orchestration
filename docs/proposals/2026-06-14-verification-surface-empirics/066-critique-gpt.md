# Set 066 Decomposition Critique — GPT-5.4

Do not adopt this decomposition as proposed. The approved proposal already treats Path-Aware Critique promotion as justified now and routed-fate as data-gated later; this plan defers the former, compresses the latter, and tries to ship a PyPI release in the gap.

## Fork Verdicts

1. **Scope — change.** Deferring Path-Aware Critique integration to 067 is the wrong deferral: the approved proposal makes that the first real product consumer, while the current four-session plan still sprawls by combining adapter hardening, three-provider/tool-loop work, sandboxing, the full forward A/B, routed-policy synthesis, and a release. **Revision:** keep 066 focused on adapter + shipped Path-Aware Critique integration, and move Experiment B plus routed-fate / contract-gate work to 067.

2. **Build-order risk — change.** Building the adapter before the routed-fate A/B is defensible only if 066 also ships the already-justified Path-Aware Critique surface; building it merely to power a later experiment and an immediate package release is backwards. **Revision:** productionize only the pieces needed for the path-aware critique consumer; treat the A/B as a policy study about routed verification, not as the justification for the core Mode-2 engine.

3. **Release timing — blocker.** A PyPI release in S4 is not justified if 066 still defers the first real consumer to 067; that ships unused infrastructure and binds a public release to an unsettled verification-story replan. **Revision:** either do not release in 066, or replace S4's routed-fate/release pairing with Path-Aware Critique integration and release that actual shipped surface.

4. **Multi-provider necessity & feasibility — change.** Multi-provider bindings are genuinely required for the full 2x2 forward design, but S2 is under-scoped: the repo currently has three hard-coded single-shot provider callers, no tool-loop abstraction, and no exercised OpenAI/Gemini bindings. **Revision:** split provider-abstraction / OpenAI / Gemini / sandbox work into separate sessions instead of pretending they fit beside `run_test` in one pass.

5. **A/B sizing — blocker.** The full forward design does not fit one session: Experiment A and Experiment B answer different questions, and Experiment B is its own staged-snapshot intervention study with seeded multi-tree repeats. **Revision:** at minimum split Experiment A and Experiment B into separate sessions; my recommendation is to move Experiment B and the routed keep/demote/retire decision to 067.

6. **Feasibility against the actual code — blocker.** The adapter does not fit the current router as a mere "new provider kind"; the codebase assumes single-shot text completion (`build_prompt` -> `call_model` -> string content) plus text-on-text verification, so a credible plan must budget an explicit agentic-executor seam and a separate trace/result model. **Revision:** add a first-class agentic execution abstraction beside `call_model()` before wiring `router-config.yaml`, verification, or release expectations around it.

7. **Anything unforeseen — change.** The hidden work is not the model calls; it is the disposable sandbox surface, the Full-tier close-out wiring for a new per-set critique attribute, output-capping / cost control for tool results, and rollout mechanics when only some backends support the new loop. **Revision:** treat sandbox lifecycle, gate wiring, and partial-provider rollout as first-class work items with explicit tests and feature-flagged activation.

## Findings

- **Critical** — The proposed set inverts the approved sequencing. The proposal explicitly says it ships no production change, then sequences future work as adapter -> forward A/B -> Path-Aware Critique integration -> routed-fate / contract gate, with steps 1-3 committable now and step 4 data-gated. The decomposition instead defers step 3, collapses step 4 into the same set, and still ships a release. **Refs:** `docs/proposals/2026-06-14-verification-surface-empirics/proposal.md:373-404`. **Fix:** either make 066 a no-release experimental set, or include Path-Aware Critique integration in 066 and move Experiment B plus routed-fate / contract-gate work to 067.

- **Major** — The current router/provider seam is single-shot text completion, not a pluggable agent loop. `route()` builds one prompt and calls `call_model()`, `call_model()` dispatches through three hard-coded provider functions, and verification replays a text prompt against the generated text result. **Refs:** `ai_router/__init__.py:279-406`, `ai_router/providers.py:43-56`, `ai_router/__init__.py:646-756`. **Fix:** budget a dedicated abstraction session that introduces an agentic executor and structured trace/result objects instead of trying to hide a tool loop behind the existing provider API.

- **Major** — Config/bootstrap work is understated. `load_config()` validates API keys for every enabled provider at startup and validates model/provider references eagerly, which is fine for direct text callers but awkward for a partial rollout of a new agentic provider kind. **Refs:** `ai_router/config.py:133-160`. **Fix:** keep the adapter behind an internal or explicitly disabled config path until all supported bindings land, or add a separate config surface for agentic executors rather than overloading the existing provider block.

- **Major** — The supposed "existing gate" is not already a Full-tier Path-Aware Critique gate. The dedicated-verification validator was designed for Lightweight `verificationMode == dedicated-sessions`, and `close_session` only wires it when that mode is present on the set-terminal close. **Refs:** `ai_router/dedicated_verification.py:1-18`, `ai_router/dedicated_verification.py:70-89`, `ai_router/dedicated_verification.py:799-885`, `ai_router/close_session.py:1708-1739`. **Fix:** give Full-tier path-aware critique attribute + close-out wiring its own explicit session; do not count it as "already handled" by the existing gate.

- **Major** — The disposable `run_test` sandbox is new work, not a thin reuse of the current worktree module. `ai_router.worktree` is a canonical session-set worktree CLI for long-lived sibling worktrees, not an ephemeral per-tool-call sandbox manager. **Refs:** `ai_router/worktree.py:13-54`, `ai_router/tests/test_worktree.py:1-34`. **Fix:** design a separate throwaway sandbox helper with creation, cleanup, timeout, and path-confinement tests, then let the adapter call that helper.

- **Major** — S3 massively underestimates the forward study. The design explicitly separates Experiment A from Experiment B, calls for a 2x2 factorial, K repeats on agentic arms, and a first pass of roughly 20-30 seeded defects across 4-6 frozen trees. **Refs:** `docs/session-sets/065-verification-surface-empirics/forward-ab-design.md:41-103`, `docs/session-sets/065-verification-surface-empirics/forward-ab-design.md:119-141`. **Fix:** split the experiments, or move Experiment B to a follow-on set.

- **Minor** — The decomposition treats OpenAI/Gemini bindings as routine follow-ons, but the spike explicitly says only Anthropic was exercised and that the other bindings were merely analogous, unrun designs. **Refs:** `docs/session-sets/065-verification-surface-empirics/spike-report.md:80-81`, `docs/session-sets/065-verification-surface-empirics/spike-report.md:163-180`. **Fix:** do not budget OpenAI + Gemini + sandbox + config wiring as one session.

- **Minor** — If you accept the more realistic split, 066 moves out of the guide's 2-4 session "typical band" and into the 5+ zone that needs clear synthesis points. **Refs:** `docs/planning/session-set-authoring-guide.md:191-195`. **Fix:** either give 066 an explicit multi-session DAG with named synthesis boundaries, or push Experiment B to 067 to keep 066 legible.

## Recommended Decomposition

Adopt a revised two-set plan, not the proposed four-session release set.

**Set 066 — build and ship the Mode-2 capability that is already justified**

1. **S1 — Agentic executor seam + Anthropic adapter core.** Extract a real agentic-executor abstraction inside `ai_router`, harden the Anthropic read-only loop, force the `sN-issues.json` verdict shape, and persist tool-call traces. No public release yet.
2. **S2 — OpenAI binding.** Add the OpenAI tool-loop implementation against the new abstraction, with output caps, trace coverage, and adapter-focused tests.
3. **S3 — Gemini binding + disposable `run_test` sandbox.** Add the Gemini binding, introduce an explicit throwaway test-sandbox helper, and wire guarded `run_test` support with cleanup tests.
4. **S4 — Path-Aware Critique workflow integration.** Add the per-set attribute / Full-tier close-out wiring / docs/tests so the adapter has a real shipped consumer.
5. **S5 — Experiment A only + synthesis.** Run the capability study on the shipped adapter, publish `ab-results.md` for Experiment A, and decide whether the new surface is clean enough to release. If it is, this is the release session; if not, no PyPI tag yet.

**Set 067 — finish the routed-policy question**

1. **S1 — Experiment B (cadence).** Run the staged-snapshot intervention study.
2. **S2 — Routed keep / demote / retire recommendation + contract-gate follow-on.** Use the now-complete A+B evidence to decide routed's fate and scope the contract-test / CDC gate accordingly.

## BOTTOM LINE

The current decomposition is trying to do three different jobs at once: invent a new execution abstraction, answer a two-part research question, and ship a package release. Pick two. My recommendation is: use 066 to build the adapter and ship Path-Aware Critique as the real consumer, then use 067 to run Experiment B and decide what happens to routed verification.