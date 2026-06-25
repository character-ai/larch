## Goal
Implement issue #5351: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] codex_effort plugin copy misstates per-role routing scope.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt

**Phase**: implement

**Vote tally**: N/A


## Description

`codex_effort` description in `.claude-plugin/plugin.json` still claims it applies to all Codex launches including voting. After per-role model routing, operators may assume effort affects mini review/vote slots the same as implementer launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align codex_effort copy with per-role model routing (optional follow-up).
  - From cursor-specialist-edge-cases-output.txt: Update codex_effort copy to match per-role model routing or note review/vote/fix behavior explicitly.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
