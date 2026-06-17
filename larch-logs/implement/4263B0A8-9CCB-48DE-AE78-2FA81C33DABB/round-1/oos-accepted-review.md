### OOS_1: correctness: python/pr_body.py:973-975
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] write_final_report passes in_memory_stall_tracking="" which falls back to os.environ STALL_TRACKING After panel-failed recovery clear-stall clears durable layers but orchestrator env still has STALL_TRACKING=true; outcome normalizes to stalled and IMPLEMENT_MERGE_DOWNGRADED stays false so merge-downgrade warning never appears Pass in_memory_stall_tracking=false when durable stall layers are cleared or distinguish explicit empty string from unset
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: python/stall_recovery.py:339,python/pr_body.py:974
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty in_memory_stall_tracking falls back to process STALL_TRACKING env After recovery orchestrator may still export STALL_TRACKING=true while ship state shows pr-created; outcome becomes stalled and merge_downgraded never fires Add _resolve_in_memory_stall_tracking and pass in_memory_stall_tracking=false from write_final_report
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/pr_body.py:973-974
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] write_final_report passes in_memory_stall_tracking="" which falls back to os.environ STALL_TRACKING in normalized_outcome_values After panel-failed Step 5 recovery clear-stall clears state files but orchestrator process env may still export STALL_TRACKING=true causing outcome=stalled and IMPLEMENT_MERGE_DOWNGRADED=false so the merge downgrade warning never appears in summary-final.md Implement _resolve_in_memory_stall_tracking per plan and pass in_memory_stall_tracking="false" from write_final_report
- **Suggested revision**: Address the concern above.


### OOS_4: **correctness** `python/pr_body.py:973-975` — `write_final_report` calls `normalized_outcome_values` with `in_memory_stall_tracking=""`. In `stall_recovery.py:339`, an empty value is falsy and falls through to `os.environ.get("STALL_TRACKING", "false")`. On the panel-failed recovery path, Step 5 sets orchestrator `STALL_TRACKING=true` before Step 16–17, and Step 18b re-invokes `write_final_report` after `step8-shippr`. If that process env is still `true` while durable `ship-pr-state.sh` / `finalize-state.sh` already show `STALL_TRACKING=false`, `any_stall` stays true, `IMPLEMENT_NORMALIZED_OUTCOME` becomes `stalled` instead of `pr-created`, and `merge_downgraded` (which requires `outcome == "pr-created"` at `stall_recovery.py:372-378`) never fires. The new tests avoid this by not polluting `STALL_TRACKING` in the environment. This breaks acceptance criterion 3 in the real orchestrator flow. **Suggested fix:** Pass an explicit memory layer into `write_final_report`, e.g. `in_memory_stall_tracking="false"` when all durable stall layers are false (matching Step 18a.5 after `clear-stall`), or change `normalized_outcome_values` so `""` means “ignore memory layer” rather than “read process env”. Align `skills/implement/SKILL.md:870` (“same helper used by final-report write”) with the actual call site.
- **Reviewer**: dyn-review-gate-output.txt
- **Concern**: - **correctness** `python/pr_body.py:973-975` — `write_final_report` calls `normalized_outcome_values` with `in_memory_stall_tracking=""`. In `stall_recovery.py:339`, an empty value is falsy and falls through to `os.environ.get("STALL_TRACKING", "false")`. On the panel-failed recovery path, Step 5 sets orchestrator `STALL_TRACKING=true` before Step 16–17, and Step 18b re-invokes `write_final_report` after `step8-shippr`. If that process env is still `true` while durable `ship-pr-state.sh` / `finalize-state.sh` already show `STALL_TRACKING=false`, `any_stall` stays true, `IMPLEMENT_NORMALIZED_OUTCOME` becomes `stalled` instead of `pr-created`, and `merge_downgraded` (which requires `outcome == "pr-created"` at `stall_recovery.py:372-378`) never fires. The new tests avoid this by not polluting `STALL_TRACKING` in the environment. This breaks acceptance criterion 3 in the real orchestrator flow. **Suggested fix:** Pass an explicit memory layer into `write_final_report`, e.g. `in_memory_stall_tracking="false"` when all durable stall layers are false (matching Step 18a.5 after `clear-stall`), or change `normalized_outcome_values` so `""` means “ignore memory layer” rather than “read process env”. Align `skills/implement/SKILL.md:870` (“same helper used by final-report write”) with the actual call site.
- **Suggested revision**: Address the concern above.


### OOS_5: correctness: python/stall_recovery.py:372-378
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] merge_downgraded requires stall-recovery-classification.env but clear_stall deletes that file before Step 18b write_final_report Panel-failed recovery runs step8-shippr then clear-stall then Step 18b; classification env is gone so IMPLEMENT_MERGE_DOWNGRADED stays false and the warning never renders Persist downgrade markers in durable ship/finalize/seed state before clear-stall or infer downgrade without the deleted classification file
- **Suggested revision**: Address the concern above.


