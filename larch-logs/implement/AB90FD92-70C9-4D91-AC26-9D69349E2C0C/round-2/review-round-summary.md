# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Targeted-fetch `__fetch_failed__` blocks incentive gh fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Failed targeted-fetch stub for #5461 blocks incentive gh fallback when bulk lacks the issue. Bulk JSON omits #5461; a filed-OOS targeted fetch fails and writes `{number: 5461, __fetch_failed__: True}`; merged index is non-None so `_ground_truth_calibration_incentive_shipped` skips gh fallback and returns `calibration_incentive_not_shipped` despite a successful gh issue view 5461.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: For incentive resolution only treat __fetch_failed__ entries as absent or read bulk issues before merge; add regression test for bulk-missing + failed filed stub + successful gh fallback.


### FINDING_2: `run_dir_key` isolation not propagated to OOS dedupe identity
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The new `run_dir_key` isolation never reaches the identity that downstream OOS de-dupers actually use. `_row_from_block`, `_parse_oos_issues_created`, `_join_implement_run_records`, and `_append_design_accepted_block_records` still seed `identity` from bare `run_id`, and `fate_adjusted_oos_scoring` dedupes on that field. If `design/run-1` and `implement/run-1` both emit the same issue or stable ID, the second record can be dropped, so the normal report undercounts fate buckets and reviewer points even though verdict logic treats the runs as distinct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: build emitted `identity` tuples from `run_dir_key` instead of `run_id` everywhere they flow into OOS scoring, or change `fate_adjusted_oos_scoring` to key its `seen` sets on `run_dir_key` plus the local artifact identifiers.


### FINDING_5: Accepted-evidence filtering over-applies `run_dir_key` isolation
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: `_evidence_later_than_row` now rejects every `accepted-finding` whose `run_dir_key` differs from the row, and `_candidate_evidence_for_row` also filters accepted candidates to the same `run_dir_key`. A rejected finding in `implement/run-1` that resurfaces as an accepted finding in later `implement/run-2` is now reported as `rejected_not_observed`, even when both manifests prove later ordering, so the verdict undercounts realized outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Use `run_dir_key` only for same-run ordering and dedupe isolation. Allow different-run accepted evidence through, then let `started_at` ordering decide whether it is later.


