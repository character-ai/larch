# tracking-issue-summary.sh contract

`scripts/tracking-issue-summary.sh` publishes slim marker-keyed tracking issue
comments. It replaces the old monolithic tracking-comment writer for status
summaries.

Supported verb:

```text
tracking-issue-summary.sh upsert-summary --issue N --marker '<!-- larch:... -->' --content-file F [--repo OWNER/REPO]
```

The marker must be the first line of the remote comment. Zero matching comments
creates a new comment; one matching comment patches it; multiple matches fail
closed. The body is redacted before publication.

`--repo`, when supplied or resolved from `gh repo view`, must match
`OWNER/REPO`; malformed values fail before issue/comment `gh` calls with
`FAILED=true`, `ERROR=invalid repo: expected OWNER/REPO`, exit 1.

Edit in sync with `scripts/test-tracking-issue-summary.sh`.
