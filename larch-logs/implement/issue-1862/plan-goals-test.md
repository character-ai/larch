## Goal
Add mechanical Stop-hook enforcement for the post-/review boundary (issue #1862), plus regression-test pins for the new sentinel mechanism.

## Implementation Plan

**Sentinel design** (analogous to post-design): `review-round-summary.md` (written by /review) serves as "review ran"; `.review-boundary-passed` (written by orchestrator at Step 6 start) serves as "boundary cleared". Stop hook blocks when the first exists without the second.

**Files changed**:
1. `skills/implement/scripts/hook-stop-fail-close.sh` — add post-review boundary check block
2. `skills/implement/SKILL.md` — add `.review-boundary-passed` sentinel write at Step 6 start + update anti-halt description
3. `scripts/test-implement-anti-halt.sh` — add two check_contains assertions for the new sentinel
4. `scripts/test-implement-anti-halt.md` — update assertion count

## Test plan
- `bash scripts/test-implement-anti-halt.sh` → all assertions pass
- `/relevant-checks` → pre-commit + agent-lint pass
