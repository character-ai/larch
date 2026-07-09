### FINDING_1: [OUT_OF_SCOPE] stale current-pointer state after activate failure
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Best-effort `progress activate` failures can leave stale or missing current-pointer state in place, so later breadcrumb or statusline writes may silently attach to the wrong run or stay blank.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Track outside this PR; consider surfacing activate failure in execution-issues or a one-line warning when the first append returns False with no current pointer.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] no-create fd helper coverage gaps
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new no-create fd helpers do not have focused unit coverage, so future changes to subdir lookup could regress symlink rejection without a test anchored on the helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

