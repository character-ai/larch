### FINDING_1: MAIN_ADVANCED pre-rebase flush may use stale state_file context
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The MAIN_ADVANCED rebase steps do not pin the pre-rebase flush context the way `monitor.goto_rebase` does. A blind copy of the `goto_rebase` block can call `run_logs.flush_logs_pre` with `working` still carrying `state_file` set, so `_pre_push_probe` reads stale `MERGE_RESULT` from disk and may skip or stall the flush differently than the established `goto_rebase` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Spell out run_logs.flush_logs_pre(runner, working.with_(state_file=None), cwd=repo_root) in the MAIN_ADVANCED branch, matching ship.py:1593


### FINDING_2: MAIN_ADVANCED plan may increment counters on PrePushConflictHandoff
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The MAIN_ADVANCED bullet list orders `rebase_count` and `iteration` increments after `PrePushConflictHandoff` handling without stating they run only on successful `rebase_and_push`. An implementer following the listed bullets sequentially can increment `REBASE_COUNT` and `ITERATION` even when `rebase_and_push` raises `PrePushConflictHandoff`, diverging from `monitor.goto_rebase` and desynchronizing stall-resume counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Match goto_rebase structure explicitly: try rebase_and_push, except PrePushConflictHandoff write state and re-raise, increment rebase_count and iteration only on success, then continue


### FINDING_3: Item 3 fix lacks focused regression validation in plan
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan fixes Item 3 but omits the focused regression or validation required for that fix. The approved scope asks for focused regression tests for each fix, but existing research structure lint only pins sidecar command presence. The research exit-code capture acceptance remains unverifiable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal research-phase test or structural lint that fails on the unsafe if ! command then rc=$? pattern and verifies both sidecar commands use the safe rc-capture pattern.


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/progress_report.py:556-580,620-626,990-996
- **Concern**: [SCOPE-REDUCTION] Plan applies CI/probe filtering inside the shared inflight Gantt path instead of only the Step 5 caller. Scenario: The issue targets live Step 5. The shared _render_inflight_gantt path is also used by design plan review, so the plan can change design progress rendering without scope need
- **Proposed resolution**: Add skip_ci: bool = False to _render_inflight_gantt, pass it through to _progress_vendor_rows, set skip_ci=True only from _render_step5, and leave the design caller unchanged


### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/progress_report.py:556-584,620-627,990-997
- **Concern**: [SCOPE-REDUCTION] Proposed skip_ci=True inside _render_inflight_gantt applies the Step 5 filter to design plan-review progress too. Scenario: _render_design_plan_review also calls _render_inflight_gantt, so CI-like or probe-named design Step 3 rows can disappear even though the issue scope is live Step 5 only
- **Proposed resolution**: Add a skip_ci parameter to _render_inflight_gantt with default False, pass it through to _progress_vendor_rows, and set it to True only from _render_step5.



### FINDING_1: MAIN_ADVANCED must exit before shared increment-only tail
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a dedicated MAIN_ADVANCED rebase path with its own `rebase_count += 1` and `iteration += 1`, but the live code unions `MERGE_RESULT_CI_NOT_READY` and `MERGE_RESULT_MAIN_ADVANCED` at 1656 and always runs the shared tail at 1673-1683 (`iteration += 1`, `phase=ci-initial`, `continue`) for any result that is not `MERGE_RESULT_REVIEW_REQUIRED`. If MAIN_ADVANCED is not removed from that union and does not `continue` immediately after the new rebase sequence, a single loop can increment `iteration` twice (once on the MAIN_ADVANCED path, once in the shared tail). That undermines the forced-rebase semantics Item 1 targets and can leave ship retrying merge without rebasing until the iteration cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Restructure the merge-result branch so `MERGE_RESULT_CI_NOT_READY` keeps the review-probe + increment-only path, `MERGE_RESULT_MAIN_ADVANCED` runs the mirrored `goto_rebase` sequence and `continue`s immediately, and MAIN_ADVANCED is removed from the shared increment-only condition.
  - From Cursor-Innovation: Handle MAIN_ADVANCED in a dedicated elif with continue immediately after the rebase pass. Keep CI_NOT_READY-only logic in the remaining branch. Pin ITERATION delta in the new test.


