### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:887-895
- **Concern**: Plan does not close the since_committed fallback to pre-coder-head. Scenario: _collect_review_fix_stage_paths calls _collect_round_stage_paths(..., since_committed=True). Current _round_diff_base falls back to pre-coder-head.txt when post-coder-head.txt is missing or empty, so the proposed early diff_base == "" guard will not fire. A round with an empty post-coder baseline can still stage stale deltas since the pre-coder baseline, violating OOS_1 and the plan edge case.
- **Proposed resolution**: Make since_committed require a present non-empty post-coder-head.txt, either by returning "" from _round_diff_base for that case or by guarding in _collect_round_stage_paths before pre-head fallback. Add a focused empty post-coder-head since_committed test.




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:887-896
- **Concern**: `since_committed=True` can still use the pre-coder head when the post-coder head is missing or empty. Scenario: The planned early guard only fires when `_round_diff_base(...)` returns empty. Current `_round_diff_base` falls back to `pre-coder-head.txt`, so review-fix staging can still use a stale baseline and stage unrelated drift.
- **Proposed resolution**: Make `_round_diff_base(..., since_committed=True)` return `post-coder-head.txt` only when it is present and non-empty; otherwise return `""`. Cover missing or empty post-head in the OOS_1 tests.




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py:OOS_3-test
- **Concern**: pin OOS_3 regression to full snapshot mode only. Scenario: _verify_post_cleanup_state only runs per-path checks in full/head_untracked branches (python/review_and_fix.py:772-813); missing mode uses porcelain-only (814-817). A head-only fixture (pre-coder-head.txt without pre-coder-tracked-paths.txt) makes a _path_matches_pre_coder_snapshot monkeypatch a no-op and the test would not cover the rolled-up partial-verification gap
- **Proposed resolution**: State explicitly that OOS_3 must rely on _ensure_pre_coder_snapshot / _write_pre_coder_snapshot (mode full) and must not reuse head-only snapshot setups from test_apply_findings_with_coder_head_only_*




### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_review_and_fix.py:OOS_3
- **Concern**: OOS_3 regression must pin full pre-coder snapshot mode. Scenario: The plan says to monkeypatch `_path_matches_pre_coder_snapshot` for one path, but head-only rounds (`pre-coder-head.txt` without `pre-coder-tracked-paths.txt`) use `_snapshot_mode` `head_untracked` and `_verify_post_cleanup_state` checks `_path_matches_attempt_snapshot` instead. A test built on head-only setup would not exercise the intended single-path verification branch and could pass without covering the OOS_3 failure mode.
- **Proposed resolution**: Specify that the OOS_3 test uses default `_ensure_pre_coder_snapshot` / full snapshot (`mode == "full"`) and monkeypatches the helper that the active verify branch actually calls (`_path_matches_pre_coder_snapshot` for full mode).




### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:1139-1154
- **Concern**: `_lint_fix_delta_paths` plan can return reported paths that no longer differ from the pre-lint baseline. Scenario: The lint loop unions reported paths across attempts. If an earlier reported path is reverted or removed by a later attempt, the plan still returns it unless it was pre-lint dirty and matches the stored snapshot, so the post-loop commit may stage a clean or missing path despite the acceptance contract.
- **Proposed resolution**: Filter the reported set by current repo state before returning. Keep only reported paths that still have a current tracked diff against `pre_lint_head` or current untracked presence, then apply the existing pre-lint snapshot exclusion. Add one focused assertion for a reported-but-reverted path.




### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:887-895; python/test_review_and_fix.py:1039-1086
- **Concern**: Plan lacks required empty post-coder-head since_committed validation. Scenario: _round_diff_base currently falls back from an empty or missing post-coder-head.txt to pre-coder-head.txt, so the proposed early guard can still use a stale baseline on the since_committed path
- **Proposed resolution**: Require a focused test with since_committed=True and empty post-coder-head.txt that proves no pre-coder-head fallback is used and no stage paths are returned




