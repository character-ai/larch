### OOS_1:
- **Description**: Fixed-path A1 scanner will drift when new implement timing call sites land outside the list. Scenario: The next timing-ledger.sh or timing-report.sh added under implement without updating the scanner array silently evades the general pin guard
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh:13-22
- **Phase**: design

