# Review Round 2

- Mode: `diff`
- 3 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Unparseable `collect-results` early return skips `write_reviewer_status_tsv`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-path-lookup-output.txt, dyn-tsv-contract-output.txt
- **Severity**: important
- **Concern**: When `collect-results` exits non-zero and stdout has no parseable records, `execute_round` returns at 577–588 before `write_reviewer_status_tsv()` runs. Manifest slots may be fully launched and `collector-results.env` may exist on disk, but no `reviewer-status.tsv` or `latest-reviewer-status.tsv` is written, so `panel-failed` terminals after broken collection still leave the post-notification table empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Invoke write_reviewer_status_tsv() on this path so manifest slots get skipped/failed rows before returning.
  - From cursor-specialist-edge-cases-output.txt: Call write_reviewer_status_tsv (or manifest-only variant) before the early return at 577-588
  - From dyn-path-lookup-output.txt: Call write_reviewer_status_tsv (or a shared helper) on that exit path too, before return; all manifest slots can map to skipped when no records parse. Add a regression test for collect_rc != 0 with empty/unparseable collector output.
  - From dyn-tsv-contract-output.txt: Call write_reviewer_status_tsv (or a shared helper that marks all manifest slots skipped/failed from available state) on every terminal round exit, including pre-collection failures when plan-review-slots.ndjson exists; add regression tests for dispatch-failed and empty-collector early exits.


### FINDING_6: Missing regression test for subprocess `reviewer-status` fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers `_run_round_body` materializing `reviewer-status.tsv` when `RUN_STEP3_PLAN_REVIEW_LOOP_SH` subprocess omits the file. The override seam is how harnesses stub Step 3; fallback breakage can pass `py-test` while stub rounds never create `round-N/reviewer-status.tsv` or `latest-reviewer-status.tsv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test_plan_review.py case seeding manifest and collector-results.env then exercising _run_round_body subprocess branch.
  - From cursor-specialist-testing-output.txt: Add a test_plan_review.py stub-round test: subprocess stub seeds manifest/collector artifacts but omits reviewer-status.tsv; assert _run_round_body materializes round-N/reviewer-status.tsv and latest-reviewer-status.tsv


### FINDING_7: `PANEL_PRUNED_EMPTY` path leaves stale `latest-reviewer-status.tsv`
- **Reviewer(s)**: codex-generic-output.txt, dyn-tsv-contract-output.txt
- **Severity**: important
- **Concern**: The pruned-empty round path (`PANEL_PRUNED_EMPTY=true`, 539–552) returns before refreshing or clearing `latest-reviewer-status.tsv`. In multi-round `/design`, a prior round can populate `latest`, then a pruned-empty round launches no reviewers but the post-notification renderer still reads stale per-slot statuses from the previous round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: before this early return, write a current empty/header-only plan-review/round-N/reviewer-status.tsv and sync it to latest, or remove/clear latest-reviewer-status.tsv when no slots were launched. Add a regression test with a stale latest file plus panel_pruned_empty=True.
  - From dyn-tsv-contract-output.txt: Call write_reviewer_status_tsv (or a shared helper that marks all manifest slots skipped/failed from available state) on every terminal round exit, including pre-collection failures when plan-review-slots.ndjson exists; add regression tests for dispatch-failed and empty-collector early exits.


