### [Plan Review] FINDING_1

### FINDING_1: Step 3 direct-review step-1e write host is ambiguous
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Concern**: The plan folds `step-1e` into Step 3 but does not pin it to the first Step 3 bash fence before the pause-check. Because Step 3 has multiple entry fences, a pause between them can still snapshot before `step-1e` is written and resume by replaying Gate A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the folded step-1e write to the first bash fence after <!-- step:3 (timing prelude), before its pause-check; mirror that host in assert_folded_sentinel_writes via extract_first_bash_fence_after. Optionally idempotently repeat in the preview fence
  - From Cursor-dyn-test-claim-mapping: step-1e may be written after the first pause-check so pause/resume replays Gate A instead of continuing review Pin step-1e to the first Step 3 timing prelude fence (before its pause-check) and add a matching assert_folded host row


### [Plan Review] FINDING_3

### FINDING_3: Step 3 direct-review resume needs more than step-1e
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Writing only `step-1e` before Step 3 pause-check may not make direct-review pause snapshots resume at Step 3, because `design-pause-save.sh` derives the resume step from sentinel state rather than current control flow. Missing prior sentinels or stale downstream sentinels can resume too early or too late.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a route shape the saver can distinguish before Step 3 pause-check: either reset downstream review/finalization sentinels and ensure prior plan-production sentinels exist when plan.txt exists, or add an explicit Step 3 re-entry marker that design-pause-save.sh honors. Extend the pause-resume test to cover a prior Gate C stale-sentinel direct-review case.


### [Plan Review] FINDING_9

### FINDING_9: Step 3.5 folded assertions can conflict with Gate-B-bypass writes
- **Reviewer(s)**: Cursor-dyn-test-claim-mapping
- **Severity**: important
- **Concern**: If `assert_folded_sentinel_writes` treats Step 3.5 as the only valid `step-3` host, it can false-fail or fight the preserved Gate-B-bypass inline triple-sentinel writes in Step 3 branch prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-claim-mapping: An assert_folded implementation that treats Step 3.5 as the only valid step-3 host can false-fail or fight preserved Gate-B-bypass pins Document that assert_folded applies only to listed host fences; keep Gate-B-bypass prose writes under existing contains pins without requiring pause-check ordering there


