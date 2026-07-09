### FINDING_3: [OUT_OF_SCOPE] Closed-PR edge-case coverage and docs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The out-of-scope notes all point at lock-in around closed-PR edge behavior: malformed `PR_CLOSED` values, stall-before-skip ordering while a rebase is already in progress, and the `reship`/`ci-fix` documentation split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add test_ship_pre_fix_rebase_closed_pr_stalls_when_rebase_in_progress mirroring the existing open-PR stall test.
  - From cursor-specialist-testing: Mirror the PR_CLOSED carve-out note on the ci-fix bullet or in a shared pre-fix-rebase note.
  - From cursor-specialist-testing: Add parametrized truthy/falsy cases if you want wire-format lock-in.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

