## Goal
Implement issue #4060: [IMPLEMENTING] In both /design and /implement, starting with review round 3, we don't spawn codex as reviewer, only Cursor\n\nWe only spawn Codex as replacement for Cursor, if Cursor is unavailable, but we don't spawn Codex starting with round 3..

## Implementation Plan
We only spawn Codex as replacement for Cursor, if Cursor is unavailable, but we don't spawn Codex starting with round 3.
For rounds 1 and 2, nothing changes from status quo -- we spawn both.

## Test plan
(no test plan section in plan-file)
