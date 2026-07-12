### OOS_1: [OUT_OF_SCOPE] Timing allowlist omits the new specialist task kinds.
- **Description**: [OUT_OF_SCOPE] Timing allowlist omits the new specialist task kinds.. Scenario: Dispatch emits cursor/codex phase timing kinds that record as unknown and produce telemetry warnings.
- **Reviewer**: Codex-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/timing.py:34-42
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Focus-area lint allowlists omit the new hand-maintained agent.
- **Description**: [OUT_OF_SCOPE] Focus-area lint allowlists omit the new hand-maintained agent.. Scenario: An enum regression in the new agent would evade lint and CI checks.
- **Reviewer**: Codex-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/voting.py:48-58; .github/workflows/ci.yaml:467-481
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Static timing allowlist omits compliance task kinds
- **Description**: [OUT_OF_SCOPE] Static timing allowlist omits compliance task kinds. Scenario: Compliance launches emit unknown task-kind warnings in timing telemetry
- **Reviewer**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/report/timing.py:22-43
- **Phase**: design



