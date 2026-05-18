## Goal
Add boundary-state detection to sessionstart-health.sh to re-prompt on session resume after turn-boundary halt

## Implementation Plan

### Goal
Add boundary-state detection to `scripts/sessionstart-health.sh` so the SessionStart hook re-prompts the orchestrator about pending /implement boundary states (post-/design, post-/review, post-/bump-version) when a session resumes/clears/compacts after a turn-boundary halt.

### Files to Modify
1. **`scripts/sessionstart-health.sh`** — add stdin reading, cwd/session_id extraction, lib-resolve-implement-tmpdir.sh sourcing, and three boundary state checks
2. **`scripts/sessionstart-health.md`** — update contract doc to describe new stdin reading and boundary detection
3. **`scripts/test-sessionstart-health.sh`** — add test cases 12–16 covering all three boundary states and the sentinel suppression cases
4. **`scripts/test-sessionstart-health.md`** — update stub to reference new test coverage

### Approach

#### `scripts/sessionstart-health.sh`
1. Update top comment: replace "The hook does not read stdin." with description of stdin payload use.
2. After `LC_ALL=C`, add: `INPUT=$(cat 2>/dev/null) || INPUT=''`
3. Initialize `HOOK_CWD=""` and `SID=""` alongside `MSG=""`.
4. After the git-state block, add a boundary-detection block gated on `JQ_AVAILABLE=true && -n "$INPUT"`:
   - Extract `HOOK_CWD` and `SID` from `$INPUT` via jq
5. In a block gated on `[[ -n "$HOOK_CWD" ]]`:
   - Derive `PLUGIN_ROOT` from `CLAUDE_PLUGIN_ROOT` or `$SCRIPT_DIR/..`
   - Source `$PLUGIN_ROOT/skills/implement/scripts/lib-resolve-implement-tmpdir.sh` (with `2>/dev/null || true`)
   - If `resolve_implement_tmpdir` function is defined:
     - Export `LARCH_TOKEN_SESSION_ID="$SID"` if SID non-empty
     - `IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD") || IMPLEMENT_TMPDIR=""`
     - If tmpdir found and `.run-cleaned-up` absent:
       - Check `design-export/manifest.env` without `.boundary-gate-passed` → append advisory
       - Check `review-round-summary.md` without `.review-boundary-passed` → append advisory
       - Check `.bump-version-armed` without `postbump-state.sh` → append advisory

All advisory messages go through `append_msg`, which feeds into `jq -n --arg ctx "$MSG"` at emission time. This preserves the INVARIANT: dynamic content (including TMPDIR_BASENAME) is interpolated only via `jq -n --arg`.

#### `scripts/test-sessionstart-health.sh`
1. Add `stat`, `basename`, `date`, `touch` to `build_bin` so resolver's mtime/basename calls work in the test PATH.
2. Add `run_with_stdin` helper that pipes JSON to stdin and accepts `XDG_CACHE_HOME`.
3. Create `XDG_TEST="$tmp/xdg-cache"` and `make_impl_tmpdir` helper.
4. Add test cases:
   - **Case 12**: manifest.env without .boundary-gate-passed → advisory contains "post-/design boundary" and "post-design-boundary.sh"
   - **Case 12b**: manifest.env WITH .boundary-gate-passed → no "post-/design boundary" in advisory
   - **Case 13**: .run-cleaned-up present → no advisory
   - **Case 14**: review-round-summary.md without .review-boundary-passed → advisory contains "post-/review boundary"
   - **Case 14b**: review-round-summary.md WITH .review-boundary-passed → no advisory
   - **Case 15**: .bump-version-armed without postbump-state.sh → advisory contains "post-/bump-version boundary"
   - **Case 15b**: .bump-version-armed WITH postbump-state.sh → no advisory

### Edge Cases
- Empty INPUT (stdin from /dev/null, existing tests): HOOK_CWD stays empty, boundary detection skipped — no regression
- jq unavailable: boundary detection skipped (JQ_AVAILABLE=false gate), existing fixed-literal path unchanged
- lib not found: `[[ -f "$LIB_RESOLVE" ]]` guard, fail-open
- resolver returns empty: `[[ -n "$IMPLEMENT_TMPDIR" ]]` guard, fail-open
- All three boundaries can fire simultaneously (MSG concatenated)

### Testing Strategy
Run `bash scripts/test-sessionstart-health.sh` — all existing cases (1-11) plus new cases (12-15b) must pass.
Also run `make lint` to catch any linting regressions.

## Test plan
(no test plan section in plan-file)
