### FINDING_1: Step 3 recovery waiter still denied by hook-bg-poll-guard
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-sentinel-correctness, Codex-dyn-sentinel-correctness
- **Severity**: blocking
- **Concern**: Fix A documents a bare orchestrator `until [ -f "$DESIGN_TMPDIR/.completed/step-3" ]; do sleep N; done` recovery waiter, but the planned hook allowlist lives in `bash_segment_is_wrapper_routed`, which only exempts strict wrapper-only Bash via `bash_is_strict_wrapper_only`. The sanctioned waiter is not wrapper-routed. While `.bg-wait-active` is live, the hook still classifies it as `bash_is_filetest_sleep_loop` plus `bash_has_probe_target` and denies it. `bash_first_sync_segment` can also truncate the loop at the first semicolon, so a wrapper-segment pattern containing `; do sleep` may never match the full command. Fix A therefore cannot run when the hook fires; the orchestrator may fall back to stale `.step3-review-result.env` instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated bash_is_step3_recovery_waiter (or equivalent) checked in the Bash deny path before bash_is_filetest_sleep_loop; keep bash_segment_is_wrapper_routed for wrapper-only commands only
  - From Cursor-Innovation: Add a dedicated bash_is_step3_terminal_waiter (or equivalent) that matches only the until/.completed/step-3/sleep pattern with no probe verbs, and call it before the deny loop (for example immediately after line 297). Do not put this in bash_segment_is_wrapper_routed.
  - From Cursor-Pragmatic: Add a dedicated bash_is_step3_terminal_waiter (or equivalent) that matches only the `.completed/step-3` until/sleep pattern and exit 0 before the filetest-sleep denial loop (~line 309). Do not rely on bash_segment_is_wrapper_routed; bash_is_strict_wrapper_only only exempts wrapper-only commands.
  - From Codex-Pragmatic: Add a full-command exact waiter predicate before the denial checks, and reject any trailing command or probe
  - From Cursor-Requirements: Add a dedicated bash_is_sanctioned_step3_completion_waiter (or equivalent) checked before the deny loop (same tier as bash_is_strict_wrapper_only), matching only the narrow .completed/step-3 until sleep pattern; keep denying .step3-review-result.env loops
  - From Codex-Requirements: Add an exact full-command Step 3 recovery-waiter predicate before the filetest/probe denials, or change the parser so complete shell loops are matched atomically; keep the positive and appended-probe hook tests.
  - From Cursor-dyn-sentinel-correctness: Add a dedicated matcher (for example `bash_is_step3_recovery_waiter`) checked in the live-marker deny loop **before** `bash_is_filetest_sleep_loop`, requiring only `$DESIGN_TMPDIR/.completed/step-3` + `sleep` with no probe verbs; keep denying `.step3-review-result.env` loops and compound `&&` probe tails.
  - From Codex-dyn-sentinel-correctness: Use a dedicated exact full-command allow predicate immediately before the filetest-sleep-loop denial only; allow only the completed/step-3 waiter and keep appended or in-loop probes denied


### FINDING_2: Fix B on-disk edit does not ship via embedded legacy assets
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-sentinel-correctness
- **Severity**: blocking
- **Concern**: The plan edits `skills/design/scripts/review-design-step3-loop.sh` for Fix B (`rm -f "$DESIGN_TMPDIR/.step3-review-result.env"` before round 2), but `plan-review run --mode loop` materializes that script from the gzip-embedded `_LEGACY_ASSETS` blob in `python/plan_review.py` because `review-design-step3-loop.sh` is in `_RETIRE_DESIGN_SKIPS`. The on-disk `.sh` change never reaches the live CLI path, so stale `.step3-review-result.env` can still wake a recovery waiter during auto-continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update the embedded _LEGACY_ASSETS entry for review-design-step3-loop.sh or unretire the script so the live CLI uses the edited file
  - From Cursor-Requirements: Add ### UPDATED: python/plan_review.py: regenerate the embedded review-design-step3-loop.sh asset from the edited source per plan_review.py header and docs/python-migration.md C3a1; include a test or lint step that fails when blob and source diverge
  - From Cursor-dyn-sentinel-correctness: After editing `review-design-step3-loop.sh`, regenerate the `_LEGACY_ASSETS` entry in `python/plan_review.py` (same workflow as other retired Step 3 scripts). Add or extend a harness that fails when the blob drifts from the on-disk source.


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step6-cleanup.sh:121-122
- **Concern**: [SCOPE-REDUCTION] Plan reintroduces Fix C kill-before-cleanup despite approved non-goal. Scenario: Approved outline scoped verify-only for finalize.py and excluded new kill logic; Fix A plus Fix B address the stale-sentinel root cause; step6 kill is orthogonal defense that broadens blast radius (|| true swallow)
- **Proposed resolution**: Drop design-step6-cleanup.sh and design-step6-cleanup.md kill changes; rely on .completed/step-3 waiter plus per-round env clear


### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step6-cleanup.sh:121-122
- **Concern**: [SCOPE-REDUCTION] Fix C adds cleanup-time process killing outside the approved minimum. Scenario: Fix A and Fix B remove the premature Step 6 path; adding a SIGTERM sweep changes cleanup behavior and can terminate same-tmpdir helper processes even though the approved outline listed new kill logic as a non-goal
- **Proposed resolution**: Remove the design-step6-cleanup.sh and design-step6-cleanup.md Fix C changes; keep cleanup_tmpdir behavior unchanged


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step6-cleanup.sh:121-122
- **Concern**: [SCOPE-REDUCTION] Plan implements Fix C (kill-background-processes before cleanup-tmpdir) despite approved outline non-goals and verify-only Fix C. Scenario: Approved direction limits surfaces to SKILL.md and review-design-step3-loop; non-goals forbid kill logic beyond finalize.py; issue DoD allows cleanup kill OR fixing the waiter sentinel, so A+B already satisfy DoD without Step 6 mutation
- **Proposed resolution**: Drop design-step6-cleanup.sh and design-step6-cleanup.md kill changes; replace with a verify-only note that session_env.cleanup_tmpdir_main does not kill (design-step3-review.sh trap kills on normal loop exit) per approved outline


### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:9-11; plan.txt:39-49; skills/design/scripts/design-step6-cleanup.sh:122
- **Concern**: [SCOPE-REDUCTION] Fix C adds kill logic that the approved scope made a non-goal. Scenario: The approved direction asks to verify existing `finalize.py` cleanup behavior and says not to add kill logic beyond it; Fix A plus Fix B already prevents stale-sentinel cleanup, so adding a best-effort SIGTERM call in Step 6 expands the feature and can terminate unrelated tmpdir-matching work.
- **Proposed resolution**: Drop the `design-step6-cleanup.sh` and `design-step6-cleanup.md` Fix C changes; keep any Fix C mention as validation-only if needed.


### FINDING_9:
- **Reviewer(s)**: Codex-dyn-sentinel-correctness
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step6-cleanup.sh:121-122; python/session_env.py:1077-1108; python/finalize.py:641-644
- **Concern**: [SCOPE-REDUCTION] Fix C adds Step 6 kill-before-cleanup beyond the minimum sentinel fix. Scenario: The issue is fixed when the recovery waiter uses .completed/step-3 and auto-continuation clears the stale per-round env; adding a process-kill call broadens cleanup behavior on every successful Step 6 path
- **Proposed resolution**: Remove design-step6-cleanup.sh and design-step6-cleanup.md from the plan; keep only the verification note that finalize cleanup already kills before rmtree while session cleanup-tmpdir remains a plain cleanup helper




### FINDING_1: Post-notification routing lacks `.completed/step-3` terminal gate
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After a spurious `<task-notification>`, the orchestrator may treat Step 3 as finished by reading `.step3-review-result.env` with `LOOP_STATUS=complete` from an intermediate round (e.g. round 1) while `run_design_step3_loop` is still in apply, continuation, or round 2. `.step3-review-result.env` is written after each round body, not only at loop exit; `.completed/step-3` is written only by `step3_loop_write_completed_step3()` at terminal envelope emission. SKILL.md Anti-pattern #4 and the Step 3 task-notification blocks permit a sanctioned `until` waiter but do not require `.completed/step-3` as the completion sentinel, and the post-loop branch matrix routes on `STEP3_REVIEW_LOOP_STATUS=complete` without gating on that sentinel. That can advance the orchestrator through Steps 3b–6 while the background loop is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add to both Task notification boundary blocks and the post-loop matrix: before routing on `STEP3_REVIEW_LOOP_STATUS=complete` or synthesized `LOOP_STATUS=complete`, require `[ -f "$DESIGN_TMPDIR/.completed/step-3" ]`; if absent while the background Step 3 fence may still be running, use the sanctioned recovery waiter on `.completed/step-3` (never read terminal status from `.step3-review-result.env` alone)



