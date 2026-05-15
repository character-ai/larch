# gather-context.sh Contract

`skills/review/scripts/gather-context.sh` gathers `/review` context for diff and description modes.

Diff mode delegates directly to `${CLAUDE_PLUGIN_ROOT}/scripts/gather-branch-context.sh` after creating the output directory, then appends only its own envelope keys.

Description mode resolves the description with deterministic filesystem tools only: `git ls-files`, token matching, and fixed-string `rg`. Output paths are repo-relative existing non-symlink files with no `..`.

Stdout is `KEY=value` only: `DIFF_FILE`, `FILE_LIST_FILE`, `COMMIT_LOG_FILE`, `COMMIT_COUNT`, `SCOPE_FILES_COUNT`, and `MODE`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-gather-context.sh`, wired through `make test-gather-context`.
