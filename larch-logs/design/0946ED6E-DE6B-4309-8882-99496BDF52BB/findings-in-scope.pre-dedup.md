### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md:33-35
- **Concern**: Sentinel-present branch ignores the #5418 pre-emit window where hooks still block progress. Scenario: #5418 writes `.completed/step-3-terminal` before stdout emit but often without `.step3-terminal-persisted-this-run`; `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh` treat Step 3 as incomplete until both files exist and `.bg-wait-active` is removed. The plan keeps "sentinel present → run post-notification" and only silent-yields when the sentinel is absent, so repeated identical notifications with terminal present still drive blocked Read/post-notification attempts each turn instead of silent yield.
- **Proposed resolution**: Condition silent yield on repeated byte-identical non-empty notifications when `.bg-wait-active` is still present or `.step3-terminal-persisted-this-run` is absent, even if `step-3-terminal` exists; run post-notification only after hook release (marker gone or both hook completion files present).



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 routing preamble still authorizes probe on every premature delivery. Scenario: SKILL.md requires terminal and `.step3-review-result.env` and otherwise says "yield or probe without parsing." That re-authorizes one probe per redelivered notification and can override the fingerprint rule loaded only from the shared anchor.
- **Proposed resolution**: Extend the plan's `skills/design/SKILL.md` edits to amend the Step 3 `NEXT_ACTION` preamble: before any probe, apply the byte-identical fingerprint silent-yield rule from `design-background-wait.md`; probe only on the first non-empty notification with new content.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81
- **Concern**: Anti-pattern #5 extension alone may not stop ScheduleWakeup recovery loops. Scenario: The issue reports ~6 ScheduleWakeup recovery cycles compounded with re-notifications; anti-pattern #4 still routes premature recovery to `design-background-wait.md` without forbidding ScheduleWakeup on repeated identical non-empty Step 3 notifications.
- **Proposed resolution**: In the anti-pattern #5 extension, explicitly forbid `ScheduleWakeup` on repeated byte-identical non-empty notifications (not only empty-output #5240) and state that silent end-turn is the only recovery action until hook release.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 post-loop routing still authorizes probe on every premature notification. Scenario: The line says to yield or probe when `.completed/step-3-terminal` or `.step3-review-result.env` is missing. That sits after the wait and can override the fingerprint rule on repeated byte-identical notifications. The bug report shows hook-blocked probes and ScheduleWakeup churn on each re-delivery.
- **Proposed resolution**: Qualify the premature branch: apply `skills/shared/design-background-wait.md` fingerprint silent-yield before any probe; probe only on the first non-empty notification per wait sequence when output is not byte-identical to the prior fingerprint.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81
- **Concern**: Anti-pattern #5 probe-allowance sentence will contradict the planned repeat-notification rule. Scenario: The closing sentence limits the one-foreground-probe allowance to non-empty-output notifications only. After extending #5 for repeated byte-identical non-empty notifications, that sentence still tells the orchestrator to probe any non-empty notification, including duplicates.
- **Proposed resolution**: When extending #5, qualify the probe allowance to first non-empty per wait sequence only, and state that repeated byte-identical non-empty notifications end the turn silently with no probe (per `design-background-wait.md` #5418).



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/shared/design-background-wait.md:19-25
- **Concern**: Silent-yield turns still trip the live-marker no-progress breaker. Scenario: scripts/hook-no-progress-guard.sh:4-11 counts every turn end while `.bg-wait-active` is live. In the 10+ repeat-notification case from the bug report, the breaker fires after five silent yields and blocks the next prompt before the review exits, so the long-review path still dead-ends.
- **Proposed resolution**: Add a carve-out or counter reset for repeated-identical Step 3 waits, or change the recovery so those repeats do not end a turn that the no-progress guard counts.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 NEXT_ACTION routing still says yield or probe for every premature notification. Scenario: The post-loop table tells the orchestrator to yield or probe whenever step-3-terminal or .step3-review-result.env is missing. That overrides the planned repeated-identical silent-yield rule and can keep re-probing (or ScheduleWakeup recovery) on the same taskId during long Step 3 waits.
- **Proposed resolution**: Add a firm ### UPDATED: skills/design/SKILL.md item (or equivalent bullet in the existing Step 3 section) ordering notification handling: empty output -> silent yield; first/new non-empty with absent sentinel -> at most one foreground probe; byte-identical repeat with absent sentinel -> silent yield per design-background-wait.md; sentinel present -> post-notification sequence.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:80
- **Concern**: Anti-pattern #4 still mandates one foreground probe per recovery turn with no repeat carve-out. Scenario: Each re-delivered identical notification can be read as a new recovery turn, so NEVER #4 still authorizes another probe even after the shared anchor's #5418 rule. test-design-structure.sh pins the foreground-probe literal, so the conflict must be resolved in prose, not by deleting the pin.
- **Proposed resolution**: In the plan's skills/design/SKILL.md edit, add one exception sentence to anti-pattern #4 (after the pinned probe-per-recovery-turn phrase) that repeated byte-identical non-empty notifications are not recovery turns and must follow the #5418 silent-yield rule in design-background-wait.md and the extended anti-pattern #5.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: AGENTS.md:64
- **Concern**: Tier-1 AGENTS.md still orders a foreground probe for every premature /design non-empty notification. Scenario: AGENTS.md is always loaded and does not carve out repeated byte-identical notifications or reference the Step 3 fingerprint rule. Orchestrators can keep probing (and burning turns) despite the two-file doc clarification.
- **Proposed resolution**: Add ### MAY_UPDATE: AGENTS.md with a short carve-out: after one foreground probe on a new non-empty premature /design notification, end turns silently on byte-identical repeats while .completed/step-3-terminal (or the fence sentinel) is absent; point to skills/shared/design-background-wait.md for the fingerprint rule.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: AGENTS.md:64
- **Concern**: Plan leaves the root /design recovery contract unchanged, so the new repeated-byte-identical silent-yield rule never reaches the highest-priority guidance surface.. Scenario: AGENTS.md:64 and skills/shared/orchestrator-never.md:9-11 still tell `/design` to probe after any non-empty premature notification. A consumer following the loaded root docs will keep probing repeated notifications and can re-enter the loop this change is meant to suppress.
- **Proposed resolution**: Add AGENTS.md and skills/shared/orchestrator-never.md to the UPDATED list, and narrow their non-empty-notification recovery text to defer repeated byte-identical Step 3 notifications to skills/shared/design-background-wait.md instead of probing.



### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:413
- **Concern**: Step 3 NEXT_ACTION gate still says yield or probe on premature notifications without fingerprint carve-out. Scenario: Repeated byte-identical notifications with absent step-3-terminal still match premature and yield or probe; orchestrator may run a foreground probe each turn, hook denies while bg-wait-active is live, and ScheduleWakeup or prose loops continue
- **Proposed resolution**: In the Step 3 post-loop routing paragraph add: on byte-identical non-empty repeat with absent step-3-terminal end the turn silently with no probe; probe only on the first or changed non-empty premature notification per design-background-wait.md



### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:81
- **Concern**: Anti-pattern #5 still says one-foreground-probe allowance applies only to non-empty-output notifications. Scenario: Plan extends #5 for repeated byte-identical non-empty waits but leaves the existing sentence implying every non-empty notification may probe; agents can probe on identical repeats before reading the new carve-out
- **Proposed resolution**: When extending #5 revise that sentence to new non-empty notifications excluding byte-identical repeats; point to design-background-wait.md fingerprint rule



### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/design-background-wait.md:29-33
- **Concern**: Fingerprint silent-yield rule is ordered after the foreground-probe instruction and uses yield without probing not the empty-output no-tool list. Scenario: Agent reads line 29 first and may probe before evaluating byte-identical fingerprint; yield without probing omits explicit no Bash no wc no ScheduleWakeup no prose parity with line 29 empty-output branch
- **Proposed resolution**: Reorder or prefix Step 3 boundary: evaluate empty then byte-identical fingerprint before any probe; mirror line 29 no-tool list and add bg-wait-active may remain until wrapper EXIT trap per issue



### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:80
- **Concern**: Anti-pattern #4 still mandates one foreground probe per recovery turn for any premature notification. Scenario: No carve-out for byte-identical repeats; conflicts with planned silent-yield contract and reinforces probe-on-every-notification behavior during long Step 3 waits
- **Proposed resolution**: Add one clause to #4 How to apply: byte-identical non-empty repeats with absent terminal sentinel end silently with no probe per design-background-wait.md Step 3 boundary



### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-Orchestrator Wait Contract
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/shared/design-background-wait.md:33-35
- **Concern**: [SCOPE-REDUCTION] Plan says replace repeated-notification sentence but repo already has #5418 fingerprint and sentinel-present branch. Scenario: Implementer may rewrite or drop working text instead of minimal strengthen-only delta
- **Proposed resolution**: Retitle plan edit to strengthen/clarify existing lines 33-35; list only additive deltas explicit no-tool list bg-wait-active note ScheduleWakeup ban



### FINDING_16:
- **Reviewer(s)**: Codex-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:5-11,15-35,50-57
- **Concern**: The plan forbids Bash changes, but the new repeated-notification silent-yield contract is only enforceable by Bash harness pins.. Scenario: make test-design-structure and make test-implement-anti-polling-rule currently assert only the existing empty-output and foreground-probe literals at scripts/test-design-structure.sh:201-206,223-260 and scripts/test-implement-anti-polling-rule.sh:230-244,512-530, so a later edit can drop the new no-ScheduleWakeup/no-prose/sentinel-present behavior without failing CI.
- **Proposed resolution**: Add scripts/test-design-structure.sh and scripts/test-implement-anti-polling-rule.sh to the file list, and pin the repeated-notification sentence plus the sentinel-present branch there.



