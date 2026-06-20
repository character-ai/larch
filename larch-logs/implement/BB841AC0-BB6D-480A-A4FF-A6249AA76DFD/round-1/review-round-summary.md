# Review Round 1

- Mode: `diff`
- 6 accepted, 13 rejected (0 neutral)

## Accepted Findings

### FINDING_2: correctness: python/test_voting.py (and sibling test modules)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-required tests for neutralization sidecar coverage artifact restore and pipeline wiring were not added; no python test files changed vs main. Regressions in anonymous ballots sidecar fail-closed tally or round-2 ballot rebuild ship without CI detection. Add planned tests in test_voting.py test_plan_review.py test_review_tally.py test_review_pipeline.py test_agent_voters.py per acceptance criteria.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: python/test_voting.py
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] The branch adds substantial voting/sidecar logic but ships no tests in the plan-required test modules. Regressions such as round-2 ballot reuse, missing sidecar coverage, or silent anonymous scoring can merge undetected; acceptance criteria explicitly require pytest coverage. Add unit tests in test_voting.py and integration tests in test_plan_review.py, test_review_tally.py, test_review_pipeline.py, and test_agent_voters.py per the plan testing strategy.
- **Suggested revision**: Address the concern above.


### FINDING_19: `5ea150e25` — Apply relevant-checks fixes (dead-code removal in `review_tally.py`)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `5ea150e25` — Apply relevant-checks fixes (dead-code removal in `review_tally.py`) The feature commit touches 11 files (Python voting pipeline + docs/skills). **No test files were changed.**
- **Suggested revision**: Address the concern above.


### FINDING_20: **risk-integration** `python/test_voting.py` (plan-required, absent from diff) — The plan and acceptance criteria require new unit tests for `neutralize_reviewer_attribution`, `proposer_map_from_ballot`, `validate_proposer_map_coverage`, `restore_reviewer_attribution`, `proposer_for_item` fail-closed behavior, and body-text preservation (`Codex`/`Cursor`/`Claude` unchanged). None of the five plan-listed test modules (`test_voting.py`, `test_plan_review.py`, `test_review_tally.py`, `test_review_pipeline.py`, `test_agent_voters.py`) appear in the branch diff. **Suggested fix:** Add the plan-specified cases to those modules (start with `test_voting.py` for pure helpers, then pipeline/round integration tests).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `python/test_voting.py` (plan-required, absent from diff) — The plan and acceptance criteria require new unit tests for `neutralize_reviewer_attribution`, `proposer_map_from_ballot`, `validate_proposer_map_coverage`, `restore_reviewer_attribution`, `proposer_for_item` fail-closed behavior, and body-text preservation (`Codex`/`Cursor`/`Claude` unchanged). None of the five plan-listed test modules (`test_voting.py`, `test_plan_review.py`, `test_review_tally.py`, `test_review_pipeline.py`, `test_agent_voters.py`) appear in the branch diff. **Suggested fix:** Add the plan-specified cases to those modules (start with `test_voting.py` for pure helpers, then pipeline/round integration tests).
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: python/voting.py:244-356
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] New neutralization and proposer-map behavior has no accompanying test changes despite explicit plan requirements. CI would not catch dispatching attributed ballots, missing OOS sidecar coverage, or neutralized findings being scored as anonymous. Add the plan-required tests across python/test_voting.py, python/test_plan_review.py, python/test_review_tally.py, python/test_review_pipeline.py, and python/test_agent_voters.py.
- **Suggested revision**: Address the concern above.


### FINDING_37: **risk-integration** `python/voting.py`, `python/plan_review_tally.py`, `python/review_tally.py`, `python/review_pipeline.py` — The implementation plan’s acceptance criteria require new regression tests for neutralization, sidecar coverage, scoreboard attribution, and post-vote artifact restoration (`test_voting.py`, `test_plan_review.py`, `test_review_tally.py`, `test_review_pipeline.py`). Commit `4fe1d49c1` ships none of them. The attribution split (anonymous ballot vs sidecar-backed scoring/artifacts) has no automated guard against silent regression. **Suggested fix:** Add the planned tests, at minimum: neutralized ballot + sidecar restores original reviewer lines in accepted/rejected/OOS outputs; missing sidecar on neutralized ballot fails tally; MAV/re-tally without `--proposer-map-file` fails or auto-binds the sidecar.
- **Reviewer**: dyn-artifact-attribution-output.txt
- **Concern**: - **risk-integration** `python/voting.py`, `python/plan_review_tally.py`, `python/review_tally.py`, `python/review_pipeline.py` — The implementation plan’s acceptance criteria require new regression tests for neutralization, sidecar coverage, scoreboard attribution, and post-vote artifact restoration (`test_voting.py`, `test_plan_review.py`, `test_review_tally.py`, `test_review_pipeline.py`). Commit `4fe1d49c1` ships none of them. The attribution split (anonymous ballot vs sidecar-backed scoring/artifacts) has no automated guard against silent regression. **Suggested fix:** Add the planned tests, at minimum: neutralized ballot + sidecar restores original reviewer lines in accepted/rejected/OOS outputs; missing sidecar on neutralized ballot fails tally; MAV/re-tally without `--proposer-map-file` fails or auto-binds the sidecar.
- **Suggested revision**: Address the concern above.


