## Goal
Align step8b_same_version to canonical step8_apply_bump_same_version in SKILL.md

## Implementation Plan

**Objective**: Align the `step8b_same_version` token in `skills/implement/SKILL.md` to the canonical `step8_apply_bump_same_version` token defined in `skills/implement/references/rebase-rebump-subprocedure.md`.

**Files to modify**:
- `skills/implement/SKILL.md` (2 occurrences of `step8b_same_version`)

**Occurrences to replace**:
1. NEVER #15 (~line 62): "currently `step8b_same_version` and `step8b_rebase`" → "currently `step8_apply_bump_same_version` and `step8b_rebase`"
2. Step 8+ exit-5 handler (~line 1752): "(`step8b_rebase` or `step8b_same_version`)" → "(`step8b_rebase` or `step8b_same_version`)" (also `step8b_same_version`)

**Approach**: Use `sed` or `Edit` tool for a replace_all substitution. The canonical token `step8_apply_bump_same_version` is established in `rebase-rebump-subprocedure.md` as a "do NOT rename" contract token. No script files change — the sub-procedure already uses the canonical name.

**Verification**: Run `/relevant-checks` after edit to confirm no lint failures.

**Edge cases**: Confirm no other occurrences elsewhere (e.g., in scripts or agents). Grep confirms the two SKILL.md occurrences are the only divergence.

**Test strategy**: `make lint` / `/relevant-checks` (pre-commit + agent-lint).

## Test plan
(no test plan section in plan-file)
