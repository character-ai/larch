### FINDING_1:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:778-785
- **Concern**: OOS_3 test fixture does not require the monkeypatched path to be in pre-coder-tracked-paths.txt. Scenario: _verify_post_cleanup_state only calls _path_matches_pre_coder_snapshot for paths captured as pre-coder tracked baseline dirt. A clean full snapshot plus a later touched tracked file will not exercise the intended single-path verification branch, so the regression can fail for the wrong reason or miss the target gap.
- **Proposed resolution**: Revise the OOS_3 test plan to create a pre-dirty tracked path before _write_pre_coder_snapshot, use that same path for the narrow _path_matches_pre_coder_snapshot failure, and assert the monkeypatch was called plus coder-cleanup.log contains that path-specific mismatch.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py:OOS_3
- **Concern**: OOS_3 partial-verification fixture does not require the edited path to be listed in pre-coder-tracked-paths.txt. Scenario: In full mode `_verify_post_cleanup_state` calls `_path_matches_pre_coder_snapshot` only for paths in the pre-coder tracked baseline; a coder edit to a new or off-baseline path is validated via coder-delta branches instead, so a narrow `_path_matches_pre_coder_snapshot` monkeypatch may never run and the test would not exercise the intended single-path snapshot verifier failure from OOS_3
- **Proposed resolution**: Pin the fixture: commit a baseline tracked file, let `_write_pre_coder_snapshot` capture it, have the failing coder mutate only that listed path, and monkeypatch snapshot match for that same path; assert `coder-cleanup.log` contains `pre-coder snapshot mismatch: <path>`

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py:planned OOS_3 test; python/review_and_fix.py:772-779
- **Concern**: OOS_3 fixture may not put the monkeypatched path into the full snapshot. Scenario: _verify_post_cleanup_state calls _path_matches_pre_coder_snapshot only for paths listed in pre-coder-tracked-paths.txt. A clean baseline plus a later coder edit leaves that list empty, so the planned test may not exercise the partial verification branch and may force unnecessary cleanup code changes.
- **Proposed resolution**: Make the target tracked path dirty or staged before _write_pre_coder_snapshot, and assert pre-coder-tracked-paths.txt contains it before monkeypatching _path_matches_pre_coder_snapshot for that same path.
