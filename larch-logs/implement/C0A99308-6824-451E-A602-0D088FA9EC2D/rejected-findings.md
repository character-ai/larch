### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Initial-wait failure uses non-legacy diagnostic trailer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-caller-cutover-output.txt, dyn-retirement-hygiene-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: On `wait_reviewers` non-zero exit, the Python collector emits `collect-results: wait-reviewers exited <rc>` instead of the retired bash trailer `collect-agent-results.sh: wait-for-reviewers.sh exited <rc>`. Operator grep patterns, `collect-findings.sh` replay paths, and harness expectations keyed on the legacy string can miss real initial-wait fatals after cutover. No pytest pins the trailer on simulated `wait_reviewers` failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit the exact legacy trailer via `_diagnostic()` after relaying buffered wait diagnostics.
  - From dyn-caller-cutover-output.txt: Emit the legacy trailer string through `logging_util.diagnostic()` for parity (or update every consumer grep pin and run-log contract in the same change).
  - From dyn-retirement-hygiene-output.txt: Either restore the legacy diagnostic prefix for initial-wait fatals only (distinct from pre-wait timeout validation), or document the new prefix everywhere operators grep (including `SECURITY.md`, `docs/external-reviewers.md`) and add a pytest that asserts the exact trailer on simulated `wait_reviewers` non-zero exit.
  - From cursor-specialist-testing-output.txt: Monkeypatch `wait_reviewers` to return non-zero; assert exit 1, no `REVIEWER_FILE=` stdout, relayed stderr diagnostics and wait-exit trailer.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Bad `--timeout` pre-validation not proven to skip `wait_reviewers`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Acceptance #18 requires invalid `--timeout` values to fail before calling `wait_reviewers`. A refactor could reintroduce spurious wait side effects on `--timeout 0` or `--timeout abc` with no test failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monkeypatch `wait_reviewers` to fail if called; run `--timeout 0` and `--timeout abc`; expect exit 1 without invocation.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_13: Outer-launcher and `cmd_json_requires_outer_launcher` fail-closed behavior lacks pytest matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Beyond the missing-`CMD_JSON` case, review-shaped `CMD_JSON` without outer metadata could replay through `run-external-agent` and bypass launcher post-processing undetected. No pytest matrix covers outer-launcher replay, codex-exec path, and review-shaped fail-closed cases from the deleted retry harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest matrix for outer-launcher replay, codex-exec path, and review-shaped `CMD_JSON` fail-closed cases from deleted `test-collect-agent-retry.sh`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: `quiet_init()` tmpdir precedence misaligns with `lib-quiet.sh`
- **Reviewer(s)**: dyn-caller-cutover-output.txt
- **Severity**: important
- **Concern**: Python `quiet_init()` prefers `DESIGN_TMPDIR`, then `IMPLEMENT_TMPDIR`, then `TMPDIR`, and never considers `REVIEW_TMPDIR` or `RESEARCH_TMPDIR`. Bash `larch_quiet_default_log()` prefers `IMPLEMENT_TMPDIR`, then `REVIEW_TMPDIR`, then `DESIGN_TMPDIR`, then `RESEARCH_TMPDIR`. When `dispatch-with-waterfall.sh` invokes `agent collect-results --summary-only` without `LARCH_QUIET_DISABLE=1`, diagnostics can land in a stale design/implement session log instead of the active review tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-cutover-output.txt: Align `logging_util.quiet_init()` tmpdir precedence with `larch_quiet_default_log()` in `scripts/lib-quiet.sh`, including `REVIEW_TMPDIR` and `RESEARCH_TMPDIR`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Duplicated stderr-tail resolution in Python and shell
- **Reviewer(s)**: dyn-retirement-hygiene-output.txt
- **Severity**: important
- **Concern**: Collector stderr-tail resolution exists in both `collect_results.py` and `scripts/lib-failed-agent-stderr-tail.sh`. Live collection uses Python, but `collect-findings.sh` still calls the shell `resolve_collector_stderr_tail_file` during replay when `LARCH_QUIET_DISABLE=1`. Drift between implementations would change which tail operators see at collection time versus replay time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-hygiene-output.txt: Move the three helpers into one shared Python module (for example `review_dispatch.py` or a sibling), have `collect_results.py` import them, and either delete the shell collector-specific functions from `lib-failed-agent-stderr-tail.sh` with a thin Python CLI bridge for replay, or add a parity test that runs the same fixture through both paths and asserts identical tail selection.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Broader collector diagnostic prefix drift from bash parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Diagnostic messages use `collect-results:` instead of the legacy `collect-agent-results.sh:` prefix. Existing log triage and retired harness expectations for transient/invalid-exit messages no longer match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Centralize diagnostics under the legacy `collect-agent-results.sh:` prefix.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

