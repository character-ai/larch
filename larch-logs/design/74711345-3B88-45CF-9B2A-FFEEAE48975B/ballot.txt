### FINDING_1: Step 18 safety-net must not truncate `execution-issues.md` on any flush path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Reusing `flush_execution_issues()` for Step 18 `--no-truncate` / teardown safety-net is unsafe unless every truncate site is gated. The shared helper truncates on `already-flushed`, `no-records`, and successful `ok` paths (`issue_log.write_text("", ...)` at lines 121, 130, 138). Wiring Step 18 through it without guarding all three branches would clear stall-time diagnostics and break the append-only safety-net contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In every path that calls `issue_log.write_text("", ...)`, gate on `no_truncate`/safety-net mode; or implement a dedicated `flush_execution_issues_safety_net()` that mirrors `scripts/implement-finalize.sh:212-253` (sentinel + append only, never truncate).

### FINDING_2: Teardown safety-net drops run-log redaction for committed execution-issues batches
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Today's `_teardown_log_flush` uses `run_logs.render_execution_issues_batch`, which redacts bodies via `_redact_batch_payload` before NDJSON append. A planned safety-net path that reuses `write_execution_issues_records` embeds raw `execution-issues.md` text with no redaction (same as Step 7a flush, unlike the live teardown path). Stall-time Tool Failures can contain secrets; committed `execution-issues.ndjson` may retain them after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add redaction to the shared safety-net writer (mirror `_redact_batch_payload` fail-closed semantics) or call the existing `run_logs` record builder without `_should_flush_execution_issues` gating; cover with a pytest that asserts redacted tokens in the batch body.

### FINDING_3: Plan omits harness and contract updates for retired shell scripts (lint/CI breakage)
- **Reviewer(s)**: Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The port retires wrappers such as `step-8-ship.sh`, `flush-execution-issues.sh`, `lib-execution-issues.sh`, and `step-8-seed-initial.sh`, but surviving harness and contract files still reference them. After appending retired helpers to `python/migrated-scripts.tsv`, `make lint-retired-scripts` will still scan tracked files and fail. Separately, `test-harnesses-5` still runs `skills/implement/scripts/test-step-8-ship.sh` via the Makefile target at lines 740–741; deleting the wrapper without repointing leaves `make test-step-8-ship` / `make lint` broken even if `python/test_ship.py` gains coverage. `test-step-7a.sh` stubs and assertions still name `flush-execution-issues.sh` and copy `lib-execution-issues.sh`; `lib-implement-clone-tag.md` still documents `step-8-ship.sh` and `step-8-seed-initial.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: Makefile` (and pre-deletion parity list) to repoint `test-step-8-ship` to `python3 -m pytest python/test_ship.py -q -k step8` (or equivalent), retire `test-step-8-ship.sh`, and append it to `migrated-scripts.tsv`
  - From Codex-Generic: Add these files to the plan as updated or deleted. Retarget test-step-7a stubs and assertions to the Python execution-issues surface or delete the unused shell harness. Update or retire the clone-tag helper doc when the Python clone-tag helper supersedes the bash callers.

### FINDING_4: Step 7a port must preserve bash already-flushed branch split (sentinel-match vs batch-match)
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The proposed Step 7a flush behavior changes the sentinel `already-flushed` branch from no-truncate to truncate. Bash returns `already-flushed` without clearing `execution-issues.md` when the SHA sentinel already matches (lines 109–112), but truncates on batch/source-match `already-flushed` (lines 115–124). Python merges both into one condition that always truncates (lines 119–122). A retry can erase local diagnostics the current shell path preserves.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Preserve the branch split in the Python port: sentinel-match already-flushed returns without truncating, while batch/source-match, no-records, and ok may keep the current clearing behavior. Add tests for both already-flushed cases.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/execution_issues.py:119-139
- **Concern**: [SCOPE-REDUCTION] Step 18 append-only flush must never call shared truncate branches. Scenario: Plan allows `--no-truncate` on shared `flush_execution_issues()`; today `already-flushed`, `no-records`, and `ok` all call `issue_log.write_text("")`. Guarding only the success path still clears stall-time Tool Failures on idempotent teardown replay.
- **Proposed resolution**: Prefer a dedicated `flush_execution_issues_safety_net()` mirroring bash `flush_execution_issues_safety_net()` (append via `run-log append` only). If a flag is kept, gate every `issue_log.write_text("", ...)` site.
