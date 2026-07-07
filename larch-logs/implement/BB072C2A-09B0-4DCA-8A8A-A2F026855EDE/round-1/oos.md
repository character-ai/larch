### FINDING_3: [OUT_OF_SCOPE] collision regression only checks literal strings
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The collision regression only compares hard-coded path strings; it does not verify the actual slug→result-env mapping or runtime collision behavior, so a bad slug collision can still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] bgjob migration wording is stale or inconsistent
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The docs still mix older “background launch” language with the new bgjob flow, and the fallback terminology is inconsistent. That is prose-only, but it can mislead operators reading the plan top-to-bottom.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] legacy timeout harness remains in collector prose
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The collector prose still references the legacy auto-background timeout harness; that is preexisting and outside this chunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] bgjob start failure routing is still implicit
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: `bgjob start` can still exit 2 without `BGJOB_ERROR` on pipe failure, and the research prose does not yet document that preexisting failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] external reviewers still have broad filesystem access
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: External reviewers still have filesystem access beyond the Claude Edit/Write hook coverage; that is the existing trust model, not a new issue from this chunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

