# test-lib-cursor-auth.sh

Hermetic regression harness for `scripts/lib-cursor-auth.sh` and `python/cli.py agent cursor-auth-preflight`. Pins:

- `cursor_auth_export_env` normalizes `CURSOR_API_KEY` for empty / whitespace-only / single-line / leading-or-trailing-whitespace key values without building auth argv.
- `cursor_auth_preflight` returns 0 when `CURSOR_API_KEY` non-empty (regardless of platform), 0 on non-Darwin (override via `LIB_CURSOR_AUTH_TEST_UNAME=Linux`), 0 on Darwin when the mocked keychain return code is 0, and 2 on Darwin when retries exhaust with mocked failures.
- `cursor_auth_preflight` retries Darwin keychain reads, honors `LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ` before `LIB_CURSOR_AUTH_TEST_SECURITY_RC`, and suppresses production `security find-generic-password` retry stderr.
- `cursor_preread_service_token` preserves an existing `CURSOR_API_KEY`, no-ops on non-Darwin, exports a mocked Darwin keychain token, and no-ops on empty mocked token reads.
- `cursor_launcher_setup_auth_argv` calls the pre-read before env export, so a mocked Darwin token becomes the inherited `CURSOR_API_KEY`.
- `LIB_CURSOR_AUTH_TEST_*` overrides are silently ignored when `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1` is NOT set (production cannot bypass Darwin preflight by setting one stray env var).
- `cursor_auth_preflight` stderr message contains the documented anchors: caller identity prefix, `docs/installation-and-setup.md` pointer, and both remediation suggestions (`export CURSOR_API_KEY=...` and `security delete-generic-password -a cursor-user`).
- `python/cli.py agent cursor-auth-preflight` acts as a preflight gate and emits no argv flags.

## Producer / runtime references

- `scripts/lib-cursor-auth.sh` (producer) and `scripts/lib-cursor-auth.md` (sibling contract).
- `python/cli.py agent cursor-auth-preflight` (line-per-element emitter) and `python/agents.py` (sibling contract).

## Makefile wiring

`make test-lib-cursor-auth` runs this harness directly. Wired into `make test-harnesses-2` (same shard as `test-launch-review`, `test-check-reviewers`, `test-cursor-implementer`).

## agent-lint

Excluded from `agent-lint.toml` per the standard pattern for test scripts and their `.md` siblings.
