### OOS_1: [OUT_OF_SCOPE] Loop stderr trapped with no replay or execution-issues surfacing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Loop and reviewer stderr now land only in `plan-review-loop-stderr.log`, with no reader, replay, or execution-issues surfacing. Warnings like `dialectic-clear-stale` (`plan_review.py` ~1798) become invisible unless an operator opens the log manually. Documented in `design-step3-review.md` as an intentional tradeoff; orchestrator routing does not depend on loop stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: If those warnings matter operationally, replay selected lines through `normalize-status` or append a bounded excerpt to `execution-issues.md`.

### OOS_2: [OUT_OF_SCOPE] Test harness does not exercise deferred set -m job-control path
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-edge-cases, dyn-dyn-bash-jobcontrol
- **Severity**: nit
- **Concern**: New #5511 coverage asserts loop stderr isolation and statically bans the narrow #5240 pattern, but does not runtime-check that deferred `set -m` job-status lines (for example `[1] <pid>` / `[1]+ Done`) land in `bash-job-control.log` rather than the wrapper stream. The test can pass even if the original empty-notification bug still reproduces. Hard-to-simulate path; shell redirect mechanics for deferred notices are considered sound and the static guard reduces regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a harness that launches a stub background job under `set -m` and greps `bash-job-control.log` for job-control markers while asserting the wrapper stream stays clean.
  - From codex-specialist-edge-cases: Force the monitor-mode job-control path or assert bash-job-control.log contains the notices.
  - From dyn-dyn-bash-jobcontrol: Extend the harness with a fake monitor-mode run (or a stub that forces a visible job-control flush) and assert `bash-job-control.log` is populated while wrapper stdout/stderr stay clean.

### OOS_3: [OUT_OF_SCOPE] SKILL.md residual platform-notification uncertainty
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Anti-pattern #4 in `skills/design/SKILL.md` (~164) still documents that empty-output notifications may persist from residual platform-level behavior the script cannot intercept, while the issue expected behavior asked for "at most once." Pre-existing platform uncertainty; SKILL.md already documents the residual case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: After a live `/design` panel run, confirm notification count dropped materially; if platform SIGCHLD-style events remain, track a follow-up outside this stderr-redirect scope.

### OOS_4: [OUT_OF_SCOPE] Platform-level notification sources beyond bash redirects
- **Reviewer(s)**: dyn-dyn-bash-jobcontrol
- **Severity**: latent
- **Concern**: The widened redirect correctly covers bash stderr sources (deferred `set -m` notices, synchronous teardown, `set +m`). It cannot suppress notifications if Claude Code's `run_in_background` harness fires on process-tree exit/SIGCHLD rather than stream writes. The original report's "10+ notifications for 11 reviewer slots" is hard to explain from bash job control alone (the wrapper has one background job), which points at platform-level or descendant-process signaling as a remaining source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bash-jobcontrol: Treat empty-output yields as still required; if spurious volume persists after ship, investigate harness notification triggers or add an offline repro that correlates notification count with `bash-job-control.log` / `plan-review-loop-stderr.log` growth versus child exit events.

### OOS_5: [OUT_OF_SCOPE] Cleanup wait outside redirect group on abnormal EXIT
- **Reviewer(s)**: dyn-dyn-bash-jobcontrol
- **Severity**: latent
- **Concern**: On abnormal EXIT during the critical section, `_step3_review_cleanup` still runs `wait "$_loop_pid" 2>/dev/null` outside the #5511 redirect group. Any job-control text from that second wait can still reach the task stream. This predates #5511 and is limited to interrupt/error paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bash-jobcontrol: If abort-path spurious notifications matter, route cleanup's wait/teardown through the same `bash-job-control.log` redirect or duplicate stderr suppression inside `_step3_review_cleanup`.

