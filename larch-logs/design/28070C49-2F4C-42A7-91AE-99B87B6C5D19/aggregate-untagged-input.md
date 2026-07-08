### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/agents/test_agents.py
- **Concern**: Pre-write events fixture cannot survive launcher prep. Scenario: The plan has the new integration test pre-write `paths.events` before `run_external_agent`. `_prepare_run_external_agent_files` unlinks `stdout_path` and the child opens it with `"wb"`, so pre-written JSONL is deleted/truncated. A sleep-only stub leaves an empty events stream and the test passes without exercising nested `exit_code: 0` `aggregated_output`.
- **Proposed resolution**: Have the stub child print the nested `item.completed` JSONL line to stdout (events sink) on startup, then sleep; do not rely on pre-launch writes.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/agents/_run_external.py
- **Concern**: Strip-gate contract contradicts itself across plan sections. Scenario: Approach and failure mode 1 require preserving `aggregated_output` when `exit_code` is absent/null and output is non-empty. The Files section has `_strip_gated_aggregated_output` call `_should_strip_aggregated_output(node.get("exit_code"))` only, which invites stripping all `exit_code is None` rows and can hide in-progress command evidence.
- **Proposed resolution**: Make one contract: pass both `exit_code` and `aggregated_output` into `_should_strip_aggregated_output`, strip only on `exit_code == 0` or falsy empty output, and recurse with that rule. ### 1. [correctness] `python/tests/agents/test_agents.py` — integration test setup conflicts with launcher prep The planned false-positive regression test says to pre-write `paths.events` before launch. `run_external_agent` always removes that path in `_prepare_run_external_agent_files` (lines 218–224) and reopens it with `"wb"` (line 297). Pre-written JSONL never reaches the policy watcher. A sleep-only stub after that leaves an empty events file. The test would pass vacuously and would not guard the nested `exit_code: 0` false-positive path from FINDING_3. **Suggested revision:** Emit the production-shaped `item.completed` / `command_execution` JSONL from the stub child's stdout at startup, then sleep (same pattern as `test_run_external_agent_codex_policy_rejection_fast_fails`, but with nested JSON and both trigger families inside `aggregated_output`). ### 2. [correctness] `python/larch/agents/_run_external.py` — gated strip helper contract is internally inconsistent The Approach correctly gates stripping on `exit_code == 0` or (`exit_code is None` and empty `aggregated_output`), and failure mode 1 says absent `exit_code` with non-empty output must be preserved. The Files section narrows `_should_strip_aggregated_output` to `exit_code` only and has the walker call it without the output emptiness check. An implementer following the Files block literally could strip every `exit_code is None` node, including in-progress rows that already accumulated policy-rejection text. **Suggested revision:** Unify on one signature, e.g. `_should_strip_aggregated_output(exit_code, aggregated_output)`, and have `_strip_gated_aggregated_output` pass both fields from each dict that owns `aggregated_output`. --- **Accepted prior-round items:** The primary gated recursive sanitization, nested fixture shape, and preserve-on-non-zero paths look aligned with FINDING_1–3. The secondary retry-counter subtraction matches the issue's optional cleanup (FINDING_4 was rejected but the issue still asked for it). **Skipped as duplicate/low-legitimacy OOS:** sidecar/stderr scanning (OOS_2), blanket-strip alternative (OOS_3/OOS_4), and a standalone `append_failure_main` unit test (OOS_1) unless you want those filed separately.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/agents/test_agents.py
- **Concern**: Integration test pre-write of paths.events cannot work with run_external_agent stdout redirect. Scenario: run_external_agent opens stdout_path with mode wb (python/larch/agents/_run_external.py:297), which truncates paths.events on child launch; pre-writing the false-positive JSONL before launch leaves the watcher an empty file, so the test passes vacuously or still times out without exercising sanitized scan
- **Proposed resolution**: Have the long-sleep stub print the nested item.completed JSONL line (with exit_code 0 and trigger phrases in item.aggregated_output) to stdout, mirroring test_run_external_agent_codex_policy_rejection_fast_fails; keep poll_interval low and assert no early policy-rejection kill

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/agents/_run_external.py
- **Concern**: _strip_gated_aggregated_output must gate exit_code None on empty aggregated_output. Scenario: Plan requires strip only when exit_code is None and aggregated_output is empty, but the UPDATED walker calls _should_strip_aggregated_output(node.get("exit_code")) without reading aggregated_output; treating all None as strip-eligible can hide in-progress non-empty output if Codex ever streams partial bodies before completion
- **Proposed resolution**: In _strip_gated_aggregated_output, pop aggregated_output only when exit_code == 0, or when exit_code is None and aggregated_output is falsy; when exit_code key is absent, preserve per failure mode 1

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/agents/test_agents.py
- **Concern**: False-positive integration test cannot rely on pre-writing paths.events. Scenario: The planned test pre-writes JSONL to paths.events, then launches run_external_agent with stdout_path=paths.events. Popen opens that path with wb, which truncates the file before the child runs. A sleep-only stub leaves an empty events stream, so the watcher never scans trigger phrases and the test passes even without sanitization.
- **Proposed resolution**: Have the stub child print/flush the nested item.completed JSONL line to stdout (then sleep), matching test_run_external_agent_codex_policy_rejection_fast_fails. Optionally drop the pre-write step entirely. **1. [correctness] `python/tests/agents/test_agents.py` — integration test fixture delivery** The planned false-positive regression test says to pre-write `paths.events` and then run a long-sleep stub. `run_external_agent` opens `stdout_path` with `wb`, which truncates on launch (`python/larch/agents/_run_external.py` around line 297). A child that only sleeps never repopulates the file, so the policy watcher sees an empty stream and the test gives false confidence. **Suggested revision:** Emit the nested `item.completed` / `command_execution` JSONL from the stub child's stdout (with flush), then sleep; do not depend on a pre-write surviving launch.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/agents/test_agents.py:967-1000
- **Concern**: Planned false-positive integration test pre-writes paths.events before launch, but run_external_agent deletes stdout_path during prep. Scenario: _prepare_run_external_agent_files unlinks stdout_path (paths.events) before Popen, so a pre-written JSONL fixture is removed. A long-sleep stub that writes nothing leaves an empty events stream, the watcher never sees trigger phrases, and the test passes even without sanitization (vacuous green)
- **Proposed resolution**: Have the stub child emit the nested item.completed JSONL line (exit_code 0, trigger phrases inside item.aggregated_output) to stdout with flush before sleeping, or append that line after launch starts; do not rely on pre-writing paths.events
