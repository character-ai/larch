### FINDING_1: OOS_3 fixture may not exercise single-path snapshot verification
- **Reviewer(s)**: Cursor-Arch Phase2, Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The OOS_3 regression fixture does not require the monkeypatched path to be listed in `pre-coder-tracked-paths.txt`. In full mode, `_verify_post_cleanup_state` calls `_path_matches_pre_coder_snapshot` only for paths captured in the pre-coder tracked baseline. A clean full snapshot plus a later coder edit to a new or off-baseline path routes validation through coder-delta branches instead, so the narrow `_path_matches_pre_coder_snapshot` monkeypatch may never run. The test may therefore fail to exercise the intended single-path verification failure from OOS_3, pass or fail for the wrong reason, or push unnecessary cleanup code changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch Phase2: Revise the OOS_3 test plan to create a pre-dirty tracked path before _write_pre_coder_snapshot, use that same path for the narrow _path_matches_pre_coder_snapshot failure, and assert the monkeypatch was called plus coder-cleanup.log contains that path-specific mismatch.
  - From Cursor-Pragmatic: Pin the fixture: commit a baseline tracked file, let `_write_pre_coder_snapshot` capture it, have the failing coder mutate only that listed path, and monkeypatch snapshot match for that same path; assert `coder-cleanup.log` contains `pre-coder snapshot mismatch: <path>`
  - From Codex-Generic: Make the target tracked path dirty or staged before _write_pre_coder_snapshot, and assert pre-coder-tracked-paths.txt contains it before monkeypatching _path_matches_pre_coder_snapshot for that same path.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9,124-147,196; python/test_ci_agentic_fix.py:1034-1082; python/ci_agentic_fix.py:398-403
- **Concern**: [SCOPE-REDUCTION] Plan maps OOS_3 to review_and_fix cleanup instead of the stated mixed mechanical rollback test. Scenario: The issue asks to cover the mixed mechanical rollback verify loop. The existing test uses one fixable job, so a bug that verifies only the first job could still pass. The plan spends OOS_3 scope on unrelated review_and_fix cleanup coverage.
- **Proposed resolution**: Replace the OOS_3 review_and_fix cleanup section with a two-fixable-job regression in python/test_ci_agentic_fix.py where one job verify fails. Assert rollback and delegate behavior. Touch python/ci_agentic_fix.py only if that test exposes a real bug.
