# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Vote sourcing mismatch between tally and agreement rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_voter_agreement_row_for_item` switched vote sourcing from `vote_for_id` to `parse_judge_vote` while `_tally_votes_for_id` still uses `vote_for_id`. A voter file with `FINDING_1: YES SEVERITY=major` followed by `FINDING_1:` comment (no vote token) can be counted YES by tally and accepted, but the live severity scoreboard omits that YES/major; offline TSV calibration still counts it from `vN_vote`/`vN_severity`. Tally and agreement therefore disagree on vote and severity attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Build agreement votes with `vote_for_id` and attach severity from `parse_judge_vote` (or use one parser for tally and agreement).


