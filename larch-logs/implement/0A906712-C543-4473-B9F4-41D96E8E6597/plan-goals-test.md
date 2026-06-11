## Goal
Implement issue #3997: [IMPLEMENTING] All long-running scripts should be spawned in immediate-background (rather than after-10-minutes) mode\n\n/design:.

## Implementation Plan
/design:
  - review loop

/implement:   
  - review loop
  - ship-pr

Also, other scripts called from both skills should be inspected to see if they take over 30 seconds (can check run logs), and if yes, should also be backgrounded on launch immediately, rather than kept in foreground for first 10 minutes.

## Test plan
(no test plan section in plan-file)
