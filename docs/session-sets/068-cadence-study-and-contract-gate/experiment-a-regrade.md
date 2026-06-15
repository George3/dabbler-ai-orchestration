# Experiment A — Symmetric Re-grade (Set 068 S2)

> **Purpose:** Settle the H1-magnitude / H2 question the Set 067 `ai_router`
> 0.21.1 erratum opened (`experiment-a-results.md` §8). The original Experiment A
> manual audit was **one-directional** — the strict "names the actual mechanism"
> rule was applied only to **routed × cross-file** catches (to *subtract* routed
> credits), while **path-aware × cross-file** catches were taken as
> evidence-grounded and never held to the same standard. This re-grade applies the
> **identical** strict rule to both arms and recomputes the contrasts on the
> **pre-registered automated primary** metric (not only the audit-dependent union),
> so any Set-068 reasoning rests on what the data actually establishes.
>
> **Created:** 2026-06-15 (Session 2). **Method:** deterministic, no new API
> calls — re-analysis of the committed Set 067 raw outputs.
> **Reproduce:** `python docs/session-sets/068-cadence-study-and-contract-gate/experiment-a-regrade/regrade.py`
> (reads `../067-…/experiment-a/{catalogue,audit}.json` + `raw/` and this set's
> `experiment-a-regrade/audit-symmetric.json`; writes `experiment-a-regrade-data.json`).

---

## 1. Headline

**H1 *direction* is CONFIRMED and survives on audit-independent evidence. H1
*magnitude* is metric-sensitive but positive everywhere:** the **GPT** contrast
exceeds the noise band under **every** regime (audit-free primary **+0.2315**,
symmetric mechanism-audited replicate-mean **+0.2870**, symmetric union +0.25);
the **Gemini** contrast is **within the band under the pre-registered automated
primary (+0.0833 < 0.111)** — unresolved there — **but resolves to +0.2778
(exceeds band) once routed's wrong-mechanism cross-file credits are removed at the
replicate level** (the symmetric mechanism-audited metric). In other words, the
Gemini "within-band" result is an **artifact of the automated grade crediting
routed with cross-file matches that do not name the mechanism**; held to the same
"name the mechanism" standard as everything else, both same-provider contrasts
resolve. The **H2** reading splits: "a second routed provider adds nothing" is
**robust and audit-independent** (`A1_auto == A2_auto`, +0.0000); the specific
+0.31 union *magnitude* is union/audit-dependent and is downgraded to exploratory.

This concurs with the 0.21.1 erratum and tightens it on two points (§5).

---

## 2. What the symmetric audit changed

The original routed audit removed **6 of 8** routed cross-file credits
(`A1:D9, A2:D9, A2:D10, A1:D13, A2:D13, A2:D6`). Applying the **same** rule to
the path-aware cross-file cells (`audit-symmetric.json`, with quotes) removes
exactly **one**:

- **`B1:D12 = false` (REJECT).** B1's tree3 findings (k1–k3) name `count_statements`
  (D11), `all_refs` dropping the whole call/return-ref category (D9), and
  `build_index` `str(ref)` (D10) — but **never** the seeded D12 mechanism
  (`collect_call_refs` capturing only a single bare-identifier argument via
  `isidentifier()`). The D12 predicate fired only because B1's **D9** finding
  contains the tokens "collect_call_refs … silently dropped." This is the same
  cross-finding token-spillover the routed audit corrected (cf. `A2:D10`
  matching "contra**dict**s", `A1:D13` token spillover). **`B2:D12` is KEPT** —
  B2 k2 explicitly names the `isidentifier()` single-argument limitation.

The other 13 path-aware cross-file cells survive: each names the actual seeded
mechanism (the arm read the omitted file). Full keep/reject quotes:
`experiment-a-regrade/audit-symmetric.json`; raw evidence dump:
`experiment-a-regrade/pathaware-crossfile-evidence.md`.

**Honest symmetry check — cross-file catches surviving the *identical* rule:**

| Side | Survive / automated cross-file credits |
|---|---|
| Routed (A1, A2) | **2 / 8** (25%) — only `A1:D6`, `A1:D10` |
| Path-aware (B1, B2) | **13 / 14** (93%) |

This asymmetry is the substance, not a bias: when both arms are held to "name
the mechanism," path-aware's cross-file catches are overwhelmingly real and
routed's are overwhelmingly token/docstring artifacts. The one-directional audit
inflated the *magnitude*, but symmetric grading still favors path-aware — by a lot.

---

## 3. The contrasts under three regimes

Severity-weighted catch rate (total weight 36). Four regimes:
**automated primary** = pre-registered per-replicate mean ± across-K noise band,
**no audit** (the metric the pre-registration named primary);
**sym mechanism-audited replicate-mean** = the same per-replicate mean but with
**both** mechanism audits applied at the replicate level (the apples-to-apples
mechanism-grounded metric — both arms held to "name the mechanism"); **asym
union** = Set 067's union-over-K with the routed audit only; **sym union** =
union-over-K with both audits.

| Contrast | Regime | Gap | Noise band | Verdict |
|---|---|---:|---:|---|
| **B1−A1 (GPT)** | automated primary (replicate mean) | **+0.2315** | 0.0834 | **EXCEEDS** |
| | sym mechanism-audited replicate-mean | **+0.2870** | 0.0555 | **EXCEEDS** |
| | asym union (067) | +0.3056 | 0.0834 | EXCEEDS |
| | sym union (068) | +0.2500 | 0.0834 | EXCEEDS |
| **B2−A2 (Gemini)** | automated primary (replicate mean) | **+0.0833** | 0.1111 | **INSIDE** |
| | sym mechanism-audited replicate-mean | **+0.2778** | 0.0556 | **EXCEEDS** |
| | asym union (067) | +0.3611 | 0.1111 | EXCEEDS |
| | sym union (068) | +0.3611 | 0.1111 | EXCEEDS |

Per-arm replicate mean (automated → sym-mechanism-audited): A1 0.750→**0.639** ·
A2 0.778→**0.583** · B1 0.981→**0.926** · B2 0.861→**0.861**.

Reading:

- **GPT contrast is robust** — it exceeds the band under *every* regime, including
  the audit-free primary (+0.23) and the symmetric mechanism-audited replicate-mean
  (+0.29). It does not depend on any audit.
- **The Gemini contrast is metric-sensitive, and that is the informative finding.**
  Under the **pre-registered automated primary** it is **within the band**
  (+0.083 < 0.111) — unresolved, exactly as the erratum recorded. But that
  automated grade **credits A2 with four cross-file matches that do not name the
  mechanism** (D6, D9, D10, D13 — the audit rejects three of A2's, all four under
  the symmetric standard), inflating A2's replicate mean to 0.778. Removing those
  wrong-mechanism credits at the **replicate level** (symmetric mechanism-audited
  metric) drops A2 to **0.583** and opens the Gemini gap to **+0.2778**, which
  **exceeds** the (now 0.056) band. So the Gemini magnitude is not "too small" —
  it was **masked by routed false-positive credit**; held to the same standard as
  every other cell, it resolves.
- **Honest caveat on which is primary.** The pre-registration named the
  *automated* grade primary, so the strictly-pre-registered verdict for Gemini is
  "within band / unresolved." The mechanism-audited replicate-mean is a metric
  this re-grade introduces; it is more defensible (it is the only metric that holds
  **both** arms to the mechanism standard) but it is **author-applied audit**, so
  it carries the audit-subjectivity caveat (mitigated by committed per-cell quotes
  and this cross-provider review). Both numbers are reported; **direction holds
  under either**, and the Set-068 work leans on direction, not on the contested
  Gemini magnitude.

---

## 4. H2 (provider-multiplicity vs context-access) — split verdict

- **"A second routed provider buys nothing" — ROBUST, audit-independent.** Under
  the automated grade A1's and A2's catch sets are identical, so
  `routed_pair − best_single_routed = +0.0000`. Adding a second *routed* validator
  closes none of the gap. This half stands without any audit.
- **"Context-access is the larger lever (+0.31)" — DOWNGRADED to exploratory.**
  The `path_aware_pair − routed_pair = +0.3056` figure is union-and-audit-
  dependent. Context-access is **directionally** the bigger lever (and the only one
  that moved the needle at all — a second routed provider added exactly 0), but the
  specific +0.31 *magnitude* is not established by the pre-registered automated
  primary. (Per-provider, the mechanism-audited replicate-mean does resolve both
  same-provider contrasts — GPT +0.29, Gemini +0.28 — but that is the
  audit-dependent metric, §3.)

---

## 5. Two corrections to the erratum (this re-grade tightens it)

1. **Only D5 is a fully audit-independent existence proof — not both Criticals.**
   The erratum stated D5 *and* D9 were "caught by neither routed arm, independent
   of the audit." The re-grade shows routed's automated predicate **did** match
   **D9** for both A1 and A2 (`routed_A1_any_k = routed_A2_any_k = True`). Reading
   the raw, that match is a *wrong-mechanism* false positive — routed flagged that
   `build_index`'s docstring says "superset" while it correctly filters KNOWN refs
   (a docstring nitpick), and **never** saw that `analyzer.all_refs` (omitted file)
   drops call/return refs. So D9 is an existence proof **conditional on the audit**
   (which removes the nitpick), whereas **D5 is unconditional**: routed never
   matched D5 even by automated predicate (`routed_A1_any_k = routed_A2_any_k =
   False`), while both path-aware arms caught it in **all** replicates.
2. **The union magnitude was inflated by the one-directional audit, but the effect
   was not created by it.** Symmetric grading lowers the GPT union gap +0.31→+0.25,
   and the GPT effect persists +0.23 on the audit-free primary and +0.29 on the
   symmetric mechanism-audited replicate-mean. The downgrade the erratum called for
   (treat the union +0.31/+0.36 as exploratory) is correct; the direction it
   preserved is correct and, on D5 + the GPT contrast, does not rest on the audit.
   The re-grade additionally shows the Gemini magnitude was **masked, not absent**:
   within-band under the automated primary, +0.28 once routed's wrong-mechanism
   cross-file credit is removed symmetrically (§3).

**Net for Set 068:** rely on **H1 direction** (path-aware catches real,
high-severity cross-file defects snippet-fed routed structurally cannot — the D5
clean audit-independent existence proof + the GPT primary +0.23 (audit-free) + the
13/14 vs 2/8 symmetric cross-file survival). Treat **magnitude** as: GPT robust
(+0.23 to +0.29 depending on metric); Gemini "within band under the pre-registered
primary, +0.28 under symmetric mechanism-grounded grading." Treat the H2 union
magnitude as exploratory. None of the Set-068 work depends on the inflated
+0.31/+0.36 union figures, and the keep/demote/retire decision (S4) was always
gated on **cadence (Experiment B)**, which Experiment A holds constant —
unaffected by this re-grade.

---

## 6. Threats / honesty (carried)

- The re-grade re-uses the same n=5 trees / K=3 / seeded-defect instrument; it
  re-analyses, it does not re-collect. Small-n caveats from `experiment-a-results.md`
  §6 still hold — the re-grade resolves the *grading-symmetry* confound, not the
  sample-size one.
- The symmetric audit is author-applied, like the original. Mitigation is the
  same: an objective rule, committed per-cell quotes, and cross-provider review of
  this document. The verifier should spot-check `B1:D12` (the one reject) and a
  sample of the 13 keeps against `../067-…/experiment-a/raw/`.
- I re-examined all 6 routed rejections against the raw (k1 representative) and
  concur they apply the same standard symmetrically (e.g. `A1:D6`/`A1:D10` were
  correctly *kept* because A1 names the real mechanism; `A2` and the D9/D13 cells
  name the wrong one). The standard is applied equally to both arms.
