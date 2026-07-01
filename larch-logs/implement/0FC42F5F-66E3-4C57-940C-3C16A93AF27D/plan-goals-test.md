## Goal
Implement issue #5921: [IMPLEMENTING] /implement --force forces coder=claude; split into new --self-implement flag (default false).

## Implementation Plan
/implement --force should NOT force main agent to implement, it should only allow an issue to be implemented without /design.  To force main agent to implement, add a new flag --self-implement (similar to --self-review).  --self-implement by default is FALSE, and only becomes true if the flag is passed.

## Test plan
(no test plan section in plan-file)
