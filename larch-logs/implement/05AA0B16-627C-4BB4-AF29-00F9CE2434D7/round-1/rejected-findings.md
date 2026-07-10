### [rejected] FINDING_9

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_9: Invalid explicit bgjob run IDs are silently ignored
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: An invalid explicit `--run-id` can be ignored by `resolve_owned_run_id`, causing the job to run under a persisted or fallback identity instead of the identity the caller requested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0
