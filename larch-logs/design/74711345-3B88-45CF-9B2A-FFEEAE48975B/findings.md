### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/execution_issues.py:119-138
- **Concern**: Step 18 `--no-truncate` / safety-net must skip every truncate branch in shared flush code. Scenario: The plan prefers reusing `flush_execution_issues()` with `--no-truncate`, but the current function truncates on `already-flushed`, `no-records`, and successful `ok` paths. Wiring Step 18 through that helper without guarding all three branches would clear stall-time `execution-issues.md` despite the append-only contract.
- **Proposed resolution**: In every path that calls `issue_log.write_text("", ...)`, gate on `no_truncate`/safety-net mode; or implement a dedicated `flush_execution_issues_safety_net()` that mirrors `scripts/implement-finalize.sh:212-253` (sentinel + append only, never truncate).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/finalize.py:548-554
- **Concern**: Teardown safety-net switch drops run-log redaction. Scenario: `_teardown_log_flush` today calls `run_logs.render_execution_issues_batch`, which redacts bodies via `_redact_batch_payload` before NDJSON append. The planned `execution_issues` safety-net reuses `write_execution_issues_records`, which embeds raw `execution-issues.md` text with no redaction (same as Step 7a flush, but unlike the current live teardown path). Stall-time Tool Failures can contain secrets; committed `execution-issues.ndjson` may retain them after cutover.
- **Proposed resolution**: Add redaction to the shared safety-net writer (mirror `_redact_batch_payload` fail-closed semantics) or call the existing `run_logs` record builder without `_should_flush_execution_issues` gating; cover with a pytest that asserts redacted tokens in the batch body.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/execution_issues.py:119-139
- **Concern**: [SCOPE-REDUCTION] Step 18 append-only flush must never call shared truncate branches. Scenario: Plan allows `--no-truncate` on shared `flush_execution_issues()`; today `already-flushed`, `no-records`, and `ok` all call `issue_log.write_text("")`. Guarding only the success path still clears stall-time Tool Failures on idempotent teardown replay.
- **Proposed resolution**: Prefer a dedicated `flush_execution_issues_safety_net()` mirroring bash `flush_execution_issues_safety_net()` (append via `run-log append` only). If a flag is kept, gate every `issue_log.write_text("", ...)` site.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:740-741,Makefile:112
- **Concern**: Plan retires `step-8-ship.sh` but does not retarget the `test-step-8-ship` lint harness (`test-harnesses-5`) away from `skills/implement/scripts/test-step-8-ship.sh`. Scenario: After wrapper deletion the harness still execs the removed script; `make test-step-8-ship` / `make lint` fails even if `python/test_ship.py` gains coverage
- **Proposed resolution**: Add `### UPDATED: Makefile` (and pre-deletion parity list) to repoint `test-step-8-ship` to `python3 -m pytest python/test_ship.py -q -k step8` (or equivalent), retire `test-step-8-ship.sh`, and append it to `migrated-scripts.tsv`

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:236-302,494-795; skills/implement/scripts/test-step-7a.md:23; skills/implement/scripts/lib-implement-clone-tag.md:7
- **Concern**: The plan omits surviving harness and contract files that still name paths it retires. Scenario: After appending the retired helpers to python/migrated-scripts.tsv, make lint-retired-scripts will still scan these tracked files and fail on flush-execution-issues.sh, lib-execution-issues.sh, step-8-ship.sh, and step-8-seed-initial.sh
- **Proposed resolution**: Add these files to the plan as updated or deleted. Retarget test-step-7a stubs and assertions to the Python execution-issues surface or delete the unused shell harness. Update or retire the clone-tag helper doc when the Python clone-tag helper supersedes the bash callers.

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/flush-execution-issues.sh:109-124
- **Concern**: The proposed Step 7a flush behavior changes the sentinel already-flushed branch from no-truncate to truncate. Scenario: The bash port returns already-flushed without clearing execution-issues.md when the SHA sentinel already matches, but the plan asks to truncate on already-flushed; a retry can erase local diagnostics that the current shell path preserves
- **Proposed resolution**: Preserve the branch split in the Python port: sentinel-match already-flushed returns without truncating, while batch/source-match, no-records, and ok may keep the current clearing behavior. Add tests for both already-flushed cases.
