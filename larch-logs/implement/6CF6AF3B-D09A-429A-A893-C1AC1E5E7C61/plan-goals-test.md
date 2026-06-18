## Goal
Implement issue #4638: [IMPLEMENTING] sh-to-py G9: /implement Step-0/2/5/6 entry + OOS + execution-issues bodies — port in-process.

## Implementation Plan
## Plan

Port the remaining `/implement` step-entry wrappers, OOS helpers, and execution-issues bodies to direct Python CLI surfaces per the standard sh-to-py recipe. Use existing Python ports where present; add only missing in-process verbs. Keep behavior byte-compatible.

Key scope notes from plan review:
- No parallel `implement post-tracking-issue/slack-issue-announce/code-flow-diagram` verbs; use existing `tracking post-issue`, `slack issue-announce`, `diagram code-flow`.
- Step 18 safety-net: dedicated `flush_execution_issues_safety_net()` + `execution-issues flush-safety-net` verb (append-only, never truncates).
- Step 7a flush parity: fix sentinel-match vs batch-match branch split before wrapper deletion.
- Harness cutover: retire shell harnesses before deleting underlying scripts.

## Acceptance

The plan review panel ran 5 rounds and accepted 5 findings (all applied). No OOS items filed.

diff_lines: 5900

## Test plan
(no test plan section in plan-file)
