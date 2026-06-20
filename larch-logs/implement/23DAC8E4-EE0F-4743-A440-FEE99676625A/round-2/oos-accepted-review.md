### OOS_1: correctness: python/test_agents.py:2466-2488
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Implement failure test does not cover pre-existing .failure-diag masking sidecar merge. Test passes with only .diag seeded while production bug with pre-existing .failure-diag remains untested. Seed non-empty .failure-diag before _append_implement_launch_failure and assert sidecar content is merged and selected.
- **Suggested revision**: Address the concern above.


