### FINDING_17: [OUT_OF_SCOPE] Branch mixes #3210 ship-pr with #3217 anti-poll hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated hook/polling/docs changes bundled with #3210 increase review/revert surface and can distract from or block ship-pr regression focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Fork `ACTION=rebase` still bypasses `run_rebase_rebump`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Two fork rebase behaviors may coexist after the CI-fix path enhancement (`ci-wait` / `ci-decide` fork rebase vs new post-fix rebump); fork `ACTION=rebase` should eventually unify under `run_rebase_rebump` when bump plumbing is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


