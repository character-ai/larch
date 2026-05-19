## Goal
Change default coder from codex to cursor in the implementer waterfall

## Implementation Plan

Goal: Change the default implementer from Codex to Cursor when --coder is not explicitly passed.

Files to modify:
1. skills/implement/SKILL.md — reverse waterfall (lines 1072, 1080-1082, 1226)
2. skills/implement/scripts/step2-implement.sh — default CODER=cursor (lines 16, 124-126)
3. skills/implement/scripts/test-step2-dispatch.sh — update test 1b (lines 7-8, 92-106)
4. skills/implement/scripts/test-step2-dispatch.md — update test 1b description (line 5)
5. scripts/test-implement-step2-routing.sh — update string assertions (lines 23, 27, 29)
6. scripts/test-implement-step2-routing.md — update waterfall description (lines 5-6)

Verification: make test-step2-dispatch && make test-implement-step2-routing

## Test plan
(no test plan section in plan-file)
