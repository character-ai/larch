### FINDING_3: Synthetic dynamic drop keys bypass collector dedupe
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: When a dropped dynamic row cannot resolve a basename, the synthetic `dyn-slot:{slot}:{tool}` fallback key no longer matches the collector/output key that may already exist for the same reviewer. A `dyn-*` drop row with no basename match still falls into `count_once(base=_synthetic_dynamic_drop_key(...))` even if the same slot already has a collector record under its real basename, so one dynamic failure can be counted twice, `FAILED_SLOTS` and `COUNTED_SLOTS` inflate, an OK collector record can be flipped to ERROR, and the threshold can trip early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Key the fallback on the same slot identity as the collector row, or skip the synthetic branch when that slot/tool pair has already been counted.
  - From Codex-Innovation: Skip the synthetic basename path. Dedup unresolved dynamic drops by slot/tool identity, or check the synthetic key against both collector and output records before incrementing counts.
  - From Codex-Pragmatic: Carry a real output basename through the dropped row, or suppress the synthetic fallback unless the slot has no earlier collector/output record.


### FINDING_4: `cap_hit` collector status not treated as success in `_failed_reviewers`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds `round_dir/collector-results.env` as a primary failure source but does not pin success semantics. Reusing `_collector_failure_records` (`status != "OK"`) or an equivalent filter counts `cap_hit` slots as failures. Threshold accounting treats `cap_hit` as success (`status_success` includes `cap_hit`), so committed runs can show inflated `Reviewer slot failures` after this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When merging collector-results.env, use `collect_results.parse_collector_records` and count only records whose `STATUS` is neither `OK` nor `cap_hit` (match `check_reviewer_failure_threshold` success semantics). Keep `round-meta.json` fallback behavior unchanged.


### FINDING_5: Settled-round dropped-reviewer warnings lost after successful retry
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: If the first `review_core_capture` attempt drops a dynamic reviewer and the retry succeeds, the plan reads only the final core and threshold files. The first attempt's `DYNAMIC_FAILED_SLOTS` or `DYNAMIC_DROPPED_SLOTS` counters are overwritten before `_surface_dropped_reviewer_warning` runs, so dynamic failures can still end with no warning even though the round did drop a dynamic reviewer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Persist a per-attempt accumulator across retries, or merge the first attempt's dynamic-drop summary into the final threshold state before surfacing warnings.
  - From Codex-Requirements: Persist or merge the first-attempt dynamic failure summary before rerunning the round, then surface from the merged record.


### FINDING_6: `STRAGGLER_DROPPED_COUNT` / `WATERFALL_WARN` threshold-env merge undersourced
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires appending `STRAGGLER_DROPPED_COUNT` and `WATERFALL_WARN` after threshold parse, but review core today writes only `threshold_result.stdout`. The threshold CLI does not emit those keys; only `dispatch_panel` forwards them (once `WATERFALL_WARN` forwarding lands). If the implementer treats the append step as redundant with threshold stdout, the threshold env file omits dispatch straggler metadata and the dynamic-qualified STRAGGLER backstop in `_surface_dropped_reviewer_warning` cannot fire when `DYNAMIC_*` counters stay zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After writing threshold stdout to `review-core-threshold.env`, append `STRAGGLER_DROPPED_COUNT` and `WATERFALL_WARN` from the parsed `dispatch` dict (not from threshold stdout). Keep `DYNAMIC_*` / `DROPPED_SLOTS` from the threshold parse. Add a review-core test that dispatch-forwarded `STRAGGLER_DROPPED_COUNT` survives into the threshold env file.


### FINDING_7: Later output-file checks can downgrade collector OK to ERROR
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan only gives collector precedence for dropped rows. A slot that collector recorded as OK can be counted again from the `--reviewer-output-files` list and flipped back to ERROR, so the new slot accounting is still wrong on a real launch path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Skip output-file counting for basenames already seen from collector records, or make `count_once` source-aware so later sources cannot downgrade collector OK.


