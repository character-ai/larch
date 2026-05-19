## Goal
Fix parsing-corrupted reviewer names in scoreboard and missing dynamic slot rows

## Implementation Plan

### Bug 1: reviewer_for_block() matches any line with "Reviewer" (scripts/lib-vote-tally.sh:35-50)

Fix: anchor the awk pattern to match only canonical attribution lines:
  - `- **Reviewer**: ...` or `- **Reviewers**: ...` (bolded, the canonical form in voting-protocol.md)
  - `Reviewer: ...` or `Reviewers: ...` at line start (unbolded fallback)
Pattern: `^[[:space:]-]*\*\*Reviewers?\*\*:` OR `^[[:space:]-]*Reviewers?:`

Preserve the FS=: split and trailing-text extraction after matching.

### Bug 2: Dynamic slots completely absent from scoreboard (skills/review/scripts/tally-code-votes.sh:462)

Fix: Remove the `if (normed ~ /^dyn-/) continue` guard in the dead-slot awk block.
Dynamic slots that produce zero findings should still get a scoreboard row (STATUS=OK).

### Bug 3: STATUS=UNKNOWN for static zero-finding slots (skills/review/scripts/tally-code-votes.sh:464)

Fix: Change default from "UNKNOWN" to "OK":
  `st = (normed in collector_status) ? collector_status[normed] : "OK"`
A slot that ran, produced output, but found zero findings → STATUS=OK.
STATUS=UNKNOWN should only appear for genuinely unclassified/error cases.

### Regression tests (scripts/test-lib-vote-tally.sh)

Add under "# reviewer_for_block":
1. Block with "Reviewer" in prose body (not attribution) → unknown
2. Block with "Reviewer" in embedded colon sentence → unknown  
3. Block with "- **Reviewer**: cursor-specialist-correctness-output.txt" → correct name
4. Block with "- **Reviewers**: slot-a, slot-b" → "slot-a, slot-b"
5. Block with unbolded "Reviewer: name" at line start → "name"

### Documentation updates

- scripts/lib-vote-tally.md: update reviewer_for_block() contract to reflect anchored pattern
- scripts/test-lib-vote-tally.md: note new regression cases

## Test plan
(no test plan section in plan-file)
