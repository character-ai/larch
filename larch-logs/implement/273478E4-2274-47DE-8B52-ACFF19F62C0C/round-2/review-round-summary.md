# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (2 neutral)

## Accepted Findings

### FINDING_1: collect_results fixture still uses retired severity
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The structured-validation test fixture still encodes the old Important severity, but the validator now expects major/minor/nit. That mismatch makes the collect_results path fail validation, record NOT_SUBSTANTIVE, and break the OK plus sidecar assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: missing tally test for accepted all-minor OOS not being filed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: There is no end-to-end tally test proving that accepted out-of-scope results with only minor YES severities do not get filed. That leaves room for `oos-accepted-review.md` to be repopulated and the token-saving gate to regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: design nit-drop coverage checks the wrong audit path
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The plan-review nit-drop coverage is asserting that an OOS nit survives, and it checks the wrong top-level audit path. That would let CI miss regressions where explicit nit rows stop being dropped or the per-round dropped-nit audit files stop being written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Update the test fake or call the real prune helper, then assert the OOS nit is removed from findings-oos.md and ballot.txt and recorded under plan-review/round-6/oos-dropped-before-vote.md.


