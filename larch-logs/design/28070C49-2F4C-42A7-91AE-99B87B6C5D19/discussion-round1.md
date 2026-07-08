## Decision 1: Secondary cleanup scope
- **Question**: Should the plan include the `run_logs.py` attempt-counter label fix?
- **Resolution**: Yes — include the secondary cleanup alongside the primary fix.
- **Source**: user

## Decision 2: Backward compatibility for non-JSON lines
- **Question**: Should the JSON-line parser skip lines that fail to parse?
- **Resolution**: Skip non-JSON lines silently (no kill). This avoids false kills during startup noise and preserves robustness.
- **Source**: codebase (the events file is raw stdout; non-JSON lines can appear during Codex startup)

## Decision 3: Regression test scope
- **Question**: What tests must be updated or added?
- **Resolution**: Update existing `test_run_external_agent_codex_policy_rejection_fast_fails` and `test_launch_codex_exec_fast_fails_policy_rejection` to emit JSON-line fixtures; add a new fixture where `aggregated_output` contains the trigger phrases but no genuine rejection event fires — must not kill.
- **Source**: codebase (existing tests in python/tests/agents/test_agents.py use plain-text stdout)
