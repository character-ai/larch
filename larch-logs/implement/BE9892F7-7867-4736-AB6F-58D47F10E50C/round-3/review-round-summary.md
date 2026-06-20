# Review Round 3

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_5: Plan-required live-vs-committed tally parity incomplete in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required live-vs-committed parity is only partial in mixed plan-review and three-slot code-review tally tests (`python/test_plan_review.py:891-951`, `python/test_review_tally.py:608-617`). Live tally vote assembly could diverge from classification TSV serialization while hardcoded tally substring checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Reuse the per-record line loop from `test_tally_excludes_narrative_only_voter_parse_rate_check` in both tests.


### FINDING_6: Zero-judge tally test lacks voter agreement scoreboard assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Code-review zero-judge tally test (`python/test_review_tally.py:408-423`) does not assert the new voter agreement scoreboard. Zero-judge path could regress to missing section or fake voter rows without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror `test_tally_plan_review_zero_voters_requires_main_agent` scoreboard assertions on `voting-tally.md`.


### FINDING_8: Schema support too loose in voting.py
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `python/voting.py:176-185` — schema support is too loose. Any TSV with only `reviewer_slots` or `finding_reviewers` is treated as supported, so `skills/voter-calibration/scripts/voter-calibration.py:168-176` will not count unknown schemas as skipped. A concrete failure is a review TSV with `finding_id reviewer_slots voting_result judge1_vote`: an accepted row is reported as an ineligible panel instead of an unsupported file, which hides parser drift and skews corpus counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Require the supported header shapes explicitly: design must include `voting_result` and `v1_vote` through `v3_vote` with optional `body_severity`; code review must match the 21-column tool shape or the 18-column compact shape. Return/count unsupported schemas as skipped files before row-level ineligible counting.
