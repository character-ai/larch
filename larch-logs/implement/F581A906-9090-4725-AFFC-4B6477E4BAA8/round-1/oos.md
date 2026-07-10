### FINDING_5: Dispatch-time invariant identity and evidence are not fully revalidated
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The pre-dispatch check does not fully revalidate identity metadata and, in some paths, evidence content after initial validation. Drift or replacement of `.identity.env` or invariant evidence can reach the fixer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-read and verify identity metadata immediately before _dispatch; fail on mismatch.
  - From cursor-specialist-edge-cases: Re-run full invariant identity validation immediately before _dispatch.
  - From codex-specialist-edge-cases: Revalidate metadata and a content digest immediately before dispatch, then fail closed on any mismatch.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] Launcher lacks plan-file context
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The launcher argv omits plan-file context used by production CI fixers. This is not required while the lane remains dormant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Wire plan-file when lane goes live; not required for dormant piece 3.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Pending run-ID resolution does not wait for checks
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `resolve_failed_run_id_once` returns `None` for pending checks without waiting, so an early pending snapshot can prevent resolution when `FAILED_RUN_ID` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Consider bounded wait in resolver or document ship-state precondition.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Dormant wrapper lacks bgjob matrix coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The shell harness does not exercise the planned bgjob matrix, leaving dormant wrapper regressions untested until wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Expand harness when lane is activated.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Launcher relies on inherited IMPLEMENT_TMPDIR
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The launcher relies on inherited `IMPLEMENT_TMPDIR` rather than explicitly setting the validated identity-specific temporary directory, which can cause validation against the wrong root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Set os.environ IMPLEMENT_TMPDIR to identity.implement_tmpdir before launcher call.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Argparse SystemExit with no code can report success
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `SystemExit` with `None` can become exit code 0 in `fixer_lane_main`, causing argument-processing failures to be reported as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Return a documented non-zero usage code when exc.code is None.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Wrapper forwards invariant evidence without requiring canonical identity metadata
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The wrapper can forward invariant evidence without requiring a present and matching `.identity.env`, causing the dormant child to close-fail rather than avoid an invalid dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only forward --invariant-evidence when canonical .identity.env exists and matches current HEAD/fingerprint.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Evidence failures should be typed before production wiring
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Evidence failures currently exit closed without a typed operator-bail merge result. This is dormant today but may conflict with planned routing when wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Map recoverable evidence failures to operator-bail persistence before production integration.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_21: [OUT_OF_SCOPE] Dispatch tests lack future subprocess-wrapper coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Dispatch tests do not cover the subprocess wrapper cases required by the plan; there is no immediate production impact while the wrapper is dormant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add subprocess harness cases when expanding test_implement_dispatch coverage.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_22: [OUT_OF_SCOPE] Dormant scripts are excluded from orphaned-script lint
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Orphaned-script lint excludes the dormant wrapper and harness, reducing mechanical enforcement until the skill wires them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Re-enable lint inclusion when SKILL.md wires the wrapper.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_23: [OUT_OF_SCOPE] Merge-result validation does not fully compare identity metadata
- **Reviewer(s)**: dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: Existing merge-result validation compares `STEP` but not the stored `STARTING_HEAD` and `INPUT_FINGERPRINT`, leaving a possible same-step partial-write stale-data path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-wire: No suggested revision provided.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_24: [OUT_OF_SCOPE] Invariant metadata has a dispatch-time TOCTOU window
- **Reviewer(s)**: dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: Invariant evidence path regularity is rechecked before dispatch, but `.identity.env` metadata is not re-read, leaving a time-of-check/time-of-use window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-wire: No suggested revision provided.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_25: [OUT_OF_SCOPE] Dormant-lane acceptance tests are structurally incomplete
- **Reviewer(s)**: dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: Acceptance tests do not exercise PR-only run-ID resolution, merge/status cross-checks, or multi-tier rounds re-entry, so the dormant wire risks would not be detected before production wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-wire: No suggested revision provided.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
