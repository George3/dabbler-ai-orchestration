# Set 064 S1 design-lock consult — gpt-5-4 (openai/gpt-5.4)

1. **D1 — Cost reporter:** **AGREE-WITH-MODIFICATION** — Keep `ceil(chars/4)` and ASCII output. Modify the freshness stamping to be **optional via explicit `--write-headers`**; default report should be read-only. In-place mutation by a reporting command is a footgun in CI/editor workflows.

2. **D2 — Per-lesson metadata serialization:** **AGREE-WITH-MODIFICATION** — HTML comment trailer is the right choice **if and only if** you constrain values to a tiny grammar (`[A-Za-z0-9._-]+`, lists comma-separated, no spaces) and ship a strict parser/formatter. Also add a stable field order. Do **not** use YAML blocks; too heavy and indentation-fragile. Visible trailer is worse for readability.  
   **Explicit answer:** HTML-comment trailer is better than visible trailer or YAML for this file shape.

3. **D3 — Citation-at-close seam:** **AGREE** — The agent-run `cite_lessons` inside the final commit is cleaner than `close_session` mutating markdown post-gate. It keeps guidance edits inside the auditable work commit and avoids making close dirty a second content file.  
   **Preferred seam:** exactly this one, with one guard: `close_session` should validate that cited IDs exist and warn/error on mismatch with ledger recording.

4. **D4 — Active/archive split:** **AGREE** — Correct mechanical split. Explicitly excluding archive from always-load instructions is the right lock.

5. **D5 — Steady-state triggers + backstop ceiling:** **AGREE-WITH-MODIFICATION** — Keep evidence-based triggers and hard ceiling as backstop. Modify defaults to **N=12 sets** instead of 20. Twenty is too inert for repos already carrying large context tax; operator review plus “not referenced by active guidance” already prevents unsafe churn. Keep **10k / 6k** as initial ceilings.  
   **Explicit answer:** 10k/6k are reasonable defaults. N should be lower than 20; recommend 12.

6. **D6 — Backlog-remediation recipe:** **AGREE-WITH-MODIFICATION** — Keep the recipe and routed helper. **Offer archive-bankruptcy only behind an explicit repo-owner confirmation step and only after generating a projected active set from triage first.** It should be a last-resort escape hatch, not a co-equal option in normal flow.  
   **Explicit answer:** yes, offer it, but heavily gated.

7. **D7 — Ship to consumers:** **AGREE** — Template + extension bundle changes imply Marketplace bump. Cross-repo notice to both over-budget consumers is correct.

8. **D8 — Docs + release:** **AGREE** — Canonical lifecycle doc plus PyPI and Marketplace bumps is the right release packaging.

## Explicit answers

### Q2. D2 serialization choice
**HTML-comment trailer wins**, with constraints:
- strict key set
- fixed field order
- no spaces in values
- comma-separated multi-values if ever needed
- formatter command to normalize edits

YAML block is more expressive but too error-prone for hand-edited markdown and overkill here. Visible trailer degrades scanability.

### Q3. D3 seam preference
**Yes** — agent-runs-`cite_lessons` in the final commit is cleaner than post-gate `close_session` mutation.

Preferred seam:
- work agent decides citations
- runs `cite_lessons --set N ...`
- commits/pushes
- writes same IDs into `disposition.json`
- `close_session` validates/records only

That is the cleanest split of responsibilities.

### Q4. D5 defaults
- **Ceilings:** keep **10k lessons / 6k project-guidance**
- **Disuse window:** use **12 sets**, not 20

Reason: 20 delays useful pruning too much; your other safeguards already make pruning conservative.

### Q5. Archive-bankruptcy
**Yes, but gated.** It is worth offering because two repos are already deeply over budget and archive != delete. But it should require:
- explicit opt-in
- preview/projection first
- repo-owner signoff
- immediate ability to grep archive and re-surface by citation

## Blind spots

1. **ID governance is underspecified.**  
   You need a lock for uniqueness, permanence, and behavior on heading rename/merge/split. IDs must never be regenerated casually.

2. **`project-guidance.md` has no per-item metadata.**  
   Yet D5 says “not referenced by active guidance.” If that reference is textual/manual only, sweeps become subjective. Define what counts as “referenced by active guidance.”

3. **Citations can be noisy or gamed.**  
   “Instrumental” is human-judged. That’s fine, but document that citations are evidence, not truth. Don’t make archival depend on citation counts alone.

4. **Merge/supersession mechanics need a tool.**  
   If D6 includes “merge,” add a helper to rewrite metadata consistently (`superseded-by`, archived status, pointer text), or humans will drift formats.

5. **Reporter header writes can create merge churn.**  
   Another reason to make header stamping opt-in. Otherwise every report run dirties docs.

6. **Backstop enforcement point is unclear.**  
   “Sweep required before adding new content” needs an enforcement seam: CI check, close-time warning, or authoring-time command. If nowhere enforced, it will slip.

7. **Archive retrieval UX is not defined.**  
   “grep-on-demand” is okay, but a tiny helper like `guidance_search --archive <term>` would materially improve actual use.

8. **Ordering risk:**  
   Ship order should be:
   - D2 parser/formatter
   - D3 cite path
   - D1 reporter/check
   - D4 split
   - D5 policy
   - D6 remediation
   - D7/D8 rollout  
   If you do policy/docs before tools, repos will hand-edit inconsistent metadata.

9. **Freshness header location/format not specified tightly enough.**  
   Lock one marker block format and one placement rule per file, or the reporter will become brittle.

10. **No rule for archived lesson reactivation.**  
   Define whether citation of an archived lesson merely signals relevance or should trigger operator review for move-back-to-active. That loop is currently missing.