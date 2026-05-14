## Goal
Fix cli-config.json rename race in Cursor launchers by per-invocation CURSOR_CONFIG_DIR isolation.

## Implementation Plan
## Goal
Fix the cli-config.json rename race in parallel Cursor agent invocations by giving each launcher its own private CURSOR_CONFIG_DIR, eliminating the shared resource contention.

## Implementation Plan

### 1. Add helpers to `scripts/lib-cursor-launcher-common.sh`

Add two functions after `cursor_launcher_promote_inner_done`:

```bash
cursor_launcher_setup_private_config_dir() {
    # Give each cursor agent invocation a private config dir to avoid the
    # cli-config.json rename race when multiple processes share ~/.cursor.
    # CURSOR_CONFIG_DIR is documented at https://cursor.com/docs/cli/reference/configuration
    # (not surfaced in `cursor agent --help` as of v2026.05.09-0afadcc).
    local cfg_tmp
    cfg_tmp=$(mktemp -d "${TMPDIR:-/tmp}/larch-cursor-cfg.XXXXXX") || return 1
    if [[ -f "$HOME/.cursor/cli-config.json" ]]; then
        cp "$HOME/.cursor/cli-config.json" "$cfg_tmp/cli-config.json" 2>/dev/null || true
    fi
    export CURSOR_CONFIG_DIR="$cfg_tmp"
    CURSOR_CONFIG_DIR_TMP="$cfg_tmp"
}

cursor_launcher_cleanup_private_config_dir() {
    if [[ -n "${CURSOR_CONFIG_DIR_TMP:-}" ]]; then
        rm -rf "$CURSOR_CONFIG_DIR_TMP" 2>/dev/null || true
        unset CURSOR_CONFIG_DIR_TMP CURSOR_CONFIG_DIR
    fi
}
```

### 2. `scripts/launch-review.sh` — `_launch_cursor()` function

- Before the auth retry loop (immediately before `external_serial_lock_acquire _SERIAL_LOCK "cursor"`), add:
  ```bash
  cursor_launcher_setup_private_config_dir
  ```
- Extend `_publish_done_on_exit` to call `cursor_launcher_cleanup_private_config_dir` before it returns.

Exact insertion: The `CURSOR_CONFIG_DIR` setup goes before the `while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES ))` loop around line 856. The cleanup call goes at the end of `_publish_done_on_exit`.

### 3. `scripts/launch-cursor-ci.sh`

- Before the auth retry loop (`while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES ))`), add:
  ```bash
  cursor_launcher_setup_private_config_dir
  ```
- After the loop (`break`), add cleanup:
  ```bash
  cursor_launcher_cleanup_private_config_dir
  ```

### 4. `scripts/launch-cursor-implement.sh`

- Before the auth retry loop, add `cursor_launcher_setup_private_config_dir`.
- After the loop (`break`), add `cursor_launcher_cleanup_private_config_dir`.

### 5. `scripts/cursor-wrap-prompt.sh`

Update the comment at lines 7-10 to note that the per-invocation private dir handles the cli-config.json race; the /max-mode prefix is still the larch-controlled mechanism for max-mode.

### 6. `scripts/test-launch-review.sh` — add CURSOR_CONFIG_DIR isolation test

After existing test cases, add a test that:
- Adds `CURSOR_CONFIG_DIR` capture to the stub cursor binary (write it to a log file)
- Launches two parallel cursor reviews using the stub
- Asserts each invocation received a different CURSOR_CONFIG_DIR
- Asserts neither equals `~/.cursor`

Pattern: extend the existing stub to log `$CURSOR_CONFIG_DIR` via `CURSOR_STUB_CONFIG_DIR_LOG`, then assert the two log files differ and are not `~/.cursor`.

### 7. Sibling `.md` docs to update

- `scripts/launch-review.md`
- `scripts/launch-cursor-ci.md`
- `scripts/launch-cursor-implement.md`
- `scripts/cursor-wrap-prompt.md`
- `scripts/lib-cursor-launcher-common.md`

### Testing strategy
`/relevant-checks` clean. The new test in `test-launch-review.sh` asserts per-invocation isolation at the harness level.

### Keychain lock: do not remove
`external_serial_lock_acquire _SERIAL_LOCK "cursor"` is retained unchanged.

### Acceptance criteria check
1. ✓ Each cursor agent invocation in all 3 launchers exports a unique CURSOR_CONFIG_DIR.
2. ✓ Private config dir seeded from ~/.cursor/cli-config.json when present.
3. ✓ Cleanup in EXIT trap / inline after loop.
4. ✓ Keychain lock retained.
5. ✓ Test asserting distinct CURSOR_CONFIG_DIR per invocation.
6. After landing: compare timing-report.md cursor-specialist failures.
7. ✓ /relevant-checks clean.
