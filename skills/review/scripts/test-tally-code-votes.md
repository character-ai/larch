# test-tally-code-votes.sh

Regression harness for `skills/review/scripts/tally-code-votes.sh`.

## Coverage

- 3-voter threshold: 2 YES accepts (in-scope), 1 YES rejects, OOS 2 YES accepted.
- Rejected OOS subtracts 1 from the reviewer score and appears in the `OOS-Rejected` scoreboard column.
- 2-voter unanimous: both YES accepts, 1Y/1N rejects (not unanimous).
- 1 voter: skip path with `VOTING_SKIPPED_WARNING`, all findings auto-accepted.
- `--both-down true`: bypass voting, all findings auto-accepted.
- Security-tag filter: accepted OOS with `focus-area = security` is counted but NOT written to `oos-accepted-review.md` (held locally).
- `--manifest-file`: writes `scout-archetype-yield.tsv`, maps static/dynamic/generalist rows, and normalizes fallback suffixes such as `-phase2`.

## Invocation

```bash
skills/review/scripts/test-tally-code-votes.sh
```

Exit 0 → pass, exit 1 → at least one assertion failed.
