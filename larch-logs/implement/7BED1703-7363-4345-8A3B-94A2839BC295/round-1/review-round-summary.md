# Review Round 1

- Mode: `diff`
- 7 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_4: External log-directory re-attach failure
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `adapt` accepts an external `--log-dir` on first launch, but registry validation rejects it on re-attach, producing `registry-invalid` instead of reusing the daemon.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Ambiguous process-probe failure handling
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Treating `missing-pid` as proven dead can clear an entry whose process is merely uninspectable and launch a duplicate job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Completed-result parsing mismatch
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Adapter result parsing rejects blank lines that the wait path accepts, potentially causing a completed job to be relaunched or misclassified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_9: Symlink-swap risk during merge-env publication
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Pathname-based merge-env publication can be redirected outside the temporary directory by a same-UID symlink swap after validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_11: Incomplete merge-env publication test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The merge-env test prewrites rows instead of exercising child publication, leaving child-protocol regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: Missing startup-pipe failure coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Closed and malformed daemon startup pipes are not separately tested through `adapt_main` for machine-readable failure output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_18: Re-attach emits an unvalidated PGID
- **Reviewer(s)**: dyn-dyn-process-ownership
- **Severity**: major
- **Concern**: Re-attach can emit the persisted PGID when daemon liveness passes even if child identity validation reports a PGID mismatch, producing a false healthy `STARTED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-ownership: Address the concern above.
