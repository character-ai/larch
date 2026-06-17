### FINDING_1: Empty `in_memory_stall_tracking` falls back to process env `STALL_TRACKING`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Callers pass `in_memory_stall_tracking=""` into `normalized_outcome_values`. An empty string is falsy, so the helper falls back to `os.environ["STALL_TRACKING"]`. After a Step 5 stall, the orchestrator can still export `STALL_TRACKING=true` while `ship-pr-state.sh` and `finalize-state.sh` already reflect a recovered `pr-created` run. `any_stall` stays true, the normalized outcome remains `stalled`, and merge-downgrade signaling (e.g. `IMPLEMENT_MERGE_DOWNGRADED`) never fires even though `summary-final.md` should report `pr-created`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass in_memory_stall_tracking="false" (or read durable layers only) when evaluating merge downgrade from ship-seed-input.env and execution-issues.md, matching the Step 18a.5 post-clear-stall contract.


