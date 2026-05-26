### OOS_1:
- **Description**: [OUT_OF_SCOPE] Flag parser can spin forever when `--issue` or `--repo` is the final argv. Scenario: With `set -u` but not `set -e`, `${2:-}` assigns empty and `shift 2` fails without consuming `$1`, so the while loop repeats and emits shift errors indefinitely
- **Reviewer**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/get-issue-state.sh:35-38
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2861
