### FINDING_3: Scope-anchor PR bundles unrelated line-count work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/compute-pr-line-counts.sh` and related final-report metrics work appear unrelated to the scope-anchor change, increasing review surface and merge risk for the plan-review anchoring fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.



### FINDING_33: Final-report line-count cache can become stale before merge summary
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` reuses the first cached `LINES_STATUS=ok` block for a PR, so the post-merge final report can under-report or misstate diff size after later pushes, CI fixes, or log flushes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.



