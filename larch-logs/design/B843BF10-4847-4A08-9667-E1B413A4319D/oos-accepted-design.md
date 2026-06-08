### OOS_1:
- **Description**: Deleted harness drops LARCH_REPORT_TOKENS_REPO unsafe-slug subprocess coverage. Scenario: The plan retires skills/report-tokens/scripts/test-run-analysis-quiet.sh (exit-4 case at lines 104-118) but test_cli.py ported-wrapper cases only list bogus --skill and --plot-from; no python/ test currently covers LARCH_REPORT_TOKENS_REPO rejection
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/test_cli.py:41-43
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3739
