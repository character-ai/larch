## Goal
Add a test case to `scripts/test-larch-log.sh` covering the `commit --no-push` staging path when `LARCH_LOG_ROOT` is unset and `IMPLEMENT_TMPDIR` is set, asserting that files appear under `larch-logs/<skill>/<run-id>/` inside a disposable git repo.

## Implementation Plan

### Context
`lib-larch-log.sh`'s `larch_log_root()` resolves the write root in priority order:
1. `$LARCH_LOG_ROOT` (if set)
2. `$IMPLEMENT_TMPDIR/larch-logs` (if set)
3. `$LARCH_LOG_REPO_ROOT/larch-logs` (the consuming repo)

The `commit` subcommand in `larch-log.sh` copies from `larch_log_run_dir` (which uses `larch_log_root`) to `larch_log_repo_run_dir` (always `$LARCH_LOG_REPO_ROOT/larch-logs/...`) when they differ.

The existing test always sets `LARCH_LOG_ROOT="$TMP/larch-logs"`, so `src_path == repo_path` and the copy branch never runs. The new test must exercise the copy branch.

### Files to modify
- `scripts/test-larch-log.sh` — append a new test section after the existing tests

### Approach
1. Create a disposable bare git repo (just enough for `git init`, `git add`, `git commit`) inside `$TMP`.
2. Unset `LARCH_LOG_ROOT`; set `IMPLEMENT_TMPDIR` to a sub-dir of `$TMP`.
3. Run `larch-log.sh init` (writes to `$IMPLEMENT_TMPDIR/larch-logs/...`).
4. Run `larch-log.sh write` for one batch (writes to same staging location).
5. Run `larch-log.sh commit --no-push` with `cwd` pointing at the disposable repo.
6. Assert the batch file exists at `$REPO_DIR/larch-logs/implement/<run-id>/<batch>.md`.
7. Restore `LARCH_LOG_ROOT` and unset `IMPLEMENT_TMPDIR` after the test section.

### Edge cases
- The disposable repo must have at least one commit so `git commit` in the `commit` subcommand succeeds (git refuses to commit if there's no HEAD).
- `IMPLEMENT_TMPDIR` must NOT equal the disposable repo root, so `src_path != repo_path` triggers the copy.

### Testing strategy
Run `/relevant-checks` after the edit; the test suite itself (`scripts/test-larch-log.sh`) will be invoked by `make test` / pre-commit as the verification.
