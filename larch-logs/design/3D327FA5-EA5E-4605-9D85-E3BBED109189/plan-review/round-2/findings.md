### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh (planned A1 awk scanner)
- **Concern**: Failure-modes text reuses Invariant B `scripts/timing-ledger.sh` index literals but half the scanned production emitters use `$SCRIPT_DIR/timing-ledger.sh` / `$SCRIPT_DIR/timing-report.sh`. Scenario: Scanner modeled literally on `test-implement-timing-rehydration.sh` never flags unpinned marks in `implement-bootstrap.sh`, `implement-finalize.sh`, `refresh-run-logs.sh`, `step-telemetry-mark.sh`, or `run-relevant-checks-captured.sh`, defeating A1 for those surfaces
- **Proposed resolution**: In the A1 awk, treat any line with `timing-ledger.sh` plus `mark` or `record-vendor-task` (exclude `dump`) or any `timing-report.sh` line as a timing line; require `LARCH_TIMING_SKILL=implement` on that same line; do not require the `scripts/` path prefix from the SKILL.md fence harness

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:17-24; scripts/launch-codex-ci.sh:247-254; scripts/launch-cursor-ci.sh:230-237; scripts/launch-claude-ci.sh:192-199
- **Concern**: A1 omits implement CI launchers that emit record-vendor-task rows, so A2 fixes Step 2 vendor rows but leaves Step 8 CI-fix vendor rows exposed to the same ambient LARCH_TIMING_SKILL pollution. Scenario: An /implement run started from a polluted design shell can still tag codex/cursor/claude CI-fix timing rows as design, and the new scanner would pass because those known implement production emitters are not in its file set
- **Proposed resolution**: Add scripts/launch-codex-ci.sh, scripts/launch-cursor-ci.sh, and scripts/launch-claude-ci.sh to the A1 scanned set and pin their record-vendor-task calls with DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement; keep launch-review.sh excluded

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:442-443
- **Concern**: poll_ci never returns action=wait to monitor(). Scenario: Plan B candidate to assert monitor-level Outcome for decide() fallthrough wait is unreachable: poll_ci loops while decision.action==wait and only returns non-wait or timeout bail, so monitor()'s final branch for action=wait (lines 1564-1567) is dead from the public entrypoint
- **Proposed resolution**: Drop wait fallthrough from monitor-level B targets; keep wait coverage in test_decide_parity_table (already has pending/0-behind→wait) or test poll_ci loop behavior if needed

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:409-423
- **Concern**: poll_ci coerces single gather_status error before decide() error bail. Scenario: Plan B candidate to test monitor Outcome for decide() status=error→bail (reason at ci_monitor.py:141-145) does not match the live monitor() path: poll_ci increments ci_failures and rewrites error to pending until three consecutive failures, then bails with a different reason (lines 411-417)
- **Proposed resolution**: Reframe B error-path test as monitor Outcome after three consecutive status errors (STALLED with consecutive-failure bail_reason), or omit as duplicate of test_decide_parity_table / existing poll_ci bail tests

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh:383-388
- **Concern**: A3 workflow_path negative grep lacks an explicit production file list. Scenario: Broad implement-tree grep for workflow_path/HARD/SIMPLE can false-fail on skills/implement/scripts/test-*.sh (e.g. test-step2-dispatch.sh --workflow HARD, test-write-final-report.sh WORKFLOW_PATH fixtures)
- **Proposed resolution**: Pin the same explicit production .sh set used for A1 timing scan (exclude test-*.sh) for the workflow_path read assertion; keep HARD/SIMPLE pins limited to run-step2-dispatch.sh and step2-implement.sh as already stated

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-codex-ci.sh:247-254; scripts/launch-cursor-ci.sh:230-237
- **Concern**: A1/A2 timing-pin invariant omits implement CI vendor launchers. Scenario: /implement CI-fix or rebase-conflict paths can still inherit ambient LARCH_TIMING_SKILL=design and write Codex/Cursor CI vendor rows as design while the new scanner passes because these files are outside the scanned set
- **Proposed resolution**: Add these two CI launchers to the A1 scanned set and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to their record-vendor-task lines

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:118-130
- **Concern**: A1/A2 commit-order gap: separate commits but A1 scanner includes unpinned launchers. Scenario: A1 harness lands before A2 pins; scanner flags launch-codex-implement.sh and launch-cursor-implement.sh record-vendor-task lines (currently unpinned at scripts/launch-codex-implement.sh:230 and scripts/launch-cursor-implement.sh:169) and test-implement-structure.sh fails until A2 lands
- **Proposed resolution**: State in Approach that A2 must commit before A1, or land A1+A2 in one commit; keep Failure modes note that the scanner must pass only after A2 pins

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:59-63
- **Concern**: B lists decide() fallthrough wait for an unknown CI status as a candidate test. Scenario: scripts/ci-decide.sh:78-82 rejects any status outside pass|fail|pending|merged|error, so unknown-status wait is not a valid bash-parity scenario; adding it would lock Python-only fallthrough (python/ci_monitor.py:169) and expand B beyond the stated monitor-outcome gaps without protecting live behavior
- **Proposed resolution**: Drop the unknown-status wait candidate from section B; keep only genuinely uncovered monitor outcomes such as already_merged → Outcome.OK and CI status error bail → terminal Outcome.STALLED

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:55-65
- **Concern**: B still lists a decide-level unknown-status wait candidate even though B asks for focused monitor-level terminal Outcome tests. Scenario: Implementer may add a duplicate or non-terminal decide() test instead of the required small monitor-level coverage, adding scope while leaving B partly under-validated
- **Proposed resolution**: Constrain B to runner-backed monitor() tests for genuinely uncovered terminal outcomes, such as already_merged -> Outcome.OK and status-gather error bail -> Outcome.STALLED; drop unknown-status fallthrough unless a real monitor-reachable terminal Outcome is identified

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-timing-telemetry
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh (proposed A1 scanner)
- **Concern**: A1 scanner modeled on Invariant B `scripts/timing-ledger.sh` index misses `$SCRIPT_DIR` invocations. Scenario: Five scanned production scripts (`implement-bootstrap.sh`, `implement-finalize.sh`, `step-telemetry-mark.sh`, `refresh-run-logs.sh`, `run-relevant-checks-captured.sh`) invoke `"$SCRIPT_DIR/timing-ledger.sh"` / `"$SCRIPT_DIR/timing-report.sh"`; those lines lack the `scripts/timing-ledger.sh` substring, so a literal copy of `test-implement-timing-rehydration.sh` Invariant B would skip ~10 already-live implement timing call sites and give false CI safety while A2 pins only the `$PLUGIN_ROOT/scripts/…` launchers
- **Proposed resolution**: Match invocation lines on `timing-ledger.sh` / `timing-report.sh` plus subcommand (`mark`, `record-vendor-task`, or `timing-report.sh` flags), not the `scripts/timing-ledger.sh` path prefix; keep the same-line `LARCH_TIMING_SKILL=implement` check and subcommand filter from the plan edge cases

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-timing-telemetry
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-ci.sh:246-254; scripts/launch-cursor-ci.sh:229-237; scripts/ship-pr.sh:1784-1785,2511-2518,2902-2911
- **Concern**: A1/A2 omit the row-writing /implement CI vendor launchers from both the scanner set and the implement skill pins. Scenario: ship-pr.sh invokes the Codex/Cursor CI fix and conflict wrappers during /implement, but their record-vendor-task calls remain vulnerable to an inherited LARCH_TIMING_SKILL=design while the proposed scanner still passes
- **Proposed resolution**: Add scripts/launch-codex-ci.sh and scripts/launch-cursor-ci.sh to the A1 scanner list and apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to their record-vendor-task command lines; keep review-only launch-review.sh excluded

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-ci-monitor-outcomes
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:409-441
- **Concern**: poll_ci never passes status=error into decide() so the error→bail branch is not reachable on monitor()'s production path. Scenario: Candidate 1 would need a poll_ci monkeypatch and only re-checks bail→STALLED mapping already covered by test_monitor_timeout_bail_stalled; decide error→bail is already in test_decide_parity_table line 160
- **Proposed resolution**: Drop candidate 1 for this SIMPLE batch; keep already_merged monitor test plus one decide parity row for an unknown status

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-ci-monitor-outcomes
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ci_monitor.py:149-188; scripts/ci-decide.sh:78-82; python/ci_monitor.py:165-169
- **Concern**: The proposed unknown-status decide test is not a valid parity scenario. Scenario: scripts/ci-decide.sh rejects unknown statuses as invalid input, while python/ci_monitor.py currently falls through to wait; adding a test would lock in Python-only behavior and exceed the SIMPLE no-production-change scope
- **Proposed resolution**: Drop the unknown-status candidate from the plan; keep only genuinely uncovered valid monitor outcomes such as already_merged OK and CI status error bail outcome

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-quiet-log-docs
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:98-107,131-136; scripts/lib-quiet.sh:53-58,70-78; scripts/lib-quiet.md:14-17,39-44
- **Concern**: D3 documents Python append-forensics only in Python surfaces, while the bash quiet-log contract remains silent on the truncate rule that the new Python text cites. Scenario: Bash truncates the selected quiet log at each initialization, but after this PR readers would see the divergence asserted in python/README.md without the authoritative scripts/lib-quiet.md contract documenting the bash side
- **Proposed resolution**: Add a surgical D3 prose update to scripts/lib-quiet.md saying larch_quiet_init truncates the selected bash quiet log before redirecting stdout/stderr; use truncate-per-initialization wording consistently and keep it docs/comment-only
