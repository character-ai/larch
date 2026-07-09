### OOS_1: Docs still say any non-empty todos_left requires disposition
- **Description**: Docs still say any non-empty todos_left requires disposition. Scenario: Operator docs will disagree with the new blocking-only gate and prompt-only mitigation
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: docs/workflow-lifecycle.md:162
- **Phase**: design



### OOS_2: Operator doc still says any non-empty manifest todos_left requires disposition
- **Description**: Operator doc still says any non-empty manifest todos_left requires disposition. Scenario: After TODOS_LEFT_COUNT becomes blocking-only per scope_disposition.py write_coverage and dispatch_step2.py KV emit, this section overstates the gate and conflicts with the updated step2-dispatch.md prose in the plan
- **Reviewer**: Cursor-dyn-Scope Gate Reviewer
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md:162-171
- **Phase**: design



