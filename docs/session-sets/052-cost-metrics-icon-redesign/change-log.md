# Set 052 Change Log

**Cost-metrics icon redesign — audit + cross-provider design-lock,
read-path root-cause fix, router-capability tier gate, in-extension
staleness banner, three honest dashboard states, docs + UAT + version
bump, cross-provider verification of the implementation. TS-only — no
companion PyPI release. Marketplace publish (`vsix-v0.27.0`) held for
operator tag-push.**

This set fixes the "dead" cost-dashboard icon. The audit (S1) re-diagnosed
the symptom: the icon was not dead because a flag was off — it was a
**read/write path mismatch**. The Python AI router *writes* metrics to
`ai_router/router-metrics.jsonl` (configurable via `metrics.log_filename`),
but the dashboard *read* a hardcoded `ai_router/metrics.jsonl` it never
wrote to, so the panel was always empty and rendered a placeholder telling
the operator to set `METRICS_ENABLED = True` — a **fictional** flag
(`config.py METRICS_ENABLED` does not exist; the real knob,
`metrics.enabled` in `router-config.yaml`, already defaults ON).

The 3-session arc: audit + design-lock (S1) → implementation (S2) → docs,
UAT, version bump, verification, close-out (S3).

## Session 1 — Audit & design-lock

Closed 2026-05-30 with disposition `completed`. Routed: $0.048427 (consensus).

- Mapped the cost path (`CostDashboard.ts`, `utils/metrics.ts`,
  `metrics.py`, `cost_report.py`, `router-config.yaml`) and found the
  root cause: read/write path mismatch, not a disabled flag. Confirmed
  metrics already default ON and the placeholder's `config.py
  METRICS_ENABLED` flag is fictional; staleness infra already exists
  (`metadata.pricing_reviewed` + `review_frequency_days` +
  `config.py:_check_pricing_staleness`).
- Ran cross-provider consensus (gemini-2.5-pro + gpt-5.4) on the five open
  questions. Genuine split on Q4 (tier detection): resolved to a
  **router-capability** gate (resolvable `router-config.yaml`), NOT a
  per-set `tier:` field and NOT bare folder existence — the latter would
  re-create the dead icon on a Lightweight repo that merely has an empty
  `ai_router/`.
- Locked the design (D1–D8) in
  [`docs/proposals/2026-05-29-cost-metrics-icon/{proposal,verdict}.md`](../../proposals/2026-05-29-cost-metrics-icon/);
  updated [`spec.md`](spec.md). UAT **elected** at session start
  (`suggestion_disposition: uat`).

## Session 2 — Implementation (verdict D1–D7)

Closed 2026-05-30 with disposition `completed`. Routed: $0.00 (pure TS + unit tests).

- **D1 (root cause):** new shared
  [`src/utils/routerConfig.ts`](../../../tools/dabbler-ai-orchestration/src/utils/routerConfig.ts)
  resolves the metrics filename from `metrics.log_filename` (default
  `router-metrics.jsonl`); `utils/metrics.ts` (`readMetrics` +
  `readMetricsFromPath`) and the CSV export both route through it — no
  second hardcoded name. `MetricsEntry` reconciled to the on-disk schema
  (`session_number` not the never-emitted `session_num`; optional
  `call_type`; reader drops zero-cost `adjudication` rows).
- **D3 (tier gate):** `dabblerSessionSets.routesCost` context key set in
  `extension.ts` (`evaluateRouterCapabilityContextKey`) from a resolvable
  workspace `ai_router/router-config.yaml`; `package.json` gates both the
  `view/title` icon and the Command-Palette entry. Absent on Lightweight.
- **D4 (staleness):** `computeStaleness()` reuses `metadata.pricing_reviewed`
  + `review_frequency_days` (default 30; missing/invalid = stale), computed
  in-extension; non-blocking banner with an "Update cost estimates" action.
- **D5 (three honest states):** disabled (names the real `metrics.enabled`
  knob, never the fictional flag) / on-but-empty / on-with-data + a
  defensive no-router state, via pure
  [`src/dashboard/dashboardHtml.ts`](../../../tools/dabbler-ai-orchestration/src/dashboard/dashboardHtml.ts)
  builders; `CostDashboard` is now a `selectCostState` state machine.
- **D6:** update-rates opens `router-config.yaml` at the `metadata` /
  `metrics` anchor; CSP-safe button wiring. No Config Editor pricing
  section (not cheap; declined). **D2:** no metrics-default change (already on).
- **D7 (tests):** `routerConfig.test.ts`, `dashboardHtml.test.ts`,
  `costDashboardGate.test.ts`, `metrics.test.ts` schema update. The planned
  Layer-3 Playwright icon smoke was **pivoted** to the deterministic
  `costDashboardGate.test.ts` manifest guard (VS Code `view/title` actions
  duplicate-render + overflow → non-deterministic to assert in Playwright;
  flagged for the S3 verifier). Watcher allowlist line bumped 153→172.

## Session 3 — Docs, UAT, version bump, verification, close-out

Closed 2026-05-30 with disposition `completed`. Routed: $0.017121 (verification).

- **Docs reconciled.** No live human-facing doc referenced the fictional
  flag (S2 already removed it from `webview/dashboard.html`); the read-path
  was already documented as `router-metrics.jsonl` in
  `adoption-bootstrap.md`. Updated
  [`docs/repository-reference.md`](../../repository-reference.md) and the
  extension [`README.md`](../../../tools/dabbler-ai-orchestration/README.md)
  to describe the new behavior (router-capability gating, staleness prompt,
  three honest states).
- **UAT checklist** compiled (elected at S1):
  [`052-cost-metrics-icon-redesign-uat-checklist.json`](052-cost-metrics-icon-redesign-uat-checklist.json)
  — 16 items; programmatically-verifiable items marked complete with the
  test path, live-VS-Code items (icon render, painted banner, editor
  reveal) left pending for manual operator UAT post-publish. The live
  icon-visibility items are precisely the coverage the S2 D7 pivot deferred.
- **Version bump.** Extension `0.26.1` → **`0.27.0`** (feature set;
  `package.json` + `package-lock.json` both nodes), `CHANGELOG.md` 0.27.0
  entry, `CLAUDE.md` version-walk cascade. TS-only — no PyPI release.
- **Cross-provider verification** of the S2 code by `gemini-2.5-pro`
  (different provider): **VERIFIED_WITH_NOTES** — 0 critical, 0 blocking;
  **both flagged deviations APPROVED** (the D7 manifest-guard pivot judged
  "superior … stronger, more reliable coverage … without the flakiness of
  an E2E test"; the schema reconciliation judged "not scope creep but a
  necessary part of a complete fix"). One nice-to-have (a `YYYY-MM-DD`
  date-format clarification comment in `computeStaleness`) addressed
  in-flight — the only code change S3 made to S2's implementation
  (comment-only, behavior-preserving). Record:
  [`s3-verification.md`](s3-verification.md).

## Test & suite state at close

- `tsc --noEmit` clean; `npm run test:unit` **584 passing / 2 failing** —
  the 2 are the known pre-existing Set-026 stub-harness failures
  (`configEditor-foundation` panel lifecycle; `notificationsSection`
  rendering) in files this set did not touch.

## Cost

Cumulative Set 052 routed: **$0.065548 of $10 NTE (0.66%)**
($0.048427 S1 consensus + $0.017121 S3 verification; S2 routed $0).

## Publishes (held for operator tag-push)

- **Marketplace** `vsix-v0.27.0` — push the `vsix-v0.27.0` tag to trigger
  `publish-vscode.yml`. **Confirm `VSCE_PAT` freshness first** — it expired
  during the 0.24.0 publish.
- **No PyPI release** this set (TS-only; `ai_router` untouched).
