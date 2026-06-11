# Review Round 2

- Mode: `diff`
- 10 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_10: Implement structure tests do not pin all long-running implement fences
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: The implement structural harness does not enumerate and pin immediate-background markers and timeout tiers for key long-running fences such as `run-step5-review.sh`, `step-7a.sh`, and `step-8-ship.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-risk-completeness-output.txt: Address the concern above.


### FINDING_11: Design structure tests do not pin background contracts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: Design structure tests pin wrapper routing but not immediate-background markers, timeouts, or task-notification waits for design review, publish, and final-summary fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-risk-completeness-output.txt: Address the concern above.


### FINDING_13: Stall recovery still documents foreground long-runner dispatch
- **Reviewer(s)**: dyn-arch-consistency-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` still mandates foreground `run-step5-review.sh` and ship-driver launches, diverging from the new immediate-background contract for the happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-arch-consistency-output.txt: Address the concern above.


### FINDING_14: Design plan-review reference bypasses the Step 3 wrapper
- **Reviewer(s)**: dyn-arch-consistency-output.txt
- **Severity**: important
- **Concern**: Mandatory Step 3 reference prose still documents direct `run-step3-review.sh --mode loop --starting-round N`, bypassing the centralized `design-step3-review.sh` wrapper and its background contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-arch-consistency-output.txt: Address the concern above.


### FINDING_15: Legacy Step 3 continuation lacks a full background fence
- **Reviewer(s)**: dyn-arch-consistency-output.txt
- **Severity**: important
- **Concern**: The legacy `--mode single` heuristic continuation path references the wrapper only in prose and does not restate or clearly reuse the immediate-background, timeout, and task-notification contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-arch-consistency-output.txt: Address the concern above.


### FINDING_18: Design Step 5c can race ahead before background publish finishes
- **Reviewer(s)**: dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: `design-step5c.sh` is backgrounded, but the surrounding prose parses publish outputs and continues to Step 6 without a fence-local task-notification wait.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-completeness-output.txt: Address the concern above.


### FINDING_2: Step 8+ ship prose can still route long ship work foreground
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: Step 8+ still contains foreground Python ship-pr wording on launch and OOS re-entry paths, despite the immediate-background `step-8-ship.sh` fence. An orchestrator may follow the stale prose and reintroduce turn-blocking during ship or CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-risk-completeness-output.txt: Address the concern above.


### FINDING_3: Final-summary backgrounding is inconsistent and lacks wait guidance
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-risk-completeness-output.txt
- **Severity**: important
- **Concern**: `design-step-final-summary.sh` was moved to immediate-background even though the scope and runtime evidence are unclear, while script comments and cancel/terminal paths still imply foreground behavior. Without a task-notification wait, the orchestrator can emit a partial or empty summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-risk-completeness-output.txt: Address the concern above.


### FINDING_7: NEVER #13 recovery still re-invokes ship-pr directly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The default-path recovery instruction can run `python/cli.py ship pr` directly instead of the backgrounded `step-8-ship.sh` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Design Step 3 resume can pass an empty starting round
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 3 resume fence references `$N`, but that variable may be undefined. The wrapper can then treat `--starting-round ""` as absent and restart from the default round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


