# test-write-design-current-env.sh — contract

Regression harness for `scripts/write-design-current-env.sh`.

## Coverage

1. Sourceable output sets `DESIGN_TMPDIR`, `SESSION_TMPDIR`, `SESSION_ID`,
   `ISSUE_NUMBER`, reviewer booleans, and `CLAUDE_PLUGIN_ROOT` exactly as
   passed.
2. Shell-quoting via `printf '%q'` survives a `--design-tmpdir` value
   containing a space.
3. Atomic write leaves no `.tmp.*` files on success.
4. Re-runs are idempotent: the stable symlink follows the latest run, and
   re-sourcing the symlink reflects the latest values.
5. Argv validation rejects relative `--design-tmpdir` and malformed
   `--session-id`.

## Edit-in-sync

Register this harness in the top-level `Makefile` (`test-*` cluster) and
keep coverage aligned with the writer's contract documented in
`scripts/write-design-current-env.md`.
