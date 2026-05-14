## Goal
Pass the design plan to CI fix and rebase conflict launchers so they don't undo implementation work

## Implementation Plan

Goal: Pass the design plan to CI fixer and rebase conflict resolver so external agents don't undo implementation work.

### Files to modify

1. **scripts/launch-cursor-ci.sh**
   - Add `PLAN_FILE=""` variable declaration
   - Add `--plan-file PATH` to usage string
   - Add `--plan-file) PLAN_FILE=$2; shift 2 ;;` to arg parsing
   - Add path validation: `case "$PLAN_FILE" in /*) ;; "") ;; *) die "--plan-file must be an absolute path" ;; esac`
   - Before PROMPT construction: build `PLAN_CONTEXT` by reading the file when `PLAN_FILE` is non-empty and exists
   - Insert plan context into the PROMPT between "Working directory" line and "Inspect the repository" line

2. **scripts/launch-codex-ci.sh**
   - Identical changes (parity requirement per `.claude/rules/external-tool-launcher-parity.md`)

3. **scripts/ship-pr.sh**
   - Add `read_session_plan_file()` helper function that reads `PLAN_FILE` from `$IMPLEMENT_TMPDIR/session-env.sh` using awk (same safe pattern used for `LARCH_CLAUDE_PLUGIN_ROOT=` reads throughout the codebase)
   - In `run_ci_fix_vendor()`: call helper, build `plan_args=()`, append `--plan-file "$plan_file"` when PLAN_FILE non-empty and file exists; pass `${plan_args[@]+"${plan_args[@]}"}` to both launcher invocations
   - In `run_rebase_rebump()`: same for the resolve-conflict launcher invocations

4. **scripts/launch-cursor-ci.md** — update Interface section to add `[--plan-file PATH]`

5. **scripts/launch-codex-ci.md** — same update

6. **scripts/test-launch-cursor-ci.sh** — add two assertions:
   - `assert_fails "rejects relative --plan-file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --plan-file relative/plan.txt`
   - `if grep -q 'plan-file' "$REPO_ROOT/scripts/launch-cursor-ci.sh"; then ok "script supports --plan-file"; else fail "script supports --plan-file"; fi`

7. **scripts/test-launch-codex-ci.sh** — same two assertions

### Prompt change details

When `PLAN_FILE` is non-empty and the file exists:
```
PLAN_CONTEXT="
Design plan (do not revert or undo the work it describes):
$(cat "$PLAN_FILE")"
```

The PROMPT becomes:
```
You are fixing larch /implement CI subwork.

Role: $ROLE
Repository: $REPO
Failed run id: $RUN_ID
Working directory: $PWD
$PLAN_CONTEXT

Inspect the repository and CI logs as needed...
```

When `PLAN_FILE` is empty, `$PLAN_CONTEXT` is "" and the prompt is unchanged.

### ship-pr.sh helper

```bash
read_session_plan_file() {
    local session_env="$IMPLEMENT_TMPDIR/session-env.sh"
    [ -f "$session_env" ] || return 0
    awk 'BEGIN{k="PLAN_FILE"; kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$session_env"
}
```

### Testing strategy

- Run `scripts/test-launch-cursor-ci.sh` and `scripts/test-launch-codex-ci.sh` to verify existing assertions + new ones pass
- Run `/relevant-checks` (pre-commit + agent-lint)
- Verify shell scripts pass shellcheck (already enforced by pre-commit)

## Test plan
(no test plan section in plan-file)
