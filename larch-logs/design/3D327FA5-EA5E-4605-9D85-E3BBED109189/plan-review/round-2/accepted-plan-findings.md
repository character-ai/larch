### FINDING_1: Timing scanner misses non-literal timing helper paths
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-timing-telemetry
- **Severity**: important
- **Concern**: The planned A1 scanner may only match literal `scripts/timing-ledger.sh` / `scripts/timing-report.sh` paths, but several production implement scripts invoke the timing helpers via `$SCRIPT_DIR`. That would let unpinned implement timing calls escape the invariant and create false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the A1 awk, treat any line with `timing-ledger.sh` plus `mark` or `record-vendor-task` (exclude `dump`) or any `timing-report.sh` line as a timing line; require `LARCH_TIMING_SKILL=implement` on that same line; do not require the `scripts/` path prefix from the SKILL.md fence harness
  - From Cursor-dyn-timing-telemetry: Match invocation lines on `timing-ledger.sh` / `timing-report.sh` plus subcommand (`mark`, `record-vendor-task`, or `timing-report.sh` flags), not the `scripts/timing-ledger.sh` path prefix; keep the same-line `LARCH_TIMING_SKILL=implement` check and subcommand filter from the plan edge cases


### FINDING_2: Implement CI vendor launchers are omitted from timing pins and scanner coverage
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-dyn-timing-telemetry
- **Severity**: important
- **Concern**: A1/A2 cover Step 2 vendor timing rows but omit one or more implement CI-fix vendor launchers that also emit `record-vendor-task` rows. Those launchers can still inherit ambient `LARCH_TIMING_SKILL=design`, while the scanner may pass because the files are outside its scanned set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add scripts/launch-codex-ci.sh, scripts/launch-cursor-ci.sh, and scripts/launch-claude-ci.sh to the A1 scanned set and pin their record-vendor-task calls with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement; keep launch-review.sh excluded
  - From Codex-Innovation: Add these two CI launchers to the A1 scanned set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to their record-vendor-task lines
  - From Codex-dyn-timing-telemetry: Add scripts/launch-codex-ci.sh and scripts/launch-cursor-ci.sh to the A1 scanner list and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to their record-vendor-task command lines; keep review-only launch-review.sh excluded


### FINDING_3: Monitor-level wait fallthrough test is unreachable from production poll path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `poll_ci` loops while `decision.action == wait` and only returns non-wait or timeout bail decisions, so a monitor-level test expecting `monitor()` to handle `action=wait` from `poll_ci` would target dead behavior from the public entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Drop wait fallthrough from monitor-level B targets; keep wait coverage in test_decide_parity_table (already has pending/0-behind→wait) or test poll_ci loop behavior if needed


### FINDING_4: Single status-gather error does not reach decide error bail through monitor path
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-ci-monitor-outcomes
- **Severity**: important
- **Concern**: `poll_ci` does not pass a single `status=error` through to `decide()` on the production monitor path. It rewrites gather-status errors to pending until consecutive failures reach the bailout threshold, so a monitor Outcome test for immediate decide-level error bail would not match live behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reframe B error-path test as monitor Outcome after three consecutive status errors (STALLED with consecutive-failure bail_reason), or omit as duplicate of test_decide_parity_table / existing poll_ci bail tests
  - From Cursor-dyn-ci-monitor-outcomes: Drop candidate 1 for this SIMPLE batch; keep already_merged monitor test plus one decide parity row for an unknown status


### FINDING_5: A3 workflow_path grep can false-fail on test fixtures
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The A3 negative grep for `workflow_path` lacks an explicit production file list, so broad implement-tree scanning can match test fixtures and fail on non-production references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin the same explicit production .sh set used for A1 timing scan (exclude test-*.sh) for the workflow_path read assertion; keep HARD/SIMPLE pins limited to run-step2-dispatch.sh and step2-implement.sh as already stated


### FINDING_6: A1/A2 commit ordering can create a transient failing scanner
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If the A1 scanner lands before A2 pins, the scanner will flag currently unpinned implement launcher `record-vendor-task` lines and fail until A2 lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: State in Approach that A2 must commit before A1, or land A1+A2 in one commit; keep Failure modes note that the scanner must pass only after A2 pins


### FINDING_7: Unknown-status wait candidate is not valid bash parity or terminal monitor coverage
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-ci-monitor-outcomes
- **Severity**: important
- **Concern**: B includes or implies an unknown-status wait candidate, but bash rejects unknown CI statuses instead of treating them as wait. Adding that test would lock in Python-only behavior and distract from the intended focused monitor-level terminal Outcome coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Drop the unknown-status wait candidate from section B; keep only genuinely uncovered monitor outcomes such as already_merged → Outcome.OK and CI status error bail → terminal Outcome.STALLED
  - From Codex-Requirements: Constrain B to runner-backed monitor() tests for genuinely uncovered terminal outcomes, such as already_merged -> Outcome.OK and status-gather error bail -> Outcome.STALLED; drop unknown-status fallthrough unless a real monitor-reachable terminal Outcome is identified
  - From Codex-dyn-ci-monitor-outcomes: Drop the unknown-status candidate from the plan; keep only genuinely uncovered valid monitor outcomes such as already_merged OK and CI status error bail outcome


### FINDING_8: Bash quiet-log truncate contract is missing from authoritative docs
- **Reviewer(s)**: Codex-dyn-quiet-log-docs
- **Severity**: important
- **Concern**: D3 documents Python append-forensics behavior but does not update the authoritative bash quiet-log contract to state that bash quiet logs are truncated at initialization, leaving readers with an undocumented divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-quiet-log-docs: Add a surgical D3 prose update to scripts/lib-quiet.md saying larch_quiet_init truncates the selected bash quiet log before redirecting stdout/stderr; use truncate-per-initialization wording consistently and keep it docs/comment-only

