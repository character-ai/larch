### [Plan Review] FINDING_2

### FINDING_2: Guard-order regression tests incomplete
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The regression coverage does not pin the order between the allowlisted phase14 skip, the in-progress rebase probe, and the conflict-path state write, so a paused rebase could be skipped and the conflict branch may miss the `PHASE=rebase` assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a test with allowlisted REASON plus rebase_in_progress=True and no conflict metadata expecting PRE_FIX_REBASE_STATUS=stall; extend test_ship_pre_fix_rebase_routes_existing_conflict_handoff to assert PHASE=rebase in ship-pr-state.sh


