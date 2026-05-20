## Goal
Add pre-push working-tree-clean guard to prevent silent data loss from uncommitted inline-OOS-fold changes

## Implementation Plan

Add a pre-push working-tree-clean check (issue #2434, Option A).

### 1. scripts/create-pr.sh

Add before the "Get current branch" block (line ~97):

    DIRTY_FILES=$(git status --porcelain 2>/dev/null || true)
    if [[ -n "$DIRTY_FILES" ]]; then
        larch_err "ERROR: Uncommitted working-tree changes detected before push. ..."
        larch_err "$DIRTY_FILES"
        exit 1
    fi

This single check covers all three push sites in the file (new-PR path,
existing-PR fast-path plain push, existing-PR fast-path force-push escalation).

### 2. scripts/git-force-push.sh

Same check after emit_kv BRANCH "$BRANCH" (line ~55). Defense-in-depth for
direct callers (merge-pr.sh, /implement Step 8b).

### 3. scripts/test-create-pr.sh

Add 3 tests before the final echo "PASS..." line:
- (i) Clean tree → push proceeds (PR_STATUS=created)
- (ii) Dirty tracked-modified file → exits non-zero with descriptive error
- (iii) Dirty untracked file → exits non-zero with descriptive error

### 4. scripts/create-pr.md

Add a "Pre-push clean-tree guard" section documenting new exit-1 case.

### 5. scripts/git-force-push.md

Update exit-code table (add exit-1 case for dirty tree) and document the guard.

### 6. docs/workflow-lifecycle.md

Add "Pre-push Clean-Tree Invariant" section at end.

No Makefile changes needed: test-create-pr is already in test-harnesses-8.

## Test plan
(no test plan section in plan-file)
