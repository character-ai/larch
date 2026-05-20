## Goal
Fix classify_result() so unanimous EXON votes produce exonerated, not rejected

## Implementation Plan

Fix voting classifier bug where unanimous EXON votes (0 YES, 0 NO, N EXON) are
misclassified as "rejected" instead of "exonerated".

### Root Cause
`scripts/lib-vote-tally.sh::classify_result()` line 132 has:
  elif (( yes > 0 && exonerate > 0 && no == 0 ));
The `yes > 0` guard incorrectly requires at least one YES vote. With 0 YES, 0 NO,
3 EXON the guard fails and control falls to `else printf 'rejected'`.

### Changes

1. **`scripts/lib-vote-tally.sh`** — fix the condition at line 132:
   - Before: `elif (( yes > 0 && exonerate > 0 && no == 0 ))`
   - After:  `elif (( exonerate > 0 && exonerate >= no && exonerate > yes ))`
   Semantics: EXON wins when it has at least as many votes as NO and strictly
   more than YES. Consistent with the eligible==1 branch which has no yes > 0
   guard (line 122: `elif (( exonerate > 0 ))`).

2. **`scripts/test-lib-vote-tally.sh`** — add missing test case in the
   classify_result section, after existing tests:
   - `classify_result 0 0 3 3` should return `exonerated` (bug case)


## Test plan
Run `bash scripts/test-lib-vote-tally.sh` — all tests pass including the new
0Y/0N/3E case.
Also run `/relevant-checks` to validate pre-commit and agent-lint.
