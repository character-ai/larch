### OOS_1: [OUT_OF_SCOPE] Task-split via a Codex-only prompt appendix alone stops Codex from issuing blocked `exec_command` verification and matches the issue's "split fix and verify" option without touching shared `run_external_agent` or auth-retry timing for CI, implement, and review lanes.
- **Description**: [OUT_OF_SCOPE] Task-split via a Codex-only prompt appendix alone stops Codex from issuing blocked `exec_command` verification and matches the issue's "split fix and verify" option without touching shared `run_external_agent` or auth-retry timing for CI, implement, and review lanes.. Scenario: The reported stall is reproduced when Codex attempts sandboxed shell verification; edit-only Codex instructions plus existing orchestrator recheck in `review_and_fix.py` address that root cause. Ship task-split first; add shared fast-fail only if telemetry shows Codex still disobeys the appendix.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:7-11
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Path-only fast-fail hook will also catch other Codex launchers.
- **Description**: [OUT_OF_SCOPE] Path-only fast-fail hook will also catch other Codex launchers.. Scenario: The shared `run_external_agent` predicate keys on `stdout_path` being the Codex events file, but `launch_codex_ci_main` and `launch_codex_implement_main` already pass `.events.jsonl` too (`python/agents.py:3804-3813` and `python/agents.py:5287-5295`). That broadens failure timing outside lint-fix and makes the stated `launch_codex_exec_main`-only wiring impossible without an extra opt-in discriminator.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:24-32
- **Phase**: design



