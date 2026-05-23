# test-file-design-oos.sh

Offline harness for `file-design-oos.sh` (`prepare` + `annotate` paths). See `file-design-oos.md` for the primary contract. Includes cross-session cache recovery (`X1`–`X5`), sentinel precedence, `--clear-cross-session-cache`, first-write directory creation, and unwritable-cache warning paths.

Wired via `make test-file-design-oos` (see `Makefile`).
