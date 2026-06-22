## Goal
Implement issue #5082: [IMPLEMENTING] [OOS] Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Innovation
**Phase**: design
**Vote tally**: N/A

## Description

Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`. Scenario: Assessment prompts skip the containment, timeout caps, timing sidecars, and stderr capture that `launch_claude_subprocess_main` provides elsewhere; failures are harder to diagnose in run logs

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
