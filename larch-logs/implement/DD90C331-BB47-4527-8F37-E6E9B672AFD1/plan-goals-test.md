## Goal
Implement issue #5395: [IMPLEMENTING] Drop Codex GPT 5.5 generic profile reviewer in /implement and /design and /review review process.

## Implementation Plan
Currently, we launch a large set of Cursor and Codex 5.4 Mini agents during review with static and dynamic archetypes.  Yesterday, we have also added Codex generic profile reviewer (I believe first 2 rounds only).  Undo that change, i.e., drop Codex/GPT 5.5 generic profile reviewer entirely, so it's not called on any review rounds.

## Test plan
(no test plan section in plan-file)
