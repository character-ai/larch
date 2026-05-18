## Goal
Fix Cursor NOT_SUBSTANTIVE silent slot drops and missing scoreboard rows

## Implementation Plan

Issue #2323: Cursor reviewer/voter narrative-only failures + scoreboard hides dead slots

Three independent fixes:

### Fix A: NOT_SUBSTANTIVE retry in collect-agent-results.sh (section 3.6)

After section 3.5 which downgrades OK→NOT_SUBSTANTIVE, add section 3.6 that:
1. Scans RESULTS for STATUS=NOT_SUBSTANTIVE entries
2. For each, reads .meta sidecar to get launch params
3. If OUTER_LAUNCHER path is available: prepend structured-output demand to a temp
   copy of the prompt file; re-launch via OUTER_LAUNCHER with the stronger prompt
4. If only CMD_JSON available: re-launch via run-external-agent.sh (same as section 3)
5. Waits for retry sentinels (same wait-for-reviewers.sh approach as section 3)
6. Runs substantive validator on retry output; if passes → update to OK, else keep NOT_SUBSTANTIVE

Files changed:
- scripts/collect-agent-results.sh (add section 3.6, ~60 lines)
- scripts/collect-agent-results.md (document new behavior)
- scripts/test-collect-agent-results.sh (add NOT_SUBSTANTIVE + retry test case)
- scripts/test-collect-agent-results.md (update)

### Fix B: Dead slots in scoreboard (tally-code-votes.sh)

Add --collector-results-file FILE param to tally-code-votes.sh.
After main scoreboard awk block, read collector-results-file to build
reviewer_basename→STATUS map. Read archetype_map for expected reviewers.
For manifest entries not present in score_rows, emit a row:
  | cursor-specialist-structure | 0 | 0 | 0 | 0 | … | 0 | NOT_SUBSTANTIVE |

Files changed:
- skills/review/scripts/tally-code-votes.sh (add param + dead-slot rows, ~40 lines)
- skills/review/scripts/tally-code-votes.md (document new param)
- skills/review/scripts/review-core.sh (pass --collector-results-file to tally)
- skills/review/scripts/review-core.md (update)
- skills/review/scripts/test-tally-code-votes.sh (add 7-slot test)
- skills/review/scripts/test-tally-code-votes.md (update)

### Fix C: Degraded reviewer banner in voting-tally.md

Three sub-changes:
C1. check-reviewer-failure-threshold.sh: add NOT_SUBSTANTIVE_COUNT output key
C2. tally-code-votes.sh: add --not-substantive-count N flag; when N>0 emit banner
    "⚠ Degraded code-review panel: N reviewer slot(s) emitted narrative-only output (NOT_SUBSTANTIVE)"
C3. review-core.sh: capture NOT_SUBSTANTIVE_COUNT from threshold, pass to tally

Files changed:
- skills/review/scripts/check-reviewer-failure-threshold.sh (+NOT_SUBSTANTIVE_COUNT)
- skills/review/scripts/check-reviewer-failure-threshold.md (update)
- skills/review/scripts/test-check-reviewer-failure-threshold.sh (add test)
- skills/review/scripts/test-check-reviewer-failure-threshold.md (update)
- skills/review/scripts/tally-code-votes.sh (add --not-substantive-count)
- skills/review/scripts/review-core.sh (wire NOT_SUBSTANTIVE_COUNT → tally)


## Test plan
After implementing: make lint (runs all test harnesses).
