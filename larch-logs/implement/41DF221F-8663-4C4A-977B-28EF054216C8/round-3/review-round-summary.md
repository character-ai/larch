# Review Round 3

- Mode: `diff`
- 4 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_1: v2_vote not validated before YES_RATE_BEFORE
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: `_before_vote` returns raw `v2_vote` without requiring exactly `YES` or `NO`. Blank, missing, or malformed historical votes are uppercased and counted in `YES_RATE_BEFORE` as non-YES instead of failing closed. `validate_manifest_row` does not pre-check that the classification TSV exists, the row is present, or `v2_vote` is valid, so `MANIFEST_STATUS=ok` can precede a corrupted denominator or a late replay failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: require each matched `v2_vote` cell to be exactly `YES` or `NO` and raise `CalibrationReplayError` on blank or unexpected values.
  - From dyn-dyn-calibration-replay-output.txt: During `validate_manifest_row`, resolve the classification TSV the same way `_before_vote` does, require the file and `finding_id` row, and require `v2_vote` to be exactly `YES` or `NO`; surface any failure as a manifest validation error.
  - From dyn-dyn-calibration-replay-output.txt: After loading the classification row, hard-fail unless `v2_vote.strip().upper()` is `YES` or `NO`; add unit tests for missing/invalid `v2_vote` in both `_before_vote` and `validate_manifest_row`.


### FINDING_2: Round-2 replay omits prior-round findings ledger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: For `round_num>1` cohort rows, replay dispatches voters without seeding the prior-round findings ledger that production slot-v2 voters received. After-rate votes therefore lack the “Prior-round findings ledger” judge context, so before/after comparison can measure prompt changes plus missing ledger context rather than prompt changes alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-calibration-replay-output.txt: Extend the replay contract with an optional frozen ledger fixture per row (or reconstruct ledger rows from committed `findings-classification.tsv` for rounds `< round_num`), write it under the row `review_tmpdir` before `dispatch-voters`, and pass `--findings-ledger-file` so `render voter` matches production for multi-round replays.


### FINDING_8: fixture_ballot shape and finding_id not validated
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `validate_manifest_row()` only checks that `fixture_ballot` is readable and lacks a `Vote tally:` footer, then `rebuild_single_item_ballot()` trusts that file verbatim after neutralization. A zero-byte file, headerless text, a cross-wired ballot, or a fixture outside the calibration ballots directory can pass validation and replay the wrong ballot, so measured before/after YES-rates no longer correspond to the labeled cohort row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: validate the frozen ballot shape before accepting it, require exactly one `### FINDING_/OOS_` heading whose ID matches `finding_id`, and reject empty or multi-item fixtures instead of treating any readable text file as a valid `fixture_ballot`.
  - From codex-specialist-testing-output.txt: Reject ballot fixtures outside the calibration ballots dir and require a single heading that matches finding_id.


### FINDING_13: Path traversal in _resolve_voter_path and rebuild_ballot_main
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_resolve_voter_path` accepts absolute paths and relative paths containing `..`, so a malformed `VOTER_2_PATH` from dispatch can open a file outside the row work dir. The same root-prefix omission in `rebuild_ballot_main` when joining `--fixture-ballot` onto `repo_root` can read arbitrary local files instead of the committed ballot fixture, producing bogus after-rate evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: reject absolute and parent-traversal paths in both entry points, or route them through `_resolve_repo_path` with canonicalization and root-prefix enforcement before any read.
  - From codex-specialist-testing-output.txt: Reject absolute or ..-escaped paths and only parse files rooted under the row tmpdir.


