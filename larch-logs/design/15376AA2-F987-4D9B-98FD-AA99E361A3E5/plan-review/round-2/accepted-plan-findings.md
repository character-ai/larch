### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:75-320
- **Concern**: Planned wrapper-argv assertion has no viable capture path. Scenario: The harness stubs `codex` and records `codex-argv.txt`; `launch-codex-implement.sh` hardcodes `scripts/run-external-agent.sh` with no `RUN_EXTERNAL_AGENT_SH` override, so the planned “wrapper-argv capture” step cannot observe `--stderr-sink` at runtime and may be implemented as a no-op or a false check against codex argv
- **Proposed resolution**: Spell out the minimum test: e.g. `grep -Fq '--stderr-sink "$SIDECAR_LOG"'` on `scripts/launch-codex-implement.sh`, or add an opt-in env override plus a logging wrapper stub only if runtime argv proof is required


