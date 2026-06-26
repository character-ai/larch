# Review Round 2

- Mode: `diff`
- 9 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: run_replay never parses slot-v2 vote or computes before/after YES-rate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: blocking
- **Concern**: `run_replay` dispatches slot-v2 voters and records dispatch metadata (`VOTER_2_PATH`, status, tool, parse-rate KVs) but never opens the emitted vote file, parses YES/NO for the row’s `finding_id`, stores `after_vote`, or emits cohort before/after YES-rate summary. Replay can report `REPLAY_STATUS=ok` while the plan’s dispatch-voters calibration measurement and acceptance criterion remain unverified in-repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After dispatch, read VOTER_2_PATH, parse finding_id with voting.parse_judge_vote, emit after_vote and cohort YES-rate summary; add tests with mocked dispatch output.
  - From codex-specialist-correctness-output.txt: Require launched and OK, verify the expected basename, and parse the slot-v2 vote file before reporting success.
  - From cursor-specialist-edge-cases-output.txt: After dispatch parse voter output with voting.parse_judge_vote; hard-fail on empty vote; emit ROW_N_AFTER_VOTE and cohort YES_RATE_BEFORE/YES_RATE_AFTER summary
  - From codex-specialist-edge-cases-output.txt: read the emitted slot-v2 vote file, parse the vote token from it, include that parsed vote in the replay output, and hard-fail the row when the file is missing, empty, or unparsable.
  - From cursor-specialist-testing-output.txt: Parse voter output with voting.parse_judge_vote emit after_vote and cohort YES-rate summary add mocked and/or live integration coverage
  - From codex-specialist-testing-output.txt: Read the file named by VOTER_2_PATH, parse the vote, and hard-fail on unreadable or malformed output before accepting the row.
  - From codex-generalist-output.txt: After `_dispatch_voters_for_row`, parse `VOTER_2_PATH` with the existing vote parser for that row’s `finding_id`, fail closed unless it yields YES or NO, store `after_vote`, and emit per-row plus aggregate before/after YES-rate fields.
  - From dyn-dyn-calibration-replay-output.txt: After the guard checks, resolve `VOTER_2_PATH` against `repo_root` / `ballot_path.parent`, parse the row’s `finding_id` vote with `voting.parse_judge_vote`, hard-fail on empty/unparseable votes, store `after_vote` per row, emit `ROW_*_AFTER_VOTE` and a summary `YES_RATE` / `BEFORE_YES_RATE`, and add an offline unit test that mocks dispatch output plus a vote file to lock the parsing path.


### FINDING_2: VOTER_2_PARSE_RATE_STATUS guard fails open on missing or empty values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: `_dispatch_voters_for_row` treats a missing, empty, or non-`OK` `VOTER_2_PARSE_RATE_STATUS` as replay success. Dispatch stdout regressions that omit parse-rate KVs or emit blank/`SKIPPED` values can still advance replay and count toward after-rate measurement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require VOTER_2_PARSE_RATE_STATUS == OK exactly; fail closed otherwise.
  - From cursor-specialist-edge-cases-output.txt: Require VOTER_2_PARSE_RATE_STATUS == OK exactly; fail closed on missing or other values
  - From cursor-specialist-testing-output.txt: Require VOTER_2_PARSE_RATE_STATUS==OK and VOTER_2_STATUS==launched add unit test for missing KVs
  - From codex-specialist-testing-output.txt: Require the field to be exactly OK and fail closed on missing or empty parse-status output.
  - From dyn-dyn-calibration-replay-output.txt: Require `kv.get("VOTER_2_PARSE_RATE_STATUS") == "OK"` explicitly, and fail closed when the key is absent or blank.


### FINDING_3: Non-empty fixture_diff allowed when diff_required=false
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Rows with `diff_required=false` may carry a non-empty `fixture_diff`. A no-diff row with a stray diff path silently gains diff context and changes the replayed vote versus production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Reject non-empty fixture_diff when diff_required=false, or ignore it and fail closed.


### FINDING_4: Missing fixture_ballot silently falls back to log reconstruction
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: When a manifest row names a non-empty `fixture_ballot` path that is missing or unreadable, validation and replay clear the path and fall back to `findings.md` or jsonl reconstruction. `MANIFEST_STATUS=ok` can pass while replay uses a different ballot source than the manifest freeze contract specifies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: If fixture_ballot is non-empty, require the file and fail closed before falling back to logs.
  - From codex-specialist-edge-cases-output.txt: if `fixture_ballot` is populated, require the file to exist and abort validation or replay instead of dropping into the log-based fallback.
  - From dyn-dyn-calibration-replay-output.txt: If `fixture_ballot` is non-empty after strip, require the resolved path to exist and be readable; raise `CalibrationReplayError` instead of falling back. Only use jsonl/findings fallback when the manifest column is intentionally empty.


### FINDING_5: Committed ballot fixtures leak post-vote Vote tally footers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generalist-output.txt
- **Severity**: important
- **Concern**: Frozen replay ballots include `Vote tally:` footers absent from production pre-vote ballots. `dispatch-voters` therefore sees prior-round tally text; votes may diverge from historical production context and measure anchoring on old panel outcomes instead of prompt quality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Remove Vote tally lines from fixtures or strip them in rebuild_single_item_ballot/validation before dispatch
  - From codex-generalist-output.txt: Re-freeze ballots from the pre-tally production ballot text, strip any `Vote tally:` / rejected-subtype wrapper from fixtures and jsonl fallback reconstruction, and add validation that committed `fixture_ballot` files contain no historical vote tallies.


### FINDING_6: _jsonl_record fuzzy prose_body fallback can reconstruct wrong ballot
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_jsonl_record()` falls back to the first jsonl row whose `prose_body` merely contains `### {finding_id}:` when exact `id`/`round_num` match is absent. Another finding quoting the same heading can supply unrelated content instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: require an exact `id` plus `round_num` match, or raise a reconstruction error when the exact row is absent instead of guessing from substring matches.


### FINDING_7: Committed manifest omits historical diffs for diff-mode review rounds
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: All manifest rows set `diff_required=false` with no diff fixtures though source review rounds ran in diff mode. Replay omits `--diff-file` and changes plan-fidelity voter context versus production for omission findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Freeze per-row historical diffs set diff_required=true add diffs/ fixtures and pass --diff-file in run_replay


### FINDING_9: Duplicate cohort keys hidden by set comparison in _validate_cohort_binding
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_validate_cohort_binding` compares manifest and cohort rows as sets, hiding duplicate labeled rows. Repeated `(finding_id, run_id, round_num)` keys can pass validation and double-count in `run_replay`, corrupting denominator and YES-rate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Reject duplicate (finding_id, run_id, round_num) keys explicitly or compare row multiplicities instead of sets.


### FINDING_10: Dispatch stdout guards fail open beyond parse-rate (STATUS, TOOL, path)
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: important
- **Concern**: Replay hard guards accept weak dispatch metadata compared with the production-parity contract: `VOTER_2_STATUS=ok` instead of `launched`, missing `VOTER_2_PARSE_RATE_STATUS` treated as success, missing `VOTER_2_TOOL` defaulted to expected tool, and slot-v2 path/basename not verified before counting a cohort row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Require exactly `VOTER_2_STATUS=launched`, exactly `VOTER_2_PARSE_RATE_STATUS=OK`, a present `VOTER_2_TOOL` equal to the manifest row, and a present slot-v2 path with the expected basename before counting the row.


