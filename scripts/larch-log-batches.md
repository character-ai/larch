# larch-log-batches.sh contract

`scripts/larch-log-batches.sh` is the source of truth for larch log batch
slugs, file extensions, write modes, and sanitizer hooks.

The table intentionally covers the legacy tracking sections as durable files:
`plan-goals-test`, `plan-review-tally`, `code-review-tally`,
`review-findings-full`, `diagrams`, `version-bump-reasoning`, `oos-issues`,
`run-statistics`, `token-report`, `timing-report`, `execution-issues`, and
`session-transcript` (the redacted Claude Code session transcript captured at
Step 18 for full post-hoc auditability).

Edit in sync with `scripts/larch-log.sh`, `scripts/larch-log.md`, and
`scripts/test-larch-logs-batches.sh`.
