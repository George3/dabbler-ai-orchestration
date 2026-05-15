# Set 023 Session 2 — Verification of the audit summary

You are a third-provider verifier reviewing the audit-summary
authored at the close of a cross-provider design-alignment audit.
The audit's subjects were GPT 5.4 and Gemini Pro; you are not
either of those, so you can read the summary independently.

**Your job:** Confirm the audit-summary faithfully captures both
providers' positions on the five questions. You are not
re-evaluating the design — you are evaluating whether the summary
accurately reflects the raw JSON responses.

**Specifically, for each of the five questions (a)-(e):**

1. Does the summary's quoted verdict and severity match the raw
   JSON?
2. Does the summary's rationale paraphrase the raw response
   faithfully, without adding or omitting material claims?
3. Does the summary's spec-author resolution follow from what
   both providers actually said?

**Then for the "Flag to operator" section:**

4. Is the spec-author's claim that "Gemini's Critical does not
   invalidate the writer fix" defensible given Gemini's actual
   rationale? Quote the part of Gemini's response that supports
   or undermines that claim.

5. Is the framing of options A / B / C fair, or does it
   misrepresent what either provider recommended?

---

## Inputs

### Raw GPT 5.4 response

```json
{{GPT_RAW}}
```

### Raw Gemini Pro response

```json
{{GEMINI_RAW}}
```

### Audit summary (under review)

```markdown
{{AUDIT_SUMMARY}}
```

---

## Output format

Return exactly this JSON shape and nothing else:

```json
{
  "verdict": "VERIFIED" | "ISSUES_FOUND",
  "issues": [
    {
      "severity": "minor" | "major" | "critical",
      "location": "question (a) | (b) | (c) | (d) | (e) | flag-to-operator | spec-refinements-list",
      "claim_in_summary": "<exact or near-exact phrase from the summary>",
      "what_the_raw_says": "<exact or near-exact phrase from the raw JSON that contradicts or qualifies it>",
      "recommended_fix": "<what the summary should say instead>"
    }
  ],
  "notes": "<one paragraph: overall assessment of summary fidelity. If verdict is VERIFIED, state explicitly that you checked each question against both raw responses and they match.>"
}
```
