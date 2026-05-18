# slack-issue-announce.sh

Posts the optional Step 16a Slack notification when
`LARCH_SLACK_WEBHOOK_URL` is set.

Usage:

```bash
slack-issue-announce.sh --pr-url URL --issue-number N --run-id ID [--pr-title TEXT]
```

Output:

- `STATUS=posted|skipped|failed`
- `REASON=webhook-not-set` when skipped
- `ERROR=<message>` on failure
