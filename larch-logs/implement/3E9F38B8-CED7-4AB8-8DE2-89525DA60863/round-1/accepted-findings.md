### FINDING_1: SECURITY.md overstates timing-report inputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: SECURITY.md says `timing-report*.json` files are consulted for SIMPLE/HARD classification, but the scanner only reads the exact skill-specific timing report basename (`timing-report.json` or `timing-report-final.json`) plus `run-params.json`. This can mislead maintainers or reviewers into expecting other `timing-report*.json` files to affect classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


