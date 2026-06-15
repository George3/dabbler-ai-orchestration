# Set 067 S3 -- Cross-provider verification of the Experiment A analysis (gpt-5.4), Round 1

> Independent verifier: gpt-5.4 (openai), cross-provider for the Claude
> orchestrator. Checks the INFERENCE, not the wet-lab run.

Bottom line: the **core capability inference is supported**. I do **not** see evidence that H1/H3/H4 were manufactured by post-hoc threshold moves, and the load-bearing audit calls you exposed are defensible from the raw text.

## 1) Criteria discipline

### H1
Pre-registered H1 required:
1. path-aware same-provider advantage over routed exceeds the noise band,
2. the advantage is carried by the **cross-file** subclass,
3. path-aware-pair catches at least one **Critical/Major cross-file** defect that routed-pair misses.

On the audited data:
- **B1−A1 = +0.3056**, band **0.0834**
- **B2−A2 = +0.3611**, band **0.1111**

Both are comfortably above the reported bands. The unique gains are all cross-file:
- B1 gains: **D5, D9, D11, D12, D13**
- B2 gains: **D5, D6, D9, D10, D11, D12, D13**

And path-aware-pair uniquely gets **D5** and **D9** (both Critical), plus **D11/D12/D13**. So H1 is met on the pre-registered rule.

### H3
`routed-pair − path-aware-pair = ∅` in the JSON. So “**routed unique capability ruled out**” is correctly read on the seeded catalogue.

### H4
Falsifier coverage is **19/20 = 0.95**, exactly as claimed. D16 is the lone non-discriminating case.

### H2
The write-up’s substantive H2 reading is sound:
- routed-pair weighted rate = **0.6944**
- best single routed (A1) = **0.6944**
- therefore second routed validator added **0** in this instrument
- path-aware-pair − routed-pair = **0.3056**

So “context-access, not second routed provider, explains the edge” is supported **in this experiment**.

## 2) H1 soundness / causal read

The causal story is good. Provider is held constant within each context contrast, code is frozen and identical, and the gains are concentrated in the defect subtype that should require omitted-file access.

The **negative control** works in the important sense: there is **no positive in-snippet context gain**. That supports the claim that the observed edge is about cross-file access rather than generic model prompting differences.

One nuance: the prose slightly overstates this cleanliness. B2 does miss **D16**, so path-aware is not literally lossless relative to routed on every in-snippet item. That does **not** invalidate H1, because the *gains* are still entirely cross-file and the high-severity unique wins are cross-file; it is just a wording overreach.

## 3) The audit

This was the biggest risk, and the exposed examples are defensible.

### A1 tree3: REJECT D9
Raw text complains that:
- the docstring says “superset”
- the code filters out `KNOWN`
- therefore output is a filtered subset

That is **not** the seeded D9 mechanism. D9 is that omitted `analyzer.py` returns only assignment refs and drops call/return refs. A1 never identifies that omitted-file incompleteness. Rejecting D9 is fair.

### A1 tree3: KEEP D10
A1 explicitly flags:
- `name = str(ref)`
- silent coercion to string
- changed output surface / possible collapsing of distinct refs

That is the actual defective line and a real wrong-data mechanism, even if the model cannot fully name the omitted cross-file type contract. Keeping D10 is defensible.

### A2 tree2: REJECT D6
A2 says only:
- `precedence` returns default `0` for unknown symbols
- this can mask typos

That is a generic silent-default concern, not the seeded D6 mechanism that **every** symbol lookup misses because the table is keyed by operator **name**, not symbol. Rejecting D6 is fair.

So on the evidence you exposed, the audit looks like correction of predicate overmatch, not bias to manufacture a context gap.

Also importantly: even without leaning only on the audited Gemini contrast, the broader pattern is still the same—path-aware-pair uniquely gets the five routed-missed cross-file defects, including both Criticals.

## 4) H3 / H2 logic

This part is well handled.

- “H3 empty” is correctly interpreted as ruling out **unique routed capability on identical code**, not cadence value.
- The write-up is careful not to smuggle in a keep/demote/retire decision from Experiment A alone.
- “Second routed validator adds nothing” is accurate for this dataset because **A2 is a strict subset of A1** at union-over-K.

## 5) Over-claim check

The limitations are present, relevant, and not buried:
- author-seeded defects
- small n / K resolving only large effects
- audit dependence
- mock-repo simplicity
- falsifier pre-authoring caveat

The claims mostly stay scoped to:
- this instrument,
- identical frozen code,
- capability not cadence,
- direction more than field magnitude.

That is appropriately restrained.

## 6) Internal consistency

Most numbers and set relationships agree with the JSON.

The only notable mismatches I see are minor prose overstatements:
- “every arm scores 13/13” is not literally true because **B2 misses D16**
- “path-aware ... lost none” is not literally true for **B2 vs A2**, since `lost_vs_routed = ["D16"]`

These do not overturn the inference, but they should be corrected.

## Overall assessment

**Core verdict verified.**  
H1 follows from the audited data under the pre-registered rule. H3 and H4 are correctly read. The manual audit examples you exposed are defensible and do not look like outcome-driven grading.

{"verdict":"VERIFIED","issues":[{"severity":"Minor","claim":"The prose says the in-snippet control is 13/13 for every arm and that path-aware 'lost none'.","problem":"The JSON shows B2 misses D16, and `H1_context_contrasts.B2_minus_A2_Gemini.lost_vs_routed` contains `D16`. This overstates strict dominance, even though it does not change the negative-control interpretation because there are no in-snippet gains.","fix":"Revise to say there was no positive in-snippet context gain; B1 ties A1 on all in-snippet defects, while B2 misses D16."},{"severity":"Minor","claim":"The H2 write-up treats the pairwise context-vs-second-provider result as resolved without explicitly tying it back to the preregistered noise-band rule.","problem":"The prereg says H2 contrasts are resolved only if they exceed the noise band. The conclusion is still supported here, but the manuscript should explicitly connect the pairwise contrast to that rule.","fix":"Add a sentence noting that `pathaware_pair − routed_pair = 0.3056`, which in this dataset is numerically the same resolved gap as `B1 − A1`, so the H2 reading is resolved by the same band comparison."},{"severity":"Minor","claim":"The results file re-describes the pre-registered audit as 'routed×cross-file catches' only.","problem":"The prereg text describes a broader audit procedure. Restating it more narrowly after the fact can read like criteria drift, even if the only outcome-changing overrides were in routed×cross-file cells.","fix":"Clarify that routed×cross-file adjudications were the load-bearing override-generating cases, while other inspections did not change scores; do not describe the prereg itself more narrowly than written."}]}
