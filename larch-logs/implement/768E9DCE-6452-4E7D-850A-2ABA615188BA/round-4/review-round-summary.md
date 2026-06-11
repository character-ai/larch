# Review Round 4

- Mode: `diff`
- 11 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: timing harness-mark omits sentinel when child exec fails
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: timing harness-mark does not guarantee the required sentinel when the child command cannot be executed. subprocess.run raises FileNotFoundError for a missing executable, so python3 python/cli.py timing harness-mark --label smoke -- does-not-exist exits via traceback and prints no LARCH_HARNESS_TIMING line. Catch OSError around subprocess.run, map failures to shell-compatible exit codes, and print the sentinel in a finally path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: run-log refresh drops empty timing JSON reports
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Direct run-log refresh skips empty timing JSON reports. An early or degraded run with no timing marks returns {} and loses the timing-report batch on the Python path. Write the refresh JSON for any dict result, including {}.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: run-log renderer failure best-effort lacks required tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing plan-required test for renderer failure best-effort in _render_ledger_reports. A regression that stops timing refresh when token_report raises (or the reverse) would ship undetected because only the happy-path stub test exists. Add tests stubbing each renderer to raise; assert sibling JSON write and larch-log batch still occur when the other side succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: refresh-run-logs shell fixture misses python directory and dependencies
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: setup_plugin_stub copies report_tokens_cost.py into $root/python without creating that directory. make test-refresh-run-logs fails at the first setup_plugin_stub call before retained refresh-run-logs coverage runs. Create $root/python before copying, and copy or stub the Python CLI dependencies needed by render-run-summary.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_15: claude_sub fixture snapshot lacks required replay metadata
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The fixture writes only TRANSCRIPT_PATH, but token_claude_source now requires TRANSCRIPT_PATH, SESSION_DIR, and SESSION_UUID for snapshot replay. The claude_sub refresh case cannot render token-report-refresh.json, so its token-report assertion fails after setup proceeds. Add SESSION_DIR and SESSION_UUID to the snapshot and create the session directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.

### FINDING_2: token compute-pr-lines verb is not registered
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The migrated PR line-count CLI is registered as token compute-pr-line-counts instead of the planned token compute-pr-lines verb. python3 python/cli.py token compute-pr-lines --pr-number 1 returns unknown subcommand despite the implementation plan requiring that verb. Register compute-pr-lines and update call sites, keeping compute-pr-line-counts only as an internal alias if needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: tokens.py does not export planned cost helpers
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: tokens.py does not export the importable cost helpers required by the plan. import tokens; tokens.token_cost_from_args([...]) raises AttributeError because the implementation lives only in report_tokens_cost.py. Re-export or define CostBreakdown, token_cost_from_args, and render_cost_line_from_args in tokens.py while delegating to report_tokens_cost.py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Claude source snapshot replay accepts unsafe transcript paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Snapshot replay in token_claude_source accepts arbitrary TRANSCRIPT_PATH without containment or SESSION_UUID validation. A tampered LARCH_CLAUDE_SOURCE_FILE can aim token_report at any readable file (e.g. sensitive local data) while still returning complete metadata. Validate SESSION_UUID with _SAFE_SESSION_RE; resolve TRANSCRIPT_PATH and require it under SESSION_DIR or the Claude project directory before replay success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: TokenLedger can block or crash instead of failing open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: TokenLedger uses blocking flock with no timeout unlike TimingLedger bounded lock, and token mark/record_vendor catch only ValueError. A stale lock or OSError from I/O can hang or abort telemetry callers that expect fail-open behavior. Add bounded non-blocking flock handling and catch OSError in mark/record paths so write failures warn and return 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: timing telemetry-mark treats missing implement tmpdir as cwd
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: timing telemetry-mark treats missing --implement-tmpdir as Path('.') (cwd). Omitted or misparsed --implement-tmpdir causes telemetry to read cwd session-env.sh and write marks to wrong ledgers while exiting 0. Reject empty/missing --implement-tmpdir as immediate no-op; require non-empty absolute existing implement tmpdir before session-env reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: design timing reports ignore design_classification fallback
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design timing reports ignore design_classification when workflow_path is absent. Legacy or partial run-params.json files with design_classification=SIMPLE now publish workflow_path=unknown. Check design_classification after workflow_path or reuse gh.read_workflow_path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


