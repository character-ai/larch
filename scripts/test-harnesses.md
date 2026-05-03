# scripts/test-harnesses.sh — contract

`scripts/test-harnesses.sh` is the parallel runner invoked by the Makefile's `test-harnesses` target. It enumerates harness commands by running `make -n _test-harnesses-list` (the `_test-harnesses-list` target lists every regression harness as a prerequisite — single source of truth for "what counts as a harness"), then runs them with up to `MAX_JOBS` (default 10) concurrent workers. Each worker's stdout+stderr is captured to a tmpfile; output blocks are printed serially in submission order with `===== <cmd> — PASS|FAIL (exit N) =====` headers, never interleaving. Any non-zero harness exit causes the script to exit 1 after all harnesses finish.

`scripts/test-test-harnesses.sh` is its regression test, wired into `make` via the `test-test-harnesses` target which is a prerequisite of `_test-harnesses-list` (so the runner exercises itself).

## Authoring a new harness

To add a new harness:

1. Define a `test-<name>:` target in `Makefile` whose recipe is **exactly one line** of the form `bash <repo-relative-path-to-script> [<simple-args>...]`. Multi-line recipes, `&&` chains, command substitution, pipes, redirections, and embedded shell metacharacters are **rejected** by the runner's whitelist regex (the runner exits 2 with a diagnostic listing the offending recipe). This keeps the `eval` surface narrow.
2. List `test-<name>` as a prerequisite of `_test-harnesses-list`.
3. Both `make test-<name>` (direct) and `make test-harnesses` (parallel via this script) will pick it up.

## Hermeticity

Harnesses run in parallel and share a single working tree, `git` metadata, and tmp namespace. Authors **must** ensure each harness is hermetic:

- Use `mktemp -d` for any scratch space; never write under `$REPO_ROOT`.
- Do not run `git` commands that mutate the worktree state (e.g., `git checkout`, `git commit`, `git stash`) without first cd'ing into a private fixture repo.
- Do not depend on, or mutate, environment variables that other harnesses might read (PATH manipulation must be confined to a subshell).
- Do not bind to fixed network ports.
- Cleanup-on-exit is the harness's responsibility (typical pattern: `trap 'rm -rf "$WORKDIR"' EXIT INT TERM`).

A non-hermetic harness is a flaky test waiting to happen — it may pass when `MAX_JOBS=1` (serial) and fail intermittently under contention.

## Tunables

| Env var | Default | Constraint |
|---------|---------|------------|
| `MAX_JOBS` | `10` | Positive integer ≥ 1. Invalid values exit 2 with a diagnostic. |
| `POLL_MS` | `100` | Non-negative integer; clamped to a 10ms minimum to prevent CPU spin. |

## Portability

Bash 3.2 portable (no `wait -n`, no `mapfile`, no associative arrays) so it runs on macOS's stock `/bin/bash` and on Linux. The signal handler kills in-flight workers on `INT`/`TERM` so Ctrl-C / CI cancellation does not leave background processes running.
