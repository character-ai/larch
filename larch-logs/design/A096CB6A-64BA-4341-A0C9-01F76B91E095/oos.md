### OOS_1: [OUT_OF_SCOPE] Add a regression check for the wrapper's python3-missing fail-open path
- **Description**: [OUT_OF_SCOPE] Add a regression check for the wrapper's python3-missing fail-open path. Scenario: The new thin Bash wrapper introduces a new failure mode when python3 is absent or the helper import fails. Without a test, the hook can start returning non-zero and turn an advisory hook into a hard failure.
- **Reviewer**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-hook-anti-read-poll.sh
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

