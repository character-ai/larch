### FINDING_1: Pause-load test does not cover the broken Step 5c resume path
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The pause-load restore test reuses a helper that hardcodes `STEP=3`, so it can pass while the actual Step 5c resume flow still fails to restore or honor the pre-pause completion sentinels. That leaves the regression unverified on the path that matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Parameterize the helper or build the test snapshot with `STEP=5c` in `pause-state.txt` so the restore case matches the broken resume path.


