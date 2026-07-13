### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Merge-publication failure can delete the prior compatibility sidecar
- **Reviewer(s)**: dyn-dyn-adapter-races
- **Severity**: major
- **Concern**: Child mode quarantines `.step3-review-result.env` and exits on merge-publication failure without restoring it, leaving recovery dependent on the bgjob result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-adapter-races: On merge-publication failure, move the quarantined file back to `.step3-review-result.env` (or copy its contents) before exiting non-zero, and add a harness case that seeds a sidecar, forces merge publication failure, and asserts the prior envelope is restored.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
