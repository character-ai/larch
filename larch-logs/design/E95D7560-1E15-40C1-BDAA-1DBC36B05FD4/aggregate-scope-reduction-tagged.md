### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:24-40
- **Concern**: [SCOPE-REDUCTION] The plan adds the policy-rejection poll hook inside shared `run_external_agent`, but lines 31-33 claim it is wired only through `launch_codex_exec_main`. Any caller that passes `stdout_path` to a Codex events file gets the hook; `launch-codex-ci`, review Codex, and `launch-codex-implement` also use `stdout_path=paths.events` in `python/agents.py`. That broadens exit timing and auth-retry behavior beyond the lint-fix stall the issue describes.. Scenario: Add an explicit opt-in flag on `run_external_agent` (for example `policy_rejection_fast_fail=False` by default) and pass it only from `launch_codex_exec_main`, or keep detection in `launch_codex_exec_main` after the shared wait returns instead of defaulting it on for every events-stream Codex lane.
- **Proposed resolution**:
