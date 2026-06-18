# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_2: correctness: skills/implement/scripts/step-18.sh:217-223
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 18 safety-net RUN_ID resolution skips LARCH_RUN_ID and bootstrap fallbacks used elsewhere Deferred tracking or missing parent-issue.md with --run-id override: safety net uses session-id and appends to wrong implement/<run-id>/ NDJSON tree Resolve RUN_ID via same _first_nonempty chain as step8_seed_initial_main (parent-issue bootstrap-routing LARCH_RUN_ID session-env) before flush-safety-net
- **Suggested revision**: Address the concern above.


### FINDING_22: **risk-integration** `python/finalize.py:541-554` — Step 18 now runs two independent execution-issues safety nets on every teardown: `skills/implement/scripts/step-18.sh:221-225` calls `execution-issues flush-safety-net`, then `implement-finalize teardown` still invokes `_teardown_log_flush`, which calls `run_logs.render_execution_issues_batch` with `step_label="teardown"`. The plan required replacing that teardown path with in-process `execution_issues.flush_execution_issues_safety_net()`. The legacy renderer deduplicates on redacted-body `source_sha256` (`python/run_logs.py:1100-1105`), while the new helper hashes raw bodies (`python/execution_issues.py:83-84`), so post-Step-7a runs can append duplicate NDJSON rows for the same stall diagnostics under different `step`/`source` metadata. **Suggested fix:** Replace `run_logs.render_execution_issues_batch` in `_teardown_log_flush` with `execution_issues.flush_execution_issues_safety_net()` and remove the redundant pre-teardown call from `step-18.sh` once a single canonical path exists; add a `python/test_finalize.py` assertion that teardown does not call `render_execution_issues_batch`.
- **Reviewer**: dyn-safety-net-ledger-output.txt
- **Concern**: - **risk-integration** `python/finalize.py:541-554` — Step 18 now runs two independent execution-issues safety nets on every teardown: `skills/implement/scripts/step-18.sh:221-225` calls `execution-issues flush-safety-net`, then `implement-finalize teardown` still invokes `_teardown_log_flush`, which calls `run_logs.render_execution_issues_batch` with `step_label="teardown"`. The plan required replacing that teardown path with in-process `execution_issues.flush_execution_issues_safety_net()`. The legacy renderer deduplicates on redacted-body `source_sha256` (`python/run_logs.py:1100-1105`), while the new helper hashes raw bodies (`python/execution_issues.py:83-84`), so post-Step-7a runs can append duplicate NDJSON rows for the same stall diagnostics under different `step`/`source` metadata. **Suggested fix:** Replace `run_logs.render_execution_issues_batch` in `_teardown_log_flush` with `execution_issues.flush_execution_issues_safety_net()` and remove the redundant pre-teardown call from `step-18.sh` once a single canonical path exists; add a `python/test_finalize.py` assertion that teardown does not call `render_execution_issues_batch`.
- **Suggested revision**: Address the concern above.


