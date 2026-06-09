# test-file-design-oos.sh

Offline harness for `file-design-oos.sh` (`prepare` + `annotate` paths). See `file-design-oos.md` for the primary contract. Includes cross-session cache recovery (`X1`–`X5`), sentinel precedence, `--clear-cross-session-cache`, first-write directory creation, unwritable-cache warning paths, annotate graceful-skip (`A1`–`A2`: empty/missing issue-stdout-file), and prepare `oos-issue-sentinel` idempotency (`S1`: sentinel present without `oos-issues-created.md`).

Wired via `make test-file-design-oos` (see `Makefile`).
