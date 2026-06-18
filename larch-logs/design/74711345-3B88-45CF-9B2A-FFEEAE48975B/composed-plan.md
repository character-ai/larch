## Plan

Port the remaining `/implement` step-entry wrappers, OOS helpers, and execution-issues bodies to direct Python CLI surfaces per the standard sh-to-py recipe. Use existing Python ports where present; add only missing in-process verbs. Keep behavior byte-compatible.

Key scope notes from plan review:
- No parallel `implement post-tracking-issue/slack-issue-announce/code-flow-diagram` verbs; use existing `tracking post-issue`, `slack issue-announce`, `diagram code-flow`.
- Step 18 safety-net: dedicated `flush_execution_issues_safety_net()` + `execution-issues flush-safety-net` verb (append-only, never truncates).
- Step 7a flush parity: fix sentinel-match vs batch-match branch split before wrapper deletion.
- Harness cutover: retire shell harnesses before deleting underlying scripts.

## Acceptance

The plan review panel ran 5 rounds and accepted 5 findings (all applied). No OOS items filed.

review_status: complete
rounds_completed: 5
diff_lines: 5900
