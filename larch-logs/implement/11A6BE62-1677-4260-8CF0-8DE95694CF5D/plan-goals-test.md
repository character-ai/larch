## Goal
Restore the two-path exoneration classifier in classify_result() that was silently reverted by PR #2428

## Implementation Plan
Restore multi-voter exoneration branch in lib-vote-tally.sh (issue #2446)

## Context

PR #2428 silently replaced PR #2423's two-path exoneration condition in
`scripts/lib-vote-tally.sh::classify_result()` with a narrower condition
requiring YES > 0. This caused 0/0/N→rejected misclassifications (59+
documented across 9 post-29.8.39 runs, amplified by the 2-judge round-2
panel introduced in #2419/#2426).


### File 1: scripts/lib-vote-tally.sh (lines 132-136)

Replace the buggy narrow condition:
```bash
    # Multi-voter exoneration intentionally stays narrow: keep the legacy path
    # only when at least one reviewer voted YES, at least one voted EXONERATE,
    # and nobody voted NO.
    elif (( yes > 0 && exonerate > 0 && no == 0 )); then
        printf 'exonerated'
```

With the PR #2423 two-path condition:
```bash
    # Exoneration has two intentional paths:
    # 1. Legacy zero-NO panels: any EXONERATE vote with no NO votes exonerates.
    # 2. Mixed panels: EXONERATE must meet-or-beat NO and strictly exceed YES.
    elif (( exonerate > 0 && (no == 0 || (exonerate >= no && exonerate > yes)) )); then
        printf 'exonerated'
```

### File 2: scripts/test-lib-vote-tally.sh (lines 201-205)

Update test assertions to reflect correct behavior after the fix.
Cases that change (verify manually against the two-path condition):
- Line 201: classify_result 0 0 3 3 → "exonerated" (was "rejected"); label update too
- Line 202: classify_result 0 1 1 3 → "exonerated" (was "rejected"); 1E>=1N and 1E>0Y
- Line 203: classify_result 0 1 2 3 → "exonerated" (was "rejected"); 2E>=1N and 2E>0Y
- Line 204: classify_result 0 2 1 3 → still "rejected" (1E<2N); no change
- Line 205: classify_result 1 2 3 3 → "exonerated" (was "rejected"); 3E>=2N and 3E>1Y

Also add a behavioral-invariant assertion that the canonical condition string
is present in lib-vote-tally.sh, to prevent future silent reverts.

### File 3: scripts/lib-vote-tally.md (line 32)

Update the `classify_result` multi-voter description from the buggy narrow
rule to the correct two-path description.

### File 4: docs/voting-process.md

Add a "Multi-voter Exoneration" section documenting the two-path rule and a
brief note about the #2446 revert+restore history.

### File 5: CHANGELOG.md

Add entry for the fix.

## Testing Strategy

After implementation:
1. Run `scripts/test-lib-vote-tally.sh` — must pass
2. Verify the specific 0/0/3→exonerated assertion passes and would fail against
   the reverted version
3. Run `/relevant-checks` for markdownlint and agent-lint

## Test plan
(no test plan section in plan-file)
