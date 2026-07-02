## Goal
Implement issue #6031: [IMPLEMENTING] [BUG] #5974 residuals: dead symlink check and first_tool telemetry mislabel.

## Implementation Plan
## Summary

Two cosmetic telemetry defects from #5974 / PR #6012 (per-slot prompt-size instrumentation): a symlink check that can never fire in the prompt-size path resolution, and a `first_tool` label in coder telemetry that cannot represent the Claude tier of the review-fix lane.

## Original report

From the 2026-07-02 post-merge audit of #5974 / PR #6012 at 63ed17f18. Both LOW severity; neither affects functional behavior or data safety. Filed for completeness per the operator's request to file all audit findings.

## Reproduction scenario

- Symlink check: call `_repo_relative_agent_path` with a symlinked agents file; `path.resolve(strict=True)` returns the resolved target, so the subsequent `resolved.is_symlink()` is False by construction and the intended symlink policy never fires. The row is logged under the target path.
- Label: configure a claude-first order for review.fix_coder (hypothetical today; the default order is codex, cursor, claude) and complete a fix round with claude: the telemetry tool column mislabels the row.

## Expected behavior

Symlink policy is enforced where it can fire (check the original path before resolution) or removed with the target-path logging behavior documented; `first_tool` covers all tiers of the lane it labels.

## Observed behavior

- python/larch/report/tokens.py, `_repo_relative_agent_path` (near line 263 at 63ed17f18): dead `resolved.is_symlink()` check after `resolve(strict=True)`. Safety is preserved by the post-resolution repo-containment check.
- python/larch/review/coder_runner.py:409: `first_tool` filters to the set {"cursor", "codex"}; #5888 added the Claude tier to review.fix_coder, making the omission reachable-by-configuration.

## Root cause analysis

The symlink check was written after resolution rather than before it; the first_tool set predates the Claude tier. Both observed directly in code.

## Evidence

Code reads at 63ed17f18 (citations above); audit cross-check that the default registry order keeps the label accurate today.

## Affected files

- python/larch/report/tokens.py.
- python/larch/review/coder_runner.py.

## Suggested fix(es)

Move the symlink check to the pre-resolution path (or delete it and document target-path logging); add "claude" to the first_tool candidate set.

## Open questions

None identified.

## Test plan
(no test plan section in plan-file)
