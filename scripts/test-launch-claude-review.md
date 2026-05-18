# test-launch-claude-review.sh — contract

Regression harness for `scripts/launch-claude-review.sh`.

Covers: output passthrough, `.done` sentinel, `--agent-file` path, subprocess validation error propagation (#2292), subprocess-stderr tempfile cleanup, `--role voter` skips context-file forwarding (#2324), `--role reviewer` forwards diff context, and invalid `--role` validation.

Primary: `scripts/launch-claude-review.md`.
