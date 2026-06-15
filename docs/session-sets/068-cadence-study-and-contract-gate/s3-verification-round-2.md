# Set 068 S3 -- Cross-provider verification ROUND 2 (gpt-5.4)

> Focused re-verify of the four R1 findings (1 Major arm-E overstatement +
> 3 Minor: grader wording, sign-agreement fold-in, run_test citation).

Focused re-verify result:

- **R1 Major (E overstatement): resolved.** `experiment-b-results.md` Sec 0/2/5/6 now consistently says:
  - **E gpt = 12/12**
  - **E gemini = 11/12, missing BD6 (Critical)**
  This matches `experiment-b-data.json`: `E_openai` majority-misses = `[]`; `E_google` majority-misses = `["BD6"]`.

- **R1 Minor (_band_stats sign-agreement): resolved.** `grade.py` now uses  
  `resolved = (abs(mean) > band) and sign_agree`, and the decisive cells in `experiment-b-data.json` are unchanged as claimed:
  - R-vs-Q cadence-payoff `s=66` resolved
  - R-vs-E cadence-payoff `s=27/30` resolved
  - no-coupling `s=1.0` resolved
  - always-visible `s=3.0` resolved  
  So **A3 still fails** and **B3 still fires**.

- **R1 Minor (run_test raw-trace citation): resolved.** Sec 1 now cites `experiment-b/raw/numkit/E_google_S5_k1.json` for live `run_test` use.

- **NEW minor inconsistency introduced by the doc edit:** the **module docstring** now correctly says the surface gate is on the **defect’s own file**, but `grade.py::_in_surface` still has the docstring  
  `"""Is the defect's evidence file in arm's surface at snapshot i?"""`  
  That creates an internal wording mismatch in the corrected artifact, even though behavior is correct.

{"verdict":"ISSUES_FOUND","issues":["Minor: grade.py now has an internal doc inconsistency: the top-level docstring correctly says the surface gate is on the defect's own file, but _in_surface still says 'evidence file'."]}
