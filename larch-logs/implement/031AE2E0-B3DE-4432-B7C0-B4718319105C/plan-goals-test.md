## Goal
Stage unstaged tracked files in run_ci_fix_vendor() before committing, preventing dirty-tree stall when CI-fix tools modify files without staging them

## Implementation Plan

### Goal
Fix `run_ci_fix_vendor()` in `scripts/ship-pr.sh` to stage all tracked modified files before committing. When CI-fix tools leave unstaged changes, `git diff --quiet HEAD` detects them but `git-commit.sh` without file args only commits staged changes — causing either "nothing to commit" failure or a partial commit that leaves the tree dirty on the next pass.

### Files to modify
- `scripts/ship-pr.sh` (~line 724): add `git add -u` before `git-commit.sh` in `run_ci_fix_vendor()`

### Change
In `run_ci_fix_vendor()`, before the existing `git-commit.sh` call, add a `git add -u` step following the established `fail_file` / `rc` / `record_failure` pattern:

```bash
if ! git diff --quiet HEAD 2>/dev/null; then
    fail_file=$(failure_capture_path "$phase")
    git add -u > "$fail_file" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        record_failure "$phase" "git add -u" "$rc" "$fail_file" "CI Issues"
        return 1
    fi
    fail_file=$(failure_capture_path "$phase")
    "$SCRIPT_DIR/git-commit.sh" -m "Fix CI failure" > "$fail_file" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        record_failure "$phase" "git-commit.sh" "$rc" "$fail_file" "CI Issues"
        return 1
    fi
fi
```

### Audit of other git-commit.sh call sites in ship-pr.sh
Only one call at line 726 in `run_ci_fix_vendor()`. `run_rebase_rebump()` does NOT call `git-commit.sh` — it calls `classify-bump.sh` and `apply-bump.sh` directly for the re-bump, and the conflict-resolution path invokes the CI launcher tools which handle their own commits. No other callers need patching.

### Edge cases
- `git add -u` stages only tracked modified/deleted files, not untracked new files. CI-fix tools (Cursor/Codex) primarily modify tracked files — correct choice.
- If `git add -u` fails, we log to CI Issues and return 1, same as other failures in this function.


## Test plan
Run `/relevant-checks` after the change.
