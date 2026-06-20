# Review Round 3

- Mode: `diff`
- 2 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Panel-dispatch failure leaves stale `latest-reviewer-status.tsv`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-robustness-output.txt
- **Severity**: important
- **Concern**: When `panel.returncode != 0`, the round exits before materializing or syncing current-round `reviewer-status.tsv`. On round 2+, `latest-reviewer-status.tsv` can still hold prior-round slot rows while the orchestrator binds the current round for the post-notification table, showing stale done/failed/skipped icons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On panel.returncode != 0, call write_reviewer_status_tsv when manifest exists or write header-only round-N/reviewer-status.tsv and sync_latest_reviewer_status to clear stale latest.
  - From codex-generic-output.txt: In this branch, write/sync a current round status file before returning, and add a regression test with stale `latest-reviewer-status.tsv` plus a failing panel-dispatch stub.
  - From dyn-robustness-output.txt: On panel dispatch failure, materialize a header-only or all-`skipped` `reviewer-status.tsv` from the current manifest (same pattern as the pruned-empty branch at lines 550–558), or explicitly truncate `latest-reviewer-status.tsv` so the orchestrator does not read cross-round data.


### FINDING_2: Stale `collector-results.env` when collection is skipped or not refreshed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-robustness-output.txt
- **Severity**: important
- **Concern**: `write_reviewer_status_tsv` always reads `collector-results.env` from disk while `_compose_findings_from_collector` uses in-memory `collect_out`. When collection is skipped (`paths_path` missing/empty), subprocess fallback does not refresh the file, or a prior round’s records remain on disk, status rows can show done/failed from stale collector data while findings are empty or belong to another round. Basename-only join can falsely mark a current-round slot done from a prior-round OK record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: When collection is skipped, overwrite collector-results.env with empty output or pass collect_out into write_reviewer_status_tsv so status matches in-memory collection.
  - From codex-generic-output.txt: Normalize the full reviewer path while stripping `-phase2`, `-phase3`, and `-retry`, or pass fresh collector output into `write_reviewer_status_tsv` and avoid basename-only fallback across rounds.
  - From dyn-robustness-output.txt: Pass the current round’s collector text into `write_reviewer_status_tsv` (or write/clear `collector-results.env` whenever collection is skipped) so the TSV is built from the same source as `_compose_findings_from_collector`.


