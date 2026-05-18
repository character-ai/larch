# test-launch-claude-review.sh — contract

Regression harness for `scripts/launch-claude-review.sh`.

Covers: output passthrough, `.done` sentinel, `--agent-file` reviewer path, subprocess validation error propagation (#2292), subprocess-stderr tempfile cleanup, voter and reviewer diff-context forwarding validation, `--agent-file --role voter` rejection, and invalid `--role` validation.

Primary: `scripts/launch-claude-review.md`.
