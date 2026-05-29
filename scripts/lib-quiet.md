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
- `emit_kv KEY VALUE` writes `KEY=VALUE` to the caller-visible stream. Values must not contain `\n` or `\r`; the helper returns 2 with `larch_err` on violation. See `scripts/test-lib-quiet.sh` for reject coverage.
- `larch_err TEXT…` writes user-visible errors (argv validation, fatals) to the
  original stderr (FD 4 after init) so harnesses and operators still see them
  while incidental `echo`/`printf` chatter stays in the quiet log. The emitted
  text is mirrored into the quiet log and passed through
  `redact-secrets.sh --streaming` first.
- `larch_errf` is the `printf`-style variant for formatted user-visible errors
  (same routing and redaction contract as `larch_err`).
`LARCH_QUIET_DISABLE=1` leaves stdout/stderr unchanged. Test harnesses use that
override when they need direct access to stdout/stderr without quiet-log
redirection.

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

Family B scripts surface progress via `larch_err` / `larch_errf` on the
operator-visible stderr channel (FD 4 after `larch_quiet_init`).

## Harness

`scripts/test-lib-quiet.sh` exercises default redirect behavior, explicit log
paths, disable mode, nested init, contract emission, empty values, fallback
behavior when the log directory cannot be created, pure-filter disable
semantics, `larch_err` routing to real stderr, direct `redact-secrets.sh`
streaming redaction. It is wired
as `make test-lib-quiet`.
