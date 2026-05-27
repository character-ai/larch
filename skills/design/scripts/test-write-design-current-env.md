# test-write-design-current-env.sh — contract

Regression harness for `scripts/write-design-current-env.sh`.

## Coverage

1. Sourceable output sets `DESIGN_TMPDIR`, `SESSION_TMPDIR`, `SESSION_ID`,
   `MANUAL_REQUESTED`, `ISSUE_NUMBER`, reviewer booleans, and `CLAUDE_PLUGIN_ROOT` exactly as
   passed; PID-keyed stable symlink `current-design-env-<pid>.sh` points at
   `--output`.
2. Shell-quoting via `printf '%q'` survives a `--design-tmpdir` value
   containing a space.
3. Atomic write leaves no `.tmp.*` files on success.
4. Re-runs are idempotent: the stable symlink for a given `--claude-pid`
   follows the latest run, and re-sourcing the symlink reflects the latest
   values.
5. Argv validation rejects relative `--design-tmpdir` and malformed
   `--session-id`.
6. Two distinct `--claude-pid` values produce independent symlinks and
   independent sourced session state (concurrency invariant). The harness
   exercises the two slots **sequentially**; it does not simulate interleaved
   concurrent `ln -sfn` races (non-goal for this contract file).
7. Invalid `--claude-pid` values (`0`, empty when the flag is passed, non-numeric, eight digits, leading
   zero) are rejected before symlink update.
8. Omitting `--claude-pid` uses the legacy `current-design-env.sh` symlink
   and emits a stderr transition warning.

## Edit-in-sync

Register this harness in the top-level `Makefile` (`test-*` cluster) and
keep coverage aligned with the writer's contract documented in
`scripts/write-design-current-env.md`.
