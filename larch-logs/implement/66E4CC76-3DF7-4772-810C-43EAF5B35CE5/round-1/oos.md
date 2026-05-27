### FINDING_1: [OUT_OF_SCOPE] vendor verify ignores non-fixable TSV rows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_verify_failed_jobs_locally` diverges from `run_per_job_local_fix_loop` by skipping non-fixable TSV rows. Mixed fixable and unfixable failures can let vendor verification pass the fixable jobs, push, and then fail CI again on unfixable jobs. The duplicated loop structure makes this drift easier to preserve or reintroduce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

