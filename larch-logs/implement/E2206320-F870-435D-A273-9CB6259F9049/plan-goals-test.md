## Goal
Remove duplicated review loop from /implement Step 5, replace with review-and-fix.sh calls

## Implementation Plan

### Goal
Wire /implement Step 5 to review-and-fix.sh, removing ~150 lines of duplicated review logic from skills/implement/SKILL.md (the quick-mode inline loop Steps 5.1–5.8 and the normal-mode /review Skill invocation), replacing both with a single bash call per round.

### Approach

The existing `review-and-fix.sh` is a fixer-enumerator (finds accepted findings). The new orchestrator will be a NEW script at `skills/review-and-fix/scripts/review-orchestrate.sh` but the issue calls for `review-and-fix.sh` path. Rather than rename the existing file (breaking the /review-and-fix skill), I'll ADD an orchestrator mode to the existing `review-and-fix.sh` detected by the presence of `--implement-tmpdir` flag.

**Round-per-call design (not single-call for all rounds)**: The `review-and-fix.sh` script handles one review round. The SKILL.md has a compact ~20-line loop. This achieves the stated goal (remove 100+ lines of duplication) while keeping the main agent's fix-application capability intact.

### Files to modify

1. **`skills/review-and-fix/scripts/review-and-fix.sh`** — Add orchestrator mode:
   - New flags: `--panel simple|hard`, `--mode diff`, `--diff-file FILE`, `--commit-count N`, `--plan-file FILE`, `--feature-file FILE`, `--implement-tmpdir DIR`, `--session-env-path FILE`, `--run-id ID`
   - Orchestrator mode detection: `--implement-tmpdir` present → orchestrator mode
   - Calls `review-core.sh` for one round, writes `review-and-fix-summary.json`, accumulates OOS in `accumulated-oos.jsonl`
   - Exit 0: no accepted findings (done or zero-findings)
   - Exit 2: wholesale rejection (BLOCKING)
   - Exit 3: accepted findings exist → writes approved-fixes path, main agent applies

2. **`skills/review-and-fix/scripts/review-and-fix.md`** — Update contract doc

3. **`skills/implement/SKILL.md`** — Step 5 rewrite:
   - Remove Quick mode section (5.1–5.8, ~100 lines)
   - Remove Normal mode /review Skill invocation (~15 lines)
   - Remove post-/review dirty-tree handling (~30 lines)
   - Replace with breadcrumb + gather-context + compact round loop (~25 lines)
   - Update `code-review-tally` batch to read from `review-and-fix-summary.json`
   - Update `review-findings-full` batch to read from round-*/findings.md
   - Update `Track Rejected Code Review Findings` to read from round outputs
   - Remove `Pre-/review untracked snapshot` standalone block (handled by review-core.sh)
   - Update Step 9a.1 OOS to read from `accumulated_oos_file` in summary.json

4. **`.github/workflows/ci.yaml`** — Remove `skills/implement/SKILL.md` from UNQUOTED_FILES (the enum no longer lives there; it's in dispatch-panel.sh/review/SKILL.md)

5. **`skills/implement/scripts/test-implement-review-token-propagation.sh`** — Update assertions to reflect new architecture

6. **`skills/implement/scripts/test-implement-review-token-propagation.md`** — Update sibling doc

### Edge cases
- NEVER #6 compatibility: removing from SKILL.md is OK because CI check is updated in same PR
- The existing fixer mode of review-and-fix.sh is preserved for backward compat with /review-and-fix SKILL.md
- OOS accumulation across rounds via accumulated-oos.jsonl
- Dirty-tree handling moves fully into review-core.sh (already handles it)


## Test plan
- /relevant-checks passes (pre-commit + agent-lint)
- test-implement-review-token-propagation.sh assertions updated
- The enum CI check passes with SKILL.md removed from UNQUOTED_FILES
