# breadcrumb-monitor.sh contract (Stage 3 compatibility shim)

`scripts/breadcrumb-monitor.sh` is a **temporary no-op compatibility shim**
retained until Stage 4 removes the remaining Family B foreground fences from
skill prose (`#3119`).

## Behavior

- Consumes all historical CLI flags (`--stream`, `--done-sentinel`,
  `--status-file`, `--quiet-log`, `--surfaced-sentinel`, `--paired-pid-file`,
  `--poll-interval=`, `--rate-cap=`, `--final-tail-lines=`, `--mode=`,
  `-h`/`--help`, and unknown args) and **always exits 0**.
- Does **not** source `lib-quiet.sh` or `lib-larch-log.sh`.
- Does **not** stream breadcrumb records, watch sentinels, enforce paired-PID
  timeouts, or redact lines.

## Why it remains

Stage 4-deferred skill fences still invoke the monitor in the same Bash message
as a background writer. The shim's exit 0 keeps those fences on the
`monitor_rc=0` branch so they `wait` the writer PID and propagate its real exit
code. Removing the script before Stage 4 would break those fences.

## Harness

Monitor-specific harnesses (`scripts/test-breadcrumb-monitor*`,
`scripts/test-background-monitor-wait*`) were deleted in Stage 3. Forensics
still use committed `larch-logs/<run-id>/breadcrumbs/` quiet-log copies via
`lib-larch-log.sh`, not live FD-3 streaming.
