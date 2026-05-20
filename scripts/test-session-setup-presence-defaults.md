# test-session-setup-presence-defaults.sh

Regression harness for `scripts/session-setup.sh` presence propagation. It verifies `CODEX_PRESENT` / `CURSOR_PRESENT` plus `*_AVAILABLE` aliases on stdout and in session-env output, including caller-env passthrough. It also verifies validated caller-env forwarding for `LARCH_DYNAMIC_ARCHETYPES_MAX` (`0..8` accepted, invalid values warned-and-dropped).

Wired into `Makefile` as `make test-session-setup-presence-defaults`.
