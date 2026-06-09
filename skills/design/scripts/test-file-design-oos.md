# test-file-design-oos.sh

Offline harness for `file-design-oos.sh` (`prepare` + `annotate` paths). See `file-design-oos.md` for the primary contract. Includes cross-session cache recovery (`X1`–`X6`), sentinel precedence (`X2b`: both `oos-issues-created.md` and `oos-issue-sentinel` present → `skip-sentinel`), `--clear-cross-session-cache`, first-write directory creation, unwritable-cache warning paths, annotate graceful-skip (`A1`–`A2`: empty/missing issue-stdout-file with path-diagnostic assertions), and prepare `oos-issue-sentinel` idempotency (`S1`: sentinel with `ISSUES_CREATED>0`; `S2`: all-dedup sentinel with `ISSUES_CREATED=0, ISSUES_DEDUPLICATED>0`; `S3`: zero-count falls through to ready; `S4`: malformed `ISSUES_CREATED` falls through; `S5`: partial-failure sentinel with `ISSUES_FAILED>0` falls through).

Wired via `make test-file-design-oos` (see `Makefile`).
