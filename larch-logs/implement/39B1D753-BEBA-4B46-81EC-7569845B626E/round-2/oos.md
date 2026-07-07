### FINDING_1: [OUT_OF_SCOPE] Forked main-health queries ignore upstream repo
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Forked ship-phase main-health queries use `working.repo` instead of `upstream_repo`, so fork push CI can look green while upstream default-branch CI is failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pass `UPSTREAM_REPO` into `MainHealthQuery.upstream_repo` (or repo) whenever `forked_target` is true.
  - From cursor-specialist-edge-cases: Pass `upstream_repo` from session/fork metadata into `MainHealthQuery` at ship call sites.
  - From cursor-specialist-testing: Pass `UPSTREAM_REPO` as `upstream_repo` in `MainHealthQuery` when `forked_target`; add forked ship gate test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: CI monitor can merge a green rerun without an authored fix
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Flaky-defect handling exists only on `ci_agentic_fix` empty-delta; `ci_monitor` still merges after rebase/rerun green without a fix, so a PR can fail on a repo test, get rerun green, and merge with the flake still on main.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Track observed repo failures vs fix deltas and return flaky-defect-unfixed before merge/pass when CI greens without an authored fix.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: [OUT_OF_SCOPE] Same-SHA flap scan only checks one page
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Same-SHA failure scans stop at the first `MAIN_HEALTH_RUN_LIST_LIMIT` page, so an older failure can age out and a rerun success can hide the flap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Paginate or query prior same-SHA failures before returning pass.
  - From cursor-specialist-edge-cases: Paginate or query prior same-SHA failures before returning pass.
  - From cursor-specialist-testing: Increase limit paginate gh results or persist seen failure IDs per SHA.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Pre-merge gate tests are missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Pre-merge fail routing, repair-marker merge allowance, and pending/error stall tests are missing, so regressions in the merge gate can ship without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add tests for `_premerge_main_health_gate` fail→ci-fix and repair marker allow-merge paths.
  - From cursor-specialist-edge-cases: Add the planned integration tests for pre-merge gate behavior in the merge loop.
  - From cursor-specialist-testing: Add unit tests for `_premerge_main_health_gate` fail without repair marker pass with `MAIN_HEALTH_REPAIR_*` sidecar and pending/error stall paths.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Main-health flap classification is too broad
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Flap detection treats named failed jobs and `cancelled`/`timed_out` rows as repository failures, which can false-trigger repair-needed classification on infra/setup issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Narrow classification to repository test/lint job name patterns.
  - From cursor-specialist-edge-cases: Limit flap detection to repository test/lint jobs or exclude cancelled/timed_out without named test/lint evidence.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Emergency repair is still prompt-only
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Emergency repair branch/PR creation is prompt-only, so interrupted sessions depend on the orchestrator following prose instead of a bounded repair driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a bounded Python repair driver or document as intentional with stronger stall/resume contracts.
  - From cursor-specialist-testing: Add Python driver for repair-branch lifecycle or document as accepted manual path only.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Post-merge sentinel is written too early
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `post-merge-sentinel` is written at `run_postmerge_phase` entry, so helper callers can set it before push-watch completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Move sentinel write behind push-watch in all entry paths or guard helper callers.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

