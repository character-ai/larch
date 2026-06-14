### OOS_1:
- **Description**: Makefile retarget lists five harness targets but no pytest -k shard selectors. Scenario: After consolidation into python/test_implement_dispatch.py, test-harnesses-9/14/18 may each run the full module repeatedly, inflating CI time without changing correctness
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:651-684
- **Phase**: design

