### OOS_1: `voter_launcher_tool` still lacks `codex-*` prefix normalization
- **Description**: `voter_launcher_tool` still lacks `codex-*` prefix normalization. Scenario: After dispatch emits `codex-plan-fidelity` / `codex-pragmatism`, parse-rate diagnostics label the launcher as `voter parse-rate check (codex-plan-fidelity)` instead of `agent launch-review --tool codex`. Voting correctness is unaffected; only retry/diagnostic attribution drifts on the new live path.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/voting.py:1397-1400
- **Phase**: design



