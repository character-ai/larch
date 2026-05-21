## Goal
Remove the --auto flag and auto_mode variable from implement, design, fix-issue, agnix-fix, and all helper scripts

## Implementation Plan

Goal: Remove the `--auto` flag and `auto_mode` variable from /implement, /design, /fix-issue, agnix-fix, and all touched helpers/scripts.

### Files to modify

**SKILL.md files (prompt instructions)**:

1. `skills/implement/SKILL.md`
   - Remove `[--auto]` from argument-hint (line 4)
   - Remove the `--auto` flag entry from the Flags section (the entire bullet starting with `- \`--auto\``)
   - Remove `--auto` from `--forked` compatibility list
   - Remove "`[--auto] [--subagent]`" prefix from the `/design` invocation in normal mode
   - Remove `--auto-mode "$auto_mode"` from write-session-env.sh call
   - Remove `auto_mode`-gated Step 2 opportunistic questions prose
   - In NEVER #16 and Step 8+ ship-pr.sh invoke block: remove `--auto-mode "$auto_mode"` from the call, and update the "flags not recorded as durable keys in ship-pr-state.sh (at minimum `--auto-mode` and `--no-admin-fallback`)" to just "`--no-admin-fallback`"
   - In NEVER #16 and Step 8+ warning block: update "at minimum `--auto-mode` and `--no-admin-fallback`" references to just `--no-admin-fallback`
   - In Step 0 `write-session-env.sh` call: remove `--auto-mode "$auto_mode"` line
   - In session-env notes: remove `LARCH_AUTO_MODE` mention
   - In Step 2.3 Q/A loop: remove the `auto_mode=true` best-effort answer branch (make `AskUserQuestion` always happen) 
   - In Step 2.4 opportunistic questions: remove the `auto_mode=false` guard (always ask)
   - In NEVER #16 mention of "In `--auto` mode this stalls indefinitely...": remove that parenthetical
   - In Step 12 merge-conflict resolution reference: remove `auto_mode=false` → AskUserQuestion / `auto_mode=true` → bail branch

2. `skills/design/SKILL.md`
   - Remove `[--auto]` from argument-hint
   - Remove `--auto` row from the flags table  
   - Steps 1c, 1d, 3.5: remove `If auto_mode=true: Print ⏩ ... skipped (auto mode)` short-circuits; always run the interactive rounds
   - In `--subagent` nested path (Step 2a.2): remove `if auto_mode=false proceed to Step 3.5; if auto_mode=true proceed to Step 5` branching — always run Step 3.5
   - Various other `auto_mode` conditional prose: convert to unconditional

3. `skills/fix-issue/SKILL.md`
   - Remove `[--auto]` from argument-hint
   - Remove the `--auto` flag entry (entire bullet)
   - Remove `[--auto if auto_mode]` from Step 5a `/implement` invocation

4. `.claude/skills/agnix-fix/SKILL.md`
   - Drop `--auto` from the `/implement` forwarding args: change `--forked --quick --auto --coder=codex` to `--forked --quick --coder=codex`

**Script files**:

5. `scripts/ship-pr.sh`
   - Remove `AUTO_MODE="false"` default
   - Remove `--auto-mode` arg parser block
   - Remove `is_bool "$AUTO_MODE" || die_usage "--auto-mode must be true or false"` validation
   - Remove `[--auto-mode true|false]` from usage string

6. `scripts/write-session-env.sh`
   - Remove `--auto-mode` option parsing
   - Remove `AUTO_MODE` variable and validation
   - Remove `LARCH_AUTO_MODE=$AUTO_MODE` from the written output

7. `skills/implement/scripts/run-step2-dispatch.sh`
   - Remove `AUTO_MODE` variable reading from session-env
   - Remove AUTO_MODE validation
   - Remove `--auto-mode "$AUTO_MODE"` from step2-implement.sh invocation

8. `skills/implement/scripts/step2-implement.sh`
   - Remove `AUTO_MODE=""` default
   - Remove `--auto-mode` arg parser
   - Remove `AUTO_MODE` from required vars list
   - Remove AUTO_MODE case validation

9. `skills/implement/scripts/write-final-report.sh`
   - Remove `AUTO_MODE=...` read from session-env
   - Remove `[ "$AUTO_MODE" = "true" ] && mode_parts+=("--auto")` line

**Test/harness files**:

10. `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh`
    - Drop assertion (a4): the comment line and the `assert_contains "a4: ..."` line

11. `skills/implement/scripts/test-run-step2-dispatch.sh`
    - Remove `LARCH_AUTO_MODE` line from `make_tmpdir` function
    - Remove the `auto_mode` parameter from `make_tmpdir` calls
    - Remove the "reject invalid auto-mode boolean" test block
    - Update the two `assert_file_equals` argv strings to not include `--auto-mode`

**Documentation/md siblings**:

12. `skills/implement/scripts/run-step2-dispatch.md`
    - Remove `LARCH_AUTO_MODE` from the forwarded keys list

13. `skills/implement/scripts/test-run-step2-dispatch.md`
    - Remove `LARCH_AUTO_MODE` from the documented inputs

14. `skills/implement/scripts/write-final-report.md`
    - Remove `AUTO_MODE` from the session-env.sh keys table

15. `skills/design/references/flags.md`
    - Remove the `--auto` entry entirely

16. `skills/design/references/heavy-worker.md`
    - Remove `auto_mode` from the explicit data list passed to the subagent
    - Update/remove `auto_mode=true` conditional logic references

17. `skills/design/references/heavy-worker.digest.md`
    - Remove `auto_mode` from the passed-data list
    - Update/remove `auto_mode=true` references

### Approach

Mechanical search-and-delete/edit. No new abstractions. Work file by file in the order above.


## Test plan

- `make lint` and `agent-lint` pass
- `/implement --auto <issue>` refuses with unknown-flag error (acceptance criterion - via the SKILL.md change making `--auto` unrecognized)
- Acceptance: `make lint` passes cleanly
