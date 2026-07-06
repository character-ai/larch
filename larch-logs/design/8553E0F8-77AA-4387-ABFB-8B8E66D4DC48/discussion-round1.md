## Decision 1: Fix strategy for the Step 3 background-wait deadlock
- **Question**: Which of the four proposed fixes (A: hook `tasks/*.output` read exemption; B: docs; C: keepalive heartbeat; D: upstream report) should the plan implement?
- **Resolution**: Fix A + B + C (defense in depth). A = exempt write-once `tasks/*.output` reads from `scripts/hook-bg-poll-guard.sh` Read-denial logic so the orchestrator can read the empty output and apply the silent-yield rule. B = document the empty-output / terminal-sentinel contract in `AGENTS.md` and `skills/shared/design-background-wait.md`. C = add a stdout keepalive heartbeat in `skills/design/scripts/design-step3-review.sh` to reduce/prevent the premature `<task-notification>` during the long silent review window. Fix D (upstream Claude Code report) is external and captured as an OOS follow-up, NOT implemented as code here.
- **Source**: user

## Decision 2: Hard constraints to preserve
- **Question**: What must not break while applying A + B + C?
- **Resolution**: (1) The hook MUST keep denying genuine Bash polling probes (terminal-sentinel polling) during a live wait; only write-once `tasks/*.output` *reads* are exempted, not Bash probe commands. (2) The keepalive heartbeat MUST NOT corrupt the wrapper's machine KV stdout contract consumed by `normalize-status` / `.step3-review-result.env` (the orchestrator parses the completed task output). (3) Preserve the #5240 (`set -m` spurious-notification) and #6268 (`_step3_review_guarantee_post_loop_exit` marker removal) behaviors. (4) Bash 3.2 portability for both shell edits. (5) The clone-plausibility protection from #5925 must remain for the probe-denial path.
- **Source**: codebase (to be verified during drafting)
