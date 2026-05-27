# test-background-monitor-wait.sh

Offline regression harness for the top-level Family B caller contract in
`BASH_AUTHORING.md` §4.

The harness simulates a writer that publishes the done sentinel before the
writer process exits, then proves the wrapper waits for the captured writer PID
instead of returning as soon as the monitor exits. It also pins writer exit-code
propagation, monitor failure preservation, and the bounded post-monitor reap
path used after timeout signaling.

Primary callers:

- `make test-background-monitor-wait`
- `scripts/relevant-checks.sh` / local relevant-check runs when this harness or
  Family B background-monitor surfaces change
- the pre-commit/lint harness matrix via `make lint`

Keep this file in sync with `scripts/test-background-monitor-wait.sh`. The shell
harness is Bash 3.2 portable: no associative arrays, `mapfile`, namerefs, or
append-all redirection.
