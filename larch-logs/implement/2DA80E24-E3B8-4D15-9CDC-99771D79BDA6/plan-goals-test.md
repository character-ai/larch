## Goal
Fix BSD-incompatible head -n -N that truncates plan.txt and include actual tmpdir in hook directive

## Implementation Plan

Fix BSD-incompatible `head -n -N` truncating `plan.txt` during plan review, and include actual paths in the post-design-boundary hook directive.

### Files Modified

1. `skills/design/references/plan-review.md` — step 4 in Finalize Plan Review: replace ambiguous "Preserve and update the final diff_lines line" with explicit Write-tool-only directive forbidding in-place Bash manipulation.
2. `skills/implement/scripts/post-design-boundary.sh` — hook-mode NEXT REQUIRED directive: replace `...` placeholder with actual `$IMPLEMENT_TMPDIR`, `$SESSION_ENV_PATH`, and `$DESIGN_ONLY` values.

### Approach

Both changes are already committed on the feature branch. The root cause was:
- `plan-review.md` step 4 said "Preserve and update the final diff_lines line" without specifying how; the model chose `head -n -N` which fails on BSD/macOS.
- `post-design-boundary.sh` hook mode emitted `--implement-tmpdir ...` (literal `...`) leaving the model without the exact command after context compression.

The fixes add explicit Write-tool-only guidance and include actual path values in the directive.

### Edge Cases

- `head -n -N` failures: now prevented by explicit "do NOT use Bash commands" guidance.
- Post-compression halt: now mitigated by including actual tmpdir in NEXT REQUIRED directive.

### Failure Modes

1. Regression in test assertions: the test uses glob matching (`"... context;"*`) so new text after semicolon is still covered.

### Testing Strategy

- `test-post-design-boundary.sh` validates hook-mode directive starts with expected prefix (glob match).
- `/relevant-checks` runs pre-commit hooks including shellcheck and markdownlint.

diff_lines: 6

## Test plan
(no test plan section in plan-file)
