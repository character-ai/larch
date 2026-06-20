### OOS_2: [OUT_OF_SCOPE] correctness: CLI numeric bounds not validated
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `--min-votes` and `--outlier-threshold` in `skills/voter-calibration/scripts/voter-calibration.py:177-178` are not range-validated; negative `min_votes` or thresholds outside `[0, 1]` can yield misleading outlier tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add argparse validation (e.g. `min_votes >= 1`, `0.0 <= outlier_threshold <= 1.0`) with a clear stderr message and exit `2`.


### OOS_3: [OUT_OF_SCOPE] risk-integration: integration tests only spot-check voter parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance calls for live tally vs committed-TSV parity via `compute_voter_agreement(voter_agreement_rows_from_tsv(...))`. Integration tests in `python/test_plan_review.py:896-899` and `python/test_review_tally.py:598-602` only spot-check one voter field (e.g. Codex `disagree`, cursor-pragmatism `disagree`) rather than asserting full record equality against the scoreboard. `test_voter_agreement_tsv_and_panel_parity` in `python/test_voting.py` already covers the shared math path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `assert records == voting.compute_voter_agreement(...)` (or parse scoreboard rows) in the mixed plan-review and three-slot code-review fixtures.


