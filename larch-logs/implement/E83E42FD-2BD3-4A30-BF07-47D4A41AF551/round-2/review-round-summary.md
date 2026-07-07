# Review Round 2

- Mode: `diff`
- 3 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_5: Preserve terminal NEXT_ACTION on nonzero BGJOB_RC
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `--read-result-env` blanks `NEXT_ACTION` for all non-zero `BGJOB_RC` values, including terminal failure routes, so a child emitting `NEXT_ACTION=final-summary:failed-postplan` with `BGJOB_RC=1` is treated as invalid and orchestration stops instead of running final summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: Validate the bgjob parent directory before trusting it
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The bgjob result path trusts `DESIGN_TMPDIR/bgjob` without verifying the parent is a real in-tree directory, so a symlinked parent could point reads/waits/mkdir/rm at an outside result env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_8: The fake bgjob shim cannot produce BGJOB_RC=1
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The stale-merge regression expects `BGJOB_RC=1` from a fake bgjob shim, but that shim mirrors the child exit code and the empty-child branch exits 0, so the asserted nonzero rc cannot occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
