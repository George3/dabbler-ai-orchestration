```json
{
  "verdict": "ISSUES_FOUND",
  "issues": [
    {
      "title": "Budget writer contract includes uncited mode/default semantics",
      "category": "Completeness",
      "severity": "Major",
      "details": "The audit record’s §2.4/D1 lock asserts several implementation-driving semantics without corresponding file:line evidence in the record: the four `mode` bands (`0`, `<20`, `20-99`, `100+`), `verification_nte_usd` defaulting to `threshold_usd`, and D3’s legacy-compat notes such as absent `verification_method -> api` and absent `scope -> per-project`. The rest of the contract audit is well evidenced, but these specific claims are presented as locked conclusions rather than clearly marked synthesis/inference. Because Session 1’s contract requires D1-D4 to be answered with file-level evidence, this is a material evidence gap."
    }
  ]
}
```

The inventory, unreachability proof, D2/D4 locks, and the Q2 split recording all read as sound and internally consistent. The only substantive verifier concern is that a few schema semantics are locked without explicit file-level support in the audit record itself.