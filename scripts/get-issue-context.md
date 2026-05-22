# scripts/get-issue-context.sh — contract

`scripts/get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH` fetches an upstream issue title and body with `gh issue view --repo "$REPO" --json title,body`, then atomically writes:

- `PATH/upstream-issue-title.txt`
- `PATH/upstream-issue-body.txt`

Primary caller: `/implement --forked --issue N` **Step 0** (forked upstream materialization). The issue body becomes `FEATURE_DESCRIPTION` only when the user-supplied `/implement` description is empty; a user-supplied description always wins. The upstream issue number stays orchestrator-local as `UPSTREAM_DESIGN_ISSUE`; fork mode does not set `ISSUE_NUMBER` from it.

Harness: `scripts/test-get-issue-context.sh`.
