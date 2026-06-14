### OOS_1:
- **Description**: `OUTER_LAUNCHER_WORKDIR` meta still records `Path.cwd()` after workdir resolution. Scenario: After the fix, `.meta` can continue to show the plugin-cache cwd while `codex exec -C` uses the resolved consumer root, recreating the misleading signal that motivated the original bug report.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/agents.py:3163
- **Phase**: design

