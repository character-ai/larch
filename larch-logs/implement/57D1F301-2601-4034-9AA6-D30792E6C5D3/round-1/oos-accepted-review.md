### FINDING_5: [OUT_OF_SCOPE] Gate A/B trailer preservation is prompt-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Gate A/B trailer preservation in `approval-gates.md` is prompt-only without a script guard. Direct `plan.txt` rewrites can drop or alter trailers with no mechanical rejection before `EMIT_PLAN`. The same post-rewrite validator used by waterfall is not run on Gate A/B paths before Step 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


