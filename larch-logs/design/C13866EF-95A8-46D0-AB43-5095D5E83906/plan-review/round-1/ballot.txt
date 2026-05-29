### FINDING_1: Missing lib-quiet helper shims or caller sweep
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep, Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: important
- **Concern**: The plan removes `larch_quiet_append_done_trap` and/or `larch_quiet_write_paired_pid_file` from `scripts/lib-quiet.sh` while leaving live callers, especially in CI wait, dispatch, review, Step 2, and design assessor scripts. Those scripts can fail with undefined-function errors under `set -e` before doing useful work. The design assessor path also retains paired-PID cleanup/test expectations that must be updated if the writer call is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch/Codex-Arch: Keep no-op compatibility shims for larch_quiet_append_done_trap and larch_quiet_write_paired_pid_file until Stage 4, or add explicit removals for every remaining caller in this PR
  - From Cursor-Edge/Codex-Edge: Add those callers to the same change or keep compatibility helpers in lib-quiet.sh until Stage 4; at minimum remove the dispatch-plan-assessors paired-PID call and handle every remaining append_done_trap call
  - From Cursor-Innovation/Codex-Innovation: Keep larch_quiet_append_done_trap as a compatibility shim until Stage 4, preferably preserving the status-file write while fences still allocate LARCH_STATUS_FILE, or explicitly sweep every caller and update status-file consumer prose in the same PR
  - From Cursor-Pragmatic/Codex-Pragmatic: Keep a compatibility no-op larch_quiet_append_done_trap until Stage 4, or add explicit plan steps to remove/update every remaining call site and sibling docs/tests in the same PR
  - From Cursor-Requirements/Codex-Requirements: Keep larch_quiet_append_done_trap as a no-op compatibility shim for Stage 3, or add explicit plan steps to remove every call site and update their harnesses
  - From Cursor-dyn-caller-sweep/Codex-dyn-caller-sweep: For the minimum-change contract, either keep larch_quiet_append_done_trap as a no-op compatibility shim until Stage 4 or add these exact files to the Stage 3 change set and remove the calls in the same PR.
  - From Cursor-dyn-caller-sweep/Codex-dyn-caller-sweep: Add skills/design/scripts/dispatch-plan-assessors.sh to the UPDATED list and remove its paired-PID call, or keep larch_quiet_write_paired_pid_file as a no-op shim until every remaining caller is removed explicitly.
  - From Cursor-dyn-env-var-scope/Codex-dyn-env-var-scope: Add skills/design/scripts/dispatch-plan-assessors.sh to the Stage 3 update set; remove the writer call and dead unset barrier, and adjust test-dispatch-plan-assessors.sh expectations

### FINDING_2: SECURITY.md not updated for monitor and redaction behavior changes
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: important
- **Concern**: The plan changes security-relevant breadcrumb monitor behavior, paired-PID timeout signaling, and live stream redaction, but does not update `SECURITY.md`. After the PR, the security policy would still describe timeout signaling and monitor-side redaction guarantees that no longer exist, while omitting the surviving direct/durable-log redaction paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch/Codex-Arch: Add SECURITY.md to the plan and replace those sections with the Stage 3 behavior: no live monitor signaling/redaction, larch_err direct redaction remains, and durable breadcrumb publication still redacts via larch-log/design-log paths
  - From Cursor-Innovation/Codex-Innovation: Update the affected SECURITY.md paragraphs in this PR to describe the Stage 3 shim/no-op state and the surviving durable-log redaction path, or defer the behavior change until the security policy can be updated
  - From Cursor-Requirements/Codex-Requirements: Add a minimal SECURITY.md update in this PR that reflects the Stage 3 no-op monitor, removed paired-PID signaling, and surviving committed-log redaction path
  - From Cursor-dyn-env-var-scope/Codex-dyn-env-var-scope: Update SECURITY.md in this PR to remove or replace the paired-PID timeout-signaling section

### FINDING_3: relevant-checks harness expectations not updated
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The plan removes `lint-foreground` routing from `scripts/relevant-checks.sh` but omits the matching `scripts/test-relevant-checks.sh` expectation update. The harness may still expect `test-lint-foreground-markers`, causing `make lint` to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge/Codex-Edge: Update scripts/test-relevant-checks.sh expected direct targets with the relevant-checks change, or keep the routing until the harness is updated

### FINDING_4: breadcrumb-monitor contract doc left stale
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Concern**: The plan rewrites `breadcrumb-monitor.sh` to a no-op shim but leaves `scripts/breadcrumb-monitor.md` describing streaming, sentinels, paired-PID timeout signaling, and the deleted harness. The repository would document behavior that Stage 3 removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-var-scope/Codex-dyn-env-var-scope: Update scripts/breadcrumb-monitor.md in Stage 3 to document only the compatibility shim contract, or delete it with the removed monitor contract

### FINDING_5: paired-PID env var cleanup docs left stale
- **Reviewer(s)**: Cursor-dyn-env-var-scope, Codex-dyn-env-var-scope
- **Severity**: latent
- **Concern**: The plan removes parent `LARCH_PAIRED_PID_FILE` barriers but leaves docs saying `ci-wait.sh` is protected because `ship-pr.sh` unsets that env var. Future readers may preserve or reintroduce dead paired-PID plumbing based on stale documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-var-scope/Codex-dyn-env-var-scope: Add these references to the Stage 3 doc cleanup, or explicitly mark them as Stage-4-deferred skill-fence prose in the plan
