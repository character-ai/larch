### OOS_1: [OUT_OF_SCOPE] PreToolUse guard covers Read|Bash only; other tools unhooked
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-hook-enforcement-output.txt
- **Severity**: latent
- **Concern**: PreToolUse guard is registered on `Read|Bash` only. `Glob`, `TaskOutput`, `Grep`, and `Monitor` remain uncovered prompt-side gaps; orchestrator could poll via those tools during background wait. Effectiveness also depends on Claude Code honoring `permissionDecision: deny` (`SECURITY.md` documents residual risk).
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] `/implement` immediate-background fences not instrumented with `.bg-wait-active`
- **Reviewer(s)**: dyn-hook-enforcement-output.txt
- **Severity**: latent
- **Concern**: `/implement` immediate-background fences (`run-step5-review.sh`, `run-step-checks.sh`, ship driver) are not instrumented with `.bg-wait-active` in this branch; the plan's Layer 4 scope is `/design` only. Residual polling cost on `/implement` is unchanged (documented as follow-up).
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_3: [OUT_OF_SCOPE] PreToolUse guard and `hook-anti-read-poll.sh` probe classifiers can disagree
- **Reviewer(s)**: dyn-hook-enforcement-output.txt
- **Severity**: latent
- **Concern**: `hook-anti-read-poll.sh` remains PostToolUse advisory only; the new PreToolUse hook does not subsume its richer Bash parsing. The two hooks can disagree on what counts as a probe (e.g. `awk` blocked nowhere at PreToolUse, warned only after the fact if ever classified).
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_4: [OUT_OF_SCOPE] `plan-review-loop.sh` all-combos-pruned branch fall-through is pre-existing
- **Reviewer(s)**: dyn-design-wait-contract-output.txt
- **Severity**: latent
- **Concern**: The all-combos-pruned branch calls `_snapshot_terminal_exit_preserving_status` but does not `return`, so execution falls through into dispatch/collection logic. This behavior predates this branch; the new reviewer-status write amplifies stale snapshot risk but the control-flow bug itself is pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:


