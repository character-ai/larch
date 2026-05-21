## Goal
Align `CALLER_KIND` wire token `step8b_same_version` to canonical `step8_apply_bump_same_version` across SKILL contract, `ship-pr.sh`, and harnesses.

## Implementation Plan

**Objective**: Emit and assert the canonical `step8_apply_bump_same_version` token everywhere runtime state and tests depend on it, matching `skills/implement/SKILL.md`, `skills/implement/references/rebase-rebump-subprocedure.md`, and related docs.

**Files to modify**:
- `skills/implement/SKILL.md` (NEVER #15 and Step 8+ exit-5 handler prose, if any legacy name remains)
- `scripts/ship-pr.sh` (`state_set_many` for exit `5` same-version / version-regression paths)
- `scripts/test-ship-pr.sh` and `scripts/test-ship-pr.md` (assertions and harness bullet list)

**Occurrences to replace**:
1. `ship-pr.sh`: persist `CALLER_KIND=step8_apply_bump_same_version` (not `step8b_same_version`) when exiting `5` for `apply-bump.sh` same-version race and version-regression errors.
2. Harness/docs: update expected `CALLER_KIND` lines to `step8_apply_bump_same_version`.
3. `SKILL.md`: any remaining `step8b_same_version` prose → `step8_apply_bump_same_version` alongside `step8b_rebase` where the wire value is described.

**Approach**: Edit writers and tests together so `ship-pr-state.sh` matches the markdown contract; grep the repo (excluding historical `larch-logs/` transcripts) for `step8b_same_version` and eliminate runtime/script/skill occurrences.

**Verification**: Run `/relevant-checks` after edits. Scoped grep: `step8b_same_version` must not appear under `scripts/`, `skills/`, or `agents/`; `step8_apply_bump_same_version` must appear in `ship-pr.sh` exit-5 paths and harness expectations.

**Edge cases**: Old session trees or committed run logs may still mention the legacy token; do not treat those as authoritative wire values.

**Test strategy**: `make test-ship-pr` where applicable, plus `/relevant-checks` (pre-commit + agent-lint).

## Test plan
(no test plan section in plan-file)
