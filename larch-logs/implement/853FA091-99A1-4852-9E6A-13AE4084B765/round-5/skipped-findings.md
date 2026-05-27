### FINDING_3: SIMPLE reviewer emphasis diverges from locked plan prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` uses SIMPLE tier emphasis text that no longer matches the plan-locked reviewer prose, including the security carve-out and missing Accept YES line. This can bias SIMPLE reviews differently from the intended minimum-change contract while tests only check partial substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.



