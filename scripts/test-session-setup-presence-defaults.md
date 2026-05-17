# test-session-setup-presence-defaults.sh

Regression harness for `scripts/session-setup.sh` presence propagation. It verifies `CODEX_PRESENT` / `CURSOR_PRESENT` plus `*_AVAILABLE` aliases on stdout and in session-env output, including caller-env passthrough.

Wired into `Makefile` as `make test-session-setup-presence-defaults`.
