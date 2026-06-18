### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:483-509
- **Concern**: `_round_coder_untracked_delta_paths` Files delta omits head_untracked mode branch required in Approach. Scenario: The Approach binds head_untracked cleanup, no-edit skip, and delta detection to `_round_attempt_untracked_delta_paths`, but the Files section only says to swap in `_read_pre_coder_untracked_baseline`. An implementer following the Files subsection alone leaves legacy head-only MAV dirs classifying all pre-existing untracked as coder deltas (empty global baseline), breaking FINDING_1 no-edit skip and risking deleting operator untracked files during cleanup
- **Proposed resolution**: In `_round_coder_untracked_delta_paths`, branch on `_snapshot_mode(round_dir)`: full mode keeps global pre-coder baseline; head_untracked delegates to `_round_attempt_untracked_delta_paths`. Mirror the same rule anywhere `_collect_round_stage_paths` stages untracked paths so staging and cleanup share one delta source

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:489-509
- **Concern**: _collect_round_stage_paths not updated for head_untracked attempt-relative deltas. Scenario: Approach wires attempt-pre untracked and mode-aware _has_coder_worktree_deltas for head_untracked, but _collect_round_stage_paths still calls _round_coder_delta_paths and _round_coder_untracked_delta_paths globally. Legacy head-only snapshots (only pre-coder-head.txt) with an empty untracked baseline treat every pre-existing untracked file as a coder delta. FINDING_4 no-changes uses stage_paths from this helper, so a successful no-edit coder can skip no-changes and git add or commit pre-existing untracked files. Test 10 covers False-return skip only, not this True no-edit path.
- **Proposed resolution**: Add an explicit ### UPDATED step for _collect_round_stage_paths: in head_untracked mode stage only attempt-relative tracked deltas (paths whose wt or index differ from attempt-pre-path-diffs vs pre_head) plus _round_attempt_untracked_delta_paths; in full mode keep current pre-coder baseline logic. Add test 13: legacy head-only snapshot, pre-existing untracked, fake coder returns True with no edits, assert no-changes and no git add of the pre-existing file.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:483-486
- **Concern**: _round_coder_untracked_delta_paths Files section omits head_untracked mode branch. Scenario: Approach lines 70-73 require head_untracked untracked delta detection via _round_attempt_untracked_delta_paths for cleanup, no-edit skip, and verification, but the Files section only documents swapping in _read_pre_coder_untracked_baseline. _collect_round_stage_paths and _cleanup_failed_coder_attempt still call _round_coder_untracked_delta_paths directly. An implementer following the Files list can ship cleanup and no-edit logic that still uses the global baseline in head_untracked mode, reintroducing mis-deletion or false-positive delta detection on legacy MAV snapshots.
- **Proposed resolution**: Document that _round_coder_untracked_delta_paths delegates to _round_attempt_untracked_delta_paths when _snapshot_mode is head_untracked and attempt-pre-untracked-paths.txt exists, otherwise _read_pre_coder_untracked_baseline in full mode. Alternatively fold mode branching into _collect_round_stage_paths and cleanup callers so all three sites share one mode-aware delta helper.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:489-509
- **Concern**: Plan claims `_collect_round_stage_paths` is mode-aware for the FINDING_4 no-changes gate and commit staging, but the file list never updates it (or `_round_coder_delta_paths`) for `head_untracked`. Scenario: In MAV/legacy head-only snapshots there is no `pre-coder-tracked-paths.txt`, so today's `_round_coder_delta_paths` treats every path dirty vs `pre_head` as a coder delta; pre-MAV carryover is misclassified as stage/commit scope and can block `no-changes` or commit carryover
- **Proposed resolution**: Add an explicit plan step: branch `_collect_round_stage_paths` on `_snapshot_mode`; in `head_untracked` derive tracked stage paths from attempt-baseline patches (new `_round_attempt_tracked_delta_paths` or equivalent) and untracked from `_round_attempt_untracked_delta_paths`, mirroring the attempt-relative logic already specified for `_has_coder_worktree_deltas`

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:489-509
- **Concern**: Head-untracked untracked staging still flows through global `_round_coder_untracked_delta_paths` in stage-path collection even though cleanup/verification use attempt-relative untracked deltas. Scenario: After a failed first coder leaves new untracked files, cleanup may remove them, but stage-path/no-changes logic keyed on the global pre-coder baseline can still count attempt-local untracked deltas incorrectly during the waterfall or on legacy head-only dirs with pre-existing untracked files
- **Proposed resolution**: Wire `_collect_round_stage_paths` to `_round_attempt_untracked_delta_paths` when mode is `head_untracked`; keep global baseline only for `full` mode

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:215-221
- **Concern**: Head-untracked cleanup step order is inconsistent within the plan (Approach: unstage, restore tracked, then delete untracked; Files section: delete untracked then restore tracked). Scenario: If a coder creates a new untracked file under a tracked directory that restore/checkout recreates, order-dependent residue or failed verification can leave a dirty tree on rc=2 stall paths
- **Proposed resolution**: Pick one order in the plan and align both sections; prefer unstage, restore attempt-baseline tracked state, then remove attempt untracked deltas (matches Approach)

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:234-247
- **Concern**: The restructured per-coder loop documents CoderResult construction for applied, no-changes, rc=2 cleanup failure, and rc=3 submodule paths but only no-changes explicitly says return. Scenario: An implementer could fall through after a successful Cursor commit and dispatch Codex on an already-committed tree, causing duplicate edits, spurious failures, or a dirty tree that still breaks later rebases
- **Proposed resolution**: Add explicit loop-exit rules: return immediately on applied, no-changes, rc=2 (after _finalize_failed_cleanup), and rc=3 submodule-violation; only edit failure with successful cleanup and commit failure with successful cleanup may continue to the next coder

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:465-507
- **Concern**: Cleanup verification omits unexpected cached deltas. Scenario: Full-mode verification can pass with index-only staged residue outside the pre-coder baseline if git restore --staged . fails or a hook leaves cached changes. apply_findings_with_coder may then continue or return rc=4 with a dirty index, reproducing the rebase failure.
- **Proposed resolution**: In _verify_post_cleanup_state, compare git diff --cached --name-only pre_head against pre-coder tracked paths that match their cached patches, and fail verification on any unexpected cached path.

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:1386-1433
- **Concern**: [SCOPE-REDUCTION] Plan replaces a targeted failure cleanup with a new snapshot-mode state machine. Scenario: The bug needs failed-coder and failed-commit cleanup plus waterfall continuation. The proposed head_untracked attempt patches, lazy baselines, verification logs, and broad test matrix expand the change to 455 lines and add new recovery semantics not required for the reported staged residue.
- **Proposed resolution**: Reduce to one cleanup helper called from the coder-false, commit-failure, and submodule-violation paths: restore tracked coder edits to HEAD, remove untracked paths outside the pre-coder baseline, unstage before any rc=2 return, and keep tests to failed coder, failed commit, and waterfall fallback.

### OOS_1:
- **Description**: `coder-main-agent-required` prose still describes only edit exhaustion (and misorders Codex/Cursor) and does not mention commit failures now waterfall to rc=4 after clean cleanup. Scenario: Operators reading the branch doc may still expect commit-hook failures to stall as `coder-failed` rather than hand off to main-agent apply
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/references/step5-review-branches.md:25-27
- **Phase**: design
