# Review Round 2

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_7: Multi-part idempotent retry drops continuation URLs from ndjson
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multi-part OOS issues make idempotent retry drop continuation URLs from run-log output because only the first matched part enters `already` and `_write_oos_ndjson` overwrites ndjson. After a 3-part oversized OOS filing, a same-session Step 9a.1 retry matches only part 1, rewrites `oos-issues.ndjson` with one URL, and under-reports filed issues despite a complete sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: When `not blocks` and `persisted` is non-empty, build `filed` from full `persisted` (or all parts for each matched block); add a multi-part sentinel + accepted-input retry test asserting all part URLs remain in ndjson.


