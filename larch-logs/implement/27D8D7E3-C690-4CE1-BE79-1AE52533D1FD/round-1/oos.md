### FINDING_5: [OUT_OF_SCOPE] bgjob-check TOCTOU remains
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: A bgjob can start between the liveness check and `deactivate_run`, which is a pre-existing race-class issue rather than a regression introduced by this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: "Accept or add explicit locking if stronger guarantees are required later"


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] existing SessionStart payload contract still lacks `source`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Existing sibling hook tests only consume `cwd` and `session_id`, so the repo still does not establish an existing `source` field contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Address the concern above."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] matcher-split alternative was already rejected
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The alternative matcher-split design was already rejected during design review, so this is not introduced by the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Address the concern above."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] no subprocess smoke test for `session_reset_main`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `session_reset_main` does not have a subprocess CLI smoke test, leaving only unit-level coverage for the new path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: "Address the concern above."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] multi-session same-clone concurrency is unsupported
- **Reviewer(s)**: dyn-dyn-statusline-reset
- **Severity**: minor
- **Concern**: A second Claude session on the same clone can clear `current` for another active session, but that scenario is outside the stated one-active-run-per-clone model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-reset: "Address the concern above."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] post-unlink verification is omitted
- **Reviewer(s)**: dyn-dyn-statusline-reset
- **Severity**: minor
- **Concern**: `deactivate_run` does not re-check that `current` is gone after unlink, which is a low-residual-risk hardening point on the happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-reset: "Address the concern above."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] resume/compact still pay an extra interpreter launch
- **Reviewer(s)**: dyn-dyn-statusline-reset
- **Severity**: minor
- **Concern**: `scripts/sessionstart-statusline.sh` still invokes `progress session-reset` on resume/compact events even though Python no-ops there, adding an extra interpreter launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-reset: "Address the concern above."
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

