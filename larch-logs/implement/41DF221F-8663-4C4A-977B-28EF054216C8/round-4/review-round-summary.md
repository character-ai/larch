# Review Round 4

- Mode: `diff`
- 4 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Prior-round ledger rows omit production parity fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-calibration-replay-output.txt
- **Severity**: important
- **Concern**: `_reconstruct_prior_round_ledger` seeds prior-round ledger rows with empty `vote_tally`, `reason`, and `file_line` and titles derived from jsonl `category` only. Production `review_tally._ledger_entry` derives title, `file_line`, `reason`, and `YES=N/3` vote tallies from neutralized ballot blocks. Roughly half the committed cohort replays at `round_num>1`, so slot-v2 voters receive a thinner “Prior-round findings ledger” than in production. Before/after YES-rate can change for reasons other than the rubric fix (missing judge duplicate/suppression context).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-dyn-calibration-replay-output.txt: Build each prior-round ledger entry from the same neutralized ballot reconstruction used for replay (or from jsonl `prose_body`), reusing `review_tally`'s `_ledger_title`, `_ledger_file_line`, `_ledger_reason`, and vote-tally derivation from `v1_vote`/`v2_vote`/`v3_vote` in `findings-classification.tsv`. Add a round-2 replay test that asserts non-empty `vote_tally` and `file_line` when the source ballot contains them.


### FINDING_8: Manifest validation accepts arbitrary repo paths and empty diffs
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: `validate_manifest_row()` (and related manifest validation) only checks that `run_id`, `fixture_plan`, and `fixture_diff` are present and repo-relative. It does not constrain paths to committed calibration fixture directories, does not reject empty `fixture_diff` placeholders, and does not validate `run_id` shape. A malformed manifest row can point replay at unrelated repo files, sibling run directories, or blank diff context while still passing validation, so after-rate no longer measures the frozen cohort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: validate `run_id` against an allowlisted run-id shape and require the derived run root plus `fixture_plan` and `fixture_diff` to stay under the expected calibration directories before replaying.
  - From codex-specialist-testing-output.txt: Constrain fixture_plan and fixture_diff to python/test_fixtures/plan-fidelity-calibration/plans/ and .../diffs/, and add a regression test that rejects paths outside those directories.


### FINDING_9: load_fixture_plan accepts pointer-only placeholder plans
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `load_fixture_plan()` accepts any non-empty text that is not a full plan-goals document but never rejects pointer-only placeholders such as `see plan.txt` or `tbd`. Because `validate_manifest_row()` does not reuse the extractor's pointer-only guard, a committed plan fixture can pass validation and feed placeholder content to `dispatch-voters` instead of production-shaped plan text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: share the pointer-only check from `extract_implementation_plan_from_plan_goals_test()` with the loader or manifest validator and fail closed on any stubbed plan body.


### FINDING_10: rebuild-ballot lacks calibration ballots-dir and shape/purity checks
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `rebuild_ballot_main()` accepts any repo-relative `--fixture-ballot` path and does not reapply calibration-ballots root containment, heading-shape, or vote-tally/purity checks enforced elsewhere. A direct rebuild call (including a mistyped path) can read or write arbitrary repo files, return success for empty or cross-wired input, and produce bogus frozen-ballot evidence that can poison replay fixtures or PR acceptance scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: run the same ballot-root, heading-shape, and vote-tally validations in `rebuild_ballot_main()` before calling `rebuild_single_item_ballot()`.


