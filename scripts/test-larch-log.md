# test-larch-log.sh contract

Regression harness for `scripts/larch-log.sh`. It runs with `LARCH_LOG_ROOT`
pointing at a temporary directory so it does not leave runtime artifacts in the
repository.

Coverage includes manifest creation, replace-mode redaction, idempotent retry,
append-mode newline handling, json-lines rejection for raw markdown records,
`exists`, mutable manifest updates, the `commit` staging path (`LARCH_LOG_ROOT`
unset, `--log-root` set) that copies logs from an explicit temp staging dir into
the repo before committing, and the `larch-log-flush.sh` post-merge sentinel
no-op path. It also covers commit refusal on the default branch/main.
