## Goal
Remove default_ledger_path() fallback from timing-ledger.sh and token-ledger.sh; fail closed when no per-run root is set

## Implementation Plan
## Implementation Plan

Goal: Remove `default_ledger_path()` from timing-ledger.sh and token-ledger.sh, replacing it with fail-closed behavior and (for token-ledger.sh) a proper env-var priority chain (Path 2A).

### Files to Modify

1. **scripts/timing-ledger.sh**
   - Remove `default_ledger_path()` function (currently lines 60-65)
   - In `resolve_ledger_path()`, replace the final `default_ledger_path` call (currently line 97) with:
     - `warn "timing-ledger.sh: no per-run ledger root set; expected one of --ledger, LARCH_TIMING_LEDGER, IMPLEMENT_TMPDIR, SESSION_ENV_PATH, DESIGN_TMPDIR, REVIEW_TMPDIR"`
     - `return 1`
   - The `tmp_root()` helper stays; it is still used by `validate_under_tmp`.

2. **scripts/token-ledger.sh**
   - Remove `default_ledger_path()` function (currently lines 73-79)
   - Rewrite `resolve_ledger_path()` to add env-var priority chain (Path 2A):
     - `--ledger PATH` → `validate_under_tmp`
     - `$LARCH_TOKEN_LEDGER` → `validate_under_tmp`
     - `$IMPLEMENT_TMPDIR` (set + is a directory) → `$IMPLEMENT_TMPDIR/larch-tokens-<sha256(session-id)>.jsonl`
     - `$SESSION_ENV_PATH` (parent dir exists) → `$(dirname $SESSION_ENV_PATH)/larch-tokens-<sha256(session-id)>.jsonl`
     - fail closed: `warn "token-ledger.sh: no per-run ledger root set; expected one of --ledger, LARCH_TOKEN_LEDGER, IMPLEMENT_TMPDIR, or SESSION_ENV_PATH"` + `return 1`
   - The `tmp_root()` helper stays; used by `validate_under_tmp`.
   - The session-id-based filename construction stays (keeps `resolve_session_id()` + `sha256_hex()` in path building).

3. **scripts/timing-ledger.md**
   - Update path resolution list: remove item 7 (`${TMPDIR:-/tmp}/larch-timing-<sha256(cwd)>.tsv`)
   - Replace with: "7. Fails closed with a stderr warning when none of the above are set. Callers MUST set at least one root or pass `--ledger`."

4. **scripts/token-ledger.md**
   - Update session-id resolution section to document the new `resolve_ledger_path()` priority chain
   - Document fail-closed behavior when no root is set

5. **scripts/test-timing-ledger.sh**
   - Add negative test: all env vars unset (already unset at top of script), no `--ledger` → assert stderr contains "no per-run ledger root set"
   - Add positive test: `IMPLEMENT_TMPDIR` set → assert ledger resolves under it

6. **scripts/test-token-ledger.sh**
   - Add negative test: `IMPLEMENT_TMPDIR`, `LARCH_TOKEN_LEDGER`, `SESSION_ENV_PATH` all unset → assert stderr contains "no per-run ledger root set"
   - Add positive test: `IMPLEMENT_TMPDIR` set → assert ledger path is under IMPLEMENT_TMPDIR
   - Update unsafe_path test to pass `IMPLEMENT_TMPDIR` (after the change, without it the test is a no-op)

### Edge Cases
- `LARCH_TOKEN_LEDGER` with an unsafe path: `validate_under_tmp` rejects it, falls through to next priority
- `IMPLEMENT_TMPDIR` canonicalization failure: fall through to `SESSION_ENV_PATH`
- All resolved session IDs (including cwd-hash fallback) still safe since we only hash them before use in filename

### Verification
- `grep -r default_ledger_path scripts/ skills/` returns no hits
- `/relevant-checks` clean
- Existing tests continue to pass

## Test plan
(no test plan section in plan-file)
