# test-lib-cursor-auth.sh

Hermetic regression harness for `scripts/lib-cursor-auth.sh` and `scripts/cursor-auth-flags.sh`. Pins:

- `cursor_auth_argv` populates `CURSOR_AUTH_ARGS` correctly for empty / whitespace-only / single-line / leading-or-trailing-whitespace key values.
- `cursor_auth_preflight` returns 0 when `CURSOR_API_KEY` non-empty (regardless of platform), 0 on non-Darwin (override via `LIB_CURSOR_AUTH_TEST_UNAME=Linux`), 0 on Darwin when `LIB_CURSOR_AUTH_TEST_SECURITY_RC=0` is injected (keychain entry exists), 2 on Darwin when `LIB_CURSOR_AUTH_TEST_SECURITY_RC=1` is injected (keychain entry missing).
- `cursor_preread_service_token` preserves an existing `CURSOR_API_KEY`, no-ops on non-Darwin, exports a mocked Darwin keychain token, and no-ops on empty mocked token reads.
- `cursor_launcher_setup_auth_argv` calls the pre-read before `cursor_auth_argv`, so a mocked Darwin token becomes adjacent `--api-key` argv elements.
- `LIB_CURSOR_AUTH_TEST_*` overrides are silently ignored when `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1` is NOT set (production cannot bypass Darwin preflight by setting one stray env var).
- `cursor_auth_preflight` stderr message contains the documented anchors: caller identity prefix, `docs/installation-and-setup.md` pointer, and both remediation suggestions (`export CURSOR_API_KEY=...` and `security delete-generic-password -a cursor-user`).
- `scripts/cursor-auth-flags.sh` prints zero lines when `CURSOR_API_KEY` is empty and exactly two lines (`--api-key`, then the trimmed key) when set.

## Producer / runtime references

- `scripts/lib-cursor-auth.sh` (producer) and `scripts/lib-cursor-auth.md` (sibling contract).
- `scripts/cursor-auth-flags.sh` (line-per-element emitter) and `scripts/cursor-auth-flags.md` (sibling contract).

## Makefile wiring

`make test-lib-cursor-auth` runs this harness directly. Wired into `make test-harnesses-2` (same shard as `test-launch-review`, `test-check-reviewers`, `test-cursor-implementer`).

## agent-lint

Excluded from `agent-lint.toml` per the standard pattern for test scripts and their `.md` siblings.
