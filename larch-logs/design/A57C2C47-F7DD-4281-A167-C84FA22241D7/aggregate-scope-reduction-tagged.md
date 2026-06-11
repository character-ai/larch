### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/voting.py:1-1
- **Concern**: [SCOPE-REDUCTION] Four absorbed surfaces have no production callers after tally rewrites. Scenario: ballot-parse.sh tally-vote.sh and scoreboard.sh are only referenced by their own harnesses and each other; tally-code-votes.sh and tally-plan-review.sh inline scoreboard logic and never call those scripts; false-positive-keywords.sh has no live repo consumer beyond its deleted harness
- **Proposed resolution**: Retire the four scripts and harnesses without adding ballot-parse tally-vote scoreboard or false-positive-match CLI verbs; keep parity via python/test_voting.py fixtures only where harness assertions still add signal

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-bash-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-vote-tally.sh:137-155
- **Concern**: [SCOPE-REDUCTION] Plan requires split-ballot duplicate detection before writes, but bash creates the output directory and writes each block as it scans before failing on a later duplicate. Scenario: Implementing a pre-scan or no-partial-writes guarantee adds behavior and complexity beyond the current migration contract for duplicate ballots
- **Proposed resolution**: Remove the before-writes/no-partial-writes requirement, or state that duplicate detection is streaming and may leave already-written block files just like split_ballot_to_blocks
