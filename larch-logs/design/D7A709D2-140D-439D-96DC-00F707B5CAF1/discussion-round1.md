## Decision 1: Fix scope — literal count update vs. remove hardcoded count
- **Question**: Should the fix update the `Covers N cases` count to 21 (literal interpretation of the issue body), or remove the hardcoded count entirely per `.claude/rules/drift-prone-prose-in-docs.md`?
- **Resolution**: Remove the hardcoded count from the `test-step-7a` row. Rewrite to match the qualitative-coverage prose pattern of sibling rows (which describe coverage categories without numeric totals). Out of scope: greppping for hardcoded counts in other rows or other docs.
- **Source**: user (Step 1c clarification)

## Decision 2: Touch the harness?
- **Question**: Does the fix need any change to `skills/implement/scripts/test-step-7a.sh`?
- **Resolution**: No. The harness is correct; the drift is purely in the doc inventory row. Out of scope: any harness edits.
- **Source**: codebase (verified: 21 `new_case` invocations in `test-step-7a.sh`, the 3-token loop counts as 3 cases plus the bare `diagram-rejected` case, totaling 21)

## Decision 3: Bounded to the single inventory row?
- **Question**: Does the fix only touch the `test-step-7a` row in `docs/linting.md`, or does it also re-survey other inventory rows for stale counts?
- **Resolution**: Bounded to the single `test-step-7a` row. The user explicitly rejected the "remove hardcoded counts everywhere" option in Step 1c.
- **Source**: user (Step 1c clarification)
