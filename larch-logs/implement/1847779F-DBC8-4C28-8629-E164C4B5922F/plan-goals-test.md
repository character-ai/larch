## Goal
Implement issue #6493: [IMPLEMENTING] [BUG] Spurious design-step3-review notifications burn tokens despite #6478: task-output clamp fires but multiple notifications process within one turn before circuit breaker accumulates.

## Implementation Plan
  Root cause: When the orchestrator's classification Read of tasks/*.output is denied by hook-bg-poll-guard.sh (whitespace/empty content), the SKILL.md silent-yield contract requires ending the turn with zero further tools. Instead, the orchestrator continues reacting to the next
  notification within the same turn, making another denied Read — all in one model response. The no-progress circuit breaker (hook-no-progress-guard.sh, threshold 3) counts per MODEL TURN, not per notification event. A response that processes 15 notifications × denied Reads counts as
  one turn. Three such turns are needed before the circuit breaker fires.

  Why the #6478 fix (v52.5.1) is insufficient:

  1. task_output_read_clamp (hook-bg-poll-guard.sh:623-645) correctly denies Reads after 2 identical attempts, but a PreToolUse denial cannot force-end the in-flight model response. The model sees "denied" and reacts to the next queued notification in the same turn.
  2. hook-no-progress-guard.sh Stop-event logic fires after 3 completed turns and emits a block. It then relies on the UserPromptSubmit hook to block further turns. Task-notification invocations are not UserPromptSubmit events — they bypass that gate. The block fires once, but
  subsequent heartbeat notifications still invoke the model.
  3. Multiple notifications arrive within a single turn: the harness fires periodic notifications even when the task produces no new output. Each notification wakes the model; the model burns a full react cycle before the turn ends.

  The gap: the circuit breaker stops user-prompt-driven idle spinning. Task-notification-driven spinning is a different invocation path that bypasses both the UserPromptSubmit block and the multi-turn accumulation assumption.

  Reproducer: Run /design -s <issue> on a HARD-rated plan. design-step3-review.sh launches plan-review run with stdout redirected to a temp file, but the harness fires heartbeat-style notifications on the wrapper process. The task output file gets one whitespace line early;
  subsequent notifications arrive while reviewers run quietly. Each notification wakes the orchestrator; reads get denied after 2 tries; the turn ends; next notification arrives; repeat 3× before the circuit breaker fires.

  What is still needed (one or more):
  - The classification Read denial in hook-bg-poll-guard.sh should emit a Stop-level block (not just a denied-tool result), OR
  - hook-no-progress-guard.sh should arm on the first clamped-read turn (threshold 1 for design background waits), OR
  - design-background-wait.md wording should be strengthened: after the first denied classification Read, end the turn with literally zero output — no further reactions to any notifications that arrived in the same message batch.

  Observed in session C491DC8D: 15+ consecutive <task-notification> events each resulting in a denied Read, ~3 full response turns before the circuit breaker fired.

## Test plan
(no test plan section in plan-file)
