### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/breadcrumb-monitor.sh:31-44 and scripts/lib-quiet.sh:247-278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Path validation for paired-PID paths is duplicated between larch_bm_validate_path and larch_quiet_write_paired_pid_file including the LARCH_LOG_ROOT subshell hack. A future fix to session-tmpdir containment or symlink rules applied in only one copy could let the writer accept paths the monitor rejects or vice versa leaving orphans or spurious WARNs. Extract one shared larch_log_validate_session_breadcrumb_path helper in lib-larch-log.sh and call it from both sites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: scripts/test-lint-foreground-markers.sh:2481-2511
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Nested-only positive fixtures still include paired-PID tokens. Maintainers copying case 13/13b as templates may reintroduce paired-PID requirements on nested scripts despite case 33. Remove paired-PID allocation from nested-only positive fixtures; rely on case 33 for carve-out behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: security: scripts/breadcrumb-monitor.sh:182-233
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Paired-PID signaling does not re-validate the PID file as a non-symlink regular file before dd/kill. Same-UID code in the session breadcrumbs directory can replace the PID file with a symlink after the writer's atomic mv; at timeout the monitor follows the link and may kill a PID read from attacker-controlled content. Re-check -L / regular-file status (or O_NOFOLLOW read) immediately before dd; re-run larch_bm_validate_path or equivalent containment checks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: security: scripts/breadcrumb-monitor.sh:223-231
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Monitor signals file-supplied PID without proving process identity; PID reuse is accepted. After ~30 minutes a departed PID may be reused; monitor can SIGTERM/SIGKILL an unrelated same-UID process. Keep documented limitation or add optional parent/comm verification on supported platforms.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: scripts/lib-quiet.sh:222-269
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Writer fail-open skips PID registration on invalid path or write failure. Monitor timeout does not kill the background job; long-running orphan behavior returns when pairing is misconfigured. Emit structured breadcrumb on writer failure; keep return 0 for set -e.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: security: scripts/breadcrumb-monitor.sh:107-115
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] LARCH_BM_TEST_TIMEOUT_SECONDS is active outside test harnesses. Env injection shortens timeout and triggers premature SIGTERM/SIGKILL of paired jobs. Gate on a test-only env flag or document operator-trusted session env.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: scripts/ship-pr.sh:2836; scripts/run-step5-review.sh:14; scripts/dispatch-plan-voters.sh:12; scripts/collect-agent-results.sh:186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] PID write runs before session tmpdir is established from argv/export while validation requires *_TMPDIR in the child environment. Background launch exports LARCH_PAIRED_PID_FILE but child lacks exported IMPLEMENT_TMPDIR/DESIGN_TMPDIR; write fails open, monitor timeout warns paired-pid-file-missing, ship-pr/review/voter/collector keeps running orphaned. Move larch_quiet_write_paired_pid_file to after argv parsing and export of the resolved session tmpdir, matching run-step2-dispatch.sh ordering.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: architecture: scripts/lib-quiet.sh:247-268; scripts/breadcrumb-monitor.sh:182-201
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dual fail-open writer and reader paths can leave pairing fully configured but cleanup inert. Writer validation fails silently; 30 minutes later monitor exits 4 with paired-pid-file-missing and background job still running; warnings buried in quiet log. Emit structured breadcrumb or louder stderr when LARCH_PAIRED_PID_FILE is set but file never appears after write attempt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/lint-foreground-markers.sh:36-54
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] family_b_pid_writer_required hardcodes five basenames separately from DENYLIST and script callsites. Adding a new top-level Family B background entrypoint could update fences and the shell writer but omit the linter case function so CI would not require LARCH_PAIRED_PID_FILE tokens. Centralize the top-level writer basename list in one heredoc or sourced fragment shared by lint and docs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: scripts/test-breadcrumb-monitor.sh:1887-1916
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Timeout tests use 1s override instead of the plan’s 2s example. No functional gap on typical CI; minor spec drift from the written plan. Use `LARCH_BM_TEST_TIMEOUT_SECONDS=2` or note the 1s choice in the harness contract doc.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: correctness: scripts/breadcrumb-monitor.sh:182-186
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Timeout signaling is skipped when the paired PID file is missing or empty at timeout (documented race). Background job still runs orphaned after monitor exit 4 if the writer never populated the file before the 1800s timeout. Keep fail-open behavior or add a distinct WARN for empty/not-yet-written files for operability.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_8: risk-integration: scripts/test-breadcrumb-monitor.sh:1997-2028
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Test 27 does not verify the stale child PID was signaled. Monitor could stop signaling paired PIDs entirely while test 27 still passes because only the parent survival check runs. After monitor exit 4, assert child PID is gone via assert_pid_gone while retaining the parent-alive assertion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: scripts/test-breadcrumb-monitor.sh scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No end-to-end writer-to-monitor paired-PID test. Format or timing bugs specific to larch_quiet_write_paired_pid_file output would not be caught by tests that manually printf into the pid file. Add one integration harness case using the real writer helper plus monitor timeout signaling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

