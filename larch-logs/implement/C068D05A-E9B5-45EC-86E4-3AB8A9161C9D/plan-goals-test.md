## Goal
Add KeyChain serial lock acquire/release to 4 cursor/codex spawn sites that currently bypass it

## Implementation Plan

Add `external_serial_lock_acquire`/`external_serial_lock_release_after` to the 4 spawn sites that bypass the Mac KeyChain serial lock (Path B from issue #2408).

### Site 1 — `scripts/run-negotiation-round.sh`

**Problem**: does not source `lib-external-launcher-common.sh`; codex and cursor spawns are unguarded.

**Fix**:
1. After the `source "$SCRIPT_DIR/lib-quiet.sh"` line, add:
   `source "$SCRIPT_DIR/lib-external-launcher-common.sh"`
2. In the `codex)` branch, immediately before `codex exec ...`:
   ```bash
   _SERIAL_LOCK=""
   external_serial_lock_acquire _SERIAL_LOCK "codex"
   external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
   ```
3. In the `cursor)` branch, immediately before `cursor agent ...`:
   ```bash
   _SERIAL_LOCK=""
   external_serial_lock_acquire _SERIAL_LOCK "cursor"
   external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
   ```

### Site 2 — `scripts/lint-fix-loop.sh`

**Problem**: `lib-cursor-launcher-common.sh` is sourced (so `external_serial_lock_acquire` is available), but `run_codex()` and `run_cursor()` functions don't use it.

**Fix**: In `run_codex()`, before the `"$RUN_EXTERNAL_AGENT_SH" --tool codex` line:
```bash
local _SERIAL_LOCK=""
external_serial_lock_acquire _SERIAL_LOCK "codex"
external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
```
In `run_cursor()`, before the `"$RUN_EXTERNAL_AGENT_SH" --tool cursor` line:
```bash
local _SERIAL_LOCK=""
external_serial_lock_acquire _SERIAL_LOCK "cursor"
external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
```

### Site 3 — `skills/review-and-fix/scripts/review-and-fix.sh`

**Problem**: `lib-cursor-launcher-common.sh` is sourced (so `external_serial_lock_acquire` is available), but `run_coder_dispatch()` doesn't use it.

**Fix**: In `run_coder_dispatch()`, before the first `if "$RUN_EXTERNAL_AGENT_SH" --tool codex`:
```bash
local _SERIAL_LOCK=""
external_serial_lock_acquire _SERIAL_LOCK "codex"
external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
```
And before the second `if "$RUN_EXTERNAL_AGENT_SH" --tool cursor` (after cursor_launcher_setup_auth_argv):
```bash
_SERIAL_LOCK=""
external_serial_lock_acquire _SERIAL_LOCK "cursor"
external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
```

### Site 4 — `skills/design/scripts/classify-issue.sh`

**Problem**: does not source `lib-external-launcher-common.sh`; cursor spawn in `try_cursor_validation()` is unguarded.

**Fix**:
1. After the `source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"` line, add:
   `source "$REPO_ROOT/scripts/lib-external-launcher-common.sh"`
2. In `try_cursor_validation()`, immediately before `set +e` / `"$RUN_EXTERNAL_AGENT"`:
   ```bash
   local _SERIAL_LOCK=""
   external_serial_lock_acquire _SERIAL_LOCK "cursor"
   external_serial_lock_release_after "$_SERIAL_LOCK" "${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}"
   ```

### Sibling .md files

Update `scripts/run-negotiation-round.md`, `scripts/lint-fix-loop.md`, `skills/review-and-fix/scripts/review-and-fix.md`, and `skills/design/scripts/classify-issue.md` to mention the newly-added serial lock calls.


## Test plan

Run `/relevant-checks` after applying. The existing grep-based parity rule at `.claude/rules/external-tool-launcher-parity.md` acts as the ongoing regression guard.
