## Goal
Generalize the cursor startup keychain-race serial lock to all three external CLIs (cursor, codex, gemini).

## Goal
Generalize the cursor startup keychain-race serial lock to all three external CLIs (cursor, codex, gemini) by adding shared helpers to `scripts/lib-external-launcher-common.sh` and applying an outer-retry wrapper at every spawn site, then removing the old session-scoped cursor lock and renaming env vars.

## Implementation Plan

### 1. Add helpers to `scripts/lib-external-launcher-common.sh`

Add three functions before the guard-close line (`LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED=1`):

- `external_serial_lock_acquire <out_var> <tool>`: Darwin-only mkdir-based lock with stale-recovery (stat mtime vs `LARCH_EXTERNAL_SERIAL_LOCK_TTL`), fail-open after `LARCH_EXTERNAL_SERIAL_LOCK_TRIES × 0.1s`. Sets out_var to lock path or "" on fail-open. Uses per-tool path `/tmp/larch-<tool>-serial-${USER:-larch}.lock`. No-op on non-Darwin.
- `external_serial_lock_release_after <lock> <delay>`: schedules `( sleep delay; rmdir lock ) & disown` when lock is non-empty.
- `external_is_auth_failure <tool> <sidecar>`: grep-based auth-failure detection. Cursor signature verified vs #1918; codex/gemini signatures are unverified (defensive net with a comment).

### 2. Update `scripts/lib-external-launcher-common.md`

Add documentation for the three new functions. Cross-reference env vars: `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`, `LARCH_EXTERNAL_SERIAL_LOCK_TTL`, `LARCH_EXTERNAL_SERIAL_LOCK_TRIES`, `LARCH_EXTERNAL_AUTH_RETRIES`, `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME`.

### 3. Convert cursor spawn sites

**3a. `scripts/launch-review.sh` — `_launch_cursor` function**

Replace old session-scoped lock block (lines ~836–855) and post-spawn lock-release block (lines ~884–887) with calls to the shared helpers. Wrap the existing background-spawn+wait with an outer-retry loop:

```bash
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
attempt=1
EXIT_CODE=0
while (( attempt <= MAX_AUTH_RETRIES )); do
    external_serial_lock_acquire _SERIAL_LOCK "cursor"
    cursor agent ... 2>>"$_STDERR_TARGET" &
    WRAPPER_PID=$!
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    wait "$WRAPPER_PID" && EXIT_CODE=0 || EXIT_CODE=$?
    if (( EXIT_CODE != 0 )) && external_is_auth_failure "cursor" "$SIDECAR"; then
        attempt=$(( attempt + 1 ))
        : > "$SIDECAR" 2>/dev/null || true
        continue
    fi
    break
done
```

Remove `_CURSOR_SERIAL_LOCK` variable and all references to it in this file.

**3b. `scripts/launch-cursor-implement.sh` — background spawn**

Wrap the background `cursor agent ... & WRAPPER_PID=$!` + `wait "$WRAPPER_PID"` block with the same outer-retry loop (background pattern). Auth-failure sidecar is `$SIDECAR_LOG`.

**3c. `scripts/launch-cursor-ci.sh` — check spawn pattern; wrap similarly**

This file uses a foreground spawn (no background `&`). Wrap with outer-retry; use `( sleep HOLD; rmdir LOCK ) & disown $!` to schedule lock release, then run cursor synchronously and capture exit. Auth-failure check against sidecar. Reset sidecar between retries.

### 4. Convert codex spawn sites

**4a. `scripts/launch-review.sh` — `_launch_codex` function**

Two foreground codex paths (with/without SIDECAR). Wrap entire if/else block in outer-retry loop:
- Before if/else: `external_serial_lock_acquire _SERIAL_LOCK "codex"`; schedule release with `( sleep HOLD; rmdir LOCK ) & disown $!`.
- After if/else: check auth failure on `$SIDECAR`; retry if needed. Reset `$SIDECAR` and `EXIT_CODE=0` between retries.

**4b. `scripts/launch-codex-implement.sh` — foreground spawn**

Same outer-retry wrapping around the foreground `codex exec` call. Auth-failure sidecar is `$SIDECAR_LOG`.

**4c. `scripts/launch-codex-ci.sh` — foreground spawn**

Same outer-retry wrapping. Auth-failure sidecar is the codex diag file (or sidecar used in that launcher).

### 5. Convert gemini spawn sites

**5a. `scripts/launch-gemini-implement.sh` — foreground spawn**

Wrap the `run-external-agent.sh ... gemini --prompt ...` call in the outer-retry loop. Auth-failure sidecar is `$SIDECAR_LOG`.

**5b. `scripts/lib-gemini-launcher-review.sh` — `_launch_gemini_inner` function**

Wrap the `run-external-agent.sh ... gemini -m ...` call in the outer-retry loop. Auth-failure sidecar is derived from `$RAW_OUTPUT` or stderr.

### 6. Remove old cursor-specific lock code

After converting all cursor sites:
- Verify no remaining references to `_CURSOR_SERIAL_LOCK` in launch-review.sh.
- Verify no remaining references to `LARCH_CURSOR_SERIAL_LOCK_*` in any .sh file (except tests — covered below).

### 7. Rename env vars `LARCH_CURSOR_SERIAL_LOCK_*` → `LARCH_EXTERNAL_SERIAL_LOCK_*`

In `scripts/test-launch-review.sh` lines ~1635-1683: rename all occurrences of:
- `LARCH_CURSOR_SERIAL_LOCK_FORCE_UNAME` → `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME`
- `LARCH_CURSOR_SERIAL_LOCK_DELAY` → `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`  
- `LARCH_CURSOR_SERIAL_LOCK_TRIES` → `LARCH_EXTERNAL_SERIAL_LOCK_TRIES`

### 8. Update `scripts/test-launch-review.sh` — add new test cases

Add new test cases for:
- codex lock acquired under `--tool codex` (path `/tmp/larch-codex-serial-...`).
- gemini lock acquired under `--tool gemini` (path `/tmp/larch-gemini-serial-...`).
- Stale-lock recovery: pre-create lock dir, `touch -t <2s-ago>` it, assert acquire succeeds.
- Outer retry: inject fake CLI that writes auth-error string to stderr then exits 1; assert retries up to `LARCH_EXTERNAL_AUTH_RETRIES` (use `LARCH_EXTERNAL_AUTH_RETRIES=2` for test speed).
- No retry on non-auth failure: inject fake CLI that writes other error and exits 1; assert exactly one attempt.

### 9. Update implement-side test harnesses

In `skills/implement/scripts/test-cursor-implementer.sh`, `test-codex-implementer.sh`, `test-gemini-implementer.sh`:
- Add assertions that the lock is acquired (global `/tmp/larch-<tool>-serial-...` path) with `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin`.
- Add outer-retry assertion: inject auth-failure stub, assert the launcher retries.

### 10. Update sibling .md files

Update purpose / invariants / env-var sections in:
- `scripts/launch-review.md` — remove cursor-specific lock docs, add pointer to lib-external-launcher-common.sh helpers.
- `scripts/launch-cursor-ci.md`, `launch-cursor-implement.md`, `launch-codex-implement.md`, `launch-codex-ci.md`, `launch-gemini-implement.md`, `lib-gemini-launcher-review.md` — add note about the serial lock + outer-retry applied at spawn site.
- `scripts/lib-cursor-auth.md` — note that the cursor-specific lock has been generalized.

## Testing Strategy
- `/relevant-checks` after changes (pre-commit on modified files + agent-lint).
- Env var rename verified by grep: `grep -r 'LARCH_CURSOR_SERIAL_LOCK' scripts/` should return only test comments/docs.
- Stale-lock and retry cases in test-launch-review.sh exercise the new code paths.

## Edge Cases
- `lib-gemini-launcher-review.sh`'s `_launch_gemini_inner` uses `fail_closed` for non-zero exits; the outer-retry must call `external_is_auth_failure` before calling `fail_closed`, and only bypass retry on non-auth failures.
- The codex review in launch-review.sh has two paths (with/without SIDECAR); the retry loop must reset both before retry.
- For gemini in lib-gemini-launcher-review.sh, the existing function checks for non-zero exit with `fail_closed`; restructuring for retry requires extracting the auth-failure check before the `fail_closed` gate.
