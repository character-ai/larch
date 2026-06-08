### OOS_1:
- **Description**: Deleted harness drops LARCH_REPORT_TOKENS_REPO unsafe-slug subprocess coverage. Scenario: The plan retires skills/report-tokens/scripts/test-run-analysis-quiet.sh (exit-4 case at lines 104-118) but test_cli.py ported-wrapper cases only list bogus --skill and --plot-from; no python/ test currently covers LARCH_REPORT_TOKENS_REPO rejection
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:41-43
- **Phase**: design


Vote tally: YES=2 NO=0 JUDGE_ERROR=0 Result=accepted

### OOS_2:
- **Description**: Deleted quiet harness design-path parity not named in plan test_cli.py. Scenario: The retired harness asserts design --skill output includes ### HARD under foreign quiet env (test-run-analysis-quiet.sh:61-74); the planned report-tokens quiet subprocess case only exercises implement
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:41-42
- **Phase**: design

Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

