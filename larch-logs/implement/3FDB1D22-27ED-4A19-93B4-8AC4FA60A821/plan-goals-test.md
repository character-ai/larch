## Goal
Extend Cursor auth-failure regex to recognize macOS security CLI failures and trigger retry

## Implementation Plan

**Goal**: Extend `external_is_auth_failure` in `scripts/lib-external-launcher-common.sh` to recognize the macOS `security` CLI failure signature emitted by Cursor, so the auth-retry loop retries instead of bailing after one attempt.

### Files to modify

1. `scripts/lib-external-launcher-common.sh` — line 104: extend Cursor branch regex
2. `scripts/test-launch-review.sh` — add two new test cases after the SL-no-retry block
3. `scripts/lib-external-launcher-common.md` — update `external_is_auth_failure` bullet

### Changes

**A. `scripts/lib-external-launcher-common.sh` (line 104)**

Replace the current Cursor `grep -Eiq` pattern:
```
'Password not found|cursor-user|cursor-access-token|keychain.*(not found|failed)|([^-]|^)auth[-_ ]?error|authentication (failed|required)'
```
with:
```
'Password not found|cursor-user|cursor-access-token|keychain.*(not found|failed)|([^-]|^)auth[-_ ]?error|authentication (failed|required)|Security (process exited with code|command failed)'
```

Only the `cursor)` branch changes. Codex and Gemini branches stay byte-identical.

**B. `scripts/test-launch-review.sh`**

Insert two new test cases after the `rm -f "$SL_NORETRY_COUNT"` line (after the SL-no-retry block) and before "Restore normal cursor stub":

1. **SL-exit45-auth**: stub writes the exact run-00FAC6B1 two-line stderr on attempt 1, exits 0 with valid JSON on attempt 2. Assert launcher invokes stub exactly 2 times.

2. **SL-security-cmd-failed-auth**: stub writes only the outer wrapper line `Error: Security command failed: Security process exited with code: 45` on attempt 1, exits 0 with valid JSON on attempt 2. Assert launcher invokes stub exactly 2 times.

Both tests use the same `USER`, `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin`, `LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0`, `LARCH_EXTERNAL_AUTH_RETRIES=2`, `PATH="$STUB_BIN:$PATH"` setup as the existing SL-auth-retry test.

**C. `scripts/lib-external-launcher-common.md`**

Extend the `external_is_auth_failure` bullet to name the macOS `security` signature.

### Validation

1. `bash scripts/test-launch-review.sh` passes (both new cases match, no regressions)
2. Manual regex probe: `printf 'Error: Security command failed...\n' | grep -Eiq '...|Security (process exited with code|command failed)'` prints MATCH
3. `bash scripts/test-lib-external-launcher-common.sh` passes if it exists (it doesn't per issue)
4. `/relevant-checks` on modified files passes
5. Codex/Gemini branches unchanged (spot-check with diff)

### Failure modes

- The regex alternation must be Cursor-only; confirmed by checking Codex/Gemini branches remain identical
- The `|Security (process exited with code|command failed)` form is unambiguous — two-word qualifier avoids generic "Security" substring false positives

## Test plan
(no test plan section in plan-file)
