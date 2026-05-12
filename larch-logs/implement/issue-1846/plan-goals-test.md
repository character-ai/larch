## Goal
Fix the silent turn-end halt gap at the /fix-issue post-/implement boundary.

## Plan
1. `skills/fix-issue/SKILL.md` line 201: add "do NOT end the turn (neither silently nor after text output)" to the post-/implement success directive.
2. `scripts/test-implement-anti-halt.sh`: add regression test pin for this boundary.
3. `scripts/test-implement-anti-halt.md`: update assertion count from 18 to 19.

## Test plan
- `bash scripts/test-implement-anti-halt.sh` passes 19 assertions
- `/relevant-checks` (pre-commit + agent-lint) passes
