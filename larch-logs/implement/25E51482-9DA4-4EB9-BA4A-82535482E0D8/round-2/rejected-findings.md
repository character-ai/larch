### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Cursor dirty-tree validation checks the wrong workspace
- **Reviewer(s)**: dyn-dyn-launch-contract
- **Severity**: major
- **Concern**: Assessment-mode Cursor launches in the copied evidence workspace but records dirty-tree state against the repository root. Mutations to copied evidence can therefore be accepted as clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-launch-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
