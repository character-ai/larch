# slack-issue-announce.sh

Posts the optional Step 16a Slack notification when
`LARCH_SLACK_WEBHOOK_URL` is set.

Usage:

```bash
slack-issue-announce.sh --implement-tmpdir PATH
```

All session state is read from files under `IMPLEMENT_TMPDIR` rather than
CLI arguments to reduce non-determinism and context bloat:

- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID`
- `ship-pr-state.sh` → `PR_URL`, `PR_TITLE`
- `session-id` → `RUN_ID` fallback

Output:

- `STATUS=posted|skipped|failed`
- `REASON=webhook-not-set|issue-not-set` when skipped
- `ERROR=<message>` on failure
