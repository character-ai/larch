## Goal
Add restore-finalize-state.sh defensive pre-teardown helper

## Implementation Plan

### Goal
Add `scripts/restore-finalize-state.sh` as a defensive pre-teardown helper that restores `finalize-state.sh` from `ship-pr-state.sh` before `implement-finalize.sh teardown` runs. Extract the 20-key list into `scripts/lib-finalize-state-keys.sh` shared by both `restore-finalize-state.sh` and `ship-pr.sh`.

### Files to create / modify

1. **NEW `scripts/lib-finalize-state-keys.sh`** — Sourceable library (no shebang). Declares:
   - `LARCH_FINALIZE_STATE_KEYS` bash array with all 20 key names in canonical order
   - `LARCH_FINALIZE_STATE_DEFAULTS` bash associative array mapping keys to non-empty defaults (only `DESIGN_ONLY_DONE=false`)
   Load guard: `LARCH_LIB_FINALIZE_STATE_KEYS_LOADED=1` to prevent double-sourcing.

2. **NEW `scripts/restore-finalize-state.sh`** — Executable helper. Args: `--implement-tmpdir PATH`.
   - Validates `--implement-tmpdir` is set and the dir exists
   - Checks `$IMPLEMENT_TMPDIR/ship-pr-state.sh` is present; if missing: emit stderr warning, exit 1
   - Sources `lib-finalize-state-keys.sh`
   - Reads each key in `LARCH_FINALIZE_STATE_KEYS` from `ship-pr-state.sh` via awk (same logic as `ship-pr.sh`'s `read_state()`)
   - Applies defaults from `LARCH_FINALIZE_STATE_DEFAULTS`
   - Atomically writes `$IMPLEMENT_TMPDIR/finalize-state.sh` via tmp + `mv` (same pattern as `write_finalize_state()`)
   - Also writes `$IMPLEMENT_TMPDIR/final-bail-reason.txt` from `BAIL_REASON` key (matching `write_finalize_state()`'s last line)
   - Idempotent: safe to call regardless of current `finalize-state.sh` state

3. **MODIFY `scripts/ship-pr.sh`** — Refactor `write_finalize_state()` to source `lib-finalize-state-keys.sh` and use a loop over `LARCH_FINALIZE_STATE_KEYS`. This eliminates the duplicate key list. Keep `$NO_LOGS_COMMIT` shell var usage (or use `read_state NO_LOGS_COMMIT` — both give the same result since state file has it).

4. **MODIFY `skills/implement/SKILL.md`** — In Step 18, add the `restore-finalize-state.sh` call IMMEDIATELY BEFORE the `implement-finalize.sh teardown` block:
   ```bash
   "${CLAUDE_PLUGIN_ROOT}/scripts/restore-finalize-state.sh" \
     --implement-tmpdir "$IMPLEMENT_TMPDIR"

   "${CLAUDE_PLUGIN_ROOT}/scripts/implement-finalize.sh" teardown \
     --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" \
     --implement-tmpdir "$IMPLEMENT_TMPDIR"
   ```

5. **NEW `scripts/test-restore-finalize-state.sh`** — Offline regression harness covering:
   - `ship-pr-state.sh` missing → exits 1, stderr warning
   - file partial (12 keys) → restores all 20 keys correctly
   - file complete (20 keys) → idempotent, same output
   - atomic-write: tmp file is renamed into place (check `finalize-state.sh` exists after call)
   - DESIGN_ONLY_DONE default: when absent from ship-pr-state.sh, defaults to "false"
   - BAIL_REASON → written to `final-bail-reason.txt`

6. **NEW sibling .md files**:
   - `scripts/lib-finalize-state-keys.md` — stub pointing to `restore-finalize-state.md` as primary
   - `scripts/restore-finalize-state.md` — full contract: purpose, callers, invariants, Makefile wiring, harness
   - `scripts/test-restore-finalize-state.md` — stub pointing to `restore-finalize-state.md`

7. **MODIFY `Makefile`** — Add `test-restore-finalize-state` to:
   - `.PHONY` list
   - `test-harnesses-3` shard (alongside `test-implement-finalize`)
   - New target rule: `test-restore-finalize-state:\n\tbash scripts/test-restore-finalize-state.sh`

### Testing strategy
Run `/relevant-checks` after implementation (pre-commit + agent-lint). Verify `make test-restore-finalize-state` passes locally.

### Edge cases
- `--implement-tmpdir` not set: exit 2 with usage error
- `ship-pr-state.sh` present but empty: all keys emit empty values; `finalize-state.sh` is still written with 20 empty-value lines (safe for teardown)
- Partial `finalize-state.sh` (clobber scenario): overwritten atomically

## Test plan
(no test plan section in plan-file)
