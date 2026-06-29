## Goal
Implement issue #5817: [IMPLEMENTING] /design and /review skill review phase judges should have backup waterfall.

## Implementation Plan
Those that are defaulted to Cursor should be Cursor -> Codex 5.4 mini -> Claude Sonnet 4.6
Those that are defaulted to Codex 5.4 Mini should be Codex 5.4 Mini -> Cursor -> Claude Sonnet 4.6

I believe, currently, there is no waterfall, i.e., if a vendor/model combo is unavailable, its judge is simply dropped from the panel.

## Test plan
(no test plan section in plan-file)
