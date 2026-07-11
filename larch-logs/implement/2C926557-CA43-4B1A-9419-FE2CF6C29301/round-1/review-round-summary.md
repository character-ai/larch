# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Post-merge failure evidence can incorrectly trigger pre-merge reship recovery
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: When `PHASE=postmerge`, `STALL_STEP=postmerge-flush`, and the merge is terminal, evidence that combines `preterminal-outcome` with a real failure marker such as `redaction-failed`, `commit-failed`, `post-merge-refresh-failed`, or `manifest-recovery-failed` can bypass the expected-cleanup guard and then match the broad preterminal-outcome classifier. This may produce `FAILURE_CLASS=transient-infra` with `RESUME_HINT=step8-shippr`, causing an inappropriate reship against an already merged or closed PR. Known post-merge failure markers must take precedence and retain a non-resumable failure classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Tests do not cover failure-detail-log and explicit non-reship classification paths
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The regression tests primarily use state-file `NOTE=` evidence and do not adequately exercise production `--failure-detail-log` evidence or assert the resulting `FAILURE_CLASS` and `RESUME_HINT`. A regression in detail-log-only or mixed-evidence classification could therefore continue returning `transient-infra` and `step8-shippr` without failing tests. Add positive detail-log fixtures and mixed-evidence negative cases with explicit non-resumable classification assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
