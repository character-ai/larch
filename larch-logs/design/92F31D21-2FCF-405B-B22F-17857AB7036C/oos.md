### FINDING_1: Blocking todo count must cover the full manifest
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The blocking-todo count can undercount real deferred work if counting is limited to the display window or stops at the character budget, which can incorrectly clear `disposition_required` and `TODOS_LEFT_COUNT` while blocking items still exist later in the manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split classify/count from display: validate every entry, classify blocking vs nonblocking across the entire array, set `todos_left_count` to the full blocking count, then build bounded `todos_left` text from blocking items only; add a unit test with a blocking todo at index 21 (and optionally one truncated only by char budget) still requiring disposition


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Blocking classifier needs a fail-closed pre-check
- **Reviewer(s)**: Cursor-dyn-Scope Gate Reviewer
- **Severity**: minor
- **Concern**: The blocking/nonblocking classifier can miss compound todo text that includes both validation wording and real work items, which risks filtering out genuinely blocking items and suppressing disposition when work remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Scope Gate Reviewer: Define the helper as fail-closed: return blocking unless ALL hold: (1) no failure/action tokens (fail/failing/failed, fix, add, implement, missing, need, docs, write, etc.), (2) full-suite validation context, (3) make py-lint or make py-test mention. Add a unit test in python/tests/implement/test_scope_disposition.py for that compound string plus a mixed manifest case (benign validation todo + "finish docs" => todos_left_count==1)


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Docs still say any non-empty todos_left requires disposition
- **Description**: Docs still say any non-empty todos_left requires disposition. Scenario: Operator docs will disagree with the new blocking-only gate and prompt-only mitigation
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: docs/workflow-lifecycle.md:162
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_2: Operator doc still says any non-empty manifest todos_left requires disposition
- **Description**: Operator doc still says any non-empty manifest todos_left requires disposition. Scenario: After TODOS_LEFT_COUNT becomes blocking-only per scope_disposition.py write_coverage and dispatch_step2.py KV emit, this section overstates the gate and conflicts with the updated step2-dispatch.md prose in the plan
- **Reviewer**: Cursor-dyn-Scope Gate Reviewer
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md:162-171
- **Phase**: design

Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

