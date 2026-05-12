## Goal
Fix macOS keychain race condition in parallel Cursor reviewer launches.

## Goal
Fix the macOS keychain race condition that causes parallel Cursor reviewer instances to fail when multiple `cursor agent` CLIs read the `cursor-access-token` service entry simultaneously.

## Implementation Plan

### Root cause
When multiple `launch-review.sh --tool cursor` processes run in parallel, each calls `cursor_launcher_setup_auth_argv()` which sources `lib-cursor-auth.sh`, runs preflight, and calls `cursor_auth_argv()`. If `CURSOR_API_KEY` is not set, `cursor_auth_argv()` leaves `CURSOR_AUTH_ARGS` empty, so each `cursor agent` is launched without `--api-key` and reads the `cursor-access-token` from keychain itself. Multiple concurrent reads of the same keychain entry by the Cursor binary causes the race (`Error: Password not found for account 'cursor-user' and service 'cursor-access-token'`).

### Fix 1 — Pre-read token (main fix): `scripts/lib-cursor-auth.sh`

Add `cursor_preread_service_token()`:
- If `CURSOR_API_KEY` already set: no-op (idempotent)
- If not on Darwin: no-op
- Otherwise: call `security find-generic-password -a cursor-user -s cursor-access-token -w` to read the actual token value
- If successful and non-empty: `export CURSOR_API_KEY="$token"`
- Test-mode gated: when `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`, use `LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN` as the mocked token value
- Silent on failure: returns 0 so callers proceed; Cursor falls back to its own keychain auth (same behavior as before the fix)

### Fix 2 — Service-specific preflight: `scripts/lib-cursor-auth.sh`

Update `cursor_auth_preflight()`:
- Change generic check `security find-generic-password -a cursor-user` to service-specific `security find-generic-password -a cursor-user -s cursor-access-token`
- Makes preflight accurately reflect the entry that Cursor actually reads at runtime
- Test mock (`LIB_CURSOR_AUTH_TEST_SECURITY_RC`) still covers this since it overrides the entire `security` call result; no test changes needed for this specific change

### Wire the pre-read: `scripts/lib-cursor-launcher-common.sh`

Update `cursor_launcher_setup_auth_argv()` to call `cursor_preread_service_token` after `cursor_auth_preflight` succeeds and before `cursor_auth_argv`:
```
cursor_auth_preflight || return $?
CURSOR_AUTH_ARGS=()
cursor_preread_service_token   # new call
cursor_auth_argv
```
This ensures that by the time `cursor_auth_argv()` runs, `CURSOR_API_KEY` is populated from keychain, so `--api-key` appears in the Cursor argv, preventing the Cursor binary from reading the keychain itself.

### Test coverage: `scripts/test-lib-cursor-auth.sh`

Add 4 new tests for `cursor_preread_service_token`:
- Test 17: pre-read with CURSOR_API_KEY already set → no-op (existing key unchanged)
- Test 18: pre-read on non-Darwin → no-op (CURSOR_API_KEY stays unset)
- Test 19: pre-read on Darwin with mocked token → exports CURSOR_API_KEY
- Test 20: pre-read on Darwin with empty mocked token → no-op (CURSOR_API_KEY stays unset)

### Sibling .md updates (edit-in-sync)
- `scripts/lib-cursor-auth.md`: add `cursor_preread_service_token` to function list, update invariants to mention service-specific preflight and pre-read
- `scripts/lib-cursor-launcher-common.md`: update `cursor_launcher_setup_auth_argv` description to mention pre-read

## Edge Cases
- `CURSOR_API_KEY` already set in env (explicit API key): pre-read is a no-op, existing behavior unchanged
- Non-Darwin (Linux/CI): pre-read is a no-op, `cursor_auth_argv` leaves `CURSOR_AUTH_ARGS` empty, Cursor uses its own auth
- Darwin but `security` returns non-zero or empty: silent return 0, falls back to old behavior (may still race, but the same as current state)
- Concurrent `security find-generic-password ... -w` reads: macOS keychain supports concurrent reads safely; the race described in the issue was in the Cursor binary's own keychain access, not in `security` command reads

## Test Plan
- `bash scripts/test-lib-cursor-auth.sh` — must pass all existing 16 tests + 4 new tests
- Run `/relevant-checks` — pre-commit lint + agent-lint
