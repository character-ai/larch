### [Plan Review] FINDING_1

### FINDING_1: Step 3 fingerprint must precede probes and post-notification handling
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Concern**: Step 3 still routes repeated byte-identical or merely sentinel-present notifications into probe/post-notification handling before the fingerprint-based silent-yield rule, so the orchestrator can keep probing while hooks still block progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Condition silent yield on repeated byte-identical non-empty notifications when `.bg-wait-active` is still present or `.step3-terminal-persisted-this-run` is absent, even if `step-3-terminal` exists; run post-notification only after hook release (marker gone or both hook completion files present).
  - From Cursor-Innovation: Extend the plan's `skills/design/SKILL.md` edits to amend the Step 3 `NEXT_ACTION` preamble: before any probe, apply the byte-identical fingerprint silent-yield rule from `design-background-wait.md`; probe only on the first non-empty notification with new content.
  - From Cursor-Pragmatic: Qualify the premature branch: apply `skills/shared/design-background-wait.md` fingerprint silent-yield before any probe; probe only on the first non-empty notification per wait sequence when output is not byte-identical to the prior fingerprint.
  - From Cursor-Requirements: Add a firm ### UPDATED: skills/design/SKILL.md item (or equivalent bullet in the existing Step 3 section) ordering notification handling: empty output -> silent yield; first/new non-empty with absent sentinel -> at most one foreground probe; byte-identical repeat with absent sentinel -> silent yield per design-background-wait.md; sentinel present -> post-notification sequence.
  - From Cursor-dyn-Orchestrator Wait Contract: In the Step 3 post-loop routing paragraph add: on byte-identical non-empty repeat with absent step-3-terminal end the turn silently with no probe; probe only on the first or changed non-empty premature notification per design-background-wait.md
  - From Cursor-dyn-Orchestrator Wait Contract: Reorder or prefix Step 3 boundary: evaluate empty then byte-identical fingerprint before any probe; mirror line 29 no-tool list and add bg-wait-active may remain until wrapper EXIT trap per issue


### [Plan Review] FINDING_2

### FINDING_2: Anti-pattern carve-outs must suppress repeated identical probes and ScheduleWakeup
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Concern**: Anti-pattern #4/#5 still leave a path to probe or ScheduleWakeup on repeated byte-identical non-empty notifications, so the recovery loop can continue despite the new silent-yield rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the anti-pattern #5 extension, explicitly forbid `ScheduleWakeup` on repeated byte-identical non-empty notifications (not only empty-output #5240) and state that silent end-turn is the only recovery action until hook release.
  - From Cursor-Pragmatic: When extending #5, qualify the probe allowance to first non-empty per wait sequence only, and state that repeated byte-identical non-empty notifications end the turn silently with no probe (per `design-background-wait.md` #5418).
  - From Cursor-Requirements: In the plan's skills/design/SKILL.md edit, add one exception sentence to anti-pattern #4 (after the pinned probe-per-recovery-turn phrase) that repeated byte-identical non-empty notifications are not recovery turns and must follow the #5418 silent-yield rule in design-background-wait.md and the extended anti-pattern #5.
  - From Cursor-dyn-Orchestrator Wait Contract: Add one clause to #4 How to apply: byte-identical non-empty repeats with absent terminal sentinel end silently with no probe per design-background-wait.md Step 3 boundary
  - From Cursor-dyn-Orchestrator Wait Contract: When extending #5 revise that sentence to new non-empty notifications excluding byte-identical repeats; point to design-background-wait.md fingerprint rule


### [Plan Review] FINDING_3

### FINDING_3: Silent yields must not trip the no-progress guard
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Concern**: Silent-yield turns still count toward the live-marker no-progress breaker, so repeated waits can exhaust the guard and dead-end the review before the marker clears.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a carve-out or counter reset for repeated-identical Step 3 waits, or change the recovery so those repeats do not end a turn that the no-progress guard counts.


### [Plan Review] FINDING_4

### FINDING_4: Root /design guidance still probes repeats
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Tier-1 `/design` guidance still tells callers to probe on any premature non-empty notification, so repeated identical notifications can keep burning turns at the root orchestration surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### MAY_UPDATE: AGENTS.md with a short carve-out: after one foreground probe on a new non-empty premature /design notification, end turns silently on byte-identical repeats while .completed/step-3-terminal (or the fence sentinel) is absent; point to skills/shared/design-background-wait.md for the fingerprint rule.
  - From Codex-Requirements: Add AGENTS.md and skills/shared/orchestrator-never.md to the UPDATED list, and narrow their non-empty-notification recovery text to defer repeated byte-identical Step 3 notifications to skills/shared/design-background-wait.md instead of probing.


### [Plan Review] FINDING_5

### FINDING_5: The new repeat-notification contract is not pinned in test surfaces
- **Reviewer(s)**: Codex-dyn-Orchestrator Wait Contract
- **Severity**: important
- **Concern**: The proposed docs-only change leaves the repeat-notification silent-yield contract unpinned in the Bash test surfaces, so regressions can slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Orchestrator Wait Contract: Add scripts/test-design-structure.sh and scripts/test-implement-anti-polling-rule.sh to the file list, and pin the repeated-notification sentence plus the sentinel-present branch there.


