## Goal
Optimize the reviewer launch pipeline: (A) session-scoped memoization of render-specialist-prompt.sh, (B) pre-rendered agent body files for faster startup, (C) explicit GEMINI_REVIEW=1 gate for the Gemini lane.

## Implementation Plan
See above inline plan in SKILL.md.

## Test plan
- test-render-specialist-prompt.sh: cache-hit/miss cases (A), pre-rendered body detection (B)
- test-check-generators.sh: updated row count/canonical rows pin (B)
- test-launch-review.sh: GEMINI_REVIEW guard case (C)
- make relevant-checks on modified files
