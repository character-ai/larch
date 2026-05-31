### OOS_1:
- **Description**: Retry section documents `STDERR_SINK` / `--stderr-sink` replay but not `OUTER_LAUNCHER_RISK` / `--risk`, while `collect-agent-results.sh` already replays `--risk` (e.g. 638-655). Scenario: After launch-review starts writing caller risk into meta, operators reading only the collector doc see half the outer-retry argv contract
- **Reviewer**: Cursor-dyn-doc-sync
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/collect-agent-results.md:38; plan.txt:34-35
- **Phase**: design

