### OOS_1: tracking_issue still uses gh api instead of the issue-view helper
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `_fetch_issue_title` still uses `gh api` instead of `issue_view_field_read`, so helper coverage and error text can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_2: ci_timing_fetch timeout may skip large logs
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `run_log_read` now relies on the default 120s gh read timeout, which can skip large workflow logs when building timing baselines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_3: ARCH_GUIDELINES wording diverges from the paste-ready text
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Part C uses Guidance bullets instead of the exact paste-ready text the issue asked for; runtime behavior is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: gh baseline debt and timeout signaling remain inconsistent
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-wire-ratchets
- **Severity**: minor
- **Concern**: Several gh reads remain grandfathered in the subprocess baseline, and `gh.py` timeout signaling still varies between helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-wire-ratchets: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_5: `_body_file_args` still omits `dir=`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `NamedTemporaryFile` in `_body_file_args` still omits `dir=`, so session tempfiles can land in ambient system tmp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_6: docs regen list omits the wire-artifact baseline target
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The shared regen bullet list omits `make regen-wire-artifact-pairing-baseline`, so operators may miss it when updating baselines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_7: Bash empty-array false negative remains outside this focus
- **Reviewer(s)**: dyn-dyn-wire-ratchets
- **Severity**: minor
- **Concern**: The empty-array guard tracking false-negative shape is still present, but it is outside the wire-artifact/gh ratchet focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-wire-ratchets: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

