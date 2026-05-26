# test-launch-claude-review.sh — contract

Regression harness for `scripts/launch-claude-review.sh`.

Covers: output passthrough, `.done` sentinel, `--agent-file` reviewer path, subprocess validation error propagation (#2292), subprocess-stderr tempfile cleanup, voter and reviewer diff-context forwarding validation, `--agent-file --role voter` rejection, invalid `--role` validation, repeatable `--context-files` reviewer and voter paths, missing-value `--context-files` validation for trailing and flag-like next tokens, non-existent and unreadable context exit-2 handling, canonical dedup via rendered prompt, positive allow-root propagation, and subprocess symlink-rejection propagation.

Primary: `scripts/launch-claude-review.md`.
