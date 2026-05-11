# add-blocked-by.sh contract

`skills/block-issue/scripts/add-blocked-by.sh` adds a native GitHub blocked-by dependency between two issues using the `addBlockedBy` GraphQL mutation.

## Inputs

| Argument | Required | Description |
|---|---|---|
| `ISSUE_A` (positional 1) | yes | Issue to be marked as blocked |
| `ISSUE_B` (positional 2) | yes | Issue that blocks ISSUE_A |
| `--repo owner/name` | no | Repository; auto-detected via `gh repo view` if omitted |

Both issue numbers must be positive integers.

## Output

Success (exit 0):
```
SUCCESS=true
✓ #<ISSUE_A> is now blocked by #<ISSUE_B>
```

Failure (exit 1): `ERROR=<message>` on stderr.

## Behavior

1. Auto-detects repo from `gh repo view` when `--repo` is omitted.
2. Resolves both issue numbers to GraphQL node IDs in a single `gh api graphql` call.
3. Calls `addBlockedBy(input: {issueId: <A>, blockingIssueId: <B>})`.
4. Verifies by comparing `issue_dependencies_summary.blocked_by` on issue A before and after. A non-increase is warned but not treated as a hard error (already-blocked is acceptable).
5. Requires `python3` in PATH for JSON parsing of the GraphQL node-ID response.

## Callers

- `skills/block-issue/SKILL.md` Step 1 — the only caller.

## Edit-in-sync rules

Changes to flag names, exit codes, stdout keys (`SUCCESS=`, `ERROR=`), or the GraphQL mutation call must update this file in the same PR.
