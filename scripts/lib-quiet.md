# lib-quiet.sh

Shared shell library for quiet-by-default larch helpers.

## Purpose

`scripts/lib-quiet.sh` lets executable scripts keep machine-readable stdout
stable while moving incidental stdout/stderr chatter into a log file. Callers
source the library and run `larch_quiet_init` after strict-mode setup and
`SCRIPT_DIR` initialization, before argument parsing.

## API

- `larch_quiet_init` duplicates the original stdout to file descriptor 3,
  duplicates the original stderr to file descriptor 4, sets
  `LARCH_QUIET_ACTIVE=1`, records `LARCH_QUIET_LOG_FILE`, and redirects ordinary
  stdout/stderr to the quiet log.
- `emit TEXT` writes one line of contract output to the caller-visible stream.
- `emit_kv KEY VALUE` writes `KEY=VALUE` to the caller-visible stream.
- `emit_breadcrumb --category=NAME TEXT` writes progress text to the quiet log
  by default and requires the fixed breadcrumb category vocabulary. Set
  `LARCH_QUIET_BREADCRUMBS=1` to surface breadcrumbs on caller stdout. When
  `LARCH_BREADCRUMB_STREAM` is set, it writes only the structured breadcrumb
  record. When `LARCH_QUIET_BREADCRUMB_FD` is set to an inherited numeric file
  descriptor, surfaced breadcrumbs write there instead of FD 3 so nested
  scripts can stay operator-visible even when their stdout is redirected into
  capture files.
- `emit_breadcrumb_stderr --category=NAME FORMAT [ARGS...]` is the stderr
  progress bridge for legacy `larch_errf` progress callsites. Without
  `LARCH_BREADCRUMB_STREAM`, it preserves `larch_errf` formatting and no-newline
  behavior. With a stream, it writes only a structured breadcrumb record in the
  fixed category vocabulary.
- `larch_err TEXT…` writes user-visible errors (argv validation, fatals) to the
  original stderr (FD 4 after init) so harnesses and operators still see them
  while incidental `echo`/`printf` chatter stays in the quiet log.
- `larch_errf` is the `printf`-style variant for formatted user-visible errors
  (same FD routing as `larch_err`).
- `larch_quiet_write_paired_pid_file` writes the caller's `$$` to
  `LARCH_PAIRED_PID_FILE` when that env var is set. It validates an absolute,
  non-symlink path with no `..` under the active session tmpdir, requires a
  writable parent directory, writes through `mktemp` in that parent, and
  publishes with `mv -f`. Invalid paths or write failures emit
  `WARN paired-pid-file-invalid` and return 0 so callers under `set -e` do not
  abort.

`LARCH_QUIET_DISABLE=1` leaves stdout/stderr unchanged. Test harnesses that
assert legacy stdout may use that override during migration.

## Authoring Rule

After `larch_quiet_init`, do not write user-visible diagnostics with raw
`>&2` on `echo`, `printf`, or `cat`. Use `larch_err` for line diagnostics and
`larch_errf` for formatted diagnostics. S041/no-raw-stderr-after-quiet-init
enforces this for runtime shell scripts so diagnostics reach the caller's
original stderr instead of the quiet log.

## Log Selection

Callers may set `LARCH_QUIET_LOG_FILE` or `LARCH_QUIET_LOG` to choose the log
path. Otherwise the library writes `larch-quiet-<script>-<pid>.log` under the
first available session tmpdir (`IMPLEMENT_TMPDIR`, `REVIEW_TMPDIR`,
`DESIGN_TMPDIR`, `RESEARCH_TMPDIR`) or `${TMPDIR:-/tmp}`.

## Invariants

- Nested sourcing is idempotent via `LARCH_LIB_QUIET_LOADED`.
- Nested initialization is idempotent via `LARCH_QUIET_ACTIVE`.
- Log-directory derivation uses shell parameter expansion rather than external
  `dirname`, so hook helpers still initialize in deliberately stripped `PATH`
  harnesses.
- Pure stdin-to-stdout filters must either avoid `larch_quiet_init` or set
  `LARCH_QUIET_DISABLE=1` before calling it, because their data stream is
  ordinary stdout rather than contract output.
- Paired PID ownership is restricted to top-level Family B entrypoints:
  `ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`,
  `collect-agent-results.sh`, and `dispatch-plan-voters.sh`. Nested children
  (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, and
  `dispatch-with-waterfall.sh`) must not call the helper; their parents unset
  `LARCH_PAIRED_PID_FILE` before invoking them. See
  `scripts/breadcrumb-monitor.md`.

`scripts/ship-pr.sh` and the review/review-and-fix tree (`skills/review/scripts/dispatch-panel.sh`, `skills/review/scripts/review-core.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`) opt into breadcrumb surfacing via `export LARCH_QUIET_BREADCRUMBS=1` set at their `/implement` invocation sites (`skills/implement/SKILL.md` Step 8+ block and `scripts/run-step5-review.sh`).

## Harness

`scripts/test-lib-quiet.sh` exercises default redirect behavior, explicit log
paths, disable mode, nested init, contract emission, breadcrumb suppression and
opt-in surfacing, empty values, fallback behavior when the log directory cannot
be created, pure-filter disable semantics, `larch_err` routing to real stderr,
and the paired PID writer's no-op, atomic-write, validation, fail-open, and
parallel-write behavior. It is wired as `make
test-lib-quiet`.
