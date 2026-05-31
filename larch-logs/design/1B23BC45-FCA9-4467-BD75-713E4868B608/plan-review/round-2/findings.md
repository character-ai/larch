### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:398-401
- **Concern**: MAV pre-dispatch block mirrors main round by adding snapshot_pre_coder_tracked_state, but today run_implement_mav_apply only writes pre-coder-head.txt (no snapshot call at review-implement-step5-loop.sh:398-401). Scenario: Contradicts the plan’s “pure relocation” / unchanged #3272 classification contract; MAV rounds with pre-dispatch tracked dirt would newly get carryover snapshots and guard tolerance instead of today’s head-only fail-closed behavior
- **Proposed resolution**: For minimum-change relocation, only mkdir/write pre-coder-head.txt under pre_coder_snapshot_dir and repoint readers; omit snapshot_pre_coder_tracked_state unless scope explicitly widens MAV carryover parity—or drop “pure relocation” from the plan intro and add a MAV carryover harness if parity is intended
