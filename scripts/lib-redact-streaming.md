# lib-redact-streaming.sh contract

Line-oriented wrapper around `scripts/redact-secrets.sh --streaming` for callers
that need persistent PEM redaction state across multiple line writes.

## Args

- `--state-file PATH` / `--state-file=PATH` (required): stores streaming PEM
  state.
- `-h`, `--help`: print usage and exit `0`.

## Environment

No dedicated environment variables. The helper inherits only the environment
needed by `redact-secrets.sh`.

## Mode

Reads stdin line by line and pipes each line through
`redact-secrets.sh --streaming --state-file PATH`. PEM state persists in the
state file between invocations, so a `BEGIN ... PRIVATE KEY` line in one call
continues redacting body lines until a later `END ... PRIVATE KEY` line.

## Exit Codes

- `0`: all input lines redacted successfully.
- `2`: unknown option or missing `--state-file`.
- `1`: propagated redaction failure.

Callers such as `breadcrumb-monitor.sh` and `larch-log.sh commit` treat non-zero
exit as fail-closed: raw input is not surfaced or committed. The monitor also
uses the surfaced-sentinel file described in `scripts/breadcrumb-monitor.md` to
avoid duplicate foreground output when a child process already surfaces
breadcrumbs through FD 3.
