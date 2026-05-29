### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:223-311; scripts/ci-wait.sh:66-68; scripts/dispatch-with-waterfall.sh:8-10; skills/design/scripts/dispatch-plan-assessors.sh:9-11,61; skills/implement/scripts/step2-implement.sh:75-77; skills/review-and-fix/scripts/review-and-fix.sh:13-15
- **Concern**: The plan removes lib-quiet sentinel and paired-PID functions while leaving callers outside the listed update set. Scenario: After lib-quiet lands without those functions, these scripts hit command-not-found or exit under set -e before their normal work
- **Proposed resolution**: Keep no-op compatibility shims for larch_quiet_append_done_trap and larch_quiet_write_paired_pid_file until Stage 4, or add explicit removals for every remaining caller in this PR

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:211-221; SECURITY.md:269-284
- **Concern**: The plan changes breadcrumb monitor PID signaling and live stream redaction but does not update SECURITY.md. Scenario: After the PR, SECURITY.md would still promise monitor PID validation/kill behavior and monitor-side per-line redaction that the no-op shim no longer provides
- **Proposed resolution**: Add SECURITY.md to the plan and replace those sections with the Stage 3 behavior: no live monitor signaling/redaction, larch_err direct redaction remains, and durable breadcrumb publication still redacts via larch-log/design-log paths

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:223-264; skills/design/scripts/dispatch-plan-assessors.sh:11,61; scripts/ci-wait.sh:68; scripts/dispatch-with-waterfall.sh:10; skills/review-and-fix/scripts/review-and-fix.sh:15; skills/implement/scripts/step2-implement.sh:77
- **Concern**: Plan removes lib-quiet sentinel and paired-PID helpers but misses live callers. Scenario: After lib-quiet.sh drops larch_quiet_append_done_trap and larch_quiet_write_paired_pid_file, the listed scripts can exit with command not found before doing useful work
- **Proposed resolution**: Add those callers to the same change or keep compatibility helpers in lib-quiet.sh until Stage 4; at minimum remove the dispatch-plan-assessors paired-PID call and handle every remaining append_done_trap call

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/relevant-checks.sh:52-58; scripts/test-relevant-checks.sh:338-339
- **Concern**: Plan removes lint-foreground relevant-checks routing but omits the matching harness expectation. Scenario: The updated relevant-checks output will no longer include test-lint-foreground-markers, so make lint can fail in test-relevant-checks
- **Proposed resolution**: Update scripts/test-relevant-checks.sh expected direct targets with the relevant-checks change, or keep the routing until the harness is updated

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:199-245; scripts/run-step5-review.sh:7-13; skills/implement/scripts/run-step2-dispatch.sh:80-87; scripts/ship-pr.sh:3305-3307
- **Concern**: The plan deletes larch_quiet_append_done_trap and its helpers while many live scripts still call it. Scenario: run-step5-review.sh, run-step2-dispatch.sh, ship-pr.sh, ci-wait.sh, collect-agent-results.sh, dispatch-plan-voters.sh, dispatch-with-waterfall.sh, step2-implement.sh, review-and-fix.sh, and design dispatchers will hit command not found and exit under set -e before doing their work
- **Proposed resolution**: Keep larch_quiet_append_done_trap as a compatibility shim until Stage 4, preferably preserving the status-file write while fences still allocate LARCH_STATUS_FILE, or explicitly sweep every caller and update status-file consumer prose in the same PR

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:211-221; SECURITY.md:279-283
- **Concern**: The plan changes the paired-PID and live monitor redaction security contracts but omits SECURITY.md updates. Scenario: After breadcrumb-monitor.sh becomes a no-op and paired PID writing is removed, SECURITY.md will still claim the monitor can signal timed-out background processes and drops unredactable streamed lines, which is false security guidance
- **Proposed resolution**: Update the affected SECURITY.md paragraphs in this PR to describe the Stage 3 shim/no-op state and the surviving durable-log redaction path, or defer the behavior change until the security policy can be updated

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:223-235; scripts/ci-wait.sh:65-68; scripts/dispatch-with-waterfall.sh:6-10; skills/implement/scripts/step2-implement.sh:72-77; skills/review-and-fix/scripts/review-and-fix.sh:10-15; skills/design/scripts/dispatch-plan-assessors.sh:6-11
- **Concern**: Plan removes larch_quiet_append_done_trap but does not remove or shim all remaining call sites. Scenario: After the PR, these scripts source lib-quiet.sh and call a missing function; with set -e in most of them they exit before doing work, breaking CI wait, Step 2 implementation, review dispatch, review-and-fix, and plan assessor dispatch
- **Proposed resolution**: Keep a compatibility no-op larch_quiet_append_done_trap until Stage 4, or add explicit plan steps to remove/update every remaining call site and sibling docs/tests in the same PR

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:199-233; scripts/ci-wait.sh:65-68
- **Concern**: Plan removes larch_quiet_append_done_trap from lib-quiet but does not cover all callers. Scenario: After the proposed lib-quiet rewrite, still-live scripts such as ci-wait.sh, step2-implement.sh, review-and-fix.sh, dispatch-with-waterfall.sh, and dispatch-plan-assessors.sh can fail immediately with an undefined function before doing their work
- **Proposed resolution**: Keep larch_quiet_append_done_trap as a no-op compatibility shim for Stage 3, or add explicit plan steps to remove every call site and update their harnesses

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:211-221; SECURITY.md:269-303
- **Concern**: The plan changes security-relevant breadcrumb monitor and redaction behavior but omits SECURITY.md. Scenario: SECURITY.md would still describe paired-PID timeout signaling and monitor-side per-line redaction after breadcrumb-monitor.sh becomes a no-op and paired-PID plumbing is removed, violating the repo rule to update SECURITY.md for security-relevant behavior changes
- **Proposed resolution**: Add a minimal SECURITY.md update in this PR that reflects the Stage 3 no-op monitor, removed paired-PID signaling, and surviving committed-log redaction path

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:66-68, scripts/dispatch-with-waterfall.sh:8-10, skills/implement/scripts/step2-implement.sh:75-77, skills/review-and-fix/scripts/review-and-fix.sh:13-15, skills/design/scripts/dispatch-plan-assessors.sh:9-11
- **Concern**: The plan removes larch_quiet_append_done_trap from scripts/lib-quiet.sh but leaves live callers in files not listed for update or deletion.. Scenario: The Stage-4-deferred fences do not keep working via the breadcrumb-monitor shim because these scripts fail earlier with an undefined larch_quiet_append_done_trap after sourcing lib-quiet.sh.
- **Proposed resolution**: For the minimum-change contract, either keep larch_quiet_append_done_trap as a no-op compatibility shim until Stage 4 or add these exact files to the Stage 3 change set and remove the calls in the same PR.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-assessors.sh:47-61
- **Concern**: The plan removes larch_quiet_write_paired_pid_file and says to update all 6 callers, but it does not explicitly list skills/design/scripts/dispatch-plan-assessors.sh even though it calls the function at line 61.. Scenario: After lib-quiet.sh drops the function, plan assessment dispatch exits before launching assessors; this is also a caller described only by count rather than an explicit path.
- **Proposed resolution**: Add skills/design/scripts/dispatch-plan-assessors.sh to the UPDATED list and remove its paired-PID call, or keep larch_quiet_write_paired_pid_file as a no-op shim until every remaining caller is removed explicitly.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-assessors.sh:61,101-104
- **Concern**: Plan misses a live larch_quiet_write_paired_pid_file caller and paired-PID unset barrier. Scenario: After scripts/lib-quiet.sh removes larch_quiet_write_paired_pid_file, dispatch-plan-assessors.sh exits with an undefined-function error before launching assessors
- **Proposed resolution**: Add skills/design/scripts/dispatch-plan-assessors.sh to the Stage 3 update set; remove the writer call and dead unset barrier, and adjust test-dispatch-plan-assessors.sh expectations

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/breadcrumb-monitor.md:1-171
- **Concern**: Plan rewrites breadcrumb-monitor.sh to a no-op shim but leaves the sibling contract doc describing streaming, sentinels, paired-PID timeout signaling, and the deleted harness. Scenario: Post-PR repository state says the script blocks, streams, times out, signals PIDs, and is tested by scripts/test-breadcrumb-monitor.sh even though Stage 3 removes that behavior and deletes the harness
- **Proposed resolution**: Update scripts/breadcrumb-monitor.md in Stage 3 to document only the compatibility shim contract, or delete it with the removed monitor contract

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:211-221
- **Concern**: Security policy still documents paired breadcrumb monitor PID signaling, but the plan removes that behavior and does not schedule SECURITY.md. Scenario: Consumers reviewing security posture will believe monitor timeouts can still TERM/KILL the paired writer through LARCH_PAIRED_PID_FILE after the shim exits 0 and no longer enforces that path
- **Proposed resolution**: Update SECURITY.md in this PR to remove or replace the paired-PID timeout-signaling section

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ci-wait.md:11-13; skills/implement/references/rebase-rebump-subprocedure.md:189-192
- **Concern**: Plan removes parent LARCH_PAIRED_PID_FILE barriers but leaves docs saying ci-wait.sh is protected because ship-pr.sh unsets that env var. Scenario: The written contract points to a parent unset that no longer exists, so future readers may preserve or reintroduce dead paired-PID plumbing
- **Proposed resolution**: Add these references to the Stage 3 doc cleanup, or explicitly mark them as Stage-4-deferred skill-fence prose in the plan
