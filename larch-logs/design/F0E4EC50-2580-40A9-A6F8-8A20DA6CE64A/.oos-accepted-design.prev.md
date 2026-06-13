### OOS_1:
- **Description**: Structure pins only grep for literal tokens, not teardown behavior. Scenario: The planned `contains` checks for `_loop_pid=`, `set -m`, and `kill -- -"$_loop_pid"` can pass while cleanup ordering is wrong (trap left armed after `wait`, `_loop_pid` cleared too late, or `set -e` restored before trap clear), which would not be caught before production.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:213-259
- **Phase**: design

