### OOS_1: [OUT_OF_SCOPE] Analyzer lacks per-row malformed TSV warning counter
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The analyzer lacks the per-row malformed TSV warning counter specified in the plan. Short or misaligned rows are silently ignored with no operator-visible malformed-row tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return or log per-row skip counts from voter_agreement_rows_from_tsv or the analyzer loop.


