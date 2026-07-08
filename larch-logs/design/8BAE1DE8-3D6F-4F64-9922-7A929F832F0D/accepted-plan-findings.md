### FINDING_1: Normalize table-form revote rows before merging
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Targeted revote merging filters only anchored `ID:` lines, so parseable markdown-table vote rows can be dropped and the retally can keep stale under-quorum or JUDGE_ERROR results instead of incorporating the successful revote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_merge_targeted_voter_outputs`, normalize each revote file with `voting._normalize_markdown_table_votes` (or equivalent) before extracting/appending ballot-id vote lines; add a test with table-formatted revote output for an under-quorum id.
  - From Cursor-Pragmatic: In `_merge_targeted_voter_outputs`, run `_normalize_markdown_table_votes` on each revote file (or extract normalized anchored lines per `UNDER_QUORUM_ITEMS`) before appending; keep case-insensitive `FINDING_N`/`OOS_N` matching consistent with `parse_judge_vote`.
  - From Codex-Pragmatic: Normalize revote text with the existing markdown-table vote normalization before filtering, or convert matching table rows for under-quorum ids into anchored ID: vote lines before appending
  - From Codex-Requirements: Normalize revote text with the same table-to-anchored logic used by parse_judge_vote before filtering, or preserve matching markdown table rows, and cover this in the targeted success test.


### FINDING_2: Keep prune-ledger clearing/refresh on successful targeted retries
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: A successful targeted revote can leave the reviewer-prune ledger stale or uncleared, so later rounds may prune or retain reviewers using the pre-revote classification instead of the final retally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After targeted or full retry settles and post-retry `_core_round_state` shows a non-prune status, keep the existing `_clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)` guard before downstream warning/coder work; extend the targeted-success test to assert the prune ledger is cleared when degradation clears.
  - From Cursor-Innovation: In `_run_under_quorum_revote` / the degraded branch, when the final tally is clean and `degraded_this_round` is cleared, call `_clear_reviewer_prune_round` under the same `not _reviewer_prune_status_records(core_status)` guard used after `review_core_capture`.
  - From Codex-Pragmatic: After successful targeted retally, run the same prune-ledger record step as review_core_body with the updated classification TSV and panel manifest, or clear the round row if no valid classification exists
  - From Codex-Requirements: After the final targeted tally classification is written, run the existing prune-ledger recording path with reviewer-prune-ledger.tsv, panel-manifest.ndjson, and the final classification file, and assert the ledger reflects the retally.


### FINDING_3: Load scope-files for targeted retally from first-pass gather artifacts
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Targeted tally arguments can omit the first-pass `--scope-files` context, which may cause the retally to diverge from the initial scoped run and reclassify drifted findings differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `_build_targeted_tally_args`, load `round_dir/review-core-gather.env` and pass `FILE_LIST_FILE` as `--scope-files` when the file exists, matching `_tally_voted_ballot` parity.


### FINDING_4: Carry session and implement context into targeted emit-tally
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Targeted emit-tally needs the same session and implement context as the first-pass emit path so OOS serialization and parent-copy behavior stay aligned; omitting these flags can leave OOS or classification artifacts on the stale snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build targeted emit argv through the same extras as `_emit_tally_with_context`: add `--session-env-path` from `args.session_env_path` and `--implement-tmpdir` from `IMPLEMENT_TMPDIR` when set.
  - From Cursor-Requirements: Mirror `_emit_tally_with_context`: forward `--session-env-path` and `--implement-tmpdir` whenever first-pass artifacts provide them, and extend the success test to assert both flags on the emit argv.


### FINDING_5: Fail closed when targeted retally returns main-agent-vote-required
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: If a targeted retally collapses to main-agent-vote-required, continuing through the normal emit path can write the wrong rejected/OOS artifacts instead of handing control back to the existing full-panel fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: If targeted retally yields `TALLY_STATUS=main-agent-vote-required`, either run the MAV emit branch verbatim or return false before replacing round artifacts so the existing full-panel fallback runs.


### FINDING_6: Expand the retry gate to include dynamic degradation signals
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The targeted-retry gate treats the panel as healthy when `FAILED_SLOTS=0`, but dynamic failed/dropped-slot counters or straggler-drop evidence can still indicate a degraded panel that should take the full fresh-panel retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the dynamic slot counters from `review-core-threshold.env` and the existing dropped-slot evidence to the fail-closed gate before allowing `_run_under_quorum_revote`.


### FINDING_7: Do not rerun first-pass capture when the degraded-retry sentinel already settled
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: A resumed round can rerun `review_core_capture` even though the retry already completed, which can overwrite settled artifacts and then skip the retry paths because `degraded-retry.done` is already present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Short-circuit before the first `review_core_capture` when the done sentinel exists, or restore the settled artifacts instead of rerunning the round body.


### FINDING_8: Include required dispatch-voters flags in the targeted retry path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Targeted voter dispatch can fail validation or run with the wrong round context unless the required `dispatch-voters` flags are included alongside the optional context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add those three required flags to the targeted dispatch argv (sourced from `_run_round` args / first-pass round context) in `_run_under_quorum_revote`, and assert them in the targeted success test stub capture.


### FINDING_9: Preserve the pre-fallback OOS append in the fresh-panel retry path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The full-fallback retry path can lose attempt-1 OOS accumulation semantics if it skips the pre-fallback append before rerunning the first-pass capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When `targeted_ok` is false and the branch calls `review_core_capture`, keep the existing pre-fallback `_append_round_oos_artifact` call before the full retry, unchanged from current `_run_round`.


