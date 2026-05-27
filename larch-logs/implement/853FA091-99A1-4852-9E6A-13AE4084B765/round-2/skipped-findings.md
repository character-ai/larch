### FINDING_3: timing-report fallback drops workflow_path and hides classification warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` resolves fallback workflow classification only through `read-design-classification.sh`, suppressing its stderr and failing to prefer `workflow_path` from v1/v2 run params. Legacy or hand-edited run params with `workflow_path=SIMPLE` but no `design_classification` can be reported as HARD/unknown, and operators may miss HARD-default warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



