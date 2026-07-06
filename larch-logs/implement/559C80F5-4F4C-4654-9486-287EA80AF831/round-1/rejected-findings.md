### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Step 3 recovery still needs the terminal-sentinel probe
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The Step 3 recovery prose lets a non-empty task-output read fall through without the required terminal-sentinel confirmation, so a first absent probe can be followed by a prefix-identical notification that never re-probes and leaves the wait stuck in silent-yield.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a branch: non-empty bytes with sentinel not yet confirmed this wait always get one foreground sentinel probe, even when bytes are unchanged; or skip prefix-identical silent-yield after a prior absent probe.
  - From codex-specialist-correctness: Limit the no-sentinel-check wording to the empty or whitespace-only silent-yield case.
  - From codex-specialist-edge-cases: Scope the no-sentinel-check instruction to missing or whitespace-only task-output bytes.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Classification Reads need a per-wait clamp
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bg-wait
- **Severity**: minor
- **Concern**: The one classification Read per notification/wait is only documented, not enforced, so the same `tasks/*.output` path can be reread on every notification turn and act as a substitute for the banned probes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Keep doc contract or add a per-wait classification-read latch in the hook for the active task-output file.
  - From dyn-dyn-bg-wait: Add a per-wait classification-read clamp (mirroring `terminal_sentinel_probe_clamp`) keyed on marker dir + task-output path, or persist a one-shot sentinel in the tmpdir after the first post-notification classification `Read`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Pre-notification wording can be read too broadly
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bg-wait
- **Severity**: minor
- **Concern**: The exception for classification Read can be misread as allowing a Read before the first notification, which conflicts with the launch-to-notification ban and the steps that only permit that Read after a `<task-notification>`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Scope the exception to on each task-notification only; keep the pre-notification ban unconditional.
  - From dyn-dyn-bg-wait: Reword line 15 so the classification `Read` is explicitly scoped to “on each `<task-notification>`” (steps 0–3), and state that before the first notification the only allowed action is END THE TURN with zero reads.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: tmpdir-relative task-output reads need explicit deny coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `D/tasks/foo.output`-style reads under the live tmpdir are not explicitly exercised, so a mis-resolved classification path could still slip into the deny loop deadlock.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add assert_deny for Read $D/tasks/foo.output under live marker; document Claude tasks/<id>.output as the only classification target.
  - From cursor-specialist-testing: Add assert_deny for Read tasks/foo.output with cwd D while marker lives in D.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Implement-marker allow tests are missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no harness assertion that `Read tasks/foo.output` is allowed under the implement live markers, so a future hook change could re-tighten the behavior without the design tests noticing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add assert_allow Read tasks/foo.output cases with repo-root cwd under implement markers, mirroring design tests at lines 183-184.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Anti-polling rule prose is not pinned in CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The test suite does not pin the sentence that distinguishes a single classification Read from polling and after-completion parsing, so doc drift could blur those semantics without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add contains/check pins in test-implement-anti-polling-rule.sh for the line-65 sentence.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Bash-probe deny coverage is incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The plan-required Bash-probe denials for `tasks/*.output` are not fully covered, because `wc -c` and `stat` still lack standalone deny assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add standalone same-clone deny assertions for wc -c tasks/foo.output and stat tasks/foo.output.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Hook Read carve-out is broader than the documented timing
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: major
- **Concern**: Removing the `path_is_task_output && bash_probe_target_dir_plausible` arm ungates every `Read` whose resolved path is outside the live marker tmpdir for the whole marker lifetime, with no check that the path is `tasks/*.output` and no check that a `<task-notification>` has fired, so pre-notification reads in the launch-to-notification window are now hook-allowed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Restore a narrow `path_is_task_output` matcher on the `Read` deny loop without `bash_probe_target_dir_plausible`, or add an explicit `tasks/*.output` allow arm only; align `hook-bg-poll-guard.md` with whatever timing the hook actually enforces.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Non-empty output bytes need a stability guard before probing
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: major
- **Concern**: The classifier treats any non-empty `tasks/*.output` bytes as enough to trigger a terminal-sentinel probe, but incremental stdout writes can make a premature notification look complete before `.completed/step-3-terminal` exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Document that only post-`normalize-status` non-empty bytes count (e.g. require terminal sentinel before parsing KV output), or add an orchestrator-side “output stable across two notifications” check before leaving silent-yield.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

