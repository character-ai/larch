### [Plan Review] FINDING_1

### FINDING_1: `_round_coder_untracked_delta_paths` omits `head_untracked` mode branch
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan’s Files section only documents swapping in `_read_pre_coder_untracked_baseline` for `_round_coder_untracked_delta_paths`, but the Approach requires `head_untracked` untracked delta detection via `_round_attempt_untracked_delta_paths` for cleanup, no-edit skip, and verification. `_collect_round_stage_paths` and `_cleanup_failed_coder_attempt` still call `_round_coder_untracked_delta_paths` directly. An implementer following the Files list alone can ship logic that uses the global pre-coder baseline in `head_untracked` mode. On legacy head-only MAV snapshots with an empty untracked baseline, every pre-existing untracked file is misclassified as a coder delta, breaking no-edit skip and risking deletion of operator untracked files during cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_round_coder_untracked_delta_paths`, branch on `_snapshot_mode(round_dir)`: full mode keeps global pre-coder baseline; head_untracked delegates to `_round_attempt_untracked_delta_paths`. Mirror the same rule anywhere `_collect_round_stage_paths` stages untracked paths so staging and cleanup share one delta source
  - From Cursor-Innovation: Document that _round_coder_untracked_delta_paths delegates to _round_attempt_untracked_delta_paths when _snapshot_mode is head_untracked and attempt-pre-untracked-paths.txt exists, otherwise _read_pre_coder_untracked_baseline in full mode. Alternatively fold mode branching into _collect_round_stage_paths and cleanup callers so all three sites share one mode-aware delta helper.


### [Plan Review] FINDING_4

### FINDING_4: Per-coder loop missing explicit exit/return rules after `CoderResult` construction
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The restructured per-coder loop documents `CoderResult` construction for applied, no-changes, rc=2 cleanup failure, and rc=3 submodule paths, but only no-changes explicitly says return. An implementer could fall through after a successful Cursor commit and dispatch Codex on an already-committed tree, causing duplicate edits, spurious failures, or a dirty tree that still breaks later rebases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit loop-exit rules: return immediately on applied, no-changes, rc=2 (after _finalize_failed_cleanup), and rc=3 submodule-violation; only edit failure with successful cleanup and commit failure with successful cleanup may continue to the next coder


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:1386-1433
- **Concern**: [SCOPE-REDUCTION] Plan replaces a targeted failure cleanup with a new snapshot-mode state machine. Scenario: The bug needs failed-coder and failed-commit cleanup plus waterfall continuation. The proposed head_untracked attempt patches, lazy baselines, verification logs, and broad test matrix expand the change to 455 lines and add new recovery semantics not required for the reported staged residue.
- **Proposed resolution**: Reduce to one cleanup helper called from the coder-false, commit-failure, and submodule-violation paths: restore tracked coder edits to HEAD, remove untracked paths outside the pre-coder baseline, unstage before any rc=2 return, and keep tests to failed coder, failed commit, and waterfall fallback.


