### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py
- **Concern**: Normalize revote voter text before selective merge. Scenario: The plan’s `_merge_targeted_voter_outputs` step appends only `^{id}:` lines, but `voting.parse_judge_vote` first runs `_normalize_markdown_table_votes` (#5078). Codex revotes can arrive as markdown-table rows; without the same normalization, the merge appends nothing, retally reuses first-pass JUDGE_ERROR votes, and the targeted path fails the bug’s acceptance criteria while still returning success.
- **Proposed resolution**: In `_merge_targeted_voter_outputs`, normalize each revote file with `voting._normalize_markdown_table_votes` (or equivalent) before extracting/appending ballot-id vote lines; add a test with table-formatted revote output for an under-quorum id.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/round_runner.py
- **Concern**: Preserve reviewer-prune clear on clean targeted retry. Scenario: The refactored degraded-branch pseudocode omits today’s post-retry `_clear_reviewer_prune_round` call when `_reviewer_prune_status_records(core_status)` is false. Dropping it during the targeted-success path is a behavioral regression versus the current full fresh-panel retry.
- **Proposed resolution**: After targeted or full retry settles and post-retry `_core_round_state` shows a non-prune status, keep the existing `_clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)` guard before downstream warning/coder work; extend the targeted-success test to assert the prune ledger is cleared when degradation clears.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:512-513
- **Concern**: Mirror full-retry prune-ledger housekeeping after a successful targeted revote. Scenario: The full fresh-panel path clears the round prune ledger when retry settles cleanly (`_clear_reviewer_prune_round` at lines 512-513). The targeted path only refreshes `core` and tally sinks; it never clears or re-records prune state, so round-1 ledger rows can stay tied to the pre-revote classification while accepted/rejected outputs reflect the retally.
- **Proposed resolution**: In `_run_under_quorum_revote` / the degraded branch, when the final tally is clean and `degraded_this_round` is cleared, call `_clear_reviewer_prune_round` under the same `not _reviewer_prune_status_records(core_status)` guard used after `review_core_capture`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:773-773
- **Concern**: Resolve scope-files for targeted retally from first-pass gather artifacts. Scenario: First-pass tally gets `--scope-files` from `review-core-gather.env` `FILE_LIST_FILE` when argv omits it. The plan forwards scope only when a scope path artifact exists, but does not name `review-core-gather.env`, so targeted `tally-code-votes` can omit scope and reclassify drifted findings differently (see `review_tally._scope_drift`).
- **Proposed resolution**: In `_build_targeted_tally_args`, load `round_dir/review-core-gather.env` and pass `FILE_LIST_FILE` as `--scope-files` when the file exists, matching `_tally_voted_ballot` parity.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:460-472
- **Concern**: Forward emit-tally session and implement context on the targeted path. Scenario: `review_core_body._emit_tally_with_context` appends `--session-env-path` and `--implement-tmpdir` after the base emit argv. The plan mirrors only the base emit bundle, so targeted `emit-tally` can miss OOS serialization context (`review_tally.emit_tally` / `oos serialize`).
- **Proposed resolution**: Build targeted emit argv through the same extras as `_emit_tally_with_context`: add `--session-env-path` from `args.session_env_path` and `--implement-tmpdir` from `IMPLEMENT_TMPDIR` when set.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:1118-1126
- **Concern**: Fail closed when targeted retally returns main-agent-vote-required. Scenario: `review_core_body` uses a different emit path when `TALLY_STATUS=main-agent-vote-required` (clears `rejected-findings.md` before emit). The plan always runs the normal emit bundle after any `TALLY_STATUS`, so a revote that collapses to MAV can emit the wrong rejected/OOS artifacts.
- **Proposed resolution**: If targeted retally yields `TALLY_STATUS=main-agent-vote-required`, either run the MAV emit branch verbatim or return false before replacing round artifacts so the existing full-panel fallback runs.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:11-20
- **Concern**: 1. Targeted retry gate ignores dynamic reviewer-slot degradation signals. Scenario: `FAILED_SLOTS=0` can still coexist with `DYNAMIC_FAILED_SLOTS`, `DYNAMIC_DROPPED_SLOTS`, or straggler drops. The plan would send those rounds down the under-quorum-only path instead of the required full fresh-panel retry.
- **Proposed resolution**: Add the dynamic slot counters from `review-core-threshold.env` and the existing dropped-slot evidence to the fail-closed gate before allowing `_run_under_quorum_revote`.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:57-80
- **Concern**: 2. `degraded-retry.done` does not stop the initial first-pass capture on re-entry. Scenario: A resumed round with a completed retry can still run `review_core_capture` again, overwrite `voting-tally.md` and `review-core.env`, and then skip both retry paths because `degraded-retry.done` is already present.
- **Proposed resolution**: Short-circuit before the first `review_core_capture` when the done sentinel exists, or restore the settled artifacts instead of rerunning the round body.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py
- **Concern**: Normalize table-format revote votes before selective merge. Scenario: `_merge_targeted_voter_outputs` only appends lines matching `^{id}:`, but `voting.parse_judge_vote` first runs `_normalize_markdown_table_votes` (#5078). Codex voters often emit markdown-table votes, so targeted revote output can be ignored, merged files keep first-pass under-quorum votes, and full retally still leaves `UNDER_QUORUM_*` set even when the revote succeeded.
- **Proposed resolution**: In `_merge_targeted_voter_outputs`, run `_normalize_markdown_table_votes` on each revote file (or extract normalized anchored lines per `UNDER_QUORUM_ITEMS`) before appending; keep case-insensitive `FINDING_N`/`OOS_N` matching consistent with `parse_judge_vote`.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/voting.py:461-481
- **Concern**: The targeted merge drops supported markdown-table revote rows because the plan filters only raw ^ID: lines. Scenario: A voter returns a valid table row for FINDING_1; parse_judge_vote would accept it, but the merge omits it, so retally keeps the original JUDGE_ERROR and the targeted revote does not actually settle the affected item
- **Proposed resolution**: Normalize revote text with the existing markdown-table vote normalization before filtering, or convert matching table rows for under-quorum ids into anchored ID: vote lines before appending

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_tally.py:721-738
- **Concern**: The plan retallies in round_dir while also requiring failure to leave final artifacts untouched. Scenario: tally-code-votes truncates accepted/rejected/OOS sinks before it can return without TALLY_STATUS; a targeted retally failure can clobber attempt-1 artifacts before the fallback path settles
- **Proposed resolution**: Stage targeted tally outputs outside final round artifacts, or snapshot and restore every final tally sink on absent TALLY_STATUS before falling back

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:1127
- **Concern**: The targeted retally plan does not refresh the reviewer-prune ledger after replacing the classification TSV. Scenario: A targeted revote changes accepted/rejected outcomes, but round 2 pruning still reads the first-pass classification record and can prune or keep reviewer slots using stale results
- **Proposed resolution**: After successful targeted retally, run the same prune-ledger record step as review_core_body with the updated classification TSV and panel manifest, or clear the round row if no valid classification exists

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py
- **Concern**: Targeted voter dispatch contract omits required dispatch-voters flags. Scenario: Step 4 lists only optional context flags, but `agent dispatch-voters` requires `--codex-available`, `--cursor-available`, and `--round-num`. A targeted re-vote can fail validation or launch with wrong round context while the pure under-quorum path otherwise qualifies.
- **Proposed resolution**: Add those three required flags to the targeted dispatch argv (sourced from `_run_round` args / first-pass round context) in `_run_under_quorum_revote`, and assert them in the targeted success test stub capture.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py
- **Concern**: Targeted emit-tally is missing session/implement context parity. Scenario: `_build_targeted_emit_args` lists tally/mode/scout args only. `emit-tally` uses `--session-env-path` for OOS sequencing, parent OOS sinks, classification path selection, and warning sidecars, and `--implement-tmpdir` for parent copies. Omitting them can leave OOS/classification artifacts on the first-pass snapshot after an otherwise successful targeted retally.
- **Proposed resolution**: Mirror `_emit_tally_with_context`: forward `--session-env-path` and `--implement-tmpdir` whenever first-pass artifacts provide them, and extend the success test to assert both flags on the emit argv.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/review/test_review_and_fix.py
- **Concern**: Success test covers only one under-quorum id. Scenario: Acceptance criteria and the reported run used multiple under-quorum items. A single-id fixture can pass while comma-separated extraction, restricted-ballot completeness, and selective merge regress for multi-id rounds.
- **Proposed resolution**: Extend the targeted success fixture to `UNDER_QUORUM_ITEMS=FINDING_1,FINDING_2` (or five ids) and assert the restricted ballot, merge, and retally inputs include every requested id.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/round_runner.py
- **Concern**: Full-fallback OOS append step is not preserved in the new retry flow. Scenario: The plan requires full fresh-panel retry behavior to stay intact, but the refactored branch omits the pre-fallback `_append_round_oos_artifact` call that today runs before the second `review_core_capture`. Full-fallback rounds can lose attempt-1 OOS accumulation semantics.
- **Proposed resolution**: When `targeted_ok` is false and the branch calls `review_core_capture`, keep the existing pre-fallback `_append_round_oos_artifact` call before the full retry, unchanged from current `_run_round`.

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py
- **Concern**: Targeted voter merge drops valid table-formatted revote rows. Scenario: The plan filters revote output only with ^{id}: lines, but existing vote parsing normalizes markdown table rows before tallying. A targeted voter that emits a parseable table vote for FINDING_1 would be discarded, so the retally can keep the stale under-quorum result and skip the full fallback.
- **Proposed resolution**: Normalize revote text with the same table-to-anchored logic used by parse_judge_vote before filtering, or preserve matching markdown table rows, and cover this in the targeted success test.

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/round_runner.py
- **Concern**: Prior refresh fix is incomplete: targeted retally does not refresh the reviewer prune ledger. Scenario: The full review_core_body path rewrites reviewer-prune-ledger.tsv from the final classification. The targeted path can change an under-quorum item outcome but leave the first-pass ledger in place, so a later round can prune reviewers using stale accepted/rejected counts.
- **Proposed resolution**: After the final targeted tally classification is written, run the existing prune-ledger recording path with reviewer-prune-ledger.tsv, panel-manifest.ndjson, and the final classification file, and assert the ledger reflects the retally.
